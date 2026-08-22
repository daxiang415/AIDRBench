"""Preregistered scenario ensemble for PV hosting and utilisation consequences."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
from collections.abc import Mapping
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
import pandas as pd
import yaml

from aidrbench.data.frozen_scenarios import (
    FrozenHourlyScenario,
    load_frozen_hourly_scenario,
)
from aidrbench.data.splits import sha256_file
from aidrbench.evaluation.frozen_causal_certificate import _git_commit
from aidrbench.evaluation.hosting_capacity import CommunityPortfolio, load_community_portfolio
from aidrbench.evaluation.renewable_integration import (
    RenewableIntegrationSolution,
    solve_curtailment_constrained_pv_hosting,
    solve_fixed_capacity_pv_operation,
)

_RUN_STATE_NAME = "renewable_integration_run.json"
_SOURCE_PATHS = (
    "src/aidrbench/data/frozen_scenarios.py",
    "src/aidrbench/envs/community_ai_dr_env.py",
    "src/aidrbench/evaluation/hosting_capacity.py",
    "src/aidrbench/evaluation/non_anticipative.py",
    "src/aidrbench/evaluation/renewable_integration.py",
    "src/aidrbench/evaluation/renewable_ensemble.py",
)
_OPERATION_CONTRAST_METRICS = (
    "total_pv_used_kwh",
    "total_pv_curtailed_kwh",
    "pv_utilisation_fraction",
    "renewable_demand_share",
    "total_grid_import_kwh",
)


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _exact_fields(document: Mapping[str, Any], expected: set[str], name: str) -> None:
    observed = set(document)
    if observed != expected:
        raise ValueError(
            f"{name} fields mismatch; missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class RenewableIntegrationSpecification:
    """Complete specification for the non-locked renewable consequence study."""

    schema_version: int
    model_a_git_commit: str
    dataset_role: Literal[
        "development_renewable_integration",
        "validation_renewable_replication",
    ]
    independent_unit: Literal["frozen_scenario"]
    expected_scenario_count: int
    expected_episode_seed_range: tuple[int, int]
    portfolio_path: str
    portfolio_sha256: str
    solver_name: Literal["HIGHS"]
    threads_per_process: int
    bess_dispatch_mode: Literal["milp_exclusive"]
    envelope_dc_scales: tuple[float, ...]
    headline_max_curtailment_fraction: float
    sensitivity_max_curtailment_fractions: tuple[float, ...]
    fixed_comparison_dc_scale: float
    fixed_operation_dc_scale: float
    fixed_operation_pv_rated_kw: float
    near_pcc_limit_fraction: float
    lexicographic_tolerance_kwh: float
    confidence_level: float
    familywise_method: Literal["bonferroni"]
    hosting_planned_contrast_count: int
    operation_planned_contrast_count: int
    bootstrap_resamples: int
    bootstrap_seed: int
    descriptive_quantiles: tuple[float, ...]

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("unsupported renewable-integration schema_version")
        if len(self.model_a_git_commit) != 40 or any(
            value not in "0123456789abcdef" for value in self.model_a_git_commit
        ):
            raise ValueError("model_a_git_commit must be a lowercase 40-character SHA-1")
        if self.expected_scenario_count <= 1:
            raise ValueError("renewable-integration ensemble requires more than one scenario")
        start, stop = self.expected_episode_seed_range
        if start < 0 or stop < start or stop - start + 1 != self.expected_scenario_count:
            raise ValueError("expected seed range must match expected_scenario_count")
        if len(self.portfolio_sha256) != 64:
            raise ValueError("portfolio_sha256 must be a SHA-256 digest")
        if self.threads_per_process != 1:
            raise ValueError("formal renewable ensemble requires one solver thread per process")
        if self.bess_dispatch_mode != "milp_exclusive":
            raise ValueError("renewable integration requires milp_exclusive BESS dispatch")
        if not self.envelope_dc_scales or any(value <= 0.0 for value in self.envelope_dc_scales):
            raise ValueError("envelope_dc_scales must be positive")
        if tuple(sorted(set(self.envelope_dc_scales))) != self.envelope_dc_scales:
            raise ValueError("envelope_dc_scales must be unique and increasing")
        if self.fixed_comparison_dc_scale not in self.envelope_dc_scales:
            raise ValueError("fixed comparison scale must be present in the envelope")
        if self.fixed_operation_dc_scale != self.fixed_comparison_dc_scale:
            raise ValueError(
                "v1 requires fixed-capacity operation and hosting contrasts at the same "
                "data-centre scale"
            )
        fractions = (
            self.headline_max_curtailment_fraction,
            *self.sensitivity_max_curtailment_fractions,
        )
        if any(not 0.0 <= value < 1.0 for value in fractions):
            raise ValueError("PV curtailment fractions must lie in [0, 1)")
        if len(set(self.sensitivity_max_curtailment_fractions)) != len(
            self.sensitivity_max_curtailment_fractions
        ):
            raise ValueError("sensitivity curtailment fractions must be unique")
        if self.fixed_operation_pv_rated_kw <= 0.0:
            raise ValueError("fixed_operation_pv_rated_kw must be positive")
        if not 0.0 < self.near_pcc_limit_fraction <= 1.0:
            raise ValueError("near_pcc_limit_fraction must lie in (0, 1]")
        if self.lexicographic_tolerance_kwh <= 0.0:
            raise ValueError("lexicographic_tolerance_kwh must be positive")
        if not 0.0 < self.confidence_level < 1.0:
            raise ValueError("confidence_level must lie in (0, 1)")
        if self.hosting_planned_contrast_count != 2:
            raise ValueError("fixed-scale PV hosting predeclares two BESS-stratified contrasts")
        expected_operation_count = 2 * len(_OPERATION_CONTRAST_METRICS)
        if self.operation_planned_contrast_count != expected_operation_count:
            raise ValueError(
                f"fixed-PV operation predeclares {expected_operation_count} contrasts"
            )
        if self.bootstrap_resamples < 1000:
            raise ValueError("bootstrap_resamples must be at least 1000")
        if self.bootstrap_seed < 0:
            raise ValueError("bootstrap_seed must be non-negative")
        if not self.descriptive_quantiles or any(
            not 0.0 < value < 1.0 for value in self.descriptive_quantiles
        ):
            raise ValueError("descriptive_quantiles must lie in (0, 1)")
        if tuple(sorted(set(self.descriptive_quantiles))) != self.descriptive_quantiles:
            raise ValueError("descriptive_quantiles must be unique and increasing")

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["expected_episode_seed_range"] = list(self.expected_episode_seed_range)
        result["envelope_dc_scales"] = list(self.envelope_dc_scales)
        result["sensitivity_max_curtailment_fractions"] = list(
            self.sensitivity_max_curtailment_fractions
        )
        result["descriptive_quantiles"] = list(self.descriptive_quantiles)
        return result

    @property
    def sha256(self) -> str:
        return _canonical_sha256(self.as_dict())


def load_renewable_integration_specification(
    path: str | Path,
) -> RenewableIntegrationSpecification:
    """Load the complete renewable-integration specification without defaults."""

    document = _mapping(
        yaml.safe_load(Path(path).read_text(encoding="utf-8")),
        "renewable-integration specification",
    )
    _exact_fields(
        document,
        {
            "schema_version",
            "model_a_git_commit",
            "dataset_role",
            "independent_unit",
            "expected_scenario_count",
            "expected_episode_seed_range",
            "portfolio",
            "solver",
            "pv_hosting",
            "fixed_capacity_operation",
            "paired_inference",
            "capacity_aggregation",
        },
        "renewable-integration specification",
    )
    portfolio = _mapping(document["portfolio"], "portfolio")
    _exact_fields(portfolio, {"path", "sha256"}, "portfolio")
    solver = _mapping(document["solver"], "solver")
    _exact_fields(
        solver,
        {"name", "threads_per_process", "bess_dispatch_mode"},
        "solver",
    )
    hosting = _mapping(document["pv_hosting"], "pv_hosting")
    _exact_fields(
        hosting,
        {
            "envelope_dc_scales",
            "headline_max_curtailment_fraction",
            "sensitivity_max_curtailment_fractions",
            "fixed_comparison_dc_scale",
        },
        "pv_hosting",
    )
    operation = _mapping(document["fixed_capacity_operation"], "fixed_capacity_operation")
    _exact_fields(
        operation,
        {
            "dc_scale_of_reference_mix",
            "pv_rated_kw",
            "near_pcc_limit_fraction",
            "lexicographic_tolerance_kwh",
        },
        "fixed_capacity_operation",
    )
    inference = _mapping(document["paired_inference"], "paired_inference")
    _exact_fields(
        inference,
        {
            "confidence_level",
            "familywise_method",
            "hosting_planned_contrast_count",
            "operation_planned_contrast_count",
            "bootstrap_resamples",
            "bootstrap_seed",
        },
        "paired_inference",
    )
    aggregation = _mapping(document["capacity_aggregation"], "capacity_aggregation")
    _exact_fields(
        aggregation,
        {"headline", "descriptive_quantiles"},
        "capacity_aggregation",
    )
    if aggregation["headline"] != "simultaneous_scenario_feasible_minimum":
        raise ValueError("PV hosting headline must be simultaneous_scenario_feasible_minimum")
    seed_range = document["expected_episode_seed_range"]
    if not isinstance(seed_range, list) or len(seed_range) != 2:
        raise ValueError("expected_episode_seed_range must contain two integers")
    return RenewableIntegrationSpecification(
        schema_version=int(document["schema_version"]),
        model_a_git_commit=str(document["model_a_git_commit"]),
        dataset_role=str(document["dataset_role"]),  # type: ignore[arg-type]
        independent_unit=str(document["independent_unit"]),  # type: ignore[arg-type]
        expected_scenario_count=int(document["expected_scenario_count"]),
        expected_episode_seed_range=(int(seed_range[0]), int(seed_range[1])),
        portfolio_path=str(portfolio["path"]),
        portfolio_sha256=str(portfolio["sha256"]),
        solver_name=str(solver["name"]),  # type: ignore[arg-type]
        threads_per_process=int(solver["threads_per_process"]),
        bess_dispatch_mode=str(solver["bess_dispatch_mode"]),  # type: ignore[arg-type]
        envelope_dc_scales=tuple(float(value) for value in hosting["envelope_dc_scales"]),
        headline_max_curtailment_fraction=float(
            hosting["headline_max_curtailment_fraction"]
        ),
        sensitivity_max_curtailment_fractions=tuple(
            float(value) for value in hosting["sensitivity_max_curtailment_fractions"]
        ),
        fixed_comparison_dc_scale=float(hosting["fixed_comparison_dc_scale"]),
        fixed_operation_dc_scale=float(operation["dc_scale_of_reference_mix"]),
        fixed_operation_pv_rated_kw=float(operation["pv_rated_kw"]),
        near_pcc_limit_fraction=float(operation["near_pcc_limit_fraction"]),
        lexicographic_tolerance_kwh=float(operation["lexicographic_tolerance_kwh"]),
        confidence_level=float(inference["confidence_level"]),
        familywise_method=str(inference["familywise_method"]),  # type: ignore[arg-type]
        hosting_planned_contrast_count=int(inference["hosting_planned_contrast_count"]),
        operation_planned_contrast_count=int(inference["operation_planned_contrast_count"]),
        bootstrap_resamples=int(inference["bootstrap_resamples"]),
        bootstrap_seed=int(inference["bootstrap_seed"]),
        descriptive_quantiles=tuple(
            float(value) for value in aggregation["descriptive_quantiles"]
        ),
    )


def _discover_artifacts(
    scenario_path: str | Path,
    specification: RenewableIntegrationSpecification,
) -> list[FrozenHourlyScenario]:
    root = Path(scenario_path)
    if any("locked" in part.lower() for part in root.parts):
        raise ValueError("renewable-integration analysis may not read a locked path")
    required_label = (
        "validation"
        if specification.dataset_role == "validation_renewable_replication"
        else "development"
    )
    if required_label not in root.name.lower():
        raise ValueError(f"{specification.dataset_role} requires a {required_label} path")
    artifacts = [
        load_frozen_hourly_scenario(child)
        for child in sorted(root.iterdir())
        if child.is_dir() and (child / "metadata.json").is_file()
    ]
    if len(artifacts) != specification.expected_scenario_count:
        raise ValueError("renewable scenario count does not match the specification")
    expected_seeds = set(
        range(
            specification.expected_episode_seed_range[0],
            specification.expected_episode_seed_range[1] + 1,
        )
    )
    if {artifact.episode_seed for artifact in artifacts} != expected_seeds:
        raise ValueError("renewable scenario seeds do not match the specification")
    if len({artifact.scenario_hash for artifact in artifacts}) != len(artifacts):
        raise ValueError("renewable scenarios must have unique hashes")
    return artifacts


def _portfolio_variant(
    reference: CommunityPortfolio,
    *,
    bess_enabled: bool,
    dispatch_mode: Literal["milp_exclusive"],
) -> CommunityPortfolio:
    return CommunityPortfolio(
        pv_enabled=True,
        pv_rated_kw=reference.pv_rated_kw,
        bess_enabled=bess_enabled,
        bess_power_kw=reference.bess_power_kw if bess_enabled else 0.0,
        bess_energy_kwh=reference.bess_energy_kwh if bess_enabled else 0.0,
        charge_efficiency=reference.charge_efficiency,
        discharge_efficiency=reference.discharge_efficiency,
        initial_soc_fraction=reference.initial_soc_fraction,
        terminal_soc_fraction=reference.terminal_soc_fraction,
        prohibit_export=reference.prohibit_export,
        bess_dispatch_mode=dispatch_mode,
    )


def _result_row(
    artifact: FrozenHourlyScenario,
    *,
    specification_sha256: str,
    portfolio_sha256: str,
    analysis_variant: str,
    solution: RenewableIntegrationSolution | None,
    dc_operation: str,
    bess_enabled: bool,
    dc_scale: float,
    curtailment_fraction: float | None,
) -> dict[str, Any]:
    common = {
        "scenario_id": artifact.scenario_id,
        "scenario_hash": artifact.scenario_hash,
        "episode_seed": artifact.episode_seed,
        "specification_sha256": specification_sha256,
        "portfolio_sha256": portfolio_sha256,
        "analysis_variant": analysis_variant,
        "dc_operation": dc_operation,
        "bess_enabled": bess_enabled,
        "dc_scale_of_reference_mix": dc_scale,
        "maximum_pv_curtailment_fraction": curtailment_fraction,
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


def _solve_scenario_matrix(
    payload: tuple[
        str,
        dict[str, Any],
        RenewableIntegrationSpecification,
        str,
        str,
    ],
) -> list[dict[str, Any]]:
    artifact_path, portfolio_raw, specification, specification_sha256, portfolio_sha256 = (
        payload
    )
    artifact = load_frozen_hourly_scenario(artifact_path)
    reference_portfolio = CommunityPortfolio(**portfolio_raw)
    rows: list[dict[str, Any]] = []
    cache: dict[tuple[float, float, bool, str], RenewableIntegrationSolution | None] = {}
    for dc_scale in specification.envelope_dc_scales:
        for bess_enabled in (False, True):
            portfolio = _portfolio_variant(
                reference_portfolio,
                bess_enabled=bess_enabled,
                dispatch_mode=specification.bess_dispatch_mode,
            )
            for operation in ("rigid", "flexible"):
                key = (
                    dc_scale,
                    specification.headline_max_curtailment_fraction,
                    bess_enabled,
                    operation,
                )
                solution = solve_curtailment_constrained_pv_hosting(
                    artifact,
                    portfolio=portfolio,
                    dc_operation=operation,
                    dc_scale_of_reference_mix=dc_scale,
                    maximum_pv_curtailment_fraction=(
                        specification.headline_max_curtailment_fraction
                    ),
                    near_pcc_limit_fraction=specification.near_pcc_limit_fraction,
                )
                cache[key] = solution
                rows.append(
                    _result_row(
                        artifact,
                        specification_sha256=specification_sha256,
                        portfolio_sha256=portfolio_sha256,
                        analysis_variant="headline_pv_hosting_envelope",
                        solution=solution,
                        dc_operation=operation,
                        bess_enabled=bess_enabled,
                        dc_scale=dc_scale,
                        curtailment_fraction=(
                            specification.headline_max_curtailment_fraction
                        ),
                    )
                )
    all_fractions = (
        specification.headline_max_curtailment_fraction,
        *specification.sensitivity_max_curtailment_fractions,
    )
    for curtailment_fraction in all_fractions:
        for bess_enabled in (False, True):
            portfolio = _portfolio_variant(
                reference_portfolio,
                bess_enabled=bess_enabled,
                dispatch_mode=specification.bess_dispatch_mode,
            )
            for operation in ("rigid", "flexible"):
                key = (
                    specification.fixed_comparison_dc_scale,
                    curtailment_fraction,
                    bess_enabled,
                    operation,
                )
                if key not in cache:
                    cache[key] = solve_curtailment_constrained_pv_hosting(
                        artifact,
                        portfolio=portfolio,
                        dc_operation=cast(Literal["rigid", "flexible"], operation),
                        dc_scale_of_reference_mix=specification.fixed_comparison_dc_scale,
                        maximum_pv_curtailment_fraction=curtailment_fraction,
                        near_pcc_limit_fraction=specification.near_pcc_limit_fraction,
                    )
                rows.append(
                    _result_row(
                        artifact,
                        specification_sha256=specification_sha256,
                        portfolio_sha256=portfolio_sha256,
                        analysis_variant="pv_curtailment_sensitivity",
                        solution=cache[key],
                        dc_operation=operation,
                        bess_enabled=bess_enabled,
                        dc_scale=specification.fixed_comparison_dc_scale,
                        curtailment_fraction=curtailment_fraction,
                    )
                )
    for bess_enabled in (False, True):
        portfolio = _portfolio_variant(
            reference_portfolio,
            bess_enabled=bess_enabled,
            dispatch_mode=specification.bess_dispatch_mode,
        )
        for operation in ("rigid", "flexible"):
            solution = solve_fixed_capacity_pv_operation(
                artifact,
                portfolio=portfolio,
                dc_operation=cast(Literal["rigid", "flexible"], operation),
                dc_scale_of_reference_mix=specification.fixed_operation_dc_scale,
                pv_rated_kw=specification.fixed_operation_pv_rated_kw,
                near_pcc_limit_fraction=specification.near_pcc_limit_fraction,
                lexicographic_tolerance_kwh=specification.lexicographic_tolerance_kwh,
            )
            rows.append(
                _result_row(
                    artifact,
                    specification_sha256=specification_sha256,
                    portfolio_sha256=portfolio_sha256,
                    analysis_variant="fixed_capacity_pv_operation",
                    solution=solution,
                    dc_operation=operation,
                    bess_enabled=bess_enabled,
                    dc_scale=specification.fixed_operation_dc_scale,
                    curtailment_fraction=None,
                )
            )
    return rows


def _expected_partition_rows(specification: RenewableIntegrationSpecification) -> int:
    envelope = len(specification.envelope_dc_scales) * 2 * 2
    sensitivity = (1 + len(specification.sensitivity_max_curtailment_fractions)) * 2 * 2
    operation = 2 * 2
    return envelope + sensitivity + operation


def _validate_partition(
    path: Path,
    *,
    artifact: FrozenHourlyScenario,
    specification: RenewableIntegrationSpecification,
    portfolio_sha256: str,
) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    if len(frame) != _expected_partition_rows(specification):
        raise ValueError(f"renewable partition has the wrong row count: {path}")
    checks = {
        "scenario_hash": artifact.scenario_hash,
        "specification_sha256": specification.sha256,
        "portfolio_sha256": portfolio_sha256,
    }
    for column, expected in checks.items():
        if set(frame[column].astype(str)) != {expected}:
            raise ValueError(f"renewable partition {column} mismatch: {path}")
    return frame


def _quantile_label(value: float) -> str:
    return f"q{round(100 * value):02d}"


def _pv_hosting_summary(
    rows: pd.DataFrame,
    specification: RenewableIntegrationSpecification,
) -> pd.DataFrame:
    group_columns = [
        "analysis_variant",
        "dc_operation",
        "bess_enabled",
        "dc_scale_of_reference_mix",
        "maximum_pv_curtailment_fraction",
    ]
    reference_peaks = rows["reference_mix_operating_peak_kw"].dropna().astype(float).unique()
    if len(reference_peaks) != 1:
        raise ValueError("renewable ensemble must use one reference-mix operating peak")
    reference_peak_kw = float(reference_peaks[0])
    summaries: list[dict[str, Any]] = []
    for raw_key, selected in rows.groupby(group_columns, sort=True, dropna=False):
        key = cast(tuple[Any, ...], raw_key)
        feasible = selected[selected["status"].isin(["optimal", "optimal_inaccurate"])]
        values = feasible["pv_rated_kw"].astype(float)
        row = dict(zip(group_columns, key, strict=True))
        row["target_dc_peak_kw"] = (
            float(row["dc_scale_of_reference_mix"]) * reference_peak_kw
        )
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
                "minimum_scenario_pv_hosting_kw": (
                    float(values.min()) if not values.empty else np.nan
                ),
                "maximum_scenario_pv_hosting_kw": (
                    float(values.max()) if not values.empty else np.nan
                ),
            }
        )
        for quantile in specification.descriptive_quantiles:
            row[f"{_quantile_label(quantile)}_scenario_pv_hosting_kw"] = (
                float(values.quantile(quantile)) if not values.empty else np.nan
            )
        summaries.append(row)
    return pd.DataFrame.from_records(summaries).sort_values(
        group_columns, ignore_index=True
    )


def _bootstrap_contrasts(
    contrast_rows: list[dict[str, Any]],
    *,
    planned_count: int,
    specification: RenewableIntegrationSpecification,
    seed_offset: int,
) -> pd.DataFrame:
    if len(contrast_rows) != planned_count:
        raise RuntimeError("renewable contrast family does not match preregistration")
    alpha = 1.0 - specification.confidence_level
    tail_probability = alpha / (2.0 * planned_count)
    rng = np.random.default_rng(specification.bootstrap_seed + seed_offset)
    output: list[dict[str, Any]] = []
    for row in contrast_rows:
        values = np.asarray(row.pop("values"), dtype="float64")
        if len(values) != specification.expected_scenario_count or not np.isfinite(values).all():
            raise ValueError("renewable paired contrast has invalid scenario values")
        indices = rng.integers(
            0, len(values), size=(specification.bootstrap_resamples, len(values))
        )
        bootstrap_means = values[indices].mean(axis=1)
        output.append(
            {
                **row,
                "independent_unit": specification.independent_unit,
                "scenario_count": len(values),
                "estimate_mean": float(values.mean()),
                "sample_standard_deviation": float(values.std(ddof=1)),
                "simultaneous_ci_lower": float(
                    np.quantile(bootstrap_means, tail_probability)
                ),
                "simultaneous_ci_upper": float(
                    np.quantile(bootstrap_means, 1.0 - tail_probability)
                ),
                "familywise_confidence_level": specification.confidence_level,
                "planned_contrast_count": planned_count,
                "bootstrap_resamples": specification.bootstrap_resamples,
            }
        )
    return pd.DataFrame.from_records(output)


def _paired_flexible_minus_rigid(
    rows: pd.DataFrame,
    *,
    metric: str,
    bess_enabled: bool,
) -> np.ndarray:
    subset = rows[_bool_series(rows["bess_enabled"]) == bess_enabled]
    rigid = subset[subset["dc_operation"] == "rigid"].set_index("scenario_hash")[metric]
    flexible = subset[subset["dc_operation"] == "flexible"].set_index("scenario_hash")[
        metric
    ]
    if not rigid.index.is_unique or not flexible.index.is_unique:
        raise ValueError("renewable paired contrast has duplicate scenario conditions")
    if set(rigid.index) != set(flexible.index):
        raise ValueError("renewable paired contrast has unmatched scenarios")
    aligned = flexible.astype(float).sort_index() - rigid.astype(float).sort_index()
    return aligned.to_numpy(dtype="float64")


def _bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    return series.astype(str).str.lower().map({"true": True, "false": False})


def _hosting_contrasts(
    rows: pd.DataFrame,
    specification: RenewableIntegrationSpecification,
) -> pd.DataFrame:
    selected = rows[
        (rows["analysis_variant"] == "headline_pv_hosting_envelope")
        & np.isclose(
            rows["dc_scale_of_reference_mix"].astype(float),
            specification.fixed_comparison_dc_scale,
        )
    ]
    contrasts: list[dict[str, Any]] = []
    for bess_enabled in (False, True):
        contrasts.append(
            {
                "contrast": "DR_PV_HOSTING_GAIN",
                "conditioning_axis": "bess_enabled",
                "conditioning_level": str(bess_enabled),
                "dc_scale_of_reference_mix": specification.fixed_comparison_dc_scale,
                "maximum_pv_curtailment_fraction": (
                    specification.headline_max_curtailment_fraction
                ),
                "unit": "kW",
                "values": _paired_flexible_minus_rigid(
                    selected,
                    metric="pv_rated_kw",
                    bess_enabled=bess_enabled,
                ),
            }
        )
    return _bootstrap_contrasts(
        contrasts,
        planned_count=specification.hosting_planned_contrast_count,
        specification=specification,
        seed_offset=0,
    )


def _operation_summary(
    rows: pd.DataFrame,
    specification: RenewableIntegrationSpecification,
) -> pd.DataFrame:
    selected = rows[rows["analysis_variant"] == "fixed_capacity_pv_operation"]
    metrics = (
        *_OPERATION_CONTRAST_METRICS,
        "maximum_pcc_import_kw",
        "hours_near_pcc_limit",
        "total_bess_charge_kwh",
        "total_bess_discharge_kwh",
        "deadline_miss_fraction",
        "terminal_backlog_fraction",
    )
    output: list[dict[str, Any]] = []
    for (operation, bess_enabled), group in selected.groupby(
        ["dc_operation", "bess_enabled"], sort=True
    ):
        for metric in metrics:
            values = group[metric].astype(float)
            row: dict[str, Any] = {
                "dc_operation": operation,
                "bess_enabled": bool(bess_enabled),
                "scenario_count": len(group),
                "metric": metric,
                "mean": float(values.mean()),
                "minimum": float(values.min()),
                "maximum": float(values.max()),
            }
            for quantile in specification.descriptive_quantiles:
                row[_quantile_label(quantile)] = float(values.quantile(quantile))
            output.append(row)
    return pd.DataFrame.from_records(output)


def _operation_contrasts(
    rows: pd.DataFrame,
    specification: RenewableIntegrationSpecification,
) -> pd.DataFrame:
    selected = rows[rows["analysis_variant"] == "fixed_capacity_pv_operation"]
    contrasts: list[dict[str, Any]] = []
    for bess_enabled in (False, True):
        for metric in _OPERATION_CONTRAST_METRICS:
            unit = "fraction" if "fraction" in metric or "share" in metric else "kWh"
            contrasts.append(
                {
                    "contrast": "FLEXIBLE_MINUS_RIGID_FIXED_PV_OPERATION",
                    "conditioning_axis": "bess_enabled",
                    "conditioning_level": str(bess_enabled),
                    "metric": metric,
                    "unit": unit,
                    "values": _paired_flexible_minus_rigid(
                        selected,
                        metric=metric,
                        bess_enabled=bess_enabled,
                    ),
                }
            )
    return _bootstrap_contrasts(
        contrasts,
        planned_count=specification.operation_planned_contrast_count,
        specification=specification,
        seed_offset=1,
    )


def compute_renewable_integration_ensemble(
    scenario_path: str | Path,
    *,
    specification_path: str | Path,
    output_directory: str | Path,
    workers: int = 1,
) -> dict[str, Any]:
    """Solve, checkpoint and aggregate the preregistered renewable ensemble."""

    if workers <= 0:
        raise ValueError("workers must be positive")
    specification = load_renewable_integration_specification(specification_path)
    portfolio_path = Path(specification.portfolio_path)
    if sha256_file(portfolio_path) != specification.portfolio_sha256:
        raise ValueError("renewable portfolio SHA-256 mismatch")
    portfolio = load_community_portfolio(portfolio_path)
    artifacts = _discover_artifacts(scenario_path, specification)
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    partitions = output / "scenario_partitions"
    partitions.mkdir(exist_ok=True)
    run_state_path = output / _RUN_STATE_NAME
    repository_root = Path(__file__).resolve().parents[3]
    source_sha256 = {
        path: sha256_file(repository_root / path) for path in _SOURCE_PATHS
    }
    run_state = {
        "schema_version": 1,
        "dataset_role": specification.dataset_role,
        "locked_data_read": False,
        "specification": specification.as_dict(),
        "specification_sha256": specification.sha256,
        "specification_file_sha256": sha256_file(Path(specification_path)),
        "portfolio_sha256": specification.portfolio_sha256,
        "source_sha256": source_sha256,
        "scenario_hashes": [artifact.scenario_hash for artifact in artifacts],
    }
    if run_state_path.is_file():
        observed = json.loads(run_state_path.read_text(encoding="utf-8"))
        if observed != run_state:
            raise ValueError("renewable-integration resume state mismatch")
    else:
        run_state_path.write_text(
            json.dumps(run_state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    completed_frames: list[pd.DataFrame] = []
    missing: list[FrozenHourlyScenario] = []
    for artifact in artifacts:
        partition_path = partitions / f"{artifact.scenario_hash}.parquet"
        if partition_path.is_file():
            completed_frames.append(
                _validate_partition(
                    partition_path,
                    artifact=artifact,
                    specification=specification,
                    portfolio_sha256=specification.portfolio_sha256,
                )
            )
        else:
            missing.append(artifact)
    portfolio_raw = asdict(portfolio)
    if missing:
        with ProcessPoolExecutor(
            max_workers=min(workers, len(missing)),
            mp_context=multiprocessing.get_context("spawn"),
        ) as executor:
            futures = {
                executor.submit(
                    _solve_scenario_matrix,
                    (
                        str(artifact.directory),
                        portfolio_raw,
                        specification,
                        specification.sha256,
                        specification.portfolio_sha256,
                    ),
                ): artifact
                for artifact in missing
            }
            for future in as_completed(futures):
                artifact = futures[future]
                frame = pd.DataFrame.from_records(future.result())
                partition_path = partitions / f"{artifact.scenario_hash}.parquet"
                frame.to_parquet(partition_path, index=False)
                completed_frames.append(
                    _validate_partition(
                        partition_path,
                        artifact=artifact,
                        specification=specification,
                        portfolio_sha256=specification.portfolio_sha256,
                    )
                )
    scenario_results = pd.concat(completed_frames, ignore_index=True).sort_values(
        [
            "episode_seed",
            "analysis_variant",
            "dc_scale_of_reference_mix",
            "maximum_pv_curtailment_fraction",
            "bess_enabled",
            "dc_operation",
        ],
        ignore_index=True,
        na_position="last",
    )
    expected_rows = _expected_partition_rows(specification) * specification.expected_scenario_count
    if len(scenario_results) != expected_rows:
        raise RuntimeError("renewable-integration ensemble has an incomplete scenario matrix")
    hosting_rows = scenario_results[
        scenario_results["analysis_variant"].isin(
            ["headline_pv_hosting_envelope", "pv_curtailment_sensitivity"]
        )
    ]
    hosting_summary = _pv_hosting_summary(hosting_rows, specification)
    hosting_contrasts = _hosting_contrasts(scenario_results, specification)
    operation_summary = _operation_summary(scenario_results, specification)
    operation_contrasts = _operation_contrasts(scenario_results, specification)

    paths = {
        "scenario_results": output / "scenario_renewable_integration.parquet",
        "pv_hosting_summary": output / "pv_hosting_summary.parquet",
        "pv_hosting_contrasts": output / "pv_hosting_contrasts.parquet",
        "pv_operation_summary": output / "pv_operation_summary.parquet",
        "pv_operation_contrasts": output / "pv_operation_contrasts.parquet",
    }
    scenario_results.to_parquet(paths["scenario_results"], index=False)
    hosting_summary.to_parquet(paths["pv_hosting_summary"], index=False)
    hosting_contrasts.to_parquet(paths["pv_hosting_contrasts"], index=False)
    operation_summary.to_parquet(paths["pv_operation_summary"], index=False)
    operation_contrasts.to_parquet(paths["pv_operation_contrasts"], index=False)
    manifest_path = output / "renewable_integration.json"
    manifest_path.write_text(
        json.dumps(
            {
                **run_state,
                "model_a_git_commit": specification.model_a_git_commit,
                "analysis_git_commit": _git_commit(),
                "source_sha256": source_sha256,
                "workers": workers,
                "solver_threads_per_process": specification.threads_per_process,
                "outputs": {key: str(path) for key, path in paths.items()},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "manifest": str(manifest_path),
        **{key: str(path) for key, path in paths.items()},
        "scenario_count": specification.expected_scenario_count,
        "row_count": len(scenario_results),
        "resumed_scenario_count": specification.expected_scenario_count - len(missing),
        "solved_scenario_count": len(missing),
    }
