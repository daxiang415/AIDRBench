"""Sparse sensitivity schema and mandatory no-DR service-feasibility gate."""

from __future__ import annotations

import copy
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import yaml

from aidrbench.data.splits import sha256_file
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv


def _fraction(value: object, name: str, *, allow_zero: bool = True) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be in [0, 1]")
    if not allow_zero and result == 0.0:
        raise ValueError(f"{name} must be in (0, 1]")
    return result


def _positive(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be positive")
    return result


@dataclass(frozen=True, slots=True)
class SensitivityCaseSpecification:
    """One explicitly named point in the sparse factorial design."""

    name: str
    flexible_arrival_utilization: float
    rigid_gpu_utilization: float
    deadline_slack_scale: float

    def __post_init__(self) -> None:
        if not self.name or not self.name.replace("_", "").isalnum():
            raise ValueError("sensitivity case name must be alphanumeric with underscores")
        _fraction(
            self.flexible_arrival_utilization,
            "flexible_arrival_utilization",
            allow_zero=False,
        )
        _fraction(self.rigid_gpu_utilization, "rigid_gpu_utilization")
        _positive(self.deadline_slack_scale, "deadline_slack_scale")


@dataclass(frozen=True, slots=True)
class SparseSensitivitySpecification:
    """Predeclared sparse design; it is intentionally not a Cartesian product."""

    schema_version: Literal[1]
    design: Literal["sparse_factorial"]
    base_config: Path
    require_no_dr_service_feasibility: Literal[True]
    cases: tuple[SensitivityCaseSpecification, ...]

    def __post_init__(self) -> None:
        if self.schema_version != 1 or self.design != "sparse_factorial":
            raise ValueError("unsupported sensitivity schema")
        if self.require_no_dr_service_feasibility is not True:
            raise ValueError("sensitivity schema must require no-DR service feasibility")
        if not self.cases:
            raise ValueError("sensitivity schema must declare at least one case")
        names = [case.name for case in self.cases]
        if len(set(names)) != len(names):
            raise ValueError("sensitivity case names must be unique")


def load_sparse_sensitivity_specification(
    source: str | Path | Mapping[str, Any],
) -> SparseSensitivitySpecification:
    """Load and strictly validate a sparse-factorial sensitivity document."""

    if isinstance(source, str | Path):
        source_path = Path(source)
        document = yaml.safe_load(source_path.read_text(encoding="utf-8"))
        base_directory = source_path.parent
    else:
        document = dict(source)
        base_directory = Path.cwd()
    if not isinstance(document, Mapping):
        raise ValueError("sensitivity specification must be a mapping")
    required = {
        "schema_version",
        "design",
        "base_config",
        "require_no_dr_service_feasibility",
        "cases",
    }
    if set(document) != required:
        raise ValueError("sensitivity specification has missing or unknown root fields")
    raw_cases = document["cases"]
    if not isinstance(raw_cases, list):
        raise ValueError("sensitivity cases must be a list")
    case_fields = set(SensitivityCaseSpecification.__dataclass_fields__)
    cases: list[SensitivityCaseSpecification] = []
    for raw in raw_cases:
        if not isinstance(raw, Mapping) or set(raw) != case_fields:
            raise ValueError("sensitivity case has missing or unknown fields")
        cases.append(SensitivityCaseSpecification(**dict(raw)))
    base_config = Path(str(document["base_config"]))
    if not base_config.is_absolute():
        repository_candidate = Path.cwd() / base_config
        local_candidate = base_directory / base_config
        base_config = (
            repository_candidate
            if repository_candidate.is_file()
            else local_candidate
        )
    return SparseSensitivitySpecification(
        schema_version=document["schema_version"],
        design=document["design"],
        base_config=base_config,
        require_no_dr_service_feasibility=document[
            "require_no_dr_service_feasibility"
        ],
        cases=tuple(cases),
    )


def apply_sensitivity_case(
    base_document: Mapping[str, Any],
    case: SensitivityCaseSpecification,
) -> dict[str, Any]:
    """Apply only the three declared sensitivity dimensions to a base config."""

    document = copy.deepcopy(dict(base_document))
    workload = document.get("workload")
    virtual_dc = document.get("virtual_datacenter")
    if not isinstance(workload, dict) or not isinstance(virtual_dc, dict):
        raise ValueError("sensitivity base config lacks workload/virtual_datacenter mappings")
    workload.pop("target_total_utilization", None)
    virtual_dc.pop("target_total_utilization", None)
    virtual_dc.pop("target_flexible_utilization", None)
    workload["flexible_arrival_utilization"] = case.flexible_arrival_utilization
    workload["deadline_slack_scale"] = case.deadline_slack_scale
    virtual_dc["rigid_gpu_utilization"] = case.rigid_gpu_utilization
    return document


def _disable_demand_response(document: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy configured for the mandatory ordinary-service gate."""

    result = copy.deepcopy(dict(document))
    dr = result.get("dr")
    if not isinstance(dr, dict):
        raise ValueError("sensitivity base config lacks a dr mapping")
    dr["event_reduction_kw"] = 0.0
    return result


def check_sparse_sensitivity_no_dr_feasibility(
    specification: str | Path | Mapping[str, Any],
    *,
    seeds: Sequence[int],
    output_directory: str | Path,
) -> dict[str, str | int | bool]:
    """Reject sensitivity cases whose no-DR baseline violates service criteria."""

    spec = load_sparse_sensitivity_specification(specification)
    if not seeds or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise ValueError("no-DR feasibility gate requires integer seeds")
    base_document = yaml.safe_load(spec.base_config.read_text(encoding="utf-8"))
    if not isinstance(base_document, Mapping):
        raise ValueError("sensitivity base config must be a mapping")
    rows: list[dict[str, Any]] = []
    for case in spec.cases:
        document = _disable_demand_response(
            apply_sensitivity_case(base_document, case)
        )
        for seed in seeds:
            env = HourlyCommunityAIDemandResponseEnv(document)
            env.reset(seed=seed)
            snapshot = env.full_horizon_planning_snapshot()
            total_arrivals = max(snapshot.total_arrival_gpu_h, 1e-9)
            deadline_miss_rate = snapshot.baseline_deadline_miss_gpu_h / total_arrivals
            terminal_backlog_fraction = snapshot.baseline_terminal_backlog_gpu_h / total_arrivals
            service_feasible = (
                deadline_miss_rate <= env.config.reward.max_deadline_miss_rate + 1e-12
                and terminal_backlog_fraction
                <= env.config.reward.max_terminal_backlog_fraction + 1e-12
            )
            rows.append(
                {
                    "case": case.name,
                    "seed": seed,
                    **asdict(case),
                    "baseline_deadline_miss_rate": deadline_miss_rate,
                    "baseline_terminal_backlog_fraction": terminal_backlog_fraction,
                    "service_feasible": service_feasible,
                }
            )
    table = pd.DataFrame.from_records(rows)
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    table_path = output / "no_dr_service_feasibility.parquet"
    manifest_path = output / "no_dr_service_feasibility.json"
    table.to_parquet(table_path, index=False)
    all_feasible = bool(table["service_feasible"].all())
    specification_path = Path(specification) if isinstance(specification, str | Path) else None
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "design": spec.design,
                "specification": (
                    str(specification_path) if specification_path is not None else None
                ),
                "specification_sha256": (
                    sha256_file(specification_path)
                    if specification_path is not None
                    else None
                ),
                "base_config": str(spec.base_config),
                "base_config_sha256": sha256_file(spec.base_config),
                "case_count": len(spec.cases),
                "seeds": list(seeds),
                "all_cases_service_feasible": all_feasible,
                "downstream_sensitivity_execution_allowed": all_feasible,
                "table": str(table_path),
                "table_sha256": sha256_file(table_path),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if not all_feasible:
        raise RuntimeError(
            "one or more sensitivity cases fail no-DR service feasibility; "
            f"see {table_path}"
        )
    return {
        "manifest": str(manifest_path),
        "table": str(table_path),
        "case_count": len(spec.cases),
        "all_cases_service_feasible": all_feasible,
    }
