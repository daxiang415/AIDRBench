"""Perfect-information power-duration frontiers on frozen scenarios."""

from __future__ import annotations

import copy
import json
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from aidrbench.controllers.hourly_oracle import solve_full_horizon_oracle
from aidrbench.data.frozen_scenarios import FrozenHourlyScenario, load_frozen_hourly_scenario
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv
from aidrbench.evaluation.firm_flexibility import (
    lower_tolerance_order_statistic_rank,
)
from aidrbench.evaluation.provenance import optimization_provenance


def _positive_durations(durations: Sequence[int]) -> tuple[int, ...]:
    if not durations:
        raise ValueError("PI frontier needs at least one duration")
    if any(isinstance(duration, bool) or not isinstance(duration, int) for duration in durations):
        raise ValueError("PI frontier durations must be positive integers")
    normalized = tuple(int(duration) for duration in durations)
    if any(duration <= 0 for duration in normalized):
        raise ValueError("PI frontier durations must be positive integers")
    if len(set(normalized)) != len(normalized):
        raise ValueError("PI frontier durations must be unique")
    return tuple(sorted(normalized))


def _environment_document(
    artifact: FrozenHourlyScenario,
    *,
    duration_h: int,
    event_id: int,
) -> dict[str, Any]:
    document = copy.deepcopy(artifact.config_document)
    raw_scenario = document.get("scenario")
    scenario = dict(raw_scenario) if isinstance(raw_scenario, dict) else {}
    scenario.update(
        {
            "frozen_path": str(artifact.directory),
            "frozen_event_ids": [event_id],
        }
    )
    document["scenario"] = scenario
    raw_dr = document.get("dr")
    if not isinstance(raw_dr, dict):
        raise ValueError("frozen scenario environment config is missing a dr mapping")
    dr = dict(raw_dr)
    # The artifact supplies starts, notices and request anchors.  The one
    # intentional variation in this frontier is the event duration.
    dr.update(
        {
            "source": "configured",
            "events_path": None,
            "event_duration_hours": duration_h,
            "event_duration_choices": None,
            "event_notice_choices": None,
            "event_reduction_fraction_range": None,
            "event_start_jitter_hours": 0,
        }
    )
    document["dr"] = dr
    return document


def solve_frozen_pi_frontier(
    artifact: FrozenHourlyScenario,
    *,
    durations_h: Sequence[int],
    event_id: int = 0,
) -> pd.DataFrame:
    """Solve a fresh, single-event perfect-information duration frontier.

    A frozen scenario carries all exogenous data.  Each row selects the same
    event anchor and changes only its duration.  The result is explicitly a
    perfect-information bound, not a causal or certified capacity.
    """

    durations = _positive_durations(durations_h)
    available_event_ids = {int(event["event_id"]) for event in artifact.events}
    if event_id not in available_event_ids:
        raise ValueError(f"frozen scenario does not contain event ID {event_id}")
    rows: list[dict[str, Any]] = []
    for duration_h in durations:
        document = _environment_document(
            artifact,
            duration_h=duration_h,
            event_id=event_id,
        )
        env = HourlyCommunityAIDemandResponseEnv(document)
        env.reset(seed=artifact.episode_seed)
        snapshot = env.full_horizon_planning_snapshot()
        reward = env.config.reward
        solution = solve_full_horizon_oracle(
            snapshot,
            min_delivery_ratio=reward.min_delivery_ratio,
            min_interval_delivery_ratio=reward.min_delivery_ratio,
            max_deadline_miss_rate=reward.max_deadline_miss_rate,
            max_rebound_ratio=reward.max_rebound_ratio,
            min_window_peak_relief_fraction=reward.min_window_peak_relief_fraction,
            max_terminal_backlog_fraction=reward.max_terminal_backlog_fraction,
        )
        physical_upper_bound_kw = (
            max(dict(snapshot.dynamic_kw_per_gpu_h_by_class).values())
            * snapshot.capacity_gpu_h
        )
        if solution.perfect_information_capacity_kw > physical_upper_bound_kw + 1e-6:
            raise RuntimeError("perfect-information solution exceeds the physical dynamic bound")
        rows.append(
            {
                "scenario_id": artifact.scenario_id,
                "scenario_hash": artifact.scenario_hash,
                "episode_seed": artifact.episode_seed,
                "event_id": event_id,
                "duration_h": duration_h,
                "capacity_layer": "perfect_information",
                "perfect_information_capacity_kw": solution.perfect_information_capacity_kw,
                "perfect_information_capacity_fraction_of_dynamic_range": (
                    solution.perfect_information_capacity_fraction_of_dynamic_range
                ),
                "physical_dynamic_upper_bound_kw": physical_upper_bound_kw,
                "minimum_mean_delivery_ratio": solution.minimum_mean_delivery_ratio_for_bound,
                "minimum_interval_delivery_ratio": (
                    solution.minimum_interval_delivery_ratio_for_bound
                ),
                "maximum_rebound_ratio": solution.maximum_rebound_ratio_for_bound,
                "minimum_window_relief_fraction": solution.minimum_window_relief_fraction_for_bound,
                "deadline_miss_gpu_h": solution.total_deadline_miss_gpu_h,
                "terminal_backlog_gpu_h": solution.terminal_backlog_gpu_h,
                "pcc_capacity_kw": snapshot.pcc_capacity_kw,
                "reference_mix_operating_peak_kw": (
                    snapshot.reference_mix_operating_peak_kw
                ),
                "worst_class_peak_kw": snapshot.worst_class_peak_kw,
                "actual_dc_peak_kw": env._full_dc_power_kw,
                "perfect_information_status": solution.status,
                "objective_solve_seconds": solution.objective_solve_seconds,
                "refinement_solve_seconds": solution.refinement_solve_seconds,
            }
        )
    result = pd.DataFrame.from_records(rows)
    validate_pi_frontier(result)
    return result


def validate_pi_frontier(frontier: pd.DataFrame) -> None:
    """Enforce physical and duration-monotonicity invariants before reporting."""

    required = {
        "scenario_hash",
        "event_id",
        "duration_h",
        "perfect_information_capacity_kw",
        "physical_dynamic_upper_bound_kw",
    }
    missing = sorted(required - set(frontier.columns))
    if missing:
        raise ValueError(f"PI frontier is missing columns: {missing}")
    if frontier.empty:
        raise ValueError("PI frontier is empty")
    if (frontier["perfect_information_capacity_kw"] < -1e-9).any():
        raise ValueError("PI frontier contains a negative capacity")
    if (
        frontier["perfect_information_capacity_kw"]
        > frontier["physical_dynamic_upper_bound_kw"] + 1e-6
    ).any():
        raise ValueError("PI frontier exceeds the physical dynamic-power bound")
    for _, group in frontier.groupby(["scenario_hash", "event_id"], sort=False):
        ordered = group.sort_values("duration_h")
        capacity = ordered["perfect_information_capacity_kw"].to_numpy()
        if len(capacity) > 1 and (capacity[1:] > capacity[:-1] + 1e-6).any():
            raise ValueError("PI frontier violates duration monotonicity")


def summarize_pi_firm_boundary(
    frontier: pd.DataFrame,
    *,
    reliability_targets: Sequence[float],
    confidence_level: float,
    nominal_flexibility_fraction: float,
) -> pd.DataFrame:
    """Aggregate scenario optima using exact nonparametric tolerance bounds.

    The capacity is selected as a one-sided order statistic whose population
    coverage and confidence are controlled by an exact binomial probability.
    This avoids reusing a data-selected candidate in a Wilson interval.
    """

    validate_pi_frontier(frontier)
    targets = tuple(sorted({float(value) for value in reliability_targets}))
    if not targets or any(not 0.0 < value < 1.0 for value in targets):
        raise ValueError("reliability_targets must contain values in (0, 1)")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be in (0, 1)")
    nominal_fraction = float(nominal_flexibility_fraction)
    if not 0.0 <= nominal_fraction <= 1.0:
        raise ValueError("nominal_flexibility_fraction must be in [0, 1]")
    required_columns = {
        "reference_mix_operating_peak_kw",
        "worst_class_peak_kw",
    }
    missing = sorted(required_columns - set(frontier.columns))
    if missing:
        raise ValueError(f"PI frontier is missing peak-definition columns: {missing}")

    rows: list[dict[str, float | int | bool | str | None]] = []
    for duration_h, group in frontier.groupby("duration_h", sort=True):
        if group["scenario_hash"].duplicated().any():
            raise ValueError("PI boundary needs one independent row per scenario and duration")
        reference_peaks = group["reference_mix_operating_peak_kw"].unique()
        worst_peaks = group["worst_class_peak_kw"].unique()
        if len(reference_peaks) != 1 or len(worst_peaks) != 1:
            raise ValueError("PI boundary scenarios must share stable peak definitions")
        reference_peak_kw = float(reference_peaks[0])
        worst_peak_kw = float(worst_peaks[0])
        nominal_kw = nominal_fraction * reference_peak_kw
        capacities = group["perfect_information_capacity_kw"].sort_values(
            ascending=True, ignore_index=True
        )
        trial_count = len(capacities)
        for reliability in targets:
            tolerance_rank = lower_tolerance_order_statistic_rank(
                trial_count,
                reliability,
                confidence_level,
            )
            estimable = tolerance_rank is not None
            if tolerance_rank is None:
                rank = None
                achieved_confidence = None
                capacity_kw = math.nan
            else:
                rank, achieved_confidence = tolerance_rank
                capacity_kw = float(capacities.iloc[rank - 1])
            rows.append(
                {
                    "capacity_layer": "perfect_information_tolerance_bound",
                    "statistical_method": (
                        "exact_binomial_nonparametric_lower_tolerance_bound"
                    ),
                    "duration_h": int(str(duration_h)),
                    "reliability_target": reliability,
                    "confidence_level": confidence_level,
                    "scenario_count": trial_count,
                    "tolerance_order_statistic_rank": rank,
                    "achieved_tolerance_confidence": achieved_confidence,
                    "estimable": estimable,
                    "sample_size_sufficient": estimable,
                    "perfect_information_firm_capacity_kw": capacity_kw,
                    "reference_mix_operating_peak_kw": reference_peak_kw,
                    "worst_class_peak_kw": worst_peak_kw,
                    "nominal_flexibility_fraction": nominal_fraction,
                    "nominal_flexibility_kw": nominal_kw,
                    "physical_gap_kw": nominal_kw - capacity_kw,
                    "physical_gap_fraction_of_reference_peak": (
                        (nominal_kw - capacity_kw) / reference_peak_kw
                    ),
                }
            )
    return pd.DataFrame.from_records(rows)


def _discover_artifacts(path: str | Path) -> list[FrozenHourlyScenario]:
    root = Path(path)
    if (root / "metadata.json").is_file():
        return [load_frozen_hourly_scenario(root)]
    if not root.is_dir():
        raise FileNotFoundError(f"frozen scenario path does not exist: {root}")
    artifacts = [
        load_frozen_hourly_scenario(child)
        for child in sorted(root.iterdir())
        if child.is_dir() and (child / "metadata.json").is_file()
    ]
    if not artifacts:
        raise ValueError(f"no frozen scenario artifacts found in: {root}")
    return artifacts


def compute_and_save_pi_frontier(
    scenario_path: str | Path,
    *,
    durations_h: Sequence[int],
    output_directory: str | Path,
    event_id: int = 0,
    reliability_targets: Sequence[float] = (),
    confidence_level: float = 0.95,
    nominal_flexibility_fraction: float = 0.50,
) -> dict[str, str | int]:
    """Compute and persist a hash-linked PI frontier for every supplied artifact."""

    artifacts = _discover_artifacts(scenario_path)
    frames = [
        solve_frozen_pi_frontier(
            artifact,
            durations_h=durations_h,
            event_id=event_id,
        )
        for artifact in artifacts
    ]
    frontier = pd.concat(frames, ignore_index=True)
    validate_pi_frontier(frontier)
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    frontier_path = output / "pi_frontier.parquet"
    boundary_path = output / "pi_firm_boundary.parquet"
    manifest_path = output / "pi_frontier.json"
    frontier.to_parquet(frontier_path, index=False)
    boundary = None
    if reliability_targets:
        boundary = summarize_pi_firm_boundary(
            frontier,
            reliability_targets=reliability_targets,
            confidence_level=confidence_level,
            nominal_flexibility_fraction=nominal_flexibility_fraction,
        )
        boundary.to_parquet(boundary_path, index=False)
    manifest_path.write_text(
        json.dumps(
            {
                "capacity_layer": "perfect_information",
                "event_id": event_id,
                "durations_h": list(_positive_durations(durations_h)),
                "scenario_count": len(artifacts),
                "scenario_hashes": [artifact.scenario_hash for artifact in artifacts],
                "frontier": str(frontier_path),
                "reliability_targets": [float(value) for value in reliability_targets],
                "confidence_level": confidence_level,
                "firm_boundary_statistical_method": (
                    "exact_binomial_nonparametric_lower_tolerance_bound"
                ),
                "nominal_flexibility_fraction": nominal_flexibility_fraction,
                "firm_boundary": str(boundary_path) if boundary is not None else None,
                "provenance": optimization_provenance(artifacts),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    result: dict[str, str | int] = {
        "scenario_count": len(artifacts),
        "row_count": len(frontier),
        "frontier": str(frontier_path),
        "manifest": str(manifest_path),
    }
    if boundary is not None:
        result["firm_boundary"] = str(boundary_path)
        result["firm_boundary_row_count"] = len(boundary)
    return result
