"""Independent causal-capacity selection and certification on frozen scenarios."""

from __future__ import annotations

import copy
import json
import math
import multiprocessing
import subprocess
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from aidrbench.controllers.hourly import make_hourly_controller
from aidrbench.controllers.robust_mpc_spec import (
    RobustMPCSpecification,
    load_robust_mpc_specification,
    robust_mpc_specification_sha256,
)
from aidrbench.data.frozen_scenarios import (
    FrozenHourlyScenario,
    load_frozen_hourly_scenario,
)
from aidrbench.data.splits import sha256_file
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv
from aidrbench.evaluation.firm_flexibility import (
    FirmFlexibilityCriteria,
    derive_event_outcomes,
    event_outcomes_frame,
    wilson_lower_bound,
)
from aidrbench.evaluation.hourly_rollout import rollout_hourly_episode

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_CONTROLLER_SOURCE_PATHS = (
    "src/aidrbench/controllers/robust_mpc_spec.py",
    "src/aidrbench/controllers/hourly.py",
    "src/aidrbench/evaluation/hourly_rollout.py",
    "src/aidrbench/evaluation/firm_flexibility.py",
    "src/aidrbench/evaluation/frozen_causal_certificate.py",
    "src/aidrbench/envs/community_ai_dr_env.py",
    "src/aidrbench/envs/hourly_config.py",
)


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(_REPOSITORY_ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("formal causal certification requires a readable Git commit") from exc
    commit = result.stdout.strip()
    if len(commit) != 40:
        raise RuntimeError("formal causal certification obtained an invalid Git commit")
    return commit


def _controller_provenance(
    controller_config: str | Path,
    specification: RobustMPCSpecification,
) -> dict[str, Any]:
    config_path = Path(controller_config)
    if not config_path.is_file():
        raise FileNotFoundError(f"controller config does not exist: {config_path}")
    source_hashes = {
        relative: sha256_file(_REPOSITORY_ROOT / relative)
        for relative in _CONTROLLER_SOURCE_PATHS
    }
    return {
        "normalized_specification": specification.as_dict(),
        "normalized_specification_sha256": robust_mpc_specification_sha256(specification),
        "controller_config_path": str(config_path),
        "controller_config_sha256": sha256_file(config_path),
        "git_commit": _git_commit(),
        "source_sha256": source_hashes,
    }


def _verify_controller_provenance(
    frozen: object,
    *,
    controller_config: str | Path,
) -> RobustMPCSpecification:
    """Recompute every formal-controller hash and fail closed on disagreement."""

    if not isinstance(frozen, Mapping):
        raise ValueError("selection has no frozen controller provenance")
    specification = load_robust_mpc_specification(controller_config)
    observed = _controller_provenance(controller_config, specification)
    required = {
        "normalized_specification",
        "normalized_specification_sha256",
        "controller_config_path",
        "controller_config_sha256",
        "git_commit",
        "source_sha256",
    }
    if set(frozen) != required:
        raise ValueError("frozen controller provenance has an unexpected field set")
    for key in (
        "normalized_specification",
        "normalized_specification_sha256",
        "controller_config_sha256",
        "git_commit",
        "source_sha256",
    ):
        if frozen.get(key) != observed[key]:
            raise ValueError(f"frozen controller specification mismatch: {key}")
    return specification


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
    controller_specification: RobustMPCSpecification,
    duration_h: int,
    notice_h: int,
    requested_reduction_kw: float,
    criteria: FirmFlexibilityCriteria,
    event_id: int = 0,
    workers: int = 1,
) -> tuple[pd.DataFrame, dict[str, float | int | bool]]:
    """Evaluate one fixed robust-MPC capacity without fitting on the artifacts."""

    if not artifacts:
        raise ValueError("causal candidate evaluation needs frozen scenarios")
    if duration_h <= 0 or notice_h < 0:
        raise ValueError("duration must be positive and notice must be non-negative")
    if not math.isfinite(requested_reduction_kw) or requested_reduction_kw < 0.0:
        raise ValueError("requested_reduction_kw must be finite and non-negative")
    if isinstance(workers, bool) or not isinstance(workers, int) or workers <= 0:
        raise ValueError("workers must be a positive integer")
    if workers == 1:
        records = [
            _evaluate_frozen_causal_artifact(
                artifact,
                controller_specification=controller_specification,
                duration_h=duration_h,
                notice_h=notice_h,
                requested_reduction_kw=requested_reduction_kw,
                criteria=criteria,
                event_id=event_id,
            )
            for artifact in artifacts
        ]
    else:
        payloads = [
            (
                str(artifact.directory),
                controller_specification.as_dict(),
                duration_h,
                notice_h,
                requested_reduction_kw,
                criteria.as_dict(),
                event_id,
            )
            for artifact in artifacts
        ]
        with ProcessPoolExecutor(
            max_workers=min(workers, len(payloads)),
            mp_context=multiprocessing.get_context("spawn"),
        ) as executor:
            records = list(executor.map(_evaluate_frozen_causal_artifact_worker, payloads))
    outcome_table = pd.DataFrame.from_records(records)
    success_count = int(outcome_table["success"].astype(bool).sum())
    trial_count = len(outcome_table)
    lower = wilson_lower_bound(success_count, trial_count, criteria.confidence_level)
    reference_peak_kw = _stable_reference_peak_kw(artifacts)
    summary: dict[str, float | int | bool] = {
        "duration_h": duration_h,
        "notice_h": notice_h,
        "reliability_target": criteria.reliability_target,
        "confidence_level": criteria.confidence_level,
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
        "p95_terminal_backlog_fraction": float(
            outcome_table["terminal_backlog_fraction"].quantile(0.95)
        ),
        "p05_window_peak_relief_fraction": float(
            outcome_table["window_peak_relief_fraction"].quantile(0.05)
        ),
    }
    return outcome_table, summary


def _evaluate_frozen_causal_artifact(
    artifact: FrozenHourlyScenario,
    *,
    controller_specification: RobustMPCSpecification,
    duration_h: int,
    notice_h: int,
    requested_reduction_kw: float,
    criteria: FirmFlexibilityCriteria,
    event_id: int,
) -> dict[str, Any]:
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
    controller = make_hourly_controller(
        "robust_mpc",
        robust_mpc_specification=controller_specification,
    )
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
    record = {str(key): value for key, value in table.iloc[0].to_dict().items()}
    return {
        "scenario_id": artifact.scenario_id,
        "scenario_hash": artifact.scenario_hash,
        "episode_seed": artifact.episode_seed,
        "controller": "robust_mpc",
        "candidate_reduction_kw": requested_reduction_kw,
        "notice_h": notice_h,
        "duration_h": duration_h,
        **record,
    }


def _evaluate_frozen_causal_artifact_worker(
    payload: tuple[str, dict[str, Any], int, int, float, dict[str, Any], int],
) -> dict[str, Any]:
    (
        artifact_path,
        specification_document,
        duration_h,
        notice_h,
        requested_reduction_kw,
        criteria_document,
        event_id,
    ) = payload
    return _evaluate_frozen_causal_artifact(
        load_frozen_hourly_scenario(artifact_path),
        controller_specification=load_robust_mpc_specification(specification_document),
        duration_h=duration_h,
        notice_h=notice_h,
        requested_reduction_kw=requested_reduction_kw,
        criteria=FirmFlexibilityCriteria(**criteria_document),
        event_id=event_id,
    )


def _evaluate_and_record_candidate(
    artifacts: Sequence[FrozenHourlyScenario],
    *,
    controller_specification: RobustMPCSpecification,
    duration_h: int,
    notice_h: int,
    fraction: float,
    reference_peak_kw: float,
    criteria: FirmFlexibilityCriteria,
    event_id: int,
    workers: int,
    point_rows: list[dict[str, float | int | bool]],
    diagnostic_rows: list[dict[str, float | int | bool]],
) -> dict[str, float | int | bool]:
    _, summary = evaluate_frozen_causal_candidate(
        artifacts,
        controller_specification=controller_specification,
        duration_h=duration_h,
        notice_h=notice_h,
        requested_reduction_kw=fraction * reference_peak_kw,
        criteria=criteria,
        event_id=event_id,
        workers=workers,
    )
    point_rows.append(summary)
    diagnostic_rows.append(summary)
    return summary


def select_frozen_causal_capacities(
    scenario_path: str | Path,
    *,
    controller_config: str | Path,
    durations_h: Sequence[int],
    notices_h: Sequence[int],
    candidate_fractions: Sequence[float],
    search: Literal["grid", "binary"] = "binary",
    binary_iterations: int = 8,
    criteria: FirmFlexibilityCriteria,
    output_directory: str | Path,
    event_id: int = 0,
    selection_dataset_role: Literal["validation", "development_diagnostic"] = "validation",
    workers: int = 1,
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
    if search not in {"grid", "binary"}:
        raise ValueError("search must be 'grid' or 'binary'")
    if selection_dataset_role not in {"validation", "development_diagnostic"}:
        raise ValueError("unsupported causal selection dataset role")
    if isinstance(binary_iterations, bool) or binary_iterations <= 0:
        raise ValueError("binary_iterations must be a positive integer")
    if search == "binary" and len(candidates) != 2:
        raise ValueError("binary search requires exactly two candidate-fraction bounds")
    controller_specification = load_robust_mpc_specification(controller_config)
    controller_provenance = _controller_provenance(
        controller_config,
        controller_specification,
    )
    reference_peak_kw = _stable_reference_peak_kw(artifacts)
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    selection_rows: list[dict[str, float | int | bool]] = []
    diagnostic_rows: list[dict[str, float | int | bool]] = []
    for duration_h in durations:
        for notice_h in notices:
            point_rows: list[dict[str, float | int | bool]] = []

            evaluate_fraction = partial(
                _evaluate_and_record_candidate,
                artifacts,
                controller_specification=controller_specification,
                duration_h=duration_h,
                notice_h=notice_h,
                reference_peak_kw=reference_peak_kw,
                criteria=criteria,
                event_id=event_id,
                workers=workers,
                point_rows=point_rows,
                diagnostic_rows=diagnostic_rows,
            )

            if search == "grid":
                for fraction in candidates:
                    evaluate_fraction(fraction=fraction)
            else:
                lower_fraction, upper_fraction = candidates
                lower_row = evaluate_fraction(fraction=lower_fraction)
                lower_is_eligible = (
                    float(lower_row["empirical_success_fraction"]) + 1e-12
                    >= criteria.reliability_target
                )
                if not lower_is_eligible:
                    if selection_dataset_role == "validation":
                        raise RuntimeError(
                            "zero-capacity fail-safe candidate is not service-feasible"
                        )
                else:
                    upper_row = evaluate_fraction(fraction=upper_fraction)
                    upper_is_eligible = (
                        float(upper_row["empirical_success_fraction"]) + 1e-12
                        >= criteria.reliability_target
                    )
                    if not upper_is_eligible:
                        for _ in range(binary_iterations):
                            midpoint = 0.5 * (lower_fraction + upper_fraction)
                            midpoint_row = evaluate_fraction(fraction=midpoint)
                            midpoint_is_eligible = (
                                float(midpoint_row["empirical_success_fraction"]) + 1e-12
                                >= criteria.reliability_target
                            )
                            if midpoint_is_eligible:
                                lower_fraction = midpoint
                            else:
                                upper_fraction = midpoint
            eligible = [
                row
                for row in point_rows
                if float(row["empirical_success_fraction"]) + 1e-12 >= criteria.reliability_target
            ]
            capacity_estimable = bool(eligible)
            if not eligible and selection_dataset_role == "validation":
                raise RuntimeError("validation contains no service-feasible causal candidate")
            selected = (
                max(
                    eligible,
                    key=lambda row: float(row["candidate_reduction_kw"]),
                )
                if eligible
                else point_rows[0]
            )
            selection_rows.append(
                {
                    **selected,
                    "capacity_estimable": capacity_estimable,
                    "zero_capacity_service_feasible": bool(
                        point_rows[0]["empirical_success_fraction"]
                        >= criteria.reliability_target
                    ),
                    "selected_on_validation_only": selection_dataset_role == "validation",
                    "independent_certificate_pending": selection_dataset_role == "validation",
                }
            )
    diagnostics = pd.DataFrame.from_records(diagnostic_rows)
    diagnostics_path = output / "validation_candidate_diagnostics.parquet"
    diagnostics.to_parquet(diagnostics_path, index=False)
    selection_path = output / "causal_selection.json"
    selection_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "capacity_layer": "causal_robust_mpc_reference",
                "selection_interpretation": (
                    "validation_empirical_selection_not_reliability_certificate"
                    if selection_dataset_role == "validation"
                    else "development_mechanism_diagnostic_not_reliability_certificate"
                ),
                "selection_dataset_role": selection_dataset_role,
                "controller": "robust_mpc",
                "controller_provenance": controller_provenance,
                "criteria": criteria.as_dict(),
                "validation_scenario_hashes": [artifact.scenario_hash for artifact in artifacts],
                "reference_mix_operating_peak_kw": reference_peak_kw,
                "capacity_search": {
                    "method": search,
                    "candidate_fraction_grid_or_bounds": list(candidates),
                    "binary_iterations": binary_iterations if search == "binary" else None,
                    "scenario_workers": workers,
                },
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
    controller_config: str | Path,
    output_directory: str | Path,
    event_id: int = 0,
    workers: int = 1,
) -> dict[str, str | int]:
    """Evaluate frozen validation selections once on independent locked-ID data."""

    artifacts = _discover_artifacts(scenario_path)
    selection = json.loads(Path(selection_path).read_text(encoding="utf-8"))
    if not isinstance(selection, Mapping) or selection.get("schema_version") != 2:
        raise ValueError("selection is not a frozen causal-selection artifact")
    if selection.get("controller") != "robust_mpc":
        raise ValueError("Nature mainline causal selection must use robust_mpc")
    if selection.get("selection_dataset_role") != "validation":
        raise ValueError("locked-ID certification requires a validation-only selection")
    controller_specification = _verify_controller_provenance(
        selection.get("controller_provenance"),
        controller_config=controller_config,
    )
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
        if row.get("capacity_estimable") is not True:
            raise ValueError("selection contains a non-estimable causal capacity")
        outcomes, summary = evaluate_frozen_causal_candidate(
            artifacts,
            controller_specification=controller_specification,
            duration_h=int(row["duration_h"]),
            notice_h=int(row["notice_h"]),
            requested_reduction_kw=float(row["candidate_reduction_kw"]),
            criteria=criteria,
            event_id=event_id,
            workers=workers,
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
                "schema_version": 2,
                "capacity_layer": "independent_causal_certificate",
                "controller": "robust_mpc",
                "controller_provenance": selection["controller_provenance"],
                "selection": str(selection_path),
                "criteria": criteria.as_dict(),
                "scenario_workers": workers,
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
