"""Paired sparse workload sensitivity for development PI frontiers."""

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

from aidrbench.controllers.hourly_oracle import HIGHS_THREADS_PER_SOLVE
from aidrbench.data.frozen_scenarios import (
    FrozenHourlyScenario,
    freeze_hourly_scenario,
    load_frozen_hourly_scenario,
)
from aidrbench.data.splits import sha256_file
from aidrbench.envs.hourly_config import load_hourly_environment_config
from aidrbench.evaluation.frozen_causal_certificate import _git_commit
from aidrbench.evaluation.pi_frontier import (
    solve_frozen_pi_frontier,
    summarize_pi_firm_boundary,
    validate_pi_frontier,
)
from aidrbench.evaluation.provenance import optimization_provenance
from aidrbench.evaluation.sensitivity import (
    SensitivityCaseSpecification,
    SparseSensitivitySpecification,
    apply_sensitivity_case,
    load_sparse_sensitivity_specification,
)

_SCENARIO_INDEX_NAME = "workload_sensitivity_scenarios.json"
_ROOT_FIELDS = {
    "schema_version",
    "design",
    "sparse_specification",
    "service_gate_manifest",
    "development_seed_range",
    "durations_h",
    "reliability_target",
    "confidence_level",
    "nominal_flexibility_fraction",
}


def _fraction(value: object, name: str, *, strict: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    valid = 0.0 < result < 1.0 if strict else 0.0 <= result <= 1.0
    if not math.isfinite(result) or not valid:
        interval = "(0, 1)" if strict else "[0, 1]"
        raise ValueError(f"{name} must be in {interval}")
    return result


def _resolve_path(value: object, *, source_directory: Path) -> Path:
    path = Path(str(value))
    if path.is_absolute():
        return path
    repository_candidate = Path.cwd() / path
    local_candidate = source_directory / path
    if repository_candidate.exists() or not local_candidate.exists():
        return repository_candidate
    return local_candidate


@dataclass(frozen=True, slots=True)
class WorkloadSensitivitySpecification:
    """Strict execution contract for the predeclared sparse workload design."""

    schema_version: Literal[1]
    design: Literal["sparse_factorial_pi"]
    sparse_specification: Path
    service_gate_manifest: Path
    development_seed_range: tuple[int, int]
    durations_h: tuple[int, ...]
    reliability_target: float
    confidence_level: float
    nominal_flexibility_fraction: float

    def __post_init__(self) -> None:
        if self.schema_version != 1 or self.design != "sparse_factorial_pi":
            raise ValueError("unsupported workload sensitivity schema")
        start, stop = self.development_seed_range
        if (
            isinstance(start, bool)
            or isinstance(stop, bool)
            or not isinstance(start, int)
            or not isinstance(stop, int)
            or start < 0
            or stop < start
        ):
            raise ValueError("development_seed_range must be two increasing integers")
        if not self.durations_h or any(
            isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0
            for duration in self.durations_h
        ):
            raise ValueError("workload sensitivity durations must be positive integers")
        if tuple(sorted(set(self.durations_h))) != self.durations_h:
            raise ValueError("workload sensitivity durations must be sorted and unique")
        _fraction(self.reliability_target, "reliability_target", strict=True)
        _fraction(self.confidence_level, "confidence_level", strict=True)
        _fraction(
            self.nominal_flexibility_fraction,
            "nominal_flexibility_fraction",
        )

    @property
    def seeds(self) -> tuple[int, ...]:
        start, stop = self.development_seed_range
        return tuple(range(start, stop + 1))


def load_workload_sensitivity_specification(
    source: str | Path | Mapping[str, Any],
) -> WorkloadSensitivitySpecification:
    """Load a complete workload-sensitivity execution contract."""

    if isinstance(source, str | Path):
        source_path = Path(source)
        document = yaml.safe_load(source_path.read_text(encoding="utf-8"))
        source_directory = source_path.parent
    else:
        document = dict(source)
        source_directory = Path.cwd()
    if not isinstance(document, Mapping) or set(document) != _ROOT_FIELDS:
        raise ValueError("workload sensitivity specification has missing or unknown fields")
    raw_seed_range = document["development_seed_range"]
    raw_durations = document["durations_h"]
    if not isinstance(raw_seed_range, list) or len(raw_seed_range) != 2:
        raise ValueError("development_seed_range must be a two-element list")
    if not isinstance(raw_durations, list):
        raise ValueError("workload sensitivity durations_h must be a list")
    return WorkloadSensitivitySpecification(
        schema_version=document["schema_version"],
        design=document["design"],
        sparse_specification=_resolve_path(
            document["sparse_specification"],
            source_directory=source_directory,
        ),
        service_gate_manifest=_resolve_path(
            document["service_gate_manifest"],
            source_directory=source_directory,
        ),
        development_seed_range=(raw_seed_range[0], raw_seed_range[1]),
        durations_h=tuple(raw_durations),
        reliability_target=_fraction(
            document["reliability_target"],
            "reliability_target",
            strict=True,
        ),
        confidence_level=_fraction(
            document["confidence_level"],
            "confidence_level",
            strict=True,
        ),
        nominal_flexibility_fraction=_fraction(
            document["nominal_flexibility_fraction"],
            "nominal_flexibility_fraction",
        ),
    )


def _validate_service_gate(
    specification: WorkloadSensitivitySpecification,
    sparse: SparseSensitivitySpecification,
) -> dict[str, Any]:
    path = specification.service_gate_manifest
    if not path.is_file():
        raise FileNotFoundError(f"workload sensitivity service gate is missing: {path}")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise ValueError("workload sensitivity service gate must be a mapping")
    if document.get("all_cases_service_feasible") is not True or document.get(
        "downstream_sensitivity_execution_allowed"
    ) is not True:
        raise ValueError("workload sensitivity is blocked by the no-DR service gate")
    if document.get("specification_sha256") != sha256_file(
        specification.sparse_specification
    ):
        raise ValueError("workload sensitivity sparse specification hash mismatch")
    if document.get("base_config_sha256") != sha256_file(sparse.base_config):
        raise ValueError("workload sensitivity base-config hash mismatch")
    if document.get("case_count") != len(sparse.cases):
        raise ValueError("workload sensitivity service-gate case count mismatch")

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
        raise ValueError("workload sensitivity service gate lacks a table SHA-256")
    if not table_path.is_file() or sha256_file(table_path) != expected_hash:
        raise ValueError("workload sensitivity service-gate table hash mismatch")
    table = pd.read_parquet(table_path)
    expected_cases = {case.name for case in sparse.cases}
    if set(table.get("case", pd.Series(dtype=str))) != expected_cases:
        raise ValueError("workload sensitivity service gate has an incomplete case set")
    if "service_feasible" not in table or not bool(table["service_feasible"].all()):
        raise ValueError("workload sensitivity service-gate table contains a failure")
    return dict(document)


def _case_map(
    sparse: SparseSensitivitySpecification,
) -> dict[str, SensitivityCaseSpecification]:
    cases = {case.name: case for case in sparse.cases}
    if "reference" not in cases:
        raise ValueError("workload sensitivity requires a case named reference")
    return cases


def _report_progress(
    label: str,
    *,
    completed: int,
    total: int,
    started_at: float,
) -> None:
    interval = max(1, math.ceil(total / 20))
    if completed != total and completed % interval != 0:
        return
    elapsed = time.monotonic() - started_at
    print(
        f"{label}: {completed}/{total} complete "
        f"({100.0 * completed / total:.0f}%, {elapsed:.1f}s elapsed)",
        file=sys.stderr,
        flush=True,
    )


def _validate_pairing(
    artifacts_by_case: Mapping[str, Sequence[FrozenHourlyScenario]],
    *,
    seeds: Sequence[int],
) -> None:
    """Verify that community and event anchors remain paired across cases."""

    if any(len(artifacts) != len(seeds) for artifacts in artifacts_by_case.values()):
        raise ValueError("workload sensitivity cases do not share the declared seed set")
    for position, _generation_seed in enumerate(seeds):
        paired = [artifacts[position] for artifacts in artifacts_by_case.values()]
        episode_seeds = {artifact.episode_seed for artifact in paired}
        community_hashes = {
            str(artifact.metadata["files"]["community.parquet"])
            for artifact in paired
        }
        event_signatures = {
            json.dumps(
                [
                    {
                        key: event[key]
                        for key in (
                            "event_id",
                            "source_event_id",
                            "start_hour",
                            "stop_hour",
                            "notice_hours",
                        )
                    }
                    for event in artifact.metadata["events"]
                ],
                sort_keys=True,
            )
            for artifact in paired
        }
        random_streams = {
            json.dumps(
                artifact.metadata["exogenous_random_stream_seeds"],
                sort_keys=True,
            )
            for artifact in paired
        }
        if (
            len(episode_seeds) != 1
            or len(community_hashes) != 1
            or len(event_signatures) != 1
        ):
            raise ValueError("workload sensitivity pairing changed community or event anchors")
        if len(random_streams) != 1:
            raise ValueError("workload sensitivity pairing changed random-stream seeds")


def freeze_workload_sensitivity_scenarios(
    specification: str | Path,
    *,
    output_directory: str | Path,
) -> dict[str, str | int]:
    """Atomically freeze the paired scenarios for every sparse workload case."""

    specification_path = Path(specification)
    spec = load_workload_sensitivity_specification(specification_path)
    sparse = load_sparse_sensitivity_specification(spec.sparse_specification)
    gate = _validate_service_gate(spec, sparse)
    cases = _case_map(sparse)
    base_document = yaml.safe_load(sparse.base_config.read_text(encoding="utf-8"))
    if not isinstance(base_document, Mapping):
        raise ValueError("workload sensitivity base config must be a mapping")

    output = Path(output_directory)
    temporary = output.parent / f".{output.name}.incomplete"
    if output.exists():
        raise FileExistsError(f"refusing to overwrite workload scenarios: {output}")
    if temporary.exists():
        raise FileExistsError(f"incomplete workload scenario run exists: {temporary}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary.mkdir()

    total = len(cases) * len(spec.seeds)
    completed = 0
    started_at = time.monotonic()
    artifacts_by_case: dict[str, list[FrozenHourlyScenario]] = {}
    index_cases: list[dict[str, Any]] = []
    for case_name, case in cases.items():
        document = apply_sensitivity_case(base_document, case)
        case_root = temporary / case_name
        artifacts: list[FrozenHourlyScenario] = []
        index_scenarios: list[dict[str, Any]] = []
        for seed in spec.seeds:
            frozen = freeze_hourly_scenario(
                document,
                seed=seed,
                output_directory=case_root,
            )
            artifact = load_frozen_hourly_scenario(str(frozen["output"]))
            artifacts.append(artifact)
            index_scenarios.append(
                {
                    "generation_seed": seed,
                    "episode_seed": artifact.episode_seed,
                    "scenario_hash": artifact.scenario_hash,
                    "relative_path": str(Path(case_name) / artifact.directory.name),
                }
            )
            completed += 1
            _report_progress(
                "Workload scenario freeze",
                completed=completed,
                total=total,
                started_at=started_at,
            )
        artifacts_by_case[case_name] = artifacts
        index_cases.append(
            {
                "case": case_name,
                **asdict(case),
                "scenarios": index_scenarios,
            }
        )
    _validate_pairing(artifacts_by_case, seeds=spec.seeds)

    index = {
        "schema_version": 1,
        "evidence_scope": "development_only",
        "design": spec.design,
        "analysis_git_commit": _git_commit(),
        "specification": str(specification_path),
        "specification_sha256": sha256_file(specification_path),
        "sparse_specification": str(spec.sparse_specification),
        "sparse_specification_sha256": sha256_file(spec.sparse_specification),
        "service_gate_manifest": str(spec.service_gate_manifest),
        "service_gate_manifest_sha256": sha256_file(spec.service_gate_manifest),
        "service_gate": gate,
        "base_config": str(sparse.base_config),
        "base_config_sha256": sha256_file(sparse.base_config),
        "development_seed_range": list(spec.development_seed_range),
        "seeds": list(spec.seeds),
        "case_count": len(cases),
        "scenario_count": total,
        "paired_community_and_event_anchors": True,
        "cases": index_cases,
    }
    (temporary / _SCENARIO_INDEX_NAME).write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)
    return {
        "case_count": len(cases),
        "scenario_count": total,
        "scenario_index": str(output / _SCENARIO_INDEX_NAME),
        "output": str(output),
    }


def _load_scenario_index(
    scenario_directory: str | Path,
    *,
    specification_path: Path,
    specification: WorkloadSensitivitySpecification,
    sparse: SparseSensitivitySpecification,
) -> tuple[dict[str, list[FrozenHourlyScenario]], dict[str, Any]]:
    root = Path(scenario_directory)
    index_path = root / _SCENARIO_INDEX_NAME
    if not index_path.is_file():
        raise FileNotFoundError(f"workload sensitivity scenario index is missing: {index_path}")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(index, Mapping):
        raise ValueError("workload sensitivity scenario index must be a mapping")
    expected = {
        "specification_sha256": sha256_file(specification_path),
        "sparse_specification_sha256": sha256_file(
            specification.sparse_specification
        ),
        "service_gate_manifest_sha256": sha256_file(
            specification.service_gate_manifest
        ),
        "base_config_sha256": sha256_file(sparse.base_config),
    }
    if any(index.get(key) != value for key, value in expected.items()):
        raise ValueError("workload sensitivity scenario index provenance mismatch")
    if index.get("seeds") != list(specification.seeds):
        raise ValueError("workload sensitivity scenario index seed mismatch")

    case_specs = _case_map(sparse)
    raw_cases = index.get("cases")
    if not isinstance(raw_cases, list):
        raise ValueError("workload sensitivity scenario index lacks cases")
    artifacts_by_case: dict[str, list[FrozenHourlyScenario]] = {}
    seen_cases: set[str] = set()
    for raw_case in raw_cases:
        if not isinstance(raw_case, Mapping):
            raise ValueError("workload sensitivity scenario case is malformed")
        case_name = str(raw_case.get("case", ""))
        if case_name not in case_specs or case_name in seen_cases:
            raise ValueError("workload sensitivity scenario index case mismatch")
        seen_cases.add(case_name)
        declared_case = case_specs[case_name]
        for field, value in asdict(declared_case).items():
            if raw_case.get(field) != value:
                raise ValueError("workload sensitivity scenario case parameter mismatch")
        raw_scenarios = raw_case.get("scenarios")
        if not isinstance(raw_scenarios, list):
            raise ValueError("workload sensitivity scenario entries are malformed")
        artifacts: list[FrozenHourlyScenario] = []
        if len(raw_scenarios) != len(specification.seeds):
            raise ValueError("workload sensitivity scenario seed count mismatch")
        for generation_seed, raw_scenario in zip(
            specification.seeds,
            raw_scenarios,
            strict=True,
        ):
            if not isinstance(raw_scenario, Mapping):
                raise ValueError("workload sensitivity scenario entry is malformed")
            if raw_scenario.get("generation_seed") != generation_seed:
                raise ValueError("workload sensitivity generation-seed mismatch")
            relative = Path(str(raw_scenario.get("relative_path", "")))
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("workload sensitivity scenario path must remain relative")
            artifact = load_frozen_hourly_scenario(root / relative)
            if (
                artifact.episode_seed != raw_scenario.get("episode_seed")
                or artifact.scenario_hash != raw_scenario.get("scenario_hash")
            ):
                raise ValueError("workload sensitivity scenario hash mismatch")
            artifact_config = load_hourly_environment_config(
                artifact.config_document
            )
            observed_parameters = {
                "flexible_arrival_utilization": (
                    artifact_config.flexible_arrival_utilization
                ),
                "rigid_gpu_utilization": artifact_config.rigid_gpu_utilization,
                "deadline_slack_scale": artifact_config.deadline_slack_scale,
            }
            for field, observed in observed_parameters.items():
                if not math.isclose(
                    float(observed),
                    float(getattr(declared_case, field)),
                    rel_tol=0.0,
                    abs_tol=1e-12,
                ):
                    raise ValueError(
                        "workload sensitivity frozen scenario parameter mismatch"
                    )
            artifacts.append(artifact)
        artifacts_by_case[case_name] = artifacts
    if seen_cases != set(case_specs):
        raise ValueError("workload sensitivity scenario index has an incomplete case set")
    _validate_pairing(artifacts_by_case, seeds=specification.seeds)
    return artifacts_by_case, dict(index)


def _solve_worker(
    payload: tuple[str, dict[str, Any], int, str, tuple[int, ...]],
) -> pd.DataFrame:
    case_name, raw_case, generation_seed, artifact_path, durations_h = payload
    case = SensitivityCaseSpecification(**raw_case)
    artifact = load_frozen_hourly_scenario(artifact_path)
    frame = solve_frozen_pi_frontier(artifact, durations_h=durations_h)
    frame["capacity_layer"] = "perfect_information_workload_sensitivity"
    frame.insert(0, "workload_case", case_name)
    frame.insert(1, "generation_seed", generation_seed)
    frame.insert(2, "flexible_arrival_utilization", case.flexible_arrival_utilization)
    frame.insert(3, "rigid_gpu_utilization", case.rigid_gpu_utilization)
    frame.insert(4, "deadline_slack_scale", case.deadline_slack_scale)
    return frame


def validate_workload_sensitivity_frontier(
    frontier: pd.DataFrame,
    specification: WorkloadSensitivitySpecification,
    sparse: SparseSensitivitySpecification,
) -> None:
    """Fail closed on incomplete cases, seeds, durations, or PI solves."""

    required = {
        "workload_case",
        "generation_seed",
        "episode_seed",
        "duration_h",
        "perfect_information_capacity_kw",
        "perfect_information_status",
        "flexible_arrival_utilization",
        "rigid_gpu_utilization",
        "deadline_slack_scale",
    }
    missing = sorted(required - set(frontier))
    if missing:
        raise ValueError(f"workload sensitivity frontier is missing columns: {missing}")
    cases = _case_map(sparse)
    if set(frontier["workload_case"]) != set(cases):
        raise ValueError("workload sensitivity frontier has an incomplete case set")
    expected_rows = len(cases) * len(specification.seeds) * len(
        specification.durations_h
    )
    if len(frontier) != expected_rows or frontier.duplicated(
        ["workload_case", "generation_seed", "duration_h"]
    ).any():
        raise ValueError("workload sensitivity frontier has missing or duplicate rows")
    if set(frontier["generation_seed"]) != set(specification.seeds):
        raise ValueError("workload sensitivity frontier has an incomplete seed set")
    if set(frontier["duration_h"]) != set(specification.durations_h):
        raise ValueError("workload sensitivity frontier has an incomplete duration set")
    if set(frontier["perfect_information_status"]) != {"optimal"}:
        raise ValueError("workload sensitivity frontier contains a non-optimal solve")
    for case_name, case_frontier in frontier.groupby("workload_case", sort=False):
        validate_pi_frontier(case_frontier)
        case = cases[str(case_name)]
        for field in (
            "flexible_arrival_utilization",
            "rigid_gpu_utilization",
            "deadline_slack_scale",
        ):
            values = case_frontier[field].astype(float).unique()
            if len(values) != 1 or not math.isclose(
                float(values[0]),
                float(getattr(case, field)),
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                raise ValueError("workload sensitivity frontier case metadata mismatch")


def _add_paired_reference_columns(frontier: pd.DataFrame) -> pd.DataFrame:
    reference = frontier.loc[
        frontier["workload_case"] == "reference",
        ["generation_seed", "duration_h", "perfect_information_capacity_kw"],
    ].rename(
        columns={
            "perfect_information_capacity_kw": (
                "reference_perfect_information_capacity_kw"
            )
        }
    )
    paired = frontier.merge(
        reference,
        on=["generation_seed", "duration_h"],
        how="left",
        validate="many_to_one",
    )
    if paired["reference_perfect_information_capacity_kw"].isna().any():
        raise ValueError("workload sensitivity frontier cannot pair the reference case")
    paired["paired_capacity_delta_kw"] = (
        paired["perfect_information_capacity_kw"]
        - paired["reference_perfect_information_capacity_kw"]
    )
    reference_capacity = paired["reference_perfect_information_capacity_kw"]
    paired["paired_capacity_ratio"] = paired[
        "perfect_information_capacity_kw"
    ].div(reference_capacity.where(reference_capacity.abs() > 1e-12))
    return paired


def _summarize_boundaries(
    frontier: pd.DataFrame,
    specification: WorkloadSensitivitySpecification,
    sparse: SparseSensitivitySpecification,
) -> pd.DataFrame:
    cases = _case_map(sparse)
    frames: list[pd.DataFrame] = []
    for case_name, case_frontier in frontier.groupby("workload_case", sort=False):
        boundary = summarize_pi_firm_boundary(
            case_frontier,
            reliability_targets=[specification.reliability_target],
            confidence_level=specification.confidence_level,
            nominal_flexibility_fraction=specification.nominal_flexibility_fraction,
        )
        case = cases[str(case_name)]
        boundary.insert(0, "workload_case", case.name)
        boundary.insert(
            1,
            "flexible_arrival_utilization",
            case.flexible_arrival_utilization,
        )
        boundary.insert(2, "rigid_gpu_utilization", case.rigid_gpu_utilization)
        boundary.insert(3, "deadline_slack_scale", case.deadline_slack_scale)
        frames.append(boundary)
    combined = pd.concat(frames, ignore_index=True)
    reference = combined.loc[
        combined["workload_case"] == "reference",
        ["duration_h", "perfect_information_firm_capacity_kw"],
    ].rename(
        columns={
            "perfect_information_firm_capacity_kw": (
                "reference_perfect_information_firm_capacity_kw"
            )
        }
    )
    combined = combined.merge(
        reference,
        on="duration_h",
        how="left",
        validate="many_to_one",
    )
    combined["firm_capacity_delta_from_reference_kw"] = (
        combined["perfect_information_firm_capacity_kw"]
        - combined["reference_perfect_information_firm_capacity_kw"]
    )
    return combined


def compute_and_save_workload_sensitivity(
    scenario_directory: str | Path,
    *,
    specification: str | Path,
    output_directory: str | Path,
    workers: int = 1,
) -> dict[str, str | int]:
    """Solve and atomically persist the paired development PI sensitivity."""

    if isinstance(workers, bool) or not isinstance(workers, int) or workers <= 0:
        raise ValueError("workload sensitivity workers must be a positive integer")
    specification_path = Path(specification)
    spec = load_workload_sensitivity_specification(specification_path)
    sparse = load_sparse_sensitivity_specification(spec.sparse_specification)
    gate = _validate_service_gate(spec, sparse)
    artifacts_by_case, scenario_index = _load_scenario_index(
        scenario_directory,
        specification_path=specification_path,
        specification=spec,
        sparse=sparse,
    )
    cases = _case_map(sparse)
    payloads = [
        (
            case_name,
            asdict(cases[case_name]),
            generation_seed,
            str(artifact.directory),
            spec.durations_h,
        )
        for case_name, artifacts in artifacts_by_case.items()
        for generation_seed, artifact in zip(spec.seeds, artifacts, strict=True)
    ]
    worker_count = min(workers, len(payloads))
    started_at = time.monotonic()
    if worker_count == 1:
        frames = []
        for completed, payload in enumerate(payloads, start=1):
            frames.append(_solve_worker(payload))
            _report_progress(
                "Workload PI sensitivity",
                completed=completed,
                total=len(payloads),
                started_at=started_at,
            )
    else:
        completed_frames: list[pd.DataFrame | None] = [None] * len(payloads)
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(_solve_worker, payload): index
                for index, payload in enumerate(payloads)
            }
            for completed, future in enumerate(as_completed(futures), start=1):
                completed_frames[futures[future]] = future.result()
                _report_progress(
                    "Workload PI sensitivity",
                    completed=completed,
                    total=len(payloads),
                    started_at=started_at,
                )
        frames = [frame for frame in completed_frames if frame is not None]
    frontier = pd.concat(frames, ignore_index=True)
    validate_workload_sensitivity_frontier(frontier, spec, sparse)
    frontier = _add_paired_reference_columns(frontier)
    boundary = _summarize_boundaries(frontier, spec, sparse)

    output = Path(output_directory)
    temporary = output.parent / f".{output.name}.incomplete"
    if output.exists():
        raise FileExistsError(f"refusing to overwrite workload sensitivity: {output}")
    if temporary.exists():
        raise FileExistsError(f"incomplete workload sensitivity run exists: {temporary}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary.mkdir()
    frontier_path = temporary / "workload_pi_frontier.parquet"
    boundary_path = temporary / "workload_pi_firm_boundary.parquet"
    manifest_path = temporary / "workload_sensitivity.json"
    frontier.to_parquet(frontier_path, index=False)
    boundary.to_parquet(boundary_path, index=False)
    all_artifacts = [
        artifact
        for artifacts in artifacts_by_case.values()
        for artifact in artifacts
    ]
    final_frontier_path = output / frontier_path.name
    final_boundary_path = output / boundary_path.name
    manifest = {
        "schema_version": 1,
        "capacity_layer": "perfect_information_workload_sensitivity",
        "evidence_scope": "development_only",
        "design": spec.design,
        "specification": str(specification_path),
        "specification_sha256": sha256_file(specification_path),
        "sparse_specification": str(spec.sparse_specification),
        "sparse_specification_sha256": sha256_file(spec.sparse_specification),
        "service_gate_manifest": str(spec.service_gate_manifest),
        "service_gate_manifest_sha256": sha256_file(spec.service_gate_manifest),
        "service_gate": gate,
        "scenario_index": str(Path(scenario_directory) / _SCENARIO_INDEX_NAME),
        "scenario_index_sha256": sha256_file(
            Path(scenario_directory) / _SCENARIO_INDEX_NAME
        ),
        "scenario_index_analysis_git_commit": scenario_index.get(
            "analysis_git_commit"
        ),
        "durations_h": list(spec.durations_h),
        "reliability_target": spec.reliability_target,
        "confidence_level": spec.confidence_level,
        "nominal_flexibility_fraction": spec.nominal_flexibility_fraction,
        "development_seed_range": list(spec.development_seed_range),
        "case_count": len(cases),
        "scenario_count_per_case": len(spec.seeds),
        "scenario_count": len(all_artifacts),
        "row_count": len(frontier),
        "cases": [asdict(case) for case in cases.values()],
        "worker_count": worker_count,
        "solver": {"name": "HIGHS", "threads_per_worker": HIGHS_THREADS_PER_SOLVE},
        "frontier": str(final_frontier_path),
        "frontier_sha256": sha256_file(frontier_path),
        "firm_boundary": str(final_boundary_path),
        "firm_boundary_sha256": sha256_file(boundary_path),
        "provenance": optimization_provenance(all_artifacts),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)
    return {
        "case_count": len(cases),
        "scenario_count": len(all_artifacts),
        "row_count": len(frontier),
        "frontier": str(final_frontier_path),
        "firm_boundary": str(final_boundary_path),
        "manifest": str(output / manifest_path.name),
    }
