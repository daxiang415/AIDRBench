"""Development-only diagnostics for the mechanism value of advance notice."""

from __future__ import annotations

import json
import math
import multiprocessing
from collections import Counter
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from aidrbench.controllers.hourly import make_hourly_controller
from aidrbench.controllers.robust_mpc_spec import load_robust_mpc_specification
from aidrbench.data.frozen_scenarios import load_frozen_hourly_scenario
from aidrbench.data.splits import sha256_file
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv
from aidrbench.envs.hourly_config import load_hourly_environment_config
from aidrbench.evaluation.firm_flexibility import (
    FirmFlexibilityCriteria,
    derive_event_outcomes,
)
from aidrbench.evaluation.frozen_causal_certificate import (
    _controller_provenance,
    _discover_artifacts,
    _environment_document,
)
from aidrbench.evaluation.hourly_rollout import rollout_hourly_episode
from aidrbench.evaluation.non_anticipative import (
    validate_non_anticipative_frontier,
    validate_non_anticipative_notice_monotonicity,
)
from aidrbench.evaluation.pi_frontier import validate_pi_frontier

_TOLERANCE = 1e-6


def _criteria_from_frozen_config(
    document: Mapping[str, Any],
    *,
    reliability_target: float,
) -> FirmFlexibilityCriteria:
    config = load_hourly_environment_config(document)
    reward = config.reward
    return FirmFlexibilityCriteria(
        reliability_target=reliability_target,
        confidence_level=0.95,
        min_delivery_ratio=reward.min_delivery_ratio,
        min_interval_delivery_ratio=reward.min_delivery_ratio,
        max_deadline_miss_rate=reward.max_deadline_miss_rate,
        max_rebound_ratio=reward.max_rebound_ratio,
        min_window_peak_relief_fraction=reward.min_window_peak_relief_fraction,
        max_terminal_backlog_fraction=reward.max_terminal_backlog_fraction,
    )


def _empirical_pi_capacity(
    frontier: pd.DataFrame,
    *,
    scenario_hashes: set[str],
    duration_h: int,
    reliability_target: float,
) -> tuple[float, float]:
    selected = frontier.loc[
        (frontier["duration_h"].astype(int) == duration_h)
        & frontier["scenario_hash"].astype(str).isin(scenario_hashes)
    ]
    if selected["scenario_hash"].duplicated().any():
        raise ValueError("PI diagnostics contain duplicate scenario-duration rows")
    if set(selected["scenario_hash"].astype(str)) != scenario_hashes:
        raise ValueError("PI diagnostics do not cover the development scenario ensemble")
    allowed_failures = math.floor((1.0 - reliability_target) * len(selected) + 1e-12)
    capacities = selected["perfect_information_capacity_kw"].astype(float).sort_values()
    capacity_kw = float(capacities.iloc[allowed_failures])
    physical_upper_kw = float(selected["physical_dynamic_upper_bound_kw"].min())
    return capacity_kw, physical_upper_kw


def _service_margins(
    outcome: Any,
    criteria: FirmFlexibilityCriteria,
) -> dict[str, float]:
    return {
        "mean_delivery": float(outcome.delivery_ratio - criteria.min_delivery_ratio),
        "interval_delivery": float(
            outcome.minimum_interval_delivery_ratio - criteria.min_interval_delivery_ratio
        ),
        "deadline": float(criteria.max_deadline_miss_rate - outcome.deadline_miss_rate),
        "rebound": float(criteria.max_rebound_ratio - outcome.rebound_ratio),
        "window_relief": float(
            outcome.window_peak_relief_fraction
            - criteria.min_window_peak_relief_fraction
        ),
        "terminal_backlog": float(
            criteria.max_terminal_backlog_fraction - outcome.terminal_backlog_fraction
        ),
    }


def _eligible_pre_execution_work_gpu_h(
    snapshot: Any,
    frame: pd.DataFrame,
    *,
    notice_start: int,
    event_start: int,
) -> float:
    """Return a causal upper bound on work that notice could move earlier.

    Existing work is counted only if it remains queued when notice opens and
    is not due before the event. Work released later in the notice window is
    counted only when its deadline reaches the event. This excludes historical
    jobs that were released long ago but completed before notice opened.
    """

    if notice_start >= event_start:
        return 0.0
    notice_row = frame.loc[frame["hour"] == notice_start]
    if len(notice_row) != 1:
        raise RuntimeError("notice diagnostics could not locate the notice-start interval")
    remaining = np.asarray(
        notice_row["decision_remaining_by_deadline_gpu_h"].iloc[0],
        dtype="float64",
    )
    hours_until_event = event_start - notice_start
    existing_eligible = float(remaining[hours_until_event:].sum())
    future_eligible = sum(
        work_gpu_h
        for release, deadline, _, work_gpu_h in snapshot.work_groups
        if notice_start < release < event_start and deadline >= event_start
    )
    return float(existing_eligible + future_eligible)


def _scenario_mechanism_row(
    artifact: Any,
    *,
    duration_h: int,
    notice_h: int,
    requested_reduction_kw: float,
    criteria: FirmFlexibilityCriteria,
    controller_config: str | Path,
) -> tuple[dict[str, Any], pd.DataFrame]:
    specification = load_robust_mpc_specification(controller_config)
    document = _environment_document(
        artifact,
        duration_h=duration_h,
        notice_h=notice_h,
        requested_reduction_kw=requested_reduction_kw,
        event_id=0,
    )
    env = HourlyCommunityAIDemandResponseEnv(document)
    env.reset(seed=artifact.episode_seed)
    snapshot = env.full_horizon_planning_snapshot()
    controller = make_hourly_controller(
        "robust_mpc",
        robust_mpc_specification=specification,
    )
    frame, _ = rollout_hourly_episode(env, controller, seed=artifact.episode_seed)
    event = env.event_manifest[0]
    outcomes = derive_event_outcomes(
        frame,
        env.event_manifest,
        recovery_tolerance_gpu_h=(
            env.config.recovery_backlog_tolerance_fraction
            * env.power_model.flexible_capacity_gpu_h
        ),
    )
    if len(outcomes) != 1:
        raise RuntimeError("notice diagnostics require one event per development scenario")
    outcome = outcomes[0]
    notice_start = max(0, event.start_hour - notice_h)
    eligible_pre_execution_gpu_h = _eligible_pre_execution_work_gpu_h(
        snapshot,
        frame,
        notice_start=notice_start,
        event_start=event.start_hour,
    )
    pre_event_spare_gpu_h = sum(
        max(snapshot.capacity_gpu_h - snapshot.baseline_execution_gpu_h[hour], 0.0)
        for hour in range(notice_start, event.start_hour)
    )
    event_start_row = frame.loc[frame["hour"] == event.start_hour]
    if len(event_start_row) != 1:
        raise RuntimeError("notice diagnostics could not locate the event-start interval")
    margins = _service_margins(outcome, criteria)
    binding = sorted(
        name for name, margin in margins.items() if margin <= 1e-4
    )
    success, _ = outcome.success(criteria)
    row: dict[str, Any] = {
        "scenario_id": artifact.scenario_id,
        "scenario_hash": artifact.scenario_hash,
        "episode_seed": artifact.episode_seed,
        "duration_h": duration_h,
        "notice_h": notice_h,
        "fixed_capacity_kw": requested_reduction_kw,
        "eligible_pre_execution_work_gpu_h": eligible_pre_execution_gpu_h,
        "pre_event_spare_capacity_gpu_h": pre_event_spare_gpu_h,
        "event_start_backlog_gpu_h": float(
            event_start_row["decision_backlog_gpu_h"].iloc[0]
        ),
        "event_start_compute_debt_kwh": float(
            event_start_row["decision_compute_debt_kwh"].iloc[0]
        ),
        "fixed_capacity_success": success,
        "minimum_service_margin": min(margins.values()),
        "binding_constraints": ",".join(binding),
        **{f"service_margin_{name}": value for name, value in margins.items()},
    }
    schedule = frame.loc[
        :, ["hour", "executed_gpu_h", "action_fraction"]
    ].copy()
    schedule["scenario_hash"] = artifact.scenario_hash
    schedule["duration_h"] = duration_h
    schedule["notice_h"] = notice_h
    schedule["event_start_hour"] = event.start_hour
    return row, schedule


def _scenario_mechanism_worker(
    payload: tuple[str, int, int, float, dict[str, Any], str],
) -> tuple[dict[str, Any], pd.DataFrame]:
    artifact_path, duration_h, notice_h, capacity_kw, criteria_document, config_path = payload
    return _scenario_mechanism_row(
        load_frozen_hourly_scenario(artifact_path),
        duration_h=duration_h,
        notice_h=notice_h,
        requested_reduction_kw=capacity_kw,
        criteria=FirmFlexibilityCriteria(**criteria_document),
        controller_config=config_path,
    )


def _schedule_divergence(
    schedules: pd.DataFrame,
    *,
    duration_h: int,
) -> tuple[float, float]:
    selected = schedules.loc[schedules["duration_h"].astype(int) == duration_h]
    zero = selected.loc[selected["notice_h"].astype(int) == 0]
    six = selected.loc[selected["notice_h"].astype(int) == 6]
    paired = zero.merge(
        six,
        on=["scenario_hash", "duration_h", "hour", "event_start_hour"],
        suffixes=("_n0", "_n6"),
        validate="one_to_one",
    )
    if paired.empty:
        raise ValueError("notice diagnostics have no paired robust-MPC schedules")
    execution_difference = (
        paired["executed_gpu_h_n6"] - paired["executed_gpu_h_n0"]
    ).abs()
    pre_event = paired.loc[
        (paired["hour"] >= paired["event_start_hour"] - 6)
        & (paired["hour"] < paired["event_start_hour"])
    ]
    pre_event_difference = (
        pre_event["executed_gpu_h_n6"] - pre_event["executed_gpu_h_n0"]
    ).abs()
    return float(execution_difference.mean()), float(pre_event_difference.mean())


def compute_notice_mechanism_diagnostics(
    scenario_path: str | Path,
    *,
    pi_frontier_path: str | Path,
    na_frontier_path: str | Path,
    na_policies_path: str | Path,
    controller_config: str | Path,
    output_directory: str | Path,
    durations_h: Sequence[int] = (4, 8),
    notices_h: Sequence[int] = (0, 6),
    reliability_target: float = 0.95,
    workers: int = 1,
) -> dict[str, str | int]:
    """Build the preregistered development diagnostic without opening locked data."""

    durations = tuple(sorted(set(int(value) for value in durations_h)))
    notices = tuple(sorted(set(int(value) for value in notices_h)))
    if durations != (4, 8) or notices != (0, 6):
        raise ValueError("notice diagnostics are preregistered for H={4,8} and N={0,6}")
    if not math.isclose(reliability_target, 0.95, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("notice diagnostics are preregistered for q=0.95")
    artifacts = _discover_artifacts(scenario_path)
    path_labels = {part.lower() for part in Path(scenario_path).parts}
    if any(label.startswith("locked") or "locked_" in label for label in path_labels):
        raise ValueError("notice diagnostics may not read a locked scenario path")
    if any(
        str(artifact.metadata.get("dataset_role", "")).startswith("locked")
        for artifact in artifacts
    ):
        raise ValueError("notice diagnostics may not read locked scenario artifacts")
    criteria = _criteria_from_frozen_config(
        artifacts[0].config_document,
        reliability_target=reliability_target,
    )
    pi_path = Path(pi_frontier_path)
    na_path = Path(na_frontier_path)
    policies_path = Path(na_policies_path)
    pi = pd.read_parquet(pi_path)
    na = pd.read_parquet(na_path)
    policies = pd.read_parquet(policies_path)
    validate_pi_frontier(pi)
    validate_non_anticipative_frontier(na)
    validate_non_anticipative_notice_monotonicity(na)
    scenario_hashes = {artifact.scenario_hash for artifact in artifacts}
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    controller_specification = load_robust_mpc_specification(controller_config)
    controller_provenance = _controller_provenance(
        controller_config,
        controller_specification,
    )
    na_capacity_by_point: dict[tuple[int, int], float] = {}
    for duration_h in durations:
        for notice_h in notices:
            selected = na.loc[
                (na["duration_h"].astype(int) == duration_h)
                & (na["notice_h"].astype(int) == notice_h)
                & np.isclose(
                    na["ensemble_success_fraction_target"].astype(float),
                    reliability_target,
                )
            ]
            if len(selected) != 1:
                raise ValueError("NA diagnostics require exactly one row per H/N/q point")
            na_capacity_by_point[(duration_h, notice_h)] = float(
                selected["non_anticipative_capacity_kw"].iloc[0]
            )
    fixed_capacity_by_duration = {
        duration_h: min(
            na_capacity_by_point[(duration_h, notice_h)] for notice_h in notices
        )
        for duration_h in durations
    }
    mechanism_payloads = [
        (
            str(artifact.directory),
            duration_h,
            notice_h,
            fixed_capacity_by_duration[duration_h],
            criteria.as_dict(),
            str(controller_config),
        )
        for duration_h in durations
        for notice_h in notices
        for artifact in artifacts
    ]
    if workers == 1:
        mechanism_results = [
            _scenario_mechanism_worker(payload) for payload in mechanism_payloads
        ]
    else:
        with ProcessPoolExecutor(
            max_workers=min(workers, len(mechanism_payloads)),
            mp_context=multiprocessing.get_context("spawn"),
        ) as executor:
            mechanism_results = list(
                executor.map(_scenario_mechanism_worker, mechanism_payloads)
            )
    scenario_rows = [row for row, _ in mechanism_results]
    schedules = [schedule for _, schedule in mechanism_results]
    scenario_table = pd.DataFrame.from_records(scenario_rows)
    schedule_table = pd.concat(schedules, ignore_index=True)
    diagnostic_rows: list[dict[str, Any]] = []
    for duration_h in durations:
        pi_capacity_kw, physical_upper_kw = _empirical_pi_capacity(
            pi,
            scenario_hashes=scenario_hashes,
            duration_h=duration_h,
            reliability_target=reliability_target,
        )
        mean_divergence, pre_event_divergence = _schedule_divergence(
            schedule_table,
            duration_h=duration_h,
        )
        for notice_h in notices:
            na_capacity_kw = na_capacity_by_point[(duration_h, notice_h)]
            mechanism = scenario_table.loc[
                (scenario_table["duration_h"] == duration_h)
                & (scenario_table["notice_h"] == notice_h)
            ]
            binding_counts = Counter(
                name
                for value in mechanism["binding_constraints"].astype(str)
                for name in value.split(",")
                if name
            )
            point_policies = policies.loc[
                (policies["duration_h"].astype(int) == duration_h)
                & (policies["notice_h"].astype(int) == notice_h)
            ]
            information_node_count = int(
                point_policies[["hour", "information_node_id"]]
                .drop_duplicates()
                .shape[0]
            )
            diagnostic_rows.append(
                {
                    "duration_h": duration_h,
                    "notice_h": notice_h,
                    "reliability_target": reliability_target,
                    "pi_empirical_capacity_kw": pi_capacity_kw,
                    "na_capacity_kw": na_capacity_kw,
                    "robust_mpc_evaluated_capacity_kw": (
                        fixed_capacity_by_duration[duration_h]
                    ),
                    "robust_mpc_capacity_selected_on_development": False,
                    "physical_dynamic_upper_bound_kw": physical_upper_kw,
                    "pi_binding_constraints": (
                        "physical_dynamic_power"
                        if abs(pi_capacity_kw - physical_upper_kw) <= _TOLERANCE
                        else "work_conservation_or_service"
                    ),
                    "na_binding_constraints": (
                        "matched_pi_capacity"
                        if abs(
                            na_capacity_kw - pi_capacity_kw
                        )
                        <= _TOLERANCE
                        else "information_or_service"
                    ),
                    "fixed_comparison_capacity_kw": fixed_capacity_by_duration[duration_h],
                    "eligible_pre_execution_work_gpu_h_mean": float(
                        mechanism["eligible_pre_execution_work_gpu_h"].mean()
                    ),
                    "pre_event_spare_capacity_gpu_h_mean": float(
                        mechanism["pre_event_spare_capacity_gpu_h"].mean()
                    ),
                    "event_start_backlog_gpu_h_mean": float(
                        mechanism["event_start_backlog_gpu_h"].mean()
                    ),
                    "event_start_compute_debt_kwh_mean": float(
                        mechanism["event_start_compute_debt_kwh"].mean()
                    ),
                    "schedule_divergence_gpu_h_mean": mean_divergence,
                    "pre_event_schedule_divergence_gpu_h_mean": pre_event_divergence,
                    "information_node_count": information_node_count,
                    "fixed_capacity_success_fraction": float(
                        mechanism["fixed_capacity_success"].astype(bool).mean()
                    ),
                    "fixed_capacity_p05_service_margin": float(
                        mechanism["minimum_service_margin"].quantile(0.05)
                    ),
                    "binding_constraint_counts": json.dumps(
                        dict(sorted(binding_counts.items())),
                        sort_keys=True,
                    ),
                }
            )
    for duration_h in durations:
        index_by_notice = {
            int(row["notice_h"]): row
            for row in diagnostic_rows
            if int(row["duration_h"]) == duration_h
        }
        zero_row = index_by_notice[0]
        six_row = index_by_notice[6]
        for layer, column in (
            ("pi", "pi_empirical_capacity_kw"),
            ("na", "na_capacity_kw"),
        ):
            gain = float(six_row[column]) - float(zero_row[column])
            zero_row[f"{layer}_notice_gain_kw"] = gain
            six_row[f"{layer}_notice_gain_kw"] = gain
        service_margin_gain = float(six_row["fixed_capacity_p05_service_margin"]) - float(
            zero_row["fixed_capacity_p05_service_margin"]
        )
        zero_row["robust_mpc_service_margin_notice_gain"] = service_margin_gain
        six_row["robust_mpc_service_margin_notice_gain"] = service_margin_gain
        success_gain = float(six_row["fixed_capacity_success_fraction"]) - float(
            zero_row["fixed_capacity_success_fraction"]
        )
        zero_row["robust_mpc_success_fraction_notice_gain"] = success_gain
        six_row["robust_mpc_success_fraction_notice_gain"] = success_gain
        node_split = int(six_row["information_node_count"]) - int(
            zero_row["information_node_count"]
        )
        zero_row["information_node_split_count"] = node_split
        six_row["information_node_split_count"] = node_split
    diagnostics = pd.DataFrame.from_records(diagnostic_rows)
    diagnostics_path = output / "notice_mechanism_diagnostics.parquet"
    scenario_path_out = output / "notice_mechanism_scenarios.parquet"
    schedules_path = output / "notice_mechanism_schedules.parquet"
    manifest_path = output / "notice_mechanism_diagnostics.json"
    diagnostics.to_parquet(diagnostics_path, index=False)
    scenario_table.to_parquet(scenario_path_out, index=False)
    schedule_table.to_parquet(schedules_path, index=False)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "dataset_role": "development_mechanism_diagnostic",
                "locked_data_read": False,
                "design": {
                    "durations_h": list(durations),
                    "notices_h": list(notices),
                    "reliability_target": reliability_target,
                    "robust_mpc_capacity_mode": (
                        "fixed_common_minimum_NA_capacity_no_development_controller_selection"
                    ),
                    "scenario_workers": workers,
                    "zero_notice_gain_is_valid": True,
                },
                "definitions": {
                    "eligible_pre_execution_work": (
                        "causal upper bound: residual work at notice opening plus "
                        "later notice-window arrivals, restricted to deadlines at "
                        "or after event start; historical completed work is excluded"
                    ),
                    "pre_event_spare_capacity": (
                        "flexible GPU-hour capacity minus no-control baseline "
                        "execution in the notice window"
                    ),
                    "schedule_divergence": (
                        "paired mean absolute execution difference between N=0 "
                        "and N=6 at one fixed capacity"
                    ),
                    "fixed_comparison_capacity": (
                        "minimum existing NA capacity across N=0 and N=6 for each H; "
                        "the controller capacity is not selected on development"
                    ),
                    "planning_binding_constraints": (
                        "reported as active-bound diagnostics; PI physical-bound "
                        "equality and NA matched-PI equality are exact within 1e-6 kW"
                    ),
                },
                "scenario_hashes": sorted(scenario_hashes),
                "inputs": {
                    "pi_frontier": {"path": str(pi_path), "sha256": sha256_file(pi_path)},
                    "na_frontier": {"path": str(na_path), "sha256": sha256_file(na_path)},
                    "na_policies": {
                        "path": str(policies_path),
                        "sha256": sha256_file(policies_path),
                    },
                    "controller_provenance": controller_provenance,
                },
                "outputs": {
                    "diagnostics": str(diagnostics_path),
                    "scenario_mechanisms": str(scenario_path_out),
                    "paired_schedules": str(schedules_path),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "manifest": str(manifest_path),
        "diagnostics": str(diagnostics_path),
        "scenario_mechanisms": str(scenario_path_out),
        "paired_schedules": str(schedules_path),
        "diagnostic_point_count": len(diagnostics),
    }
