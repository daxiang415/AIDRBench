"""Independent causal-capacity selection and certification on frozen scenarios."""

from __future__ import annotations

import copy
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from aidrbench.controllers.hourly import make_hourly_controller
from aidrbench.data.frozen_scenarios import (
    FrozenHourlyScenario,
    load_frozen_hourly_scenario,
)
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv
from aidrbench.evaluation.firm_flexibility import (
    FirmFlexibilityCriteria,
    derive_event_outcomes,
    event_outcomes_frame,
    wilson_lower_bound,
)
from aidrbench.evaluation.hourly_rollout import rollout_hourly_episode


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
    if len({artifact.scenario_hash for artifact in artifacts}) != len(artifacts):
        raise ValueError("causal certificate scenarios must have unique hashes")
    return artifacts


def _environment_document(
    artifact: FrozenHourlyScenario,
    *,
    duration_h: int,
    notice_h: int,
    requested_reduction_kw: float,
    event_id: int,
) -> dict[str, Any]:
    document = copy.deepcopy(artifact.config_document)
    raw_scenario = document.get("scenario")
    scenario = dict(raw_scenario) if isinstance(raw_scenario, Mapping) else {}
    scenario.update(
        {
            "frozen_path": str(artifact.directory),
            "frozen_event_ids": [event_id],
            "frozen_event_notice_hours": notice_h,
        }
    )
    # A replay is an ordinary read of an already authorized artifact, not a
    # second attempt to open a locked scenario generator.
    scenario.pop("locked_set", None)
    scenario.pop("locked_ood", None)
    scenario.pop("preregistration_manifest", None)
    document["scenario"] = scenario
    raw_dr = document.get("dr")
    if not isinstance(raw_dr, Mapping):
        raise ValueError("frozen scenario environment config is missing a dr mapping")
    dr = dict(raw_dr)
    dr.update(
        {
            "source": "configured",
            "events_path": None,
            "event_duration_hours": duration_h,
            "event_notice_hours": notice_h,
            "event_reduction_kw": requested_reduction_kw,
            "event_duration_choices": None,
            "event_notice_choices": None,
            "event_reduction_fraction_range": None,
            "event_start_jitter_hours": 0,
        }
    )
    document["dr"] = dr
    return document


def _stable_reference_peak_kw(artifacts: Sequence[FrozenHourlyScenario]) -> float:
    peaks = {
        float(artifact.metadata["scenario_bases"]["reference_mix_operating_peak_kw"])
        for artifact in artifacts
    }
    if len(peaks) != 1:
        raise ValueError("causal certificate scenarios must share one reference DC peak")
    return peaks.pop()


def evaluate_frozen_causal_candidate(
    artifacts: Sequence[FrozenHourlyScenario],
    *,
    duration_h: int,
    notice_h: int,
    requested_reduction_kw: float,
    criteria: FirmFlexibilityCriteria,
    event_id: int = 0,
) -> tuple[pd.DataFrame, dict[str, float | int | bool]]:
    """Evaluate one fixed robust-MPC capacity without fitting on the artifacts."""

    if not artifacts:
        raise ValueError("causal candidate evaluation needs frozen scenarios")
    if duration_h <= 0 or notice_h < 0:
        raise ValueError("duration must be positive and notice must be non-negative")
    if not math.isfinite(requested_reduction_kw) or requested_reduction_kw < 0.0:
        raise ValueError("requested_reduction_kw must be finite and non-negative")
    controller = make_hourly_controller("robust_mpc")
    rows: list[pd.DataFrame] = []
    for artifact in artifacts:
        if event_id not in {int(event["event_id"]) for event in artifact.events}:
            raise ValueError(f"scenario {artifact.scenario_id} has no event ID {event_id}")
        document = _environment_document(
            artifact,
            duration_h=duration_h,
            notice_h=notice_h,
            requested_reduction_kw=requested_reduction_kw,
            event_id=event_id,
        )
        env = HourlyCommunityAIDemandResponseEnv(document)
        frame, _ = rollout_hourly_episode(env, controller, seed=artifact.episode_seed)
        event_outcomes = derive_event_outcomes(
            frame,
            env.event_manifest,
            recovery_tolerance_gpu_h=(
                env.config.recovery_backlog_tolerance_fraction
                * env.power_model.flexible_capacity_gpu_h
            ),
        )
        table = event_outcomes_frame(event_outcomes, criteria)
        if len(table) != 1:
            raise RuntimeError("primary causal certificate requires one event per scenario")
        table.insert(0, "scenario_id", artifact.scenario_id)
        table.insert(1, "scenario_hash", artifact.scenario_hash)
        table.insert(2, "episode_seed", artifact.episode_seed)
        table.insert(3, "controller", "robust_mpc")
        table.insert(4, "candidate_reduction_kw", requested_reduction_kw)
        table["duration_h"] = duration_h
        table.insert(5, "notice_h", notice_h)
        rows.append(table)
    outcome_table = pd.concat(rows, ignore_index=True)
    success_count = int(outcome_table["success"].astype(bool).sum())
    trial_count = len(outcome_table)
    lower = wilson_lower_bound(success_count, trial_count, criteria.confidence_level)
    reference_peak_kw = _stable_reference_peak_kw(artifacts)
    summary: dict[str, float | int | bool] = {
        "duration_h": duration_h,
        "notice_h": notice_h,
        "candidate_reduction_kw": requested_reduction_kw,
        "candidate_fraction_of_reference_mix_peak": (requested_reduction_kw / reference_peak_kw),
        "success_count": success_count,
        "trial_count": trial_count,
        "empirical_success_fraction": success_count / trial_count,
        "wilson_lower_confidence_bound": lower,
        "certified": lower + 1e-12 >= criteria.reliability_target,
        "minimum_interval_delivery_ratio": float(
            outcome_table["minimum_interval_delivery_ratio"].min()
        ),
        "p95_deadline_miss_rate": float(outcome_table["deadline_miss_rate"].quantile(0.95)),
        "p95_rebound_ratio": float(outcome_table["rebound_ratio"].quantile(0.95)),
        "p05_window_peak_relief_fraction": float(
            outcome_table["window_peak_relief_fraction"].quantile(0.05)
        ),
    }
    return outcome_table, summary


def select_frozen_causal_capacities(
    scenario_path: str | Path,
    *,
    durations_h: Sequence[int],
    notices_h: Sequence[int],
    candidate_fractions: Sequence[float],
    criteria: FirmFlexibilityCriteria,
    output_directory: str | Path,
    event_id: int = 0,
) -> dict[str, str | int]:
    """Select fixed candidates on validation; this is not a certificate."""

    artifacts = _discover_artifacts(scenario_path)
    durations = tuple(sorted(set(int(value) for value in durations_h)))
    notices = tuple(sorted(set(int(value) for value in notices_h)))
    candidates = tuple(sorted(set(float(value) for value in candidate_fractions)))
    if not durations or any(value <= 0 for value in durations):
        raise ValueError("durations_h must contain positive integers")
    if not notices or any(value < 0 for value in notices):
        raise ValueError("notices_h must contain non-negative integers")
    if not candidates or any(not 0.0 <= value <= 1.0 for value in candidates):
        raise ValueError("candidate_fractions must be in [0, 1]")
    if candidates[0] != 0.0:
        raise ValueError("candidate_fractions must include 0.0 as the fail-safe selection")
    reference_peak_kw = _stable_reference_peak_kw(artifacts)
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    selection_rows: list[dict[str, float | int | bool]] = []
    diagnostic_rows: list[dict[str, float | int | bool]] = []
    for duration_h in durations:
        for notice_h in notices:
            point_rows: list[dict[str, float | int | bool]] = []
            for fraction in candidates:
                _, summary = evaluate_frozen_causal_candidate(
                    artifacts,
                    duration_h=duration_h,
                    notice_h=notice_h,
                    requested_reduction_kw=fraction * reference_peak_kw,
                    criteria=criteria,
                    event_id=event_id,
                )
                point_rows.append(summary)
                diagnostic_rows.append(summary)
            eligible = [
                row
                for row in point_rows
                if float(row["empirical_success_fraction"]) + 1e-12 >= criteria.reliability_target
            ]
            selected = eligible[-1] if eligible else point_rows[0]
            selection_rows.append(
                {
                    **selected,
                    "selected_on_validation_only": True,
                    "independent_certificate_pending": True,
                }
            )
    diagnostics = pd.DataFrame.from_records(diagnostic_rows)
    diagnostics_path = output / "validation_candidate_diagnostics.parquet"
    diagnostics.to_parquet(diagnostics_path, index=False)
    selection_path = output / "causal_selection.json"
    selection_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "capacity_layer": "causal_robust_mpc_reference",
                "selection_interpretation": (
                    "validation_empirical_selection_not_reliability_certificate"
                ),
                "controller": "robust_mpc",
                "criteria": criteria.as_dict(),
                "validation_scenario_hashes": [artifact.scenario_hash for artifact in artifacts],
                "reference_mix_operating_peak_kw": reference_peak_kw,
                "candidate_fractions": list(candidates),
                "selected_capacities": selection_rows,
                "diagnostics": str(diagnostics_path),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "selection": str(selection_path),
        "diagnostics": str(diagnostics_path),
        "selected_capacity_count": len(selection_rows),
    }


def certify_selected_frozen_causal_capacities(
    scenario_path: str | Path,
    *,
    selection_path: str | Path,
    output_directory: str | Path,
    event_id: int = 0,
) -> dict[str, str | int]:
    """Evaluate frozen validation selections once on independent locked-ID data."""

    artifacts = _discover_artifacts(scenario_path)
    selection = json.loads(Path(selection_path).read_text(encoding="utf-8"))
    if not isinstance(selection, Mapping) or selection.get("schema_version") != 1:
        raise ValueError("selection is not a frozen causal-selection artifact")
    if selection.get("controller") != "robust_mpc":
        raise ValueError("Nature mainline causal selection must use robust_mpc")
    validation_hashes = set(str(value) for value in selection["validation_scenario_hashes"])
    test_hashes = {artifact.scenario_hash for artifact in artifacts}
    if validation_hashes & test_hashes:
        raise ValueError("locked-ID scenarios overlap the validation selection set")
    criteria_raw = selection.get("criteria")
    if not isinstance(criteria_raw, Mapping):
        raise ValueError("selection has no frozen criteria")
    criteria = FirmFlexibilityCriteria(**dict(criteria_raw))
    selected = selection.get("selected_capacities")
    if not isinstance(selected, list) or not selected:
        raise ValueError("selection contains no capacities")
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, float | int | bool]] = []
    outcome_tables: list[pd.DataFrame] = []
    for row in selected:
        if not isinstance(row, Mapping):
            raise ValueError("selection contains a malformed capacity")
        outcomes, summary = evaluate_frozen_causal_candidate(
            artifacts,
            duration_h=int(row["duration_h"]),
            notice_h=int(row["notice_h"]),
            requested_reduction_kw=float(row["candidate_reduction_kw"]),
            criteria=criteria,
            event_id=event_id,
        )
        outcome_tables.append(outcomes)
        summaries.append(summary)
    summary_table = pd.DataFrame.from_records(summaries)
    outcomes_table = pd.concat(outcome_tables, ignore_index=True)
    summary_path = output / "causal_certificates.parquet"
    outcomes_path = output / "causal_certificate_outcomes.parquet"
    summary_table.to_parquet(summary_path, index=False)
    outcomes_table.to_parquet(outcomes_path, index=False)
    manifest_path = output / "causal_certificate.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "capacity_layer": "independent_causal_certificate",
                "controller": "robust_mpc",
                "selection": str(selection_path),
                "criteria": criteria.as_dict(),
                "locked_id_scenario_hashes": [artifact.scenario_hash for artifact in artifacts],
                "all_points_certified": bool(summary_table["certified"].all()),
                "summary": str(summary_path),
                "outcomes": str(outcomes_path),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "manifest": str(manifest_path),
        "summary": str(summary_path),
        "outcomes": str(outcomes_path),
        "certificate_count": len(summary_table),
    }
