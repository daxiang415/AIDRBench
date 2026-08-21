"""Paired sparse PUE and node-overhead sensitivity on development scenarios."""

from __future__ import annotations

import copy
import json
import math
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

import pandas as pd
import yaml

from aidrbench.controllers.hourly_oracle import HIGHS_THREADS_PER_SOLVE
from aidrbench.data.frozen_scenarios import (
    FrozenHourlyScenario,
    freeze_hourly_scenario,
    load_frozen_hourly_scenario,
)
from aidrbench.data.splits import sha256_file
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv
from aidrbench.envs.hourly_config import load_hourly_environment_config
from aidrbench.evaluation.frozen_causal_certificate import _git_commit
from aidrbench.evaluation.pi_frontier import (
    solve_frozen_pi_frontier,
    summarize_pi_firm_boundary,
    validate_pi_frontier,
)
from aidrbench.evaluation.provenance import optimization_provenance

PowerCase = Literal["lower_bound", "nominal", "upper_bound"]

_SCENARIO_INDEX_NAME = "infrastructure_sensitivity_scenarios.json"
_DESIGN_FIELDS = {
    "schema_version",
    "design",
    "base_config",
    "require_no_dr_service_feasibility",
    "cases",
}
_EXECUTION_FIELDS = {
    "schema_version",
    "design",
    "case_specification",
    "service_gate_manifest",
    "service_gate_seed_range",
    "development_seed_range",
    "durations_h",
    "reliability_target",
    "confidence_level",
    "nominal_flexibility_fraction",
}


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _resolve_path(value: object, *, source_directory: Path) -> Path:
    path = Path(str(value))
    if path.is_absolute():
        return path
    repository_candidate = Path.cwd() / path
    local_candidate = source_directory / path
    return repository_candidate if repository_candidate.exists() else local_candidate


def _fraction(value: object, name: str, *, strict: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    valid = 0.0 < result < 1.0 if strict else 0.0 <= result <= 1.0
    if not math.isfinite(result) or not valid:
        interval = "(0, 1)" if strict else "[0, 1]"
        raise ValueError(f"{name} must be in {interval}")
    return result


def _pue(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("pue must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 1.0:
        raise ValueError("pue must be finite and at least 1.0")
    return result


def _power_case(value: object) -> PowerCase:
    result = str(value).strip()
    if result not in {"lower_bound", "nominal", "upper_bound"}:
        raise ValueError(
            "node_fixed_overhead_power_case must be lower_bound, nominal, or upper_bound"
        )
    return cast(PowerCase, result)


@dataclass(frozen=True, slots=True)
class InfrastructureCaseSpecification:
    """One predeclared PUE or node-overhead point in a sparse OAT design."""

    name: str
    pue: float
    node_fixed_overhead_power_case: PowerCase

    def __post_init__(self) -> None:
        if not self.name or not self.name.replace("_", "").isalnum():
            raise ValueError("infrastructure case name must be alphanumeric with underscores")
        _pue(self.pue)
        _power_case(self.node_fixed_overhead_power_case)


@dataclass(frozen=True, slots=True)
class InfrastructureSensitivityDesign:
    """Sparse infrastructure design; never an implicit Cartesian product."""

    schema_version: Literal[1]
    design: Literal["sparse_oat"]
    base_config: Path
    require_no_dr_service_feasibility: Literal[True]
    cases: tuple[InfrastructureCaseSpecification, ...]

    def __post_init__(self) -> None:
        if self.schema_version != 1 or self.design != "sparse_oat":
            raise ValueError("unsupported infrastructure sensitivity design")
        if self.require_no_dr_service_feasibility is not True:
            raise ValueError("infrastructure sensitivity must require the no-DR gate")
        names = [case.name for case in self.cases]
        if not names or len(names) != len(set(names)):
            raise ValueError("infrastructure sensitivity case names must be nonempty and unique")
        references = [case for case in self.cases if case.name == "reference"]
        if len(references) != 1:
            raise ValueError("infrastructure sensitivity requires exactly one reference case")
        reference = references[0]
        if reference.node_fixed_overhead_power_case != "nominal":
            raise ValueError("infrastructure reference must use nominal node overhead")
        points = {(case.pue, case.node_fixed_overhead_power_case) for case in self.cases}
        if len(points) != len(self.cases):
            raise ValueError("infrastructure sensitivity contains duplicate points")
        for case in self.cases:
            changed_pue = not math.isclose(case.pue, reference.pue, abs_tol=1e-12)
            changed_overhead = case.node_fixed_overhead_power_case != "nominal"
            if case.name != "reference" and changed_pue == changed_overhead:
                raise ValueError(
                    "each non-reference infrastructure case must change exactly one factor"
                )


@dataclass(frozen=True, slots=True)
class InfrastructureSensitivityExecution:
    """Complete fail-closed execution contract for the sparse PI analysis."""

    schema_version: Literal[1]
    design: Literal["sparse_oat_pi"]
    case_specification: Path
    service_gate_manifest: Path
    service_gate_seed_range: tuple[int, int]
    development_seed_range: tuple[int, int]
    durations_h: tuple[int, ...]
    reliability_target: float
    confidence_level: float
    nominal_flexibility_fraction: float

    def __post_init__(self) -> None:
        if self.schema_version != 1 or self.design != "sparse_oat_pi":
            raise ValueError("unsupported infrastructure sensitivity execution")
        for name, (start, stop) in (
            ("service_gate_seed_range", self.service_gate_seed_range),
            ("development_seed_range", self.development_seed_range),
        ):
            if (
                isinstance(start, bool)
                or isinstance(stop, bool)
                or not isinstance(start, int)
                or not isinstance(stop, int)
                or start < 0
                or stop < start
            ):
                raise ValueError(f"{name} must contain increasing integers")
        if not self.durations_h or tuple(sorted(set(self.durations_h))) != self.durations_h:
            raise ValueError("infrastructure durations must be sorted and unique")
        if any(duration <= 0 for duration in self.durations_h):
            raise ValueError("infrastructure durations must be positive")
        _fraction(self.reliability_target, "reliability_target", strict=True)
        _fraction(self.confidence_level, "confidence_level", strict=True)
        _fraction(self.nominal_flexibility_fraction, "nominal_flexibility_fraction")

    @property
    def seeds(self) -> tuple[int, ...]:
        return tuple(range(self.development_seed_range[0], self.development_seed_range[1] + 1))

    @property
    def service_gate_seeds(self) -> tuple[int, ...]:
        return tuple(
            range(self.service_gate_seed_range[0], self.service_gate_seed_range[1] + 1)
        )


def load_infrastructure_sensitivity_design(
    source: str | Path | Mapping[str, Any],
) -> InfrastructureSensitivityDesign:
    """Load and strictly validate the sparse case design."""

    if isinstance(source, str | Path):
        source_path = Path(source)
        document = _mapping(
            yaml.safe_load(source_path.read_text(encoding="utf-8")),
            "infrastructure sensitivity design",
        )
        source_directory = source_path.parent
    else:
        document = _mapping(source, "infrastructure sensitivity design")
        source_directory = Path.cwd()
    if set(document) != _DESIGN_FIELDS:
        raise ValueError("infrastructure sensitivity design has missing or unknown fields")
    raw_cases = document["cases"]
    if not isinstance(raw_cases, list):
        raise ValueError("infrastructure sensitivity cases must be a list")
    case_fields = set(InfrastructureCaseSpecification.__dataclass_fields__)
    cases: list[InfrastructureCaseSpecification] = []
    for raw in raw_cases:
        case = _mapping(raw, "infrastructure sensitivity case")
        if set(case) != case_fields:
            raise ValueError("infrastructure sensitivity case has missing or unknown fields")
        cases.append(
            InfrastructureCaseSpecification(
                name=str(case["name"]),
                pue=_pue(case["pue"]),
                node_fixed_overhead_power_case=_power_case(
                    case["node_fixed_overhead_power_case"]
                ),
            )
        )
    return InfrastructureSensitivityDesign(
        schema_version=document["schema_version"],
        design=document["design"],
        base_config=_resolve_path(
            document["base_config"], source_directory=source_directory
        ),
        require_no_dr_service_feasibility=document[
            "require_no_dr_service_feasibility"
        ],
        cases=tuple(cases),
    )


def load_infrastructure_sensitivity_execution(
    source: str | Path | Mapping[str, Any],
) -> InfrastructureSensitivityExecution:
    """Load the execution contract that binds design, gate and seed set."""

    if isinstance(source, str | Path):
        source_path = Path(source)
        document = _mapping(
            yaml.safe_load(source_path.read_text(encoding="utf-8")),
            "infrastructure sensitivity execution",
        )
        source_directory = source_path.parent
    else:
        document = _mapping(source, "infrastructure sensitivity execution")
        source_directory = Path.cwd()
    if set(document) != _EXECUTION_FIELDS:
        raise ValueError("infrastructure sensitivity execution has missing or unknown fields")
    seed_range = document["development_seed_range"]
    gate_seed_range = document["service_gate_seed_range"]
    durations = document["durations_h"]
    if not isinstance(seed_range, list) or len(seed_range) != 2:
        raise ValueError("development_seed_range must be a two-element list")
    if not isinstance(gate_seed_range, list) or len(gate_seed_range) != 2:
        raise ValueError("service_gate_seed_range must be a two-element list")
    if not isinstance(durations, list):
        raise ValueError("infrastructure durations_h must be a list")
    return InfrastructureSensitivityExecution(
        schema_version=document["schema_version"],
        design=document["design"],
        case_specification=_resolve_path(
            document["case_specification"], source_directory=source_directory
        ),
        service_gate_manifest=_resolve_path(
            document["service_gate_manifest"], source_directory=source_directory
        ),
        service_gate_seed_range=(gate_seed_range[0], gate_seed_range[1]),
        development_seed_range=(seed_range[0], seed_range[1]),
        durations_h=tuple(durations),
        reliability_target=_fraction(
            document["reliability_target"], "reliability_target", strict=True
        ),
        confidence_level=_fraction(
            document["confidence_level"], "confidence_level", strict=True
        ),
        nominal_flexibility_fraction=_fraction(
            document["nominal_flexibility_fraction"], "nominal_flexibility_fraction"
        ),
    )


def _case_map(
    design: InfrastructureSensitivityDesign,
) -> dict[str, InfrastructureCaseSpecification]:
    return {case.name: case for case in design.cases}


def apply_infrastructure_sensitivity_case(
    base_document: Mapping[str, Any],
    case: InfrastructureCaseSpecification,
) -> dict[str, Any]:
    """Change only PUE and the artifact-backed node-overhead case."""

    document = copy.deepcopy(dict(base_document))
    virtual_dc = _mapping(document.get("virtual_datacenter"), "virtual_datacenter")
    hardware = _mapping(document.get("hardware"), "hardware")
    if virtual_dc.get("node_count") == "auto":
        raise ValueError("infrastructure sensitivity requires a fixed node_count")
    if str(hardware.get("calibration_power_case", "nominal")) != "nominal":
        raise ValueError("infrastructure sensitivity requires nominal GPU power")
    if not hardware.get("calibration_artifact"):
        raise ValueError("infrastructure sensitivity requires a calibration artifact")
    virtual_dc["pue"] = case.pue
    hardware["calibration_power_case"] = "nominal"
    hardware["node_fixed_overhead_power_case"] = (
        case.node_fixed_overhead_power_case
    )
    document["virtual_datacenter"] = virtual_dc
    document["hardware"] = hardware
    return document


def _disable_demand_response(document: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(document))
    dr = _mapping(result.get("dr"), "dr")
    dr["event_reduction_kw"] = 0.0
    result["dr"] = dr
    return result


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


def check_infrastructure_no_dr_feasibility(
    specification: str | Path,
    *,
    seeds: Sequence[int],
    output_directory: str | Path,
) -> dict[str, str | int | bool]:
    """Gate every infrastructure case on ordinary no-DR service feasibility."""

    specification_path = Path(specification)
    design = load_infrastructure_sensitivity_design(specification_path)
    if not seeds or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise ValueError("infrastructure no-DR gate requires integer seeds")
    base_document = _mapping(
        yaml.safe_load(design.base_config.read_text(encoding="utf-8")),
        "infrastructure base config",
    )
    rows: list[dict[str, Any]] = []
    for case in design.cases:
        document = _disable_demand_response(
            apply_infrastructure_sensitivity_case(base_document, case)
        )
        for seed in seeds:
            env = HourlyCommunityAIDemandResponseEnv(document)
            env.reset(seed=seed)
            snapshot = env.full_horizon_planning_snapshot()
            total_arrivals = max(snapshot.total_arrival_gpu_h, 1e-9)
            deadline_miss_rate = snapshot.baseline_deadline_miss_gpu_h / total_arrivals
            terminal_backlog_fraction = snapshot.baseline_terminal_backlog_gpu_h / total_arrivals
            feasible = (
                deadline_miss_rate <= env.config.reward.max_deadline_miss_rate + 1e-12
                and terminal_backlog_fraction
                <= env.config.reward.max_terminal_backlog_fraction + 1e-12
            )
            rows.append(
                {
                    "case": case.name,
                    "seed": seed,
                    **asdict(case),
                    "node_fixed_overhead_w": env.config.node_fixed_overhead_w,
                    "baseline_deadline_miss_rate": deadline_miss_rate,
                    "baseline_terminal_backlog_fraction": terminal_backlog_fraction,
                    "service_feasible": feasible,
                }
            )
    table = pd.DataFrame.from_records(rows)
    output = Path(output_directory)
    temporary = output.parent / f".{output.name}.incomplete"
    if output.exists():
        raise FileExistsError(f"refusing to overwrite infrastructure service gate: {output}")
    if temporary.exists():
        raise FileExistsError(f"incomplete infrastructure service gate exists: {temporary}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary.mkdir()
    table_path = temporary / "no_dr_service_feasibility.parquet"
    manifest_path = temporary / "no_dr_service_feasibility.json"
    table.to_parquet(table_path, index=False)
    all_feasible = bool(table["service_feasible"].all())
    final_table = output / table_path.name
    manifest = {
        "schema_version": 1,
        "design": design.design,
        "specification": str(specification_path),
        "specification_sha256": sha256_file(specification_path),
        "base_config": str(design.base_config),
        "base_config_sha256": sha256_file(design.base_config),
        "case_count": len(design.cases),
        "seeds": list(seeds),
        "all_cases_service_feasible": all_feasible,
        "downstream_sensitivity_execution_allowed": all_feasible,
        "table": str(final_table),
        "table_sha256": sha256_file(table_path),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(output)
    if not all_feasible:
        raise RuntimeError("one or more infrastructure cases fail the no-DR service gate")
    return {
        "manifest": str(output / manifest_path.name),
        "table": str(final_table),
        "case_count": len(design.cases),
        "all_cases_service_feasible": all_feasible,
    }


def _validate_service_gate(
    execution: InfrastructureSensitivityExecution,
    design: InfrastructureSensitivityDesign,
) -> dict[str, Any]:
    path = execution.service_gate_manifest
    if not path.is_file():
        raise FileNotFoundError(f"infrastructure service gate is missing: {path}")
    document = _mapping(
        json.loads(path.read_text(encoding="utf-8")), "infrastructure service gate"
    )
    expected = {
        "specification_sha256": sha256_file(execution.case_specification),
        "base_config_sha256": sha256_file(design.base_config),
        "case_count": len(design.cases),
        "all_cases_service_feasible": True,
        "downstream_sensitivity_execution_allowed": True,
        "seeds": list(execution.service_gate_seeds),
    }
    if any(document.get(key) != value for key, value in expected.items()):
        raise ValueError("infrastructure sensitivity service-gate identity mismatch")
    table_path = Path(str(document.get("table", "")))
    if not table_path.is_absolute() and not table_path.is_file():
        table_path = Path.cwd() / table_path
    if not table_path.is_file() or sha256_file(table_path) != document.get("table_sha256"):
        raise ValueError("infrastructure sensitivity service-gate table hash mismatch")
    table = pd.read_parquet(table_path)
    if set(table.get("case", pd.Series(dtype=str))) != set(_case_map(design)):
        raise ValueError("infrastructure sensitivity service gate has incomplete cases")
    if "service_feasible" not in table or not bool(table["service_feasible"].all()):
        raise ValueError("infrastructure sensitivity service gate contains a failure")
    return document


def _validate_pairing(
    artifacts_by_case: Mapping[str, Sequence[FrozenHourlyScenario]],
    *,
    seeds: Sequence[int],
) -> None:
    if any(len(artifacts) != len(seeds) for artifacts in artifacts_by_case.values()):
        raise ValueError("infrastructure sensitivity cases do not share the seed set")
    for position, _seed in enumerate(seeds):
        paired = [artifacts[position] for artifacts in artifacts_by_case.values()]
        episode_seeds = {artifact.episode_seed for artifact in paired}
        community_hashes = {
            str(artifact.metadata["files"]["community.parquet"]) for artifact in paired
        }
        arrival_hashes = {
            str(artifact.metadata["files"]["arrivals.parquet"]) for artifact in paired
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
            json.dumps(artifact.metadata["exogenous_random_stream_seeds"], sort_keys=True)
            for artifact in paired
        }
        if any(
            len(values) != 1
            for values in (
                episode_seeds,
                community_hashes,
                arrival_hashes,
                event_signatures,
                random_streams,
            )
        ):
            raise ValueError(
                "infrastructure sensitivity pairing changed exogenous scenario inputs"
            )


def freeze_infrastructure_sensitivity_scenarios(
    specification: str | Path,
    *,
    output_directory: str | Path,
) -> dict[str, str | int]:
    """Atomically freeze paired scenarios for every infrastructure case."""

    specification_path = Path(specification)
    execution = load_infrastructure_sensitivity_execution(specification_path)
    design = load_infrastructure_sensitivity_design(execution.case_specification)
    gate = _validate_service_gate(execution, design)
    base_document = _mapping(
        yaml.safe_load(design.base_config.read_text(encoding="utf-8")),
        "infrastructure base config",
    )
    output = Path(output_directory)
    temporary = output.parent / f".{output.name}.incomplete"
    if output.exists():
        raise FileExistsError(f"refusing to overwrite infrastructure scenarios: {output}")
    if temporary.exists():
        raise FileExistsError(f"incomplete infrastructure scenarios exist: {temporary}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary.mkdir()
    total = len(design.cases) * len(execution.seeds)
    completed = 0
    started_at = time.monotonic()
    artifacts_by_case: dict[str, list[FrozenHourlyScenario]] = {}
    index_cases: list[dict[str, Any]] = []
    for case in design.cases:
        document = apply_infrastructure_sensitivity_case(base_document, case)
        artifacts: list[FrozenHourlyScenario] = []
        index_scenarios: list[dict[str, Any]] = []
        for seed in execution.seeds:
            frozen = freeze_hourly_scenario(
                document, seed=seed, output_directory=temporary / case.name
            )
            artifact = load_frozen_hourly_scenario(str(frozen["output"]))
            artifacts.append(artifact)
            index_scenarios.append(
                {
                    "generation_seed": seed,
                    "episode_seed": artifact.episode_seed,
                    "scenario_hash": artifact.scenario_hash,
                    "relative_path": str(Path(case.name) / artifact.directory.name),
                }
            )
            completed += 1
            _report_progress(
                "Infrastructure scenario freeze",
                completed=completed,
                total=total,
                started_at=started_at,
            )
        artifacts_by_case[case.name] = artifacts
        index_cases.append(
            {"case": case.name, **asdict(case), "scenarios": index_scenarios}
        )
    _validate_pairing(artifacts_by_case, seeds=execution.seeds)
    index = {
        "schema_version": 1,
        "evidence_scope": "development_only",
        "design": execution.design,
        "analysis_git_commit": _git_commit(),
        "specification": str(specification_path),
        "specification_sha256": sha256_file(specification_path),
        "case_specification": str(execution.case_specification),
        "case_specification_sha256": sha256_file(execution.case_specification),
        "service_gate_manifest": str(execution.service_gate_manifest),
        "service_gate_manifest_sha256": sha256_file(execution.service_gate_manifest),
        "service_gate": gate,
        "base_config": str(design.base_config),
        "base_config_sha256": sha256_file(design.base_config),
        "seeds": list(execution.seeds),
        "case_count": len(design.cases),
        "scenario_count": total,
        "paired_exogenous_inputs": True,
        "cases": index_cases,
    }
    (temporary / _SCENARIO_INDEX_NAME).write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(output)
    return {
        "case_count": len(design.cases),
        "scenario_count": total,
        "scenario_index": str(output / _SCENARIO_INDEX_NAME),
        "output": str(output),
    }


def _load_scenario_index(
    scenario_directory: str | Path,
    *,
    specification_path: Path,
    execution: InfrastructureSensitivityExecution,
    design: InfrastructureSensitivityDesign,
) -> tuple[dict[str, list[FrozenHourlyScenario]], dict[str, Any]]:
    root = Path(scenario_directory)
    index_path = root / _SCENARIO_INDEX_NAME
    if not index_path.is_file():
        raise FileNotFoundError(
            f"infrastructure sensitivity scenario index is missing: {index_path}"
        )
    index = _mapping(
        json.loads(index_path.read_text(encoding="utf-8")),
        "infrastructure sensitivity scenario index",
    )
    expected = {
        "specification_sha256": sha256_file(specification_path),
        "case_specification_sha256": sha256_file(execution.case_specification),
        "service_gate_manifest_sha256": sha256_file(execution.service_gate_manifest),
        "base_config_sha256": sha256_file(design.base_config),
        "seeds": list(execution.seeds),
    }
    if any(index.get(key) != value for key, value in expected.items()):
        raise ValueError("infrastructure sensitivity scenario provenance mismatch")
    case_specs = _case_map(design)
    raw_cases = index.get("cases")
    if not isinstance(raw_cases, list):
        raise ValueError("infrastructure sensitivity scenario index lacks cases")
    seen: set[str] = set()
    artifacts_by_case: dict[str, list[FrozenHourlyScenario]] = {}
    for raw_case_value in raw_cases:
        raw_case = _mapping(raw_case_value, "infrastructure scenario case")
        case_name = str(raw_case.get("case", ""))
        if case_name not in case_specs or case_name in seen:
            raise ValueError("infrastructure sensitivity scenario case mismatch")
        seen.add(case_name)
        declared = case_specs[case_name]
        for field, expected_value in asdict(declared).items():
            if raw_case.get(field) != expected_value:
                raise ValueError("infrastructure sensitivity scenario parameter mismatch")
        raw_scenarios = raw_case.get("scenarios")
        if not isinstance(raw_scenarios, list) or len(raw_scenarios) != len(
            execution.seeds
        ):
            raise ValueError("infrastructure sensitivity scenario entries are incomplete")
        artifacts: list[FrozenHourlyScenario] = []
        for generation_seed, raw_scenario_value in zip(
            execution.seeds, raw_scenarios, strict=True
        ):
            raw_scenario = _mapping(raw_scenario_value, "infrastructure scenario")
            if raw_scenario.get("generation_seed") != generation_seed:
                raise ValueError("infrastructure sensitivity generation-seed mismatch")
            relative = Path(str(raw_scenario.get("relative_path", "")))
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("infrastructure scenario path must remain relative")
            artifact = load_frozen_hourly_scenario(root / relative)
            if (
                artifact.episode_seed != raw_scenario.get("episode_seed")
                or artifact.scenario_hash != raw_scenario.get("scenario_hash")
            ):
                raise ValueError("infrastructure sensitivity scenario hash mismatch")
            config = load_hourly_environment_config(artifact.config_document)
            if not math.isclose(config.pue, declared.pue, abs_tol=1e-12):
                raise ValueError("infrastructure sensitivity frozen PUE mismatch")
            if (
                config.node_fixed_overhead_power_case
                != declared.node_fixed_overhead_power_case
                or config.calibration_power_case != "nominal"
            ):
                raise ValueError("infrastructure sensitivity frozen power-case mismatch")
            no_dr = _mapping(
                artifact.metadata.get("no_dr_baseline"),
                "infrastructure frozen no-DR baseline",
            )
            if (
                float(no_dr.get("deadline_miss_gpu_h", math.inf)) > 1e-9
                or float(no_dr.get("terminal_backlog_gpu_h", math.inf)) > 1e-9
            ):
                raise ValueError(
                    "infrastructure sensitivity frozen scenario fails no-DR service"
                )
            artifacts.append(artifact)
        artifacts_by_case[case_name] = artifacts
    if seen != set(case_specs):
        raise ValueError("infrastructure sensitivity scenario index has incomplete cases")
    _validate_pairing(artifacts_by_case, seeds=execution.seeds)
    return artifacts_by_case, index


def _solve_worker(
    payload: tuple[str, dict[str, Any], int, str, tuple[int, ...]],
) -> pd.DataFrame:
    case_name, raw_case, generation_seed, artifact_path, durations_h = payload
    case = InfrastructureCaseSpecification(
        name=str(raw_case["name"]),
        pue=_pue(raw_case["pue"]),
        node_fixed_overhead_power_case=_power_case(
            raw_case["node_fixed_overhead_power_case"]
        ),
    )
    artifact = load_frozen_hourly_scenario(artifact_path)
    config = load_hourly_environment_config(artifact.config_document)
    frame = solve_frozen_pi_frontier(artifact, durations_h=durations_h)
    frame["capacity_layer"] = "perfect_information_infrastructure_sensitivity"
    frame.insert(0, "infrastructure_case", case_name)
    frame.insert(1, "generation_seed", generation_seed)
    frame.insert(2, "pue", case.pue)
    frame.insert(
        3,
        "node_fixed_overhead_power_case",
        case.node_fixed_overhead_power_case,
    )
    frame.insert(4, "node_fixed_overhead_w", config.node_fixed_overhead_w)
    return frame


def validate_infrastructure_sensitivity_frontier(
    frontier: pd.DataFrame,
    execution: InfrastructureSensitivityExecution,
    design: InfrastructureSensitivityDesign,
) -> None:
    """Fail closed on missing cases, seeds, durations or non-optimal solves."""

    required = {
        "infrastructure_case",
        "generation_seed",
        "duration_h",
        "perfect_information_capacity_kw",
        "perfect_information_status",
        "pue",
        "node_fixed_overhead_power_case",
        "node_fixed_overhead_w",
    }
    missing = sorted(required - set(frontier))
    if missing:
        raise ValueError(f"infrastructure sensitivity frontier is missing: {missing}")
    cases = _case_map(design)
    expected_rows = len(cases) * len(execution.seeds) * len(execution.durations_h)
    if set(frontier["infrastructure_case"]) != set(cases):
        raise ValueError("infrastructure sensitivity frontier has incomplete cases")
    if len(frontier) != expected_rows or frontier.duplicated(
        ["infrastructure_case", "generation_seed", "duration_h"]
    ).any():
        raise ValueError("infrastructure sensitivity frontier has missing or duplicate rows")
    if set(frontier["generation_seed"]) != set(execution.seeds):
        raise ValueError("infrastructure sensitivity frontier has incomplete seeds")
    if set(frontier["duration_h"]) != set(execution.durations_h):
        raise ValueError("infrastructure sensitivity frontier has incomplete durations")
    if set(frontier["perfect_information_status"]) != {"optimal"}:
        raise ValueError("infrastructure sensitivity frontier contains a non-optimal solve")
    for case_name, case_frontier in frontier.groupby(
        "infrastructure_case", sort=False
    ):
        validate_pi_frontier(case_frontier)
        case = cases[str(case_name)]
        pue_values = case_frontier["pue"].astype(float).unique()
        overhead_cases = set(case_frontier["node_fixed_overhead_power_case"])
        if (
            len(pue_values) != 1
            or not math.isclose(float(pue_values[0]), case.pue, abs_tol=1e-12)
            or overhead_cases != {case.node_fixed_overhead_power_case}
        ):
            raise ValueError("infrastructure sensitivity frontier metadata mismatch")


def _add_paired_reference_columns(frontier: pd.DataFrame) -> pd.DataFrame:
    reference = frontier.loc[
        frontier["infrastructure_case"] == "reference",
        ["generation_seed", "duration_h", "perfect_information_capacity_kw"],
    ].rename(
        columns={
            "perfect_information_capacity_kw": "reference_perfect_information_capacity_kw"
        }
    )
    paired = frontier.merge(
        reference,
        on=["generation_seed", "duration_h"],
        how="left",
        validate="many_to_one",
    )
    if paired["reference_perfect_information_capacity_kw"].isna().any():
        raise ValueError("infrastructure sensitivity cannot pair the reference case")
    paired["paired_capacity_delta_kw"] = (
        paired["perfect_information_capacity_kw"]
        - paired["reference_perfect_information_capacity_kw"]
    )
    denominator = paired["reference_perfect_information_capacity_kw"]
    paired["paired_capacity_ratio"] = paired["perfect_information_capacity_kw"].div(
        denominator.where(denominator.abs() > 1e-12)
    )
    return paired


def _summarize_boundaries(
    frontier: pd.DataFrame,
    execution: InfrastructureSensitivityExecution,
    design: InfrastructureSensitivityDesign,
) -> pd.DataFrame:
    cases = _case_map(design)
    frames: list[pd.DataFrame] = []
    for case_name, case_frontier in frontier.groupby(
        "infrastructure_case", sort=False
    ):
        boundary = summarize_pi_firm_boundary(
            case_frontier,
            reliability_targets=[execution.reliability_target],
            confidence_level=execution.confidence_level,
            nominal_flexibility_fraction=execution.nominal_flexibility_fraction,
        )
        case = cases[str(case_name)]
        overhead_values = case_frontier["node_fixed_overhead_w"].astype(float).unique()
        if len(overhead_values) != 1:
            raise ValueError("infrastructure case has multiple node-overhead values")
        boundary.insert(0, "infrastructure_case", case.name)
        boundary.insert(1, "pue", case.pue)
        boundary.insert(
            2,
            "node_fixed_overhead_power_case",
            case.node_fixed_overhead_power_case,
        )
        boundary.insert(3, "node_fixed_overhead_w", float(overhead_values[0]))
        frames.append(boundary)
    combined = pd.concat(frames, ignore_index=True)
    reference = combined.loc[
        combined["infrastructure_case"] == "reference",
        ["duration_h", "perfect_information_firm_capacity_kw"],
    ].rename(
        columns={
            "perfect_information_firm_capacity_kw": (
                "reference_perfect_information_firm_capacity_kw"
            )
        }
    )
    combined = combined.merge(
        reference, on="duration_h", how="left", validate="many_to_one"
    )
    combined["firm_capacity_delta_from_reference_kw"] = (
        combined["perfect_information_firm_capacity_kw"]
        - combined["reference_perfect_information_firm_capacity_kw"]
    )
    return combined


def compute_and_save_infrastructure_sensitivity(
    scenario_directory: str | Path,
    *,
    specification: str | Path,
    output_directory: str | Path,
    workers: int = 1,
) -> dict[str, str | int]:
    """Solve and atomically persist the paired development PI sensitivity."""

    if isinstance(workers, bool) or not isinstance(workers, int) or workers <= 0:
        raise ValueError("infrastructure sensitivity workers must be positive")
    specification_path = Path(specification)
    execution = load_infrastructure_sensitivity_execution(specification_path)
    design = load_infrastructure_sensitivity_design(execution.case_specification)
    gate = _validate_service_gate(execution, design)
    artifacts_by_case, scenario_index = _load_scenario_index(
        scenario_directory,
        specification_path=specification_path,
        execution=execution,
        design=design,
    )
    cases = _case_map(design)
    payloads = [
        (
            case_name,
            asdict(cases[case_name]),
            generation_seed,
            str(artifact.directory),
            execution.durations_h,
        )
        for case_name, artifacts in artifacts_by_case.items()
        for generation_seed, artifact in zip(execution.seeds, artifacts, strict=True)
    ]
    worker_count = min(workers, len(payloads))
    started_at = time.monotonic()
    if worker_count == 1:
        frames: list[pd.DataFrame] = []
        for completed, payload in enumerate(payloads, start=1):
            frames.append(_solve_worker(payload))
            _report_progress(
                "Infrastructure PI sensitivity",
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
                    "Infrastructure PI sensitivity",
                    completed=completed,
                    total=len(payloads),
                    started_at=started_at,
                )
        frames = [frame for frame in completed_frames if frame is not None]
    frontier = pd.concat(frames, ignore_index=True)
    validate_infrastructure_sensitivity_frontier(frontier, execution, design)
    frontier = _add_paired_reference_columns(frontier)
    boundary = _summarize_boundaries(frontier, execution, design)

    output = Path(output_directory)
    temporary = output.parent / f".{output.name}.incomplete"
    if output.exists():
        raise FileExistsError(f"refusing to overwrite infrastructure result: {output}")
    if temporary.exists():
        raise FileExistsError(f"incomplete infrastructure result exists: {temporary}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary.mkdir()
    frontier_path = temporary / "infrastructure_pi_frontier.parquet"
    boundary_path = temporary / "infrastructure_pi_firm_boundary.parquet"
    manifest_path = temporary / "infrastructure_sensitivity.json"
    frontier.to_parquet(frontier_path, index=False)
    boundary.to_parquet(boundary_path, index=False)
    all_artifacts = [
        artifact for artifacts in artifacts_by_case.values() for artifact in artifacts
    ]
    manifest = {
        "schema_version": 1,
        "capacity_layer": "perfect_information_infrastructure_sensitivity",
        "evidence_scope": "development_only",
        "design": execution.design,
        "specification": str(specification_path),
        "specification_sha256": sha256_file(specification_path),
        "case_specification": str(execution.case_specification),
        "case_specification_sha256": sha256_file(execution.case_specification),
        "service_gate_manifest": str(execution.service_gate_manifest),
        "service_gate_manifest_sha256": sha256_file(execution.service_gate_manifest),
        "service_gate": gate,
        "scenario_index": str(Path(scenario_directory) / _SCENARIO_INDEX_NAME),
        "scenario_index_sha256": sha256_file(
            Path(scenario_directory) / _SCENARIO_INDEX_NAME
        ),
        "scenario_index_analysis_git_commit": scenario_index.get(
            "analysis_git_commit"
        ),
        "development_seed_range": list(execution.development_seed_range),
        "durations_h": list(execution.durations_h),
        "reliability_target": execution.reliability_target,
        "confidence_level": execution.confidence_level,
        "nominal_flexibility_fraction": execution.nominal_flexibility_fraction,
        "case_count": len(cases),
        "scenario_count_per_case": len(execution.seeds),
        "scenario_count": len(all_artifacts),
        "row_count": len(frontier),
        "cases": [asdict(case) for case in design.cases],
        "worker_count": worker_count,
        "solver": {"name": "HIGHS", "threads_per_worker": HIGHS_THREADS_PER_SOLVE},
        "frontier": str(output / frontier_path.name),
        "frontier_sha256": sha256_file(frontier_path),
        "firm_boundary": str(output / boundary_path.name),
        "firm_boundary_sha256": sha256_file(boundary_path),
        "provenance": optimization_provenance(all_artifacts),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(output)
    return {
        "case_count": len(cases),
        "scenario_count": len(all_artifacts),
        "row_count": len(frontier),
        "frontier": str(output / frontier_path.name),
        "firm_boundary": str(output / boundary_path.name),
        "manifest": str(output / manifest_path.name),
    }
