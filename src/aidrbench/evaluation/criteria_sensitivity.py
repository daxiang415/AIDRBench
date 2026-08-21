"""One-factor-at-a-time sensitivity of perfect-information firm capacity."""

from __future__ import annotations

import json
import math
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import yaml

from aidrbench.controllers.hourly_oracle import HIGHS_THREADS_PER_SOLVE, solve_full_horizon_oracle
from aidrbench.data.frozen_scenarios import FrozenHourlyScenario, load_frozen_hourly_scenario
from aidrbench.data.splits import sha256_file
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv
from aidrbench.evaluation.firm_flexibility import FirmFlexibilityCriteria
from aidrbench.evaluation.pi_frontier import (
    _environment_document,
    summarize_pi_firm_boundary,
    validate_pi_frontier,
)
from aidrbench.evaluation.provenance import optimization_provenance

CriteriaFactor = Literal[
    "reference",
    "delivery",
    "deadline",
    "rebound",
    "window_relief",
]

_CASE_FIELDS = {
    "name",
    "factor",
    "min_delivery_ratio",
    "min_interval_delivery_ratio",
    "max_deadline_miss_rate",
    "max_rebound_ratio",
    "min_window_peak_relief_fraction",
    "max_terminal_backlog_fraction",
}
_ROOT_FIELDS = {
    "schema_version",
    "design",
    "service_gate_manifest",
    "durations_h",
    "reliability_target",
    "confidence_level",
    "nominal_flexibility_fraction",
    "cases",
}
_FACTOR_FIELDS: dict[str, frozenset[str]] = {
    "delivery": frozenset({"min_delivery_ratio", "min_interval_delivery_ratio"}),
    "deadline": frozenset({"max_deadline_miss_rate"}),
    "rebound": frozenset({"max_rebound_ratio"}),
    "window_relief": frozenset({"min_window_peak_relief_fraction"}),
}
_CRITERIA_FIELDS = tuple(
    field for field in _CASE_FIELDS if field not in {"name", "factor"}
)


def _finite_fraction(value: object, name: str, *, strict: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    valid = 0.0 < result < 1.0 if strict else 0.0 <= result <= 1.0
    if not math.isfinite(result) or not valid:
        bounds = "(0, 1)" if strict else "[0, 1]"
        raise ValueError(f"{name} must be in {bounds}")
    return result


def _non_negative(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


@dataclass(frozen=True, slots=True)
class CriteriaSensitivityCase:
    """One fully specified operational success-criteria case."""

    name: str
    factor: CriteriaFactor
    min_delivery_ratio: float
    min_interval_delivery_ratio: float
    max_deadline_miss_rate: float
    max_rebound_ratio: float
    min_window_peak_relief_fraction: float
    max_terminal_backlog_fraction: float

    def __post_init__(self) -> None:
        if not self.name or not self.name.replace("_", "").isalnum():
            raise ValueError("criteria sensitivity case name must be alphanumeric with underscores")
        if self.factor not in {"reference", *_FACTOR_FIELDS}:
            raise ValueError("criteria sensitivity factor is unsupported")
        FirmFlexibilityCriteria(
            min_delivery_ratio=self.min_delivery_ratio,
            min_interval_delivery_ratio=self.min_interval_delivery_ratio,
            max_deadline_miss_rate=self.max_deadline_miss_rate,
            max_rebound_ratio=self.max_rebound_ratio,
            min_window_peak_relief_fraction=self.min_window_peak_relief_fraction,
            max_terminal_backlog_fraction=self.max_terminal_backlog_fraction,
        )
        if not math.isclose(
            self.min_delivery_ratio,
            self.min_interval_delivery_ratio,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "criteria sensitivity links mean and minimum-interval delivery thresholds"
            )

    def solver_kwargs(self) -> dict[str, float]:
        return {
            "min_delivery_ratio": self.min_delivery_ratio,
            "min_interval_delivery_ratio": self.min_interval_delivery_ratio,
            "max_deadline_miss_rate": self.max_deadline_miss_rate,
            "max_rebound_ratio": self.max_rebound_ratio,
            "min_window_peak_relief_fraction": self.min_window_peak_relief_fraction,
            "max_terminal_backlog_fraction": self.max_terminal_backlog_fraction,
        }


@dataclass(frozen=True, slots=True)
class CriteriaSensitivitySpecification:
    """Strict sparse design for operational-definition sensitivity."""

    schema_version: Literal[1]
    design: Literal["one_factor_at_a_time"]
    service_gate_manifest: Path
    durations_h: tuple[int, ...]
    reliability_target: float
    confidence_level: float
    nominal_flexibility_fraction: float
    cases: tuple[CriteriaSensitivityCase, ...]

    def __post_init__(self) -> None:
        if self.schema_version != 1 or self.design != "one_factor_at_a_time":
            raise ValueError("unsupported criteria sensitivity schema")
        if not self.durations_h or any(
            isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0
            for duration in self.durations_h
        ):
            raise ValueError("criteria sensitivity durations must be positive integers")
        if tuple(sorted(set(self.durations_h))) != self.durations_h:
            raise ValueError("criteria sensitivity durations must be sorted and unique")
        _finite_fraction(self.reliability_target, "reliability_target", strict=True)
        _finite_fraction(self.confidence_level, "confidence_level", strict=True)
        _finite_fraction(
            self.nominal_flexibility_fraction,
            "nominal_flexibility_fraction",
        )
        if not self.cases:
            raise ValueError("criteria sensitivity must declare at least one case")
        names = [case.name for case in self.cases]
        if len(set(names)) != len(names):
            raise ValueError("criteria sensitivity case names must be unique")
        references = [case for case in self.cases if case.factor == "reference"]
        if len(references) != 1 or references[0].name != "reference":
            raise ValueError("criteria sensitivity requires exactly one case named reference")
        reference = references[0]
        for case in self.cases:
            changed = {
                field
                for field in _CRITERIA_FIELDS
                if not math.isclose(
                    float(getattr(case, field)),
                    float(getattr(reference, field)),
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
            }
            expected = frozenset() if case.factor == "reference" else _FACTOR_FIELDS[case.factor]
            if changed != expected:
                raise ValueError(
                    f"criteria case {case.name!r} changes {sorted(changed)}, "
                    f"expected {sorted(expected)} for factor {case.factor!r}"
                )

    @property
    def reference_case(self) -> CriteriaSensitivityCase:
        return next(case for case in self.cases if case.factor == "reference")


def _resolve_path(value: object, *, source_directory: Path) -> Path:
    path = Path(str(value))
    if path.is_absolute():
        return path
    repository_candidate = Path.cwd() / path
    local_candidate = source_directory / path
    if repository_candidate.exists() or not local_candidate.exists():
        return repository_candidate
    return local_candidate


def load_criteria_sensitivity_specification(
    source: str | Path | Mapping[str, Any],
) -> CriteriaSensitivitySpecification:
    """Load a complete one-factor-at-a-time criteria sensitivity design."""

    if isinstance(source, str | Path):
        source_path = Path(source)
        document = yaml.safe_load(source_path.read_text(encoding="utf-8"))
        source_directory = source_path.parent
    else:
        document = dict(source)
        source_directory = Path.cwd()
    if not isinstance(document, Mapping) or set(document) != _ROOT_FIELDS:
        raise ValueError("criteria sensitivity specification has missing or unknown fields")
    raw_cases = document["cases"]
    if not isinstance(raw_cases, list):
        raise ValueError("criteria sensitivity cases must be a list")
    cases: list[CriteriaSensitivityCase] = []
    for raw_case in raw_cases:
        if not isinstance(raw_case, Mapping) or set(raw_case) != _CASE_FIELDS:
            raise ValueError("criteria sensitivity case has missing or unknown fields")
        cases.append(CriteriaSensitivityCase(**dict(raw_case)))
    raw_durations = document["durations_h"]
    if not isinstance(raw_durations, list):
        raise ValueError("criteria sensitivity durations_h must be a list")
    return CriteriaSensitivitySpecification(
        schema_version=document["schema_version"],
        design=document["design"],
        service_gate_manifest=_resolve_path(
            document["service_gate_manifest"],
            source_directory=source_directory,
        ),
        durations_h=tuple(raw_durations),
        reliability_target=_finite_fraction(
            document["reliability_target"],
            "reliability_target",
            strict=True,
        ),
        confidence_level=_finite_fraction(
            document["confidence_level"],
            "confidence_level",
            strict=True,
        ),
        nominal_flexibility_fraction=_finite_fraction(
            document["nominal_flexibility_fraction"],
            "nominal_flexibility_fraction",
        ),
        cases=tuple(cases),
    )


def _validate_service_gate(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"criteria sensitivity service gate is missing: {path}")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise ValueError("criteria sensitivity service gate must be a mapping")
    if document.get("all_cases_service_feasible") is not True or document.get(
        "downstream_sensitivity_execution_allowed"
    ) is not True:
        raise ValueError("criteria sensitivity is blocked by the no-DR service gate")
    table_path = Path(str(document.get("table", "")))
    if not table_path.is_absolute():
        repository_candidate = Path.cwd() / table_path
        table_path = (
            repository_candidate
            if repository_candidate.exists()
            else path.parent / table_path
        )
    expected_hash = document.get("table_sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise ValueError("criteria sensitivity service gate lacks a table SHA-256")
    if not table_path.is_file() or sha256_file(table_path) != expected_hash:
        raise ValueError("criteria sensitivity service-gate table hash mismatch")
    return dict(document)


def _discover_artifact_paths(path: str | Path) -> tuple[str, ...]:
    root = Path(path)
    if (root / "metadata.json").is_file():
        load_frozen_hourly_scenario(root)
        return (str(root),)
    if not root.is_dir():
        raise FileNotFoundError(f"frozen scenario path does not exist: {root}")
    paths = tuple(
        str(child)
        for child in sorted(root.iterdir())
        if child.is_dir() and (child / "metadata.json").is_file()
    )
    if not paths:
        raise ValueError(f"no frozen scenario artifacts found in: {root}")
    for artifact_path in paths:
        load_frozen_hourly_scenario(artifact_path)
    return paths


def _solve_artifact(
    artifact: FrozenHourlyScenario,
    *,
    durations_h: Sequence[int],
    cases: Sequence[CriteriaSensitivityCase],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for duration_h in durations_h:
        document = _environment_document(artifact, duration_h=duration_h, event_id=0)
        env = HourlyCommunityAIDemandResponseEnv(document)
        env.reset(seed=artifact.episode_seed)
        snapshot = env.full_horizon_planning_snapshot()
        physical_upper_bound_kw = (
            max(dict(snapshot.dynamic_kw_per_gpu_h_by_class).values())
            * snapshot.capacity_gpu_h
        )
        for case in cases:
            solution = solve_full_horizon_oracle(snapshot, **case.solver_kwargs())
            rows.append(
                {
                    "scenario_id": artifact.scenario_id,
                    "scenario_hash": artifact.scenario_hash,
                    "episode_seed": artifact.episode_seed,
                    "event_id": 0,
                    "duration_h": duration_h,
                    "capacity_layer": "perfect_information_criteria_sensitivity",
                    "criteria_case": case.name,
                    "criteria_factor": case.factor,
                    **case.solver_kwargs(),
                    "perfect_information_capacity_kw": (
                        solution.perfect_information_capacity_kw
                    ),
                    "perfect_information_capacity_fraction_of_dynamic_range": (
                        solution.perfect_information_capacity_fraction_of_dynamic_range
                    ),
                    "physical_dynamic_upper_bound_kw": physical_upper_bound_kw,
                    "minimum_mean_delivery_ratio": (
                        solution.minimum_mean_delivery_ratio_for_bound
                    ),
                    "minimum_interval_delivery_ratio": (
                        solution.minimum_interval_delivery_ratio_for_bound
                    ),
                    "maximum_rebound_ratio": solution.maximum_rebound_ratio_for_bound,
                    "minimum_window_relief_fraction": (
                        solution.minimum_window_relief_fraction_for_bound
                    ),
                    "deadline_miss_gpu_h": solution.total_deadline_miss_gpu_h,
                    "terminal_backlog_gpu_h": solution.terminal_backlog_gpu_h,
                    "pcc_capacity_kw": snapshot.pcc_capacity_kw,
                    "reference_mix_operating_peak_kw": (
                        snapshot.reference_mix_operating_peak_kw
                    ),
                    "worst_class_peak_kw": snapshot.worst_class_peak_kw,
                    "perfect_information_status": solution.status,
                    "objective_solve_seconds": solution.objective_solve_seconds,
                    "refinement_solve_seconds": solution.refinement_solve_seconds,
                }
            )
    return pd.DataFrame.from_records(rows)


def _worker(
    payload: tuple[str, tuple[int, ...], tuple[dict[str, Any], ...]],
) -> pd.DataFrame:
    artifact_path, durations_h, raw_cases = payload
    artifact = load_frozen_hourly_scenario(artifact_path)
    cases = tuple(CriteriaSensitivityCase(**raw_case) for raw_case in raw_cases)
    return _solve_artifact(artifact, durations_h=durations_h, cases=cases)


def _report_progress(*, completed: int, total: int, started_at: float) -> None:
    interval = max(1, math.ceil(total / 20))
    if completed != total and completed % interval != 0:
        return
    elapsed = time.monotonic() - started_at
    print(
        f"Criteria sensitivity: {completed}/{total} scenarios complete "
        f"({100.0 * completed / total:.0f}%, {elapsed:.1f}s elapsed)",
        file=sys.stderr,
        flush=True,
    )


def validate_criteria_sensitivity_frontier(
    frontier: pd.DataFrame,
    specification: CriteriaSensitivitySpecification,
    *,
    tolerance_kw: float = 1e-6,
) -> None:
    """Fail closed on incomplete grids and criterion-direction violations."""

    required = {
        "scenario_hash",
        "duration_h",
        "criteria_case",
        "criteria_factor",
        "perfect_information_capacity_kw",
        "physical_dynamic_upper_bound_kw",
        "perfect_information_status",
        *_CRITERIA_FIELDS,
    }
    missing = sorted(required - set(frontier))
    if missing:
        raise ValueError(f"criteria sensitivity frontier is missing columns: {missing}")
    if frontier.empty or set(frontier["criteria_case"]) != {
        case.name for case in specification.cases
    }:
        raise ValueError("criteria sensitivity frontier has an incomplete case set")
    expected_rows = (
        frontier["scenario_hash"].nunique()
        * len(specification.durations_h)
        * len(specification.cases)
    )
    if len(frontier) != expected_rows or frontier.duplicated(
        ["scenario_hash", "duration_h", "criteria_case"]
    ).any():
        raise ValueError("criteria sensitivity frontier has missing or duplicate rows")
    if set(frontier["duration_h"]) != set(specification.durations_h):
        raise ValueError("criteria sensitivity frontier has an incomplete duration set")
    if set(frontier["perfect_information_status"]) != {"optimal"}:
        raise ValueError("criteria sensitivity frontier contains a non-optimal solve")
    for _, case_frontier in frontier.groupby("criteria_case", sort=False):
        validate_pi_frontier(case_frontier)

    reference = frontier.loc[frontier["criteria_case"] == "reference"].set_index(
        ["scenario_hash", "duration_h"]
    )
    reference_case = specification.reference_case
    for case in specification.cases:
        if case.factor == "reference":
            continue
        candidate = frontier.loc[frontier["criteria_case"] == case.name].set_index(
            ["scenario_hash", "duration_h"]
        )
        candidate = candidate.loc[reference.index]
        delta = candidate["perfect_information_capacity_kw"] - reference[
            "perfect_information_capacity_kw"
        ]
        if case.factor in {"delivery", "window_relief"}:
            field = (
                "min_delivery_ratio"
                if case.factor == "delivery"
                else "min_window_peak_relief_fraction"
            )
            stricter = float(getattr(case, field)) > float(getattr(reference_case, field))
        else:
            field = (
                "max_deadline_miss_rate"
                if case.factor == "deadline"
                else "max_rebound_ratio"
            )
            stricter = float(getattr(case, field)) < float(getattr(reference_case, field))
        if stricter and (delta > tolerance_kw).any():
            raise ValueError(f"stricter criteria case {case.name!r} increased PI capacity")
        if not stricter and (delta < -tolerance_kw).any():
            raise ValueError(f"looser criteria case {case.name!r} reduced PI capacity")


def _summarize_boundaries(
    frontier: pd.DataFrame,
    specification: CriteriaSensitivitySpecification,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    cases = {case.name: case for case in specification.cases}
    for case_name, case_frontier in frontier.groupby("criteria_case", sort=False):
        boundary = summarize_pi_firm_boundary(
            case_frontier,
            reliability_targets=[specification.reliability_target],
            confidence_level=specification.confidence_level,
            nominal_flexibility_fraction=specification.nominal_flexibility_fraction,
        )
        case = cases[str(case_name)]
        boundary.insert(0, "criteria_factor", case.factor)
        boundary.insert(0, "criteria_case", case.name)
        for field, value in reversed(tuple(case.solver_kwargs().items())):
            boundary.insert(2, field, value)
        frames.append(boundary)
    return pd.concat(frames, ignore_index=True)


def compute_and_save_criteria_sensitivity(
    scenario_path: str | Path,
    *,
    specification: str | Path | Mapping[str, Any],
    output_directory: str | Path,
    workers: int = 1,
) -> dict[str, str | int]:
    """Solve and persist the predeclared development PI criteria sensitivity."""

    if isinstance(workers, bool) or not isinstance(workers, int) or workers <= 0:
        raise ValueError("criteria sensitivity workers must be a positive integer")
    spec = load_criteria_sensitivity_specification(specification)
    gate = _validate_service_gate(spec.service_gate_manifest)
    artifact_paths = _discover_artifact_paths(scenario_path)
    artifacts = [load_frozen_hourly_scenario(path) for path in artifact_paths]
    worker_count = min(workers, len(artifact_paths))
    raw_cases = tuple(asdict(case) for case in spec.cases)
    payloads = [
        (artifact_path, spec.durations_h, raw_cases) for artifact_path in artifact_paths
    ]
    started_at = time.monotonic()
    if worker_count == 1:
        frames = []
        for completed, payload in enumerate(payloads, start=1):
            frames.append(_worker(payload))
            _report_progress(completed=completed, total=len(payloads), started_at=started_at)
    else:
        completed_frames: list[pd.DataFrame | None] = [None] * len(payloads)
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(_worker, payload): index
                for index, payload in enumerate(payloads)
            }
            for completed, future in enumerate(as_completed(futures), start=1):
                completed_frames[futures[future]] = future.result()
                _report_progress(
                    completed=completed,
                    total=len(payloads),
                    started_at=started_at,
                )
        frames = [frame for frame in completed_frames if frame is not None]
    frontier = pd.concat(frames, ignore_index=True)
    validate_criteria_sensitivity_frontier(frontier, spec)
    boundary = _summarize_boundaries(frontier, spec)

    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    frontier_path = output / "criteria_pi_frontier.parquet"
    boundary_path = output / "criteria_pi_firm_boundary.parquet"
    manifest_path = output / "criteria_sensitivity.json"
    frontier.to_parquet(frontier_path, index=False)
    boundary.to_parquet(boundary_path, index=False)
    specification_path = Path(specification) if isinstance(specification, str | Path) else None
    manifest = {
        "schema_version": 1,
        "capacity_layer": "perfect_information_criteria_sensitivity",
        "evidence_scope": "development_only",
        "design": spec.design,
        "specification": str(specification_path) if specification_path is not None else None,
        "specification_sha256": (
            sha256_file(specification_path) if specification_path is not None else None
        ),
        "service_gate_manifest": str(spec.service_gate_manifest),
        "service_gate_manifest_sha256": sha256_file(spec.service_gate_manifest),
        "service_gate": gate,
        "durations_h": list(spec.durations_h),
        "reliability_target": spec.reliability_target,
        "confidence_level": spec.confidence_level,
        "nominal_flexibility_fraction": spec.nominal_flexibility_fraction,
        "cases": [asdict(case) for case in spec.cases],
        "scenario_count": len(artifacts),
        "scenario_hashes": [artifact.scenario_hash for artifact in artifacts],
        "worker_count": worker_count,
        "solver": {"name": "HIGHS", "threads_per_worker": HIGHS_THREADS_PER_SOLVE},
        "frontier": str(frontier_path),
        "frontier_sha256": sha256_file(frontier_path),
        "firm_boundary": str(boundary_path),
        "firm_boundary_sha256": sha256_file(boundary_path),
        "provenance": optimization_provenance(artifacts),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "scenario_count": len(artifacts),
        "case_count": len(spec.cases),
        "row_count": len(frontier),
        "frontier": str(frontier_path),
        "firm_boundary": str(boundary_path),
        "manifest": str(manifest_path),
    }
