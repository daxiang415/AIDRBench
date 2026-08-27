"""Climate-zone profile sensitivity of the community PV-hosting consequence."""

from __future__ import annotations

import json
import math
import multiprocessing
import sys
import time
from collections.abc import Mapping
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
import pandas as pd
import yaml

from aidrbench.data.frozen_scenarios import FrozenHourlyScenario, load_frozen_hourly_scenario
from aidrbench.data.splits import sha256_file
from aidrbench.evaluation.community_profile_sensitivity import (
    CommunityProfileSensitivityDesign,
    CommunityProfileSensitivityExecution,
    _load_scenario_index,
    _mapping,
    load_community_profile_sensitivity_design,
    load_community_profile_sensitivity_execution,
)
from aidrbench.evaluation.frozen_causal_certificate import _git_commit
from aidrbench.evaluation.hosting_capacity import CommunityPortfolio, load_community_portfolio
from aidrbench.evaluation.provenance import optimization_provenance
from aidrbench.evaluation.renewable_integration import (
    RenewableIntegrationSolution,
    _build_problem,
    _solution,
    _unit_pv_profile_kw,
    _validate_fraction,
)

_FIELDS = {
    "schema_version",
    "design",
    "community_profile_execution",
    "portfolio",
    "solver",
    "pv_hosting",
    "paired_inference",
}
_WorkerPayload = tuple[
    str,
    str,
    str,
    str,
    dict[str, Any],
    "CommunityProfileRenewableSpecification",
]


def _exact_fields(document: Mapping[str, Any], expected: set[str], name: str) -> None:
    observed = set(document)
    if observed != expected:
        raise ValueError(
            f"{name} fields mismatch; missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )


def _fraction(value: object, name: str, *, strict: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    lower_ok = result > 0.0 if strict else result >= 0.0
    if not math.isfinite(result) or not lower_ok or result >= 1.0:
        interval = "(0, 1)" if strict else "[0, 1)"
        raise ValueError(f"{name} must be in {interval}")
    return result


def _positive(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be positive")
    return result


@dataclass(frozen=True, slots=True)
class CommunityProfileRenewableSpecification:
    """Complete sparse PV-hosting profile-sensitivity contract."""

    schema_version: Literal[1]
    design: Literal["paired_climate_zone_pv_hosting"]
    community_profile_execution: Path
    portfolio_path: Path
    portfolio_sha256: str
    solver_name: Literal["HIGHS"]
    threads_per_process: Literal[1]
    time_limit_seconds: float
    bess_dispatch_mode: Literal["milp_exclusive"]
    dc_scale_of_reference_mix: float
    maximum_pv_curtailment_fraction: float
    maximum_deadline_miss_rate: float
    near_pcc_limit_fraction: float
    confidence_level: float
    familywise_method: Literal["bonferroni"]
    planned_contrast_count: int
    bootstrap_resamples: int
    bootstrap_seed: int

    def __post_init__(self) -> None:
        if self.schema_version != 1 or self.design != "paired_climate_zone_pv_hosting":
            raise ValueError("unsupported community-profile renewable design")
        if len(self.portfolio_sha256) != 64:
            raise ValueError("community-profile renewable portfolio needs SHA-256")
        if self.solver_name != "HIGHS" or self.threads_per_process != 1:
            raise ValueError("community-profile renewable solver must be one-thread HIGHS")
        _positive(self.time_limit_seconds, "time_limit_seconds")
        if self.bess_dispatch_mode != "milp_exclusive":
            raise ValueError("community-profile renewable BESS must use milp_exclusive")
        _positive(self.dc_scale_of_reference_mix, "dc_scale_of_reference_mix")
        _fraction(
            self.maximum_pv_curtailment_fraction,
            "maximum_pv_curtailment_fraction",
        )
        _fraction(self.maximum_deadline_miss_rate, "maximum_deadline_miss_rate")
        if not 0.0 < self.near_pcc_limit_fraction <= 1.0:
            raise ValueError("near_pcc_limit_fraction must be in (0, 1]")
        _fraction(self.confidence_level, "confidence_level", strict=True)
        if self.familywise_method != "bonferroni":
            raise ValueError("community-profile renewable inference requires bonferroni")
        if self.planned_contrast_count <= 0:
            raise ValueError("planned_contrast_count must be positive")
        if self.bootstrap_resamples < 1000 or self.bootstrap_seed < 0:
            raise ValueError("bootstrap needs at least 1000 resamples and a non-negative seed")


def load_community_profile_renewable_specification(
    path: str | Path,
) -> CommunityProfileRenewableSpecification:
    """Load the exact sparse renewable consequence specification."""

    source_path = Path(path)
    document = _mapping(
        yaml.safe_load(source_path.read_text(encoding="utf-8")),
        "community-profile renewable specification",
    )
    _exact_fields(document, _FIELDS, "community-profile renewable specification")
    source_directory = source_path.parent

    def resolve(value: object) -> Path:
        candidate = Path(str(value))
        if candidate.is_absolute():
            return candidate
        repository_candidate = Path.cwd() / candidate
        local_candidate = source_directory / candidate
        return repository_candidate if repository_candidate.exists() else local_candidate

    portfolio = _mapping(document["portfolio"], "community-profile renewable portfolio")
    _exact_fields(portfolio, {"path", "sha256"}, "community-profile renewable portfolio")
    solver = _mapping(document["solver"], "community-profile renewable solver")
    _exact_fields(
        solver,
        {"name", "threads_per_process", "time_limit_seconds", "bess_dispatch_mode"},
        "community-profile renewable solver",
    )
    hosting = _mapping(document["pv_hosting"], "community-profile renewable hosting")
    _exact_fields(
        hosting,
        {
            "dc_scale_of_reference_mix",
            "maximum_pv_curtailment_fraction",
            "maximum_deadline_miss_rate",
            "near_pcc_limit_fraction",
        },
        "community-profile renewable hosting",
    )
    inference = _mapping(document["paired_inference"], "paired inference")
    _exact_fields(
        inference,
        {
            "confidence_level",
            "familywise_method",
            "planned_contrast_count",
            "bootstrap_resamples",
            "bootstrap_seed",
        },
        "paired inference",
    )
    return CommunityProfileRenewableSpecification(
        schema_version=cast(Literal[1], int(document["schema_version"])),
        design=str(document["design"]),  # type: ignore[arg-type]
        community_profile_execution=resolve(document["community_profile_execution"]),
        portfolio_path=resolve(portfolio["path"]),
        portfolio_sha256=str(portfolio["sha256"]),
        solver_name=str(solver["name"]),  # type: ignore[arg-type]
        threads_per_process=int(solver["threads_per_process"]),  # type: ignore[arg-type]
        time_limit_seconds=_positive(solver["time_limit_seconds"], "time_limit_seconds"),
        bess_dispatch_mode=str(solver["bess_dispatch_mode"]),  # type: ignore[arg-type]
        dc_scale_of_reference_mix=_positive(
            hosting["dc_scale_of_reference_mix"], "dc_scale_of_reference_mix"
        ),
        maximum_pv_curtailment_fraction=_fraction(
            hosting["maximum_pv_curtailment_fraction"],
            "maximum_pv_curtailment_fraction",
        ),
        maximum_deadline_miss_rate=_fraction(
            hosting["maximum_deadline_miss_rate"], "maximum_deadline_miss_rate"
        ),
        near_pcc_limit_fraction=float(hosting["near_pcc_limit_fraction"]),
        confidence_level=_fraction(
            inference["confidence_level"], "confidence_level", strict=True
        ),
        familywise_method=str(inference["familywise_method"]),  # type: ignore[arg-type]
        planned_contrast_count=int(inference["planned_contrast_count"]),
        bootstrap_resamples=int(inference["bootstrap_resamples"]),
        bootstrap_seed=int(inference["bootstrap_seed"]),
    )


def _portfolio_variant(
    reference: CommunityPortfolio,
    *,
    bess_enabled: bool,
    dispatch_mode: Literal["milp_exclusive"],
) -> CommunityPortfolio:
    if bess_enabled:
        if not reference.bess_enabled:
            raise ValueError("reference renewable portfolio must declare a BESS")
        return replace(reference, bess_dispatch_mode=dispatch_mode)
    return replace(
        reference,
        bess_enabled=False,
        bess_power_kw=0.0,
        bess_energy_kwh=0.0,
        bess_dispatch_mode=dispatch_mode,
    )


def _solve_profile_pv_hosting(
    artifact: FrozenHourlyScenario,
    *,
    portfolio: CommunityPortfolio,
    dc_operation: Literal["rigid", "flexible"],
    specification: CommunityProfileRenewableSpecification,
) -> RenewableIntegrationSolution | None:
    """Solve the profile slice with a valid bound and an explicit time limit."""

    maximum_curtailment = specification.maximum_pv_curtailment_fraction
    near_limit = specification.near_pcc_limit_fraction
    _validate_fraction(maximum_curtailment, "maximum_pv_curtailment_fraction")
    _validate_fraction(near_limit, "near_pcc_limit_fraction", allow_one=True)
    model = _build_problem(
        artifact,
        portfolio=portfolio,
        dc_operation=dc_operation,
        dc_scale_of_reference_mix=specification.dc_scale_of_reference_mix,
        pv_rated_kw=None,
        max_deadline_miss_rate=specification.maximum_deadline_miss_rate,
    )

    # This upper bound follows from energy balance under prohibited export. It
    # is algebraically redundant, but tightens the initial MILP relaxation for
    # the climate-profile sensitivity without changing the shared formal model.
    if portfolio.prohibit_export:
        horizon = model.snapshot.total_hours
        maximum_dynamic_kw_per_gpu_h = max(
            dict(model.snapshot.dynamic_kw_per_gpu_h_by_class).values()
        )
        maximum_dc_power_kw = specification.dc_scale_of_reference_mix * (
            model.snapshot.fixed_dc_power_kw
            + maximum_dynamic_kw_per_gpu_h * model.snapshot.capacity_gpu_h
        )
        maximum_bess_charge_kw = (
            portfolio.bess_power_kw if portfolio.bess_enabled else 0.0
        )
        maximum_pv_use_kwh = float(model.community_load_kw.sum()) + horizon * (
            maximum_dc_power_kw + maximum_bess_charge_kw
        )
        unit_pv_energy_per_kw = float(_unit_pv_profile_kw(artifact, horizon).sum())
        pv_nameplate_upper_bound_kw = maximum_pv_use_kwh / (
            (1.0 - maximum_curtailment) * unit_pv_energy_per_kw
        )
        model.constraints.append(model.pv_rated_kw <= pv_nameplate_upper_bound_kw)

    model.constraints.append(
        model.cp.sum(model.pv_available_kw - model.pv_used_kw)
        <= maximum_curtailment * model.cp.sum(model.pv_available_kw)
    )
    problem = model.cp.Problem(model.cp.Maximize(model.pv_rated_kw), model.constraints)
    start = time.monotonic()
    try:
        problem.solve(
            solver="HIGHS",
            highs_options={
                "threads": specification.threads_per_process,
                "time_limit": specification.time_limit_seconds,
            },
        )
    except ImportError as exc:
        raise RuntimeError(
            "community-profile renewable sensitivity requires control dependencies"
        ) from exc
    status = str(problem.status)
    seconds = time.monotonic() - start
    if status in {"infeasible", "infeasible_inaccurate"}:
        return None
    if status not in {"optimal", "optimal_inaccurate"}:
        raise RuntimeError(
            f"community-profile renewable optimization did not solve: {status}"
        )
    return _solution(
        model,
        status=status,
        analysis="pv_hosting",
        dc_operation=dc_operation,
        portfolio=portfolio,
        dc_scale_of_reference_mix=specification.dc_scale_of_reference_mix,
        maximum_pv_curtailment_fraction=maximum_curtailment,
        near_pcc_limit_fraction=near_limit,
        solve_seconds=seconds,
    )


def _result_row(
    artifact: FrozenHourlyScenario,
    *,
    case_name: str,
    profile_id: str,
    climate_zone: str,
    operation: str,
    bess_enabled: bool,
    solution: RenewableIntegrationSolution | None,
    specification: CommunityProfileRenewableSpecification,
) -> dict[str, Any]:
    common = {
        "community_profile_case": case_name,
        "profile_id": profile_id,
        "climate_zone": climate_zone,
        "scenario_id": artifact.scenario_id,
        "scenario_hash": artifact.scenario_hash,
        "episode_seed": artifact.episode_seed,
        "dc_operation": operation,
        "bess_enabled": bess_enabled,
        "dc_scale_of_reference_mix": specification.dc_scale_of_reference_mix,
        "maximum_pv_curtailment_fraction": (
            specification.maximum_pv_curtailment_fraction
        ),
    }
    if solution is None:
        return {
            **common,
            "capacity_layer": "perfect_information_renewable_planning_bound",
            "analysis": "pv_hosting",
            "status": "infeasible",
            "pv_rated_kw": np.nan,
        }
    return {**common, **solution.summary()}


def _solve_worker(
    payload: _WorkerPayload,
) -> list[dict[str, Any]]:
    case_name, profile_id, climate_zone, artifact_path, portfolio_raw, specification = (
        payload
    )
    artifact = load_frozen_hourly_scenario(artifact_path)
    reference_portfolio = CommunityPortfolio(**portfolio_raw)
    rows: list[dict[str, Any]] = []
    for bess_enabled in (False, True):
        portfolio = _portfolio_variant(
            reference_portfolio,
            bess_enabled=bess_enabled,
            dispatch_mode=specification.bess_dispatch_mode,
        )
        for operation in ("rigid", "flexible"):
            solution = _solve_profile_pv_hosting(
                artifact,
                portfolio=portfolio,
                dc_operation=operation,
                specification=specification,
            )
            rows.append(
                _result_row(
                    artifact,
                    case_name=case_name,
                    profile_id=profile_id,
                    climate_zone=climate_zone,
                    operation=operation,
                    bess_enabled=bess_enabled,
                    solution=solution,
                    specification=specification,
                )
            )
    return rows


def _report_progress(completed: int, total: int, started_at: float) -> None:
    interval = max(1, math.ceil(total / 20))
    if completed != total and completed % interval != 0:
        return
    elapsed = time.monotonic() - started_at
    print(
        f"Community-profile PV hosting: {completed}/{total} complete "
        f"({100.0 * completed / total:.0f}%, {elapsed:.1f}s elapsed)",
        file=sys.stderr,
        flush=True,
    )


def _validate_partition(
    frame: pd.DataFrame,
    *,
    case_name: str,
    scenario_id: str,
) -> None:
    required = {
        "community_profile_case",
        "scenario_id",
        "bess_enabled",
        "dc_operation",
    }
    if set(frame.columns).isdisjoint(required) or not required.issubset(frame.columns):
        raise ValueError("community-profile PV checkpoint partition has invalid columns")
    if len(frame) != 4:
        raise ValueError("community-profile PV checkpoint partition must contain four rows")
    if set(frame["community_profile_case"].astype(str)) != {case_name}:
        raise ValueError("community-profile PV checkpoint case mismatch")
    if set(frame["scenario_id"].astype(str)) != {scenario_id}:
        raise ValueError("community-profile PV checkpoint scenario mismatch")
    expected = {
        (False, "rigid"),
        (False, "flexible"),
        (True, "rigid"),
        (True, "flexible"),
    }
    observed = set(
        zip(
            frame["bess_enabled"].astype(bool),
            frame["dc_operation"].astype(str),
            strict=True,
        )
    )
    if observed != expected:
        raise ValueError("community-profile PV checkpoint design mismatch")


def _checkpoint_identity(
    *,
    specification_path: Path,
    renewable: CommunityProfileRenewableSpecification,
    scenario_directory: str | Path,
    scenario_count: int,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "role": "resumable_scenario_checkpoint",
        "specification_sha256": sha256_file(specification_path),
        "community_profile_execution_sha256": sha256_file(
            renewable.community_profile_execution
        ),
        "scenario_index_sha256": sha256_file(
            Path(scenario_directory) / "community_profile_sensitivity_scenarios.json"
        ),
        "portfolio_sha256": sha256_file(renewable.portfolio_path),
        "scenario_count": scenario_count,
        "rows_per_scenario": 4,
    }


def _summarize(rows: pd.DataFrame) -> pd.DataFrame:
    output: list[dict[str, Any]] = []
    group_columns = [
        "community_profile_case",
        "profile_id",
        "climate_zone",
        "bess_enabled",
        "dc_operation",
    ]
    for key, selected in rows.groupby(group_columns, sort=True):
        feasible = selected[selected["status"].isin(["optimal", "optimal_inaccurate"])]
        values = feasible["pv_rated_kw"].astype(float)
        row = dict(zip(group_columns, key, strict=True))
        row.update(
            {
                "scenario_count": len(selected),
                "feasible_scenario_count": len(feasible),
                "all_scenarios_feasible": len(feasible) == len(selected),
                "simultaneous_feasible_pv_hosting_kw": (
                    float(values.min()) if len(feasible) == len(selected) else np.nan
                ),
                "mean_scenario_pv_hosting_kw": (
                    float(values.mean()) if not values.empty else np.nan
                ),
                "q05_scenario_pv_hosting_kw": (
                    float(values.quantile(0.05)) if not values.empty else np.nan
                ),
                "q50_scenario_pv_hosting_kw": (
                    float(values.quantile(0.50)) if not values.empty else np.nan
                ),
                "q95_scenario_pv_hosting_kw": (
                    float(values.quantile(0.95)) if not values.empty else np.nan
                ),
            }
        )
        output.append(row)
    return pd.DataFrame.from_records(output).sort_values(group_columns, ignore_index=True)


def _contrasts(
    rows: pd.DataFrame,
    specification: CommunityProfileRenewableSpecification,
    design: CommunityProfileSensitivityDesign,
    expected_scenario_count: int,
) -> pd.DataFrame:
    contrast_rows: list[dict[str, Any]] = []
    for case in design.cases:
        case_rows = rows[rows["community_profile_case"] == case.name]
        for bess_enabled in (False, True):
            subset = case_rows[case_rows["bess_enabled"].astype(bool) == bess_enabled]
            rigid = subset[subset["dc_operation"] == "rigid"].set_index("episode_seed")
            flexible = subset[subset["dc_operation"] == "flexible"].set_index("episode_seed")
            if set(rigid.index) != set(flexible.index) or len(rigid) != expected_scenario_count:
                raise ValueError("community-profile PV contrast has unmatched scenarios")
            if not rigid["status"].isin(["optimal", "optimal_inaccurate"]).all() or not (
                flexible["status"].isin(["optimal", "optimal_inaccurate"]).all()
            ):
                raise ValueError("community-profile PV contrast requires feasible paired solves")
            values = (
                flexible["pv_rated_kw"].astype(float).sort_index()
                - rigid["pv_rated_kw"].astype(float).sort_index()
            ).to_numpy()
            contrast_rows.append(
                {
                    "community_profile_case": case.name,
                    "profile_id": case.profile_id,
                    "climate_zone": case.climate_zone,
                    "bess_enabled": bess_enabled,
                    "values": values,
                }
            )
    if len(contrast_rows) != specification.planned_contrast_count:
        raise ValueError("community-profile PV contrast family differs from preregistration")
    alpha = 1.0 - specification.confidence_level
    tail = alpha / (2.0 * specification.planned_contrast_count)
    rng = np.random.default_rng(specification.bootstrap_seed)
    output: list[dict[str, Any]] = []
    for row in contrast_rows:
        values = np.asarray(row.pop("values"), dtype="float64")
        indices = rng.integers(
            0,
            len(values),
            size=(specification.bootstrap_resamples, len(values)),
        )
        bootstrap_means = values[indices].mean(axis=1)
        output.append(
            {
                **row,
                "contrast": "FLEXIBLE_MINUS_RIGID_PV_HOSTING",
                "independent_unit": "paired_frozen_scenario",
                "scenario_count": len(values),
                "estimate_mean_kw": float(values.mean()),
                "sample_standard_deviation_kw": (
                    float(values.std(ddof=1)) if len(values) > 1 else 0.0
                ),
                "simultaneous_ci_lower_kw": float(np.quantile(bootstrap_means, tail)),
                "simultaneous_ci_upper_kw": float(
                    np.quantile(bootstrap_means, 1.0 - tail)
                ),
                "familywise_confidence_level": specification.confidence_level,
                "familywise_method": specification.familywise_method,
                "planned_contrast_count": specification.planned_contrast_count,
                "bootstrap_resamples": specification.bootstrap_resamples,
            }
        )
    return pd.DataFrame.from_records(output)


def compute_and_save_community_profile_renewable_sensitivity(
    scenario_directory: str | Path,
    *,
    specification: str | Path,
    output_directory: str | Path,
    workers: int = 1,
) -> dict[str, str | int]:
    """Run the sparse paired PV-hosting consequence across profile archetypes."""

    if isinstance(workers, bool) or not isinstance(workers, int) or workers <= 0:
        raise ValueError("community-profile renewable workers must be positive")
    specification_path = Path(specification)
    renewable = load_community_profile_renewable_specification(specification_path)
    execution: CommunityProfileSensitivityExecution = (
        load_community_profile_sensitivity_execution(
            renewable.community_profile_execution
        )
    )
    design: CommunityProfileSensitivityDesign = load_community_profile_sensitivity_design(
        execution.case_specification
    )
    artifacts_by_case, scenario_index = _load_scenario_index(
        scenario_directory,
        specification_path=renewable.community_profile_execution,
        execution=execution,
        design=design,
    )
    if sha256_file(renewable.portfolio_path) != renewable.portfolio_sha256:
        raise ValueError("community-profile renewable portfolio SHA-256 mismatch")
    portfolio = load_community_portfolio(renewable.portfolio_path)
    case_map = {case.name: case for case in design.cases}
    payloads = [
        (
            case_name,
            case_map[case_name].profile_id,
            case_map[case_name].climate_zone,
            str(artifact.directory),
            asdict(portfolio),
            renewable,
        )
        for case_name, artifacts in artifacts_by_case.items()
        for artifact in artifacts
    ]
    output = Path(output_directory)
    temporary = output.parent / f".{output.name}.incomplete"
    if output.exists():
        raise FileExistsError(f"refusing to overwrite community-profile renewable result: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_identity = _checkpoint_identity(
        specification_path=specification_path,
        renewable=renewable,
        scenario_directory=scenario_directory,
        scenario_count=len(payloads),
    )
    checkpoint_path = temporary / "checkpoint_identity.json"
    partition_directory = temporary / "scenario_partitions"
    if temporary.exists():
        if not checkpoint_path.is_file():
            raise ValueError(
                "incomplete community-profile renewable result lacks checkpoint identity"
            )
        observed_identity = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if observed_identity != checkpoint_identity:
            raise ValueError("community-profile renewable checkpoint identity mismatch")
    else:
        temporary.mkdir()
        partition_directory.mkdir()
        checkpoint_path.write_text(
            json.dumps(checkpoint_identity, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    partition_directory.mkdir(exist_ok=True)

    completed_rows: list[list[dict[str, Any]] | None] = [None] * len(payloads)
    pending: list[tuple[int, _WorkerPayload]] = []
    resumed_partition_count = 0
    for index, payload in enumerate(payloads):
        partition_path = partition_directory / f"scenario_{index:06d}.parquet"
        if partition_path.is_file():
            frame = pd.read_parquet(partition_path)
            _validate_partition(
                frame,
                case_name=payload[0],
                scenario_id=Path(payload[3]).name,
            )
            completed_rows[index] = cast(
                list[dict[str, Any]],
                frame.to_dict(orient="records"),
            )
            resumed_partition_count += 1
        else:
            pending.append((index, payload))

    worker_count = min(workers, max(1, len(pending)))
    started_at = time.monotonic()
    if resumed_partition_count:
        _report_progress(resumed_partition_count, len(payloads), started_at)

    def persist(index: int, rows: list[dict[str, Any]]) -> None:
        frame = pd.DataFrame.from_records(rows)
        payload = payloads[index]
        _validate_partition(
            frame,
            case_name=payload[0],
            scenario_id=Path(payload[3]).name,
        )
        partition_path = partition_directory / f"scenario_{index:06d}.parquet"
        staging_path = partition_directory / f".scenario_{index:06d}.parquet.incomplete"
        frame.to_parquet(staging_path, index=False)
        staging_path.replace(partition_path)
        completed_rows[index] = rows

    if worker_count == 1:
        for offset, (index, payload) in enumerate(pending, start=1):
            persist(index, _solve_worker(payload))
            _report_progress(
                resumed_partition_count + offset,
                len(payloads),
                started_at,
            )
    elif pending:
        with ProcessPoolExecutor(
            max_workers=worker_count,
            mp_context=multiprocessing.get_context("spawn"),
        ) as executor:
            futures = {
                executor.submit(_solve_worker, payload): index for index, payload in pending
            }
            for offset, future in enumerate(as_completed(futures), start=1):
                persist(futures[future], future.result())
                _report_progress(
                    resumed_partition_count + offset,
                    len(payloads),
                    started_at,
                )
    rows = pd.DataFrame.from_records(
        [row for partition in completed_rows if partition is not None for row in partition]
    )
    expected_rows = len(payloads) * 4
    if len(rows) != expected_rows or rows.duplicated(
        ["community_profile_case", "episode_seed", "bess_enabled", "dc_operation"]
    ).any():
        raise ValueError("community-profile PV-hosting result matrix is incomplete")
    summary = _summarize(rows)
    contrasts = _contrasts(
        rows,
        renewable,
        design,
        expected_scenario_count=len(execution.seeds),
    )

    rows_path = temporary / "community_profile_pv_hosting_scenarios.parquet"
    summary_path = temporary / "community_profile_pv_hosting_summary.parquet"
    contrasts_path = temporary / "community_profile_pv_hosting_contrasts.parquet"
    manifest_path = temporary / "community_profile_renewable_sensitivity.json"
    rows.to_parquet(rows_path, index=False)
    summary.to_parquet(summary_path, index=False)
    contrasts.to_parquet(contrasts_path, index=False)
    all_artifacts = [
        artifact for artifacts in artifacts_by_case.values() for artifact in artifacts
    ]
    manifest = {
        "schema_version": 1,
        "capacity_layer": "perfect_information_renewable_planning_bound",
        "evidence_scope": "development_only",
        "interpretation": "climate_zone_profile_archetypes_not_geocoded_sites",
        "not_claimed": [
            "named_city_effect",
            "feeder_spatial_effect",
            "locked_causal_pv_hosting_effect",
        ],
        "specification": str(specification_path),
        "specification_sha256": sha256_file(specification_path),
        "community_profile_execution": str(renewable.community_profile_execution),
        "community_profile_execution_sha256": sha256_file(
            renewable.community_profile_execution
        ),
        "scenario_index_sha256": sha256_file(
            Path(scenario_directory) / "community_profile_sensitivity_scenarios.json"
        ),
        "scenario_generation_git_commit": scenario_index.get("analysis_git_commit"),
        "analysis_git_commit": _git_commit(),
        "workers": worker_count,
        "resumed_partition_count": resumed_partition_count,
        "checkpoint": {
            "identity": str(output / checkpoint_path.name),
            "identity_sha256": sha256_file(checkpoint_path),
            "partition_count": len(payloads),
            "partition_directory": str(output / partition_directory.name),
        },
        "scenario_count": len(all_artifacts),
        "case_count": len(design.cases),
        "outputs": {
            "scenario_results": str(output / rows_path.name),
            "scenario_results_sha256": sha256_file(rows_path),
            "summary": str(output / summary_path.name),
            "summary_sha256": sha256_file(summary_path),
            "contrasts": str(output / contrasts_path.name),
            "contrasts_sha256": sha256_file(contrasts_path),
        },
        "optimization_provenance": optimization_provenance(all_artifacts),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(output)
    return {
        "scenario_results": str(output / rows_path.name),
        "summary": str(output / summary_path.name),
        "contrasts": str(output / contrasts_path.name),
        "manifest": str(output / manifest_path.name),
        "scenario_count": len(all_artifacts),
        "row_count": len(rows),
    }
