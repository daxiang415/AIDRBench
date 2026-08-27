"""Paired climate-zone community-profile sensitivity on development scenarios.

The analysis changes only the NREL EULP mixed community profile while holding
the workload, hardware, event process, controller specification and scenario
seed fixed.  Climate zones are treated as modelled profile archetypes rather
than geocoded sites or feeder measurements.
"""

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
from typing import Any, Literal

import pandas as pd
import yaml

from aidrbench.controllers.robust_mpc_spec import (
    load_robust_mpc_specification,
    robust_mpc_specification_sha256,
)
from aidrbench.data.frozen_scenarios import (
    FrozenHourlyScenario,
    freeze_hourly_scenario,
    load_frozen_hourly_scenario,
)
from aidrbench.data.splits import sha256_file
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv
from aidrbench.envs.hourly_config import load_hourly_environment_config
from aidrbench.evaluation.firm_flexibility import FirmFlexibilityCriteria
from aidrbench.evaluation.frozen_causal_certificate import (
    _git_commit,
    evaluate_frozen_causal_candidate,
)
from aidrbench.evaluation.pi_frontier import (
    solve_frozen_pi_frontier,
    summarize_pi_firm_boundary,
    validate_pi_frontier,
)
from aidrbench.evaluation.provenance import optimization_provenance

_SCENARIO_INDEX_NAME = "community_profile_sensitivity_scenarios.json"
_DESIGN_FIELDS = {
    "schema_version",
    "design",
    "base_config",
    "profile_split_manifest",
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
    "controller_config",
    "reference_selection",
    "causal_notice_h",
    "causal_durations_h",
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


def _seed_range(value: object, name: str) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{name} must be a two-element list")
    start, stop = value
    if (
        isinstance(start, bool)
        or isinstance(stop, bool)
        or not isinstance(start, int)
        or not isinstance(stop, int)
        or start < 0
        or stop < start
    ):
        raise ValueError(f"{name} must contain increasing non-negative integers")
    return start, stop


def _durations(value: object, name: str) -> tuple[int, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    result = tuple(value)
    if (
        not result
        or any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in result)
        or tuple(sorted(set(result))) != result
    ):
        raise ValueError(f"{name} must contain sorted unique positive integers")
    return result


@dataclass(frozen=True, slots=True)
class CommunityProfileCaseSpecification:
    """One mixed-use climate-zone profile archetype."""

    name: str
    profile_id: str
    climate_zone: str

    def __post_init__(self) -> None:
        if not self.name or not self.name.replace("_", "").isalnum():
            raise ValueError("community-profile case name must be alphanumeric with underscores")
        if not self.profile_id.startswith("eulp_mixed_"):
            raise ValueError("community-profile sensitivity requires an eulp_mixed profile")
        if not self.climate_zone or self.profile_id.lower() != (
            f"eulp_mixed_{self.climate_zone.lower()}"
        ):
            raise ValueError("community-profile ID and climate zone do not agree")


@dataclass(frozen=True, slots=True)
class CommunityProfileSensitivityDesign:
    """Paired design that changes one community-profile factor only."""

    schema_version: Literal[1]
    design: Literal["paired_climate_zone_profiles"]
    base_config: Path
    profile_split_manifest: Path
    require_no_dr_service_feasibility: Literal[True]
    cases: tuple[CommunityProfileCaseSpecification, ...]

    def __post_init__(self) -> None:
        if self.schema_version != 1 or self.design != "paired_climate_zone_profiles":
            raise ValueError("unsupported community-profile sensitivity design")
        if self.require_no_dr_service_feasibility is not True:
            raise ValueError("community-profile sensitivity must require the no-DR gate")
        names = [case.name for case in self.cases]
        profiles = [case.profile_id for case in self.cases]
        if len(self.cases) < 2 or len(names) != len(set(names)):
            raise ValueError("community-profile cases must contain unique names")
        if len(profiles) != len(set(profiles)):
            raise ValueError("community-profile cases must contain unique profiles")
        references = [case for case in self.cases if case.name == "reference_3a"]
        if len(references) != 1 or references[0].profile_id != "eulp_mixed_3a":
            raise ValueError("community-profile sensitivity requires reference_3a")


@dataclass(frozen=True, slots=True)
class CommunityProfileSensitivityExecution:
    """Fail-closed development-only execution contract."""

    schema_version: Literal[1]
    design: Literal["paired_climate_zone_pi_and_fixed_causal"]
    case_specification: Path
    service_gate_manifest: Path
    service_gate_seed_range: tuple[int, int]
    development_seed_range: tuple[int, int]
    durations_h: tuple[int, ...]
    reliability_target: float
    confidence_level: float
    nominal_flexibility_fraction: float
    controller_config: Path
    reference_selection: Path
    causal_notice_h: int
    causal_durations_h: tuple[int, ...]

    def __post_init__(self) -> None:
        if self.schema_version != 1 or self.design != (
            "paired_climate_zone_pi_and_fixed_causal"
        ):
            raise ValueError("unsupported community-profile sensitivity execution")
        _seed_range(list(self.service_gate_seed_range), "service_gate_seed_range")
        _seed_range(list(self.development_seed_range), "development_seed_range")
        _durations(list(self.durations_h), "durations_h")
        _durations(list(self.causal_durations_h), "causal_durations_h")
        if not set(self.causal_durations_h).issubset(self.durations_h):
            raise ValueError("causal durations must be a subset of PI durations")
        if isinstance(self.causal_notice_h, bool) or self.causal_notice_h < 0:
            raise ValueError("causal_notice_h must be a non-negative integer")
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


def _load_profile_memberships(path: Path) -> set[str]:
    document = _mapping(
        yaml.safe_load(path.read_text(encoding="utf-8")), "community profile split"
    )
    strata = _mapping(document.get("supplementary_profile_strata"), "profile strata")
    profiles: set[str] = set()
    for values in strata.values():
        if not isinstance(values, list):
            raise ValueError("community profile stratum must be a list")
        profiles.update(str(value) for value in values)
    return profiles


def load_community_profile_sensitivity_design(
    source: str | Path | Mapping[str, Any],
) -> CommunityProfileSensitivityDesign:
    """Load and strictly validate the climate-zone case design."""

    if isinstance(source, str | Path):
        source_path = Path(source)
        document = _mapping(
            yaml.safe_load(source_path.read_text(encoding="utf-8")),
            "community-profile sensitivity design",
        )
        source_directory = source_path.parent
    else:
        document = _mapping(source, "community-profile sensitivity design")
        source_directory = Path.cwd()
    if set(document) != _DESIGN_FIELDS:
        raise ValueError("community-profile sensitivity design has missing or unknown fields")
    raw_cases = document["cases"]
    if not isinstance(raw_cases, list):
        raise ValueError("community-profile sensitivity cases must be a list")
    case_fields = set(CommunityProfileCaseSpecification.__dataclass_fields__)
    cases: list[CommunityProfileCaseSpecification] = []
    for raw in raw_cases:
        case = _mapping(raw, "community-profile sensitivity case")
        if set(case) != case_fields:
            raise ValueError("community-profile case has missing or unknown fields")
        cases.append(
            CommunityProfileCaseSpecification(
                name=str(case["name"]),
                profile_id=str(case["profile_id"]),
                climate_zone=str(case["climate_zone"]),
            )
        )
    profile_manifest = _resolve_path(
        document["profile_split_manifest"], source_directory=source_directory
    )
    available = _load_profile_memberships(profile_manifest)
    missing = sorted({case.profile_id for case in cases} - available)
    if missing:
        raise ValueError(f"community-profile cases are absent from the split manifest: {missing}")
    return CommunityProfileSensitivityDesign(
        schema_version=document["schema_version"],
        design=document["design"],
        base_config=_resolve_path(document["base_config"], source_directory=source_directory),
        profile_split_manifest=profile_manifest,
        require_no_dr_service_feasibility=document["require_no_dr_service_feasibility"],
        cases=tuple(cases),
    )


def load_community_profile_sensitivity_execution(
    source: str | Path | Mapping[str, Any],
) -> CommunityProfileSensitivityExecution:
    """Load the execution contract that binds profiles, gate and seed set."""

    if isinstance(source, str | Path):
        source_path = Path(source)
        document = _mapping(
            yaml.safe_load(source_path.read_text(encoding="utf-8")),
            "community-profile sensitivity execution",
        )
        source_directory = source_path.parent
    else:
        document = _mapping(source, "community-profile sensitivity execution")
        source_directory = Path.cwd()
    if set(document) != _EXECUTION_FIELDS:
        raise ValueError("community-profile sensitivity execution has missing or unknown fields")
    return CommunityProfileSensitivityExecution(
        schema_version=document["schema_version"],
        design=document["design"],
        case_specification=_resolve_path(
            document["case_specification"], source_directory=source_directory
        ),
        service_gate_manifest=_resolve_path(
            document["service_gate_manifest"], source_directory=source_directory
        ),
        service_gate_seed_range=_seed_range(
            document["service_gate_seed_range"], "service_gate_seed_range"
        ),
        development_seed_range=_seed_range(
            document["development_seed_range"], "development_seed_range"
        ),
        durations_h=_durations(document["durations_h"], "durations_h"),
        reliability_target=_fraction(
            document["reliability_target"], "reliability_target", strict=True
        ),
        confidence_level=_fraction(
            document["confidence_level"], "confidence_level", strict=True
        ),
        nominal_flexibility_fraction=_fraction(
            document["nominal_flexibility_fraction"], "nominal_flexibility_fraction"
        ),
        controller_config=_resolve_path(
            document["controller_config"], source_directory=source_directory
        ),
        reference_selection=_resolve_path(
            document["reference_selection"], source_directory=source_directory
        ),
        causal_notice_h=int(document["causal_notice_h"]),
        causal_durations_h=_durations(
            document["causal_durations_h"], "causal_durations_h"
        ),
    )


def _case_map(
    design: CommunityProfileSensitivityDesign,
) -> dict[str, CommunityProfileCaseSpecification]:
    return {case.name: case for case in design.cases}


def apply_community_profile_case(
    base_document: Mapping[str, Any],
    case: CommunityProfileCaseSpecification,
) -> dict[str, Any]:
    """Change only the selected community profile."""

    document = copy.deepcopy(dict(base_document))
    community = _mapping(document.get("community"), "community")
    if str(community.get("source")) != "nrel_eulp":
        raise ValueError("community-profile sensitivity requires community.source=nrel_eulp")
    if not community.get("path"):
        raise ValueError("community-profile sensitivity requires a processed profile table")
    community["profile_id"] = case.profile_id
    document["community"] = community
    return document


def _disable_demand_response(document: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(document))
    dr = _mapping(result.get("dr"), "dr")
    dr["event_reduction_kw"] = 0.0
    result["dr"] = dr
    return result


def _report_progress(
    label: str, *, completed: int, total: int, started_at: float
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


def check_community_profile_no_dr_feasibility(
    specification: str | Path,
    *,
    seeds: Sequence[int],
    output_directory: str | Path,
) -> dict[str, str | int | bool]:
    """Gate every profile on ordinary no-DR service feasibility."""

    specification_path = Path(specification)
    design = load_community_profile_sensitivity_design(specification_path)
    if not seeds or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise ValueError("community-profile no-DR gate requires integer seeds")
    base_document = _mapping(
        yaml.safe_load(design.base_config.read_text(encoding="utf-8")),
        "community-profile base config",
    )
    rows: list[dict[str, Any]] = []
    for case in design.cases:
        document = _disable_demand_response(apply_community_profile_case(base_document, case))
        for seed in seeds:
            env = HourlyCommunityAIDemandResponseEnv(document)
            env.reset(seed=seed)
            snapshot = env.full_horizon_planning_snapshot()
            total_arrivals = max(snapshot.total_arrival_gpu_h, 1e-9)
            miss_fraction = snapshot.baseline_deadline_miss_gpu_h / total_arrivals
            backlog_fraction = snapshot.baseline_terminal_backlog_gpu_h / total_arrivals
            feasible = (
                snapshot.baseline_deadline_miss_gpu_h <= 1e-9
                and snapshot.baseline_terminal_backlog_gpu_h <= 1e-9
            )
            rows.append(
                {
                    "case": case.name,
                    "seed": seed,
                    **asdict(case),
                    "community_episode_start": str(env._community["timestamp"].iloc[0]),
                    "gross_community_peak_kw": float(
                        env._community["community_load_kw"].max()
                    ),
                    "net_community_peak_kw": float(
                        env._community["net_community_load_kw"].max()
                    ),
                    "pv_generation_kwh": float(
                        env._community["pv_generation_kw"].sum() * env.config.timestep_hours
                    ),
                    "baseline_deadline_miss_rate": miss_fraction,
                    "baseline_terminal_backlog_fraction": backlog_fraction,
                    "service_feasible": feasible,
                }
            )
    table = pd.DataFrame.from_records(rows)
    output = Path(output_directory)
    temporary = output.parent / f".{output.name}.incomplete"
    if output.exists():
        raise FileExistsError(f"refusing to overwrite community-profile service gate: {output}")
    if temporary.exists():
        raise FileExistsError(
            f"incomplete community-profile service gate exists: {temporary}"
        )
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
        "interpretation": "climate_zone_profile_archetypes_not_geocoded_sites",
        "specification": str(specification_path),
        "specification_sha256": sha256_file(specification_path),
        "base_config": str(design.base_config),
        "base_config_sha256": sha256_file(design.base_config),
        "profile_split_manifest": str(design.profile_split_manifest),
        "profile_split_manifest_sha256": sha256_file(design.profile_split_manifest),
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
        raise RuntimeError("one or more community profiles fail the no-DR service gate")
    return {
        "manifest": str(output / manifest_path.name),
        "table": str(final_table),
        "case_count": len(design.cases),
        "all_cases_service_feasible": all_feasible,
    }


def _validate_service_gate(
    execution: CommunityProfileSensitivityExecution,
    design: CommunityProfileSensitivityDesign,
) -> dict[str, Any]:
    path = execution.service_gate_manifest
    if not path.is_file():
        raise FileNotFoundError(f"community-profile service gate is missing: {path}")
    document = _mapping(
        json.loads(path.read_text(encoding="utf-8")), "community-profile service gate"
    )
    expected = {
        "specification_sha256": sha256_file(execution.case_specification),
        "base_config_sha256": sha256_file(design.base_config),
        "profile_split_manifest_sha256": sha256_file(design.profile_split_manifest),
        "case_count": len(design.cases),
        "all_cases_service_feasible": True,
        "downstream_sensitivity_execution_allowed": True,
        "seeds": list(execution.service_gate_seeds),
    }
    if any(document.get(key) != value for key, value in expected.items()):
        raise ValueError("community-profile sensitivity service-gate identity mismatch")
    table_path = Path(str(document.get("table", "")))
    if not table_path.is_absolute() and not table_path.is_file():
        table_path = Path.cwd() / table_path
    if not table_path.is_file() or sha256_file(table_path) != document.get("table_sha256"):
        raise ValueError("community-profile service-gate table hash mismatch")
    table = pd.read_parquet(table_path)
    if set(table.get("case", pd.Series(dtype=str))) != set(_case_map(design)):
        raise ValueError("community-profile service gate has incomplete cases")
    if "service_feasible" not in table or not bool(table["service_feasible"].all()):
        raise ValueError("community-profile service gate contains a failure")
    return document


def _normalized_config_without_profile(artifact: FrozenHourlyScenario) -> str:
    document = copy.deepcopy(artifact.config_document)
    community = _mapping(document.get("community"), "community")
    community["profile_id"] = "__paired_profile__"
    document["community"] = community
    return json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _validate_pairing(
    artifacts_by_case: Mapping[str, Sequence[FrozenHourlyScenario]],
    *,
    seeds: Sequence[int],
    design: CommunityProfileSensitivityDesign,
) -> None:
    if any(len(artifacts) != len(seeds) for artifacts in artifacts_by_case.values()):
        raise ValueError("community-profile cases do not share the seed set")
    cases = _case_map(design)
    for position, _seed in enumerate(seeds):
        paired = {
            case_name: artifacts[position]
            for case_name, artifacts in artifacts_by_case.items()
        }
        episode_seeds = {artifact.episode_seed for artifact in paired.values()}
        arrival_hashes = {
            str(artifact.metadata["files"]["arrivals.parquet"])
            for artifact in paired.values()
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
            for artifact in paired.values()
        }
        random_streams = {
            json.dumps(artifact.metadata["exogenous_random_stream_seeds"], sort_keys=True)
            for artifact in paired.values()
        }
        power_hashes = {
            str(artifact.metadata["power_model"]["sha256"])
            for artifact in paired.values()
        }
        normalized_configs = {
            _normalized_config_without_profile(artifact) for artifact in paired.values()
        }
        if any(
            len(values) != 1
            for values in (
                episode_seeds,
                arrival_hashes,
                event_signatures,
                random_streams,
                power_hashes,
                normalized_configs,
            )
        ):
            raise ValueError(
                "community-profile pairing changed workload, hardware, event or config inputs"
            )
        for case_name, artifact in paired.items():
            config = load_hourly_environment_config(artifact.config_document)
            if config.community_profile_id != cases[case_name].profile_id:
                raise ValueError("community-profile pairing selected the wrong profile")


def freeze_community_profile_sensitivity_scenarios(
    specification: str | Path,
    *,
    output_directory: str | Path,
) -> dict[str, str | int]:
    """Atomically freeze paired scenarios for all climate-zone profiles."""

    specification_path = Path(specification)
    execution = load_community_profile_sensitivity_execution(specification_path)
    design = load_community_profile_sensitivity_design(execution.case_specification)
    gate = _validate_service_gate(execution, design)
    base_document = _mapping(
        yaml.safe_load(design.base_config.read_text(encoding="utf-8")),
        "community-profile base config",
    )
    output = Path(output_directory)
    temporary = output.parent / f".{output.name}.incomplete"
    if output.exists():
        raise FileExistsError(f"refusing to overwrite community-profile scenarios: {output}")
    if temporary.exists():
        raise FileExistsError(f"incomplete community-profile scenarios exist: {temporary}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary.mkdir()
    total = len(design.cases) * len(execution.seeds)
    completed = 0
    started_at = time.monotonic()
    artifacts_by_case: dict[str, list[FrozenHourlyScenario]] = {}
    index_cases: list[dict[str, Any]] = []
    for case in design.cases:
        document = apply_community_profile_case(base_document, case)
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
                    "community_sha256": artifact.metadata["files"]["community.parquet"],
                    "arrivals_sha256": artifact.metadata["files"]["arrivals.parquet"],
                    "relative_path": str(Path(case.name) / artifact.directory.name),
                }
            )
            completed += 1
            _report_progress(
                "Community-profile scenario freeze",
                completed=completed,
                total=total,
                started_at=started_at,
            )
        artifacts_by_case[case.name] = artifacts
        index_cases.append({"case": case.name, **asdict(case), "scenarios": index_scenarios})
    _validate_pairing(
        artifacts_by_case, seeds=execution.seeds, design=design
    )
    index = {
        "schema_version": 1,
        "evidence_scope": "development_only",
        "interpretation": "climate_zone_profile_archetypes_not_geocoded_sites",
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
        "profile_split_manifest": str(design.profile_split_manifest),
        "profile_split_manifest_sha256": sha256_file(design.profile_split_manifest),
        "seeds": list(execution.seeds),
        "case_count": len(design.cases),
        "scenario_count": total,
        "paired_workload_hardware_events": True,
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
    execution: CommunityProfileSensitivityExecution,
    design: CommunityProfileSensitivityDesign,
) -> tuple[dict[str, list[FrozenHourlyScenario]], dict[str, Any]]:
    root = Path(scenario_directory)
    index_path = root / _SCENARIO_INDEX_NAME
    if not index_path.is_file():
        raise FileNotFoundError(f"community-profile scenario index is missing: {index_path}")
    index = _mapping(
        json.loads(index_path.read_text(encoding="utf-8")),
        "community-profile scenario index",
    )
    expected = {
        "specification_sha256": sha256_file(specification_path),
        "case_specification_sha256": sha256_file(execution.case_specification),
        "service_gate_manifest_sha256": sha256_file(execution.service_gate_manifest),
        "base_config_sha256": sha256_file(design.base_config),
        "profile_split_manifest_sha256": sha256_file(design.profile_split_manifest),
        "seeds": list(execution.seeds),
    }
    if any(index.get(key) != value for key, value in expected.items()):
        raise ValueError("community-profile scenario provenance mismatch")
    case_specs = _case_map(design)
    raw_cases = index.get("cases")
    if not isinstance(raw_cases, list):
        raise ValueError("community-profile scenario index lacks cases")
    artifacts_by_case: dict[str, list[FrozenHourlyScenario]] = {}
    seen: set[str] = set()
    for raw_case_value in raw_cases:
        raw_case = _mapping(raw_case_value, "community-profile scenario case")
        case_name = str(raw_case.get("case", ""))
        if case_name not in case_specs or case_name in seen:
            raise ValueError("community-profile scenario case mismatch")
        seen.add(case_name)
        declared = case_specs[case_name]
        for field, expected_value in asdict(declared).items():
            if raw_case.get(field) != expected_value:
                raise ValueError("community-profile scenario parameter mismatch")
        raw_scenarios = raw_case.get("scenarios")
        if not isinstance(raw_scenarios, list) or len(raw_scenarios) != len(execution.seeds):
            raise ValueError("community-profile scenario entries are incomplete")
        artifacts: list[FrozenHourlyScenario] = []
        for generation_seed, raw_scenario_value in zip(
            execution.seeds, raw_scenarios, strict=True
        ):
            raw_scenario = _mapping(raw_scenario_value, "community-profile scenario")
            if raw_scenario.get("generation_seed") != generation_seed:
                raise ValueError("community-profile generation-seed mismatch")
            relative = Path(str(raw_scenario.get("relative_path", "")))
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("community-profile scenario path must remain relative")
            artifact = load_frozen_hourly_scenario(root / relative)
            if (
                artifact.episode_seed != raw_scenario.get("episode_seed")
                or artifact.scenario_hash != raw_scenario.get("scenario_hash")
            ):
                raise ValueError("community-profile scenario hash mismatch")
            no_dr = _mapping(
                artifact.metadata.get("no_dr_baseline"),
                "community-profile frozen no-DR baseline",
            )
            if (
                float(no_dr.get("deadline_miss_gpu_h", math.inf)) > 1e-9
                or float(no_dr.get("terminal_backlog_gpu_h", math.inf)) > 1e-9
            ):
                raise ValueError("community-profile frozen scenario fails no-DR service")
            artifacts.append(artifact)
        artifacts_by_case[case_name] = artifacts
    if seen != set(case_specs):
        raise ValueError("community-profile scenario index has incomplete cases")
    _validate_pairing(artifacts_by_case, seeds=execution.seeds, design=design)
    return artifacts_by_case, index


def _solve_pi_worker(
    payload: tuple[str, dict[str, Any], int, str, tuple[int, ...]],
) -> pd.DataFrame:
    case_name, raw_case, generation_seed, artifact_path, durations_h = payload
    case = CommunityProfileCaseSpecification(
        name=str(raw_case["name"]),
        profile_id=str(raw_case["profile_id"]),
        climate_zone=str(raw_case["climate_zone"]),
    )
    artifact = load_frozen_hourly_scenario(artifact_path)
    frame = solve_frozen_pi_frontier(artifact, durations_h=durations_h)
    frame["capacity_layer"] = "perfect_information_community_profile_sensitivity"
    frame.insert(0, "community_profile_case", case_name)
    frame.insert(1, "generation_seed", generation_seed)
    frame.insert(2, "profile_id", case.profile_id)
    frame.insert(3, "climate_zone", case.climate_zone)
    return frame


def _validate_pi_frontier(
    frontier: pd.DataFrame,
    execution: CommunityProfileSensitivityExecution,
    design: CommunityProfileSensitivityDesign,
) -> None:
    required = {
        "community_profile_case",
        "generation_seed",
        "profile_id",
        "climate_zone",
        "duration_h",
        "perfect_information_capacity_kw",
        "perfect_information_status",
    }
    missing = sorted(required - set(frontier))
    if missing:
        raise ValueError(f"community-profile frontier is missing: {missing}")
    cases = _case_map(design)
    expected_rows = len(cases) * len(execution.seeds) * len(execution.durations_h)
    if set(frontier["community_profile_case"]) != set(cases):
        raise ValueError("community-profile frontier has incomplete cases")
    if len(frontier) != expected_rows or frontier.duplicated(
        ["community_profile_case", "generation_seed", "duration_h"]
    ).any():
        raise ValueError("community-profile frontier has missing or duplicate rows")
    if set(frontier["generation_seed"]) != set(execution.seeds):
        raise ValueError("community-profile frontier has incomplete seeds")
    if set(frontier["duration_h"]) != set(execution.durations_h):
        raise ValueError("community-profile frontier has incomplete durations")
    if set(frontier["perfect_information_status"]) != {"optimal"}:
        raise ValueError("community-profile frontier contains a non-optimal solve")
    for case_name, case_frontier in frontier.groupby("community_profile_case", sort=False):
        validate_pi_frontier(case_frontier)
        case = cases[str(case_name)]
        if set(case_frontier["profile_id"]) != {case.profile_id} or set(
            case_frontier["climate_zone"]
        ) != {case.climate_zone}:
            raise ValueError("community-profile frontier metadata mismatch")


def _add_paired_reference_columns(frontier: pd.DataFrame) -> pd.DataFrame:
    reference = frontier.loc[
        frontier["community_profile_case"] == "reference_3a",
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
        raise ValueError("community-profile frontier cannot pair the reference case")
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
    execution: CommunityProfileSensitivityExecution,
    design: CommunityProfileSensitivityDesign,
) -> pd.DataFrame:
    cases = _case_map(design)
    frames: list[pd.DataFrame] = []
    for case_name, case_frontier in frontier.groupby("community_profile_case", sort=False):
        boundary = summarize_pi_firm_boundary(
            case_frontier,
            reliability_targets=[execution.reliability_target],
            confidence_level=execution.confidence_level,
            nominal_flexibility_fraction=execution.nominal_flexibility_fraction,
        )
        case = cases[str(case_name)]
        boundary.insert(0, "community_profile_case", case.name)
        boundary.insert(1, "profile_id", case.profile_id)
        boundary.insert(2, "climate_zone", case.climate_zone)
        frames.append(boundary)
    combined = pd.concat(frames, ignore_index=True)
    reference = combined.loc[
        combined["community_profile_case"] == "reference_3a",
        ["duration_h", "perfect_information_firm_capacity_kw"],
    ].rename(
        columns={
            "perfect_information_firm_capacity_kw": (
                "reference_perfect_information_firm_capacity_kw"
            )
        }
    )
    combined = combined.merge(reference, on="duration_h", how="left", validate="many_to_one")
    combined["firm_capacity_delta_from_reference_kw"] = (
        combined["perfect_information_firm_capacity_kw"]
        - combined["reference_perfect_information_firm_capacity_kw"]
    )
    return combined


def _load_reference_selection(
    execution: CommunityProfileSensitivityExecution,
) -> tuple[dict[int, float], FirmFlexibilityCriteria, dict[str, Any]]:
    selection = _mapping(
        json.loads(execution.reference_selection.read_text(encoding="utf-8")),
        "reference causal selection",
    )
    if selection.get("selection_dataset_role") != "validation":
        raise ValueError("community-profile causal transfer requires a validation selection")
    if selection.get("controller") != "robust_mpc":
        raise ValueError("community-profile causal transfer requires robust_mpc")
    raw_provenance = _mapping(selection.get("controller_provenance"), "controller provenance")
    specification = load_robust_mpc_specification(execution.controller_config)
    if raw_provenance.get("controller_config_sha256") != sha256_file(
        execution.controller_config
    ) or raw_provenance.get(
        "normalized_specification_sha256"
    ) != robust_mpc_specification_sha256(specification):
        raise ValueError("community-profile causal controller specification mismatch")
    criteria_document = _mapping(selection.get("criteria"), "reference criteria")
    criteria = FirmFlexibilityCriteria(**criteria_document)
    if (
        not math.isclose(criteria.reliability_target, execution.reliability_target)
        or not math.isclose(criteria.confidence_level, execution.confidence_level)
    ):
        raise ValueError("reference causal criteria disagree with sensitivity execution")
    raw_capacities = selection.get("selected_capacities")
    if not isinstance(raw_capacities, list):
        raise ValueError("reference selection lacks selected capacities")
    capacities: dict[int, float] = {}
    for raw_value in raw_capacities:
        raw = _mapping(raw_value, "selected causal capacity")
        duration = int(raw.get("duration_h", -1))
        notice = int(raw.get("notice_h", -1))
        reliability = float(raw.get("reliability_target", math.nan))
        if notice != execution.causal_notice_h or not math.isclose(
            reliability, execution.reliability_target
        ):
            continue
        if duration in execution.causal_durations_h:
            if duration in capacities:
                raise ValueError("reference selection contains duplicate causal capacity")
            capacities[duration] = float(raw["candidate_reduction_kw"])
    if set(capacities) != set(execution.causal_durations_h):
        raise ValueError("reference selection lacks a requested causal duration")
    return capacities, criteria, raw_provenance


def _evaluate_fixed_causal_transfer(
    artifacts_by_case: Mapping[str, Sequence[FrozenHourlyScenario]],
    *,
    execution: CommunityProfileSensitivityExecution,
    design: CommunityProfileSensitivityDesign,
    workers: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    capacities, criteria, selection_provenance = _load_reference_selection(execution)
    controller_specification = load_robust_mpc_specification(execution.controller_config)
    cases = _case_map(design)
    outcome_frames: list[pd.DataFrame] = []
    summaries: list[dict[str, Any]] = []
    started_at = time.monotonic()
    total = len(cases) * len(capacities)
    completed = 0
    for case_name, artifacts in artifacts_by_case.items():
        case = cases[case_name]
        for duration_h, capacity_kw in capacities.items():
            outcomes, summary = evaluate_frozen_causal_candidate(
                artifacts,
                controller_specification=controller_specification,
                duration_h=duration_h,
                notice_h=execution.causal_notice_h,
                requested_reduction_kw=capacity_kw,
                criteria=criteria,
                workers=workers,
            )
            outcomes.insert(0, "community_profile_case", case.name)
            outcomes.insert(1, "profile_id", case.profile_id)
            outcomes.insert(2, "climate_zone", case.climate_zone)
            outcome_frames.append(outcomes)
            summaries.append(
                {
                    "community_profile_case": case.name,
                    "profile_id": case.profile_id,
                    "climate_zone": case.climate_zone,
                    "transfer_interpretation": (
                        "fixed_validation_selected_candidate_development_diagnostic"
                    ),
                    **summary,
                }
            )
            completed += 1
            _report_progress(
                "Community-profile fixed causal transfer",
                completed=completed,
                total=total,
                started_at=started_at,
            )
    summary_table = pd.DataFrame.from_records(summaries)
    # These are transfer diagnostics, not independently selected certificates.
    summary_table = summary_table.rename(columns={"certified": "meets_target_diagnostic"})
    return (
        pd.concat(outcome_frames, ignore_index=True),
        summary_table,
        selection_provenance,
    )


def compute_and_save_community_profile_sensitivity(
    scenario_directory: str | Path,
    *,
    specification: str | Path,
    output_directory: str | Path,
    workers: int = 1,
) -> dict[str, str | int]:
    """Solve PI boundaries and fixed-controller transfer diagnostics."""

    if isinstance(workers, bool) or not isinstance(workers, int) or workers <= 0:
        raise ValueError("community-profile sensitivity workers must be positive")
    specification_path = Path(specification)
    execution = load_community_profile_sensitivity_execution(specification_path)
    design = load_community_profile_sensitivity_design(execution.case_specification)
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
            frames.append(_solve_pi_worker(payload))
            _report_progress(
                "Community-profile PI sensitivity",
                completed=completed,
                total=len(payloads),
                started_at=started_at,
            )
    else:
        completed_frames: list[pd.DataFrame | None] = [None] * len(payloads)
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(_solve_pi_worker, payload): index
                for index, payload in enumerate(payloads)
            }
            for completed, future in enumerate(as_completed(futures), start=1):
                completed_frames[futures[future]] = future.result()
                _report_progress(
                    "Community-profile PI sensitivity",
                    completed=completed,
                    total=len(payloads),
                    started_at=started_at,
                )
        frames = [frame for frame in completed_frames if frame is not None]
    frontier = pd.concat(frames, ignore_index=True)
    _validate_pi_frontier(frontier, execution, design)
    frontier = _add_paired_reference_columns(frontier)
    boundary = _summarize_boundaries(frontier, execution, design)
    causal_outcomes, causal_summary, selection_provenance = _evaluate_fixed_causal_transfer(
        artifacts_by_case,
        execution=execution,
        design=design,
        workers=workers,
    )

    output = Path(output_directory)
    temporary = output.parent / f".{output.name}.incomplete"
    if output.exists():
        raise FileExistsError(f"refusing to overwrite community-profile result: {output}")
    if temporary.exists():
        raise FileExistsError(f"incomplete community-profile result exists: {temporary}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary.mkdir()
    frontier_path = temporary / "community_profile_pi_frontier.parquet"
    boundary_path = temporary / "community_profile_pi_firm_boundary.parquet"
    causal_summary_path = temporary / "community_profile_causal_transfer_summary.parquet"
    causal_outcomes_path = temporary / "community_profile_causal_transfer_outcomes.parquet"
    manifest_path = temporary / "community_profile_sensitivity.json"
    frontier.to_parquet(frontier_path, index=False)
    boundary.to_parquet(boundary_path, index=False)
    causal_summary.to_parquet(causal_summary_path, index=False)
    causal_outcomes.to_parquet(causal_outcomes_path, index=False)
    all_artifacts = [
        artifact for artifacts in artifacts_by_case.values() for artifact in artifacts
    ]
    manifest = {
        "schema_version": 1,
        "capacity_layers": [
            "perfect_information_community_profile_sensitivity",
            "fixed_validation_selected_robust_mpc_transfer_diagnostic",
        ],
        "evidence_scope": "development_only",
        "interpretation": "climate_zone_profile_archetypes_not_geocoded_sites",
        "not_claimed": [
            "named_city_effect",
            "feeder_spatial_effect",
            "locked_certificate",
            "causal_effect_of_climate_zone",
        ],
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
        "scenario_index_git_commit": scenario_index.get("analysis_git_commit"),
        "analysis_git_commit": _git_commit(),
        "controller_config": str(execution.controller_config),
        "controller_config_sha256": sha256_file(execution.controller_config),
        "reference_selection": str(execution.reference_selection),
        "reference_selection_sha256": sha256_file(execution.reference_selection),
        "reference_selection_controller_provenance": selection_provenance,
        "case_count": len(design.cases),
        "scenario_count": len(all_artifacts),
        "unique_scenario_hash_count": len(
            {artifact.scenario_hash for artifact in all_artifacts}
        ),
        "durations_h": list(execution.durations_h),
        "causal_durations_h": list(execution.causal_durations_h),
        "causal_notice_h": execution.causal_notice_h,
        "reliability_target": execution.reliability_target,
        "confidence_level": execution.confidence_level,
        "worker_count": worker_count,
        "outputs": {
            "pi_frontier": str(output / frontier_path.name),
            "pi_frontier_sha256": sha256_file(frontier_path),
            "pi_firm_boundary": str(output / boundary_path.name),
            "pi_firm_boundary_sha256": sha256_file(boundary_path),
            "causal_transfer_summary": str(output / causal_summary_path.name),
            "causal_transfer_summary_sha256": sha256_file(causal_summary_path),
            "causal_transfer_outcomes": str(output / causal_outcomes_path.name),
            "causal_transfer_outcomes_sha256": sha256_file(causal_outcomes_path),
        },
        "optimization_provenance": optimization_provenance(all_artifacts),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(output)
    return {
        "pi_frontier": str(output / frontier_path.name),
        "pi_firm_boundary": str(output / boundary_path.name),
        "causal_transfer_summary": str(output / causal_summary_path.name),
        "causal_transfer_outcomes": str(output / causal_outcomes_path.name),
        "manifest": str(output / manifest_path.name),
        "row_count": len(frontier),
        "causal_summary_row_count": len(causal_summary),
    }
