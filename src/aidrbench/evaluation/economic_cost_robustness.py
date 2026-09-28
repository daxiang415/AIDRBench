"""Post-hoc cost sensitivity of a frozen, verified economic event ledger.

Only monetary coordinates and Monte Carlo draw counts change. The original
Figure 6 bundle, technical certificates and physical trajectories are inputs,
never outputs. Common annual draws preserve paired contrasts across costs.
"""

from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from aidrbench.data.splits import sha256_file
from aidrbench.economics.accounting import annual_economic_value
from aidrbench.economics.specification import (
    CostParameterGrid,
    EconomicParticipationSpecification,
    MarketArchetype,
    load_cost_parameter_grid,
    load_economic_participation_specification,
    load_market_archetypes,
    verify_economic_input_hashes,
)
from aidrbench.evaluation.economic_participation import (
    _SCALABLE_LEDGER_METRICS,
    _git_state,
    _group_metrics,
    _load_verified_ledger,
    _make_inputs,
    _risk_statistics,
    _stable_seed,
    _validate_grid,
)

_ROOT = Path(__file__).resolve().parents[3]
_RISK_COLUMN = "risk_adjusted_break_even_capacity_payment_per_kw_year"
_ROLE = "post_hoc_development_parameterized_sensitivity"


@dataclass(frozen=True, slots=True)
class CostRobustnessSpecification:
    schema_version: int
    analysis_id: str
    analysis_role: str
    economic_specification: str
    economic_specification_sha256: str
    ledger: str
    ledger_sha256: str
    reference_table: str
    reference_table_sha256: str
    delay_cost_multipliers: tuple[float, ...]
    fixed_site_cost_multipliers: tuple[float, ...]
    annual_event_counts: tuple[int, ...]
    bootstrap_draw_counts: tuple[int, ...]
    work_zero_tolerance_gpu_h: float

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("cost robustness schema_version must be integer 1")
        if self.analysis_role != _ROLE:
            raise ValueError("cost robustness must be explicitly post-hoc development sensitivity")
        for name in ("analysis_id", "economic_specification", "ledger", "reference_table"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be a non-empty string")
        for name in (
            "economic_specification_sha256", "ledger_sha256", "reference_table_sha256"
        ):
            if re.fullmatch(r"[0-9a-f]{64}", str(getattr(self, name))) is None:
                raise ValueError(f"{name} must be a lowercase SHA-256")
        for name in ("delay_cost_multipliers", "fixed_site_cost_multipliers"):
            values = getattr(self, name)
            if not values or any(
                isinstance(value, bool) or not isinstance(value, (int, float))
                or not np.isfinite(value) or value < 0
                for value in values
            ):
                raise ValueError(f"{name} must contain finite non-negative coordinates")
            if len(set(values)) != len(values) or 1.0 not in values:
                raise ValueError(f"{name} must be unique and include the original 1.0 coordinate")
        for name in ("annual_event_counts", "bootstrap_draw_counts"):
            values = getattr(self, name)
            if not values or any(type(value) is not int or value <= 0 for value in values):
                raise ValueError(f"{name} must contain positive integers")
            if len(set(values)) != len(values):
                raise ValueError(f"{name} must contain unique coordinates")
        if not set(self.annual_event_counts).issubset({1, 12, 50}):
            raise ValueError("cost robustness is restricted to the original fresh-event screens")
        if min(self.bootstrap_draw_counts) < 100:
            raise ValueError("bootstrap draw counts must be at least 100")
        if (
            isinstance(self.work_zero_tolerance_gpu_h, bool)
            or not isinstance(self.work_zero_tolerance_gpu_h, (int, float))
            or not np.isfinite(self.work_zero_tolerance_gpu_h)
            or self.work_zero_tolerance_gpu_h <= 0
        ):
            raise ValueError("work-zero tolerance must be finite and positive")


def load_cost_robustness_specification(path: str | Path) -> CostRobustnessSpecification:
    document = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    expected = {field.name for field in fields(CostRobustnessSpecification)}
    if not isinstance(document, dict) or set(document) != expected:
        raise ValueError("cost robustness specification has unknown or missing fields")
    for name in (
        "delay_cost_multipliers", "fixed_site_cost_multipliers",
        "annual_event_counts", "bootstrap_draw_counts",
    ):
        if not isinstance(document[name], list):
            raise ValueError(f"{name} must be a list")
        document[name] = tuple(document[name])
    return CostRobustnessSpecification(**document)


def _service_diagnostics(ledger: pd.DataFrame, tolerance: float) -> pd.DataFrame:
    rows = []
    for duration, group in ledger.groupby("duration_h", sort=True):
        row: dict[str, Any] = {
            "analysis_role": _ROLE,
            "duration_h": int(str(duration)),
            "scenario_count": len(group),
            "technical_success_count": int(group["technical_success"].sum()),
            "work_zero_tolerance_gpu_h": tolerance,
            "opportunity_cost_interpretation": "conditional_exposure_not_observed_revenue_loss",
        }
        for metric in ("missed_gpu_h", "terminal_backlog_gpu_h"):
            row[f"mean_incremental_{metric}"] = float(group[metric].mean())
            row[f"max_incremental_{metric}"] = float(group[metric].max())
            row[f"incremental_{metric}_above_tolerance_count"] = int(
                (group[metric] > tolerance).sum()
            )
        for metric in (
            "deferred_gpu_h", "incremental_backlog_area_within_recovery_gpu_h_h",
            "incremental_backlog_area_through_episode_end_gpu_h_h",
            "incremental_energy_within_recovery_kwh", "incremental_energy_through_episode_end_kwh",
        ):
            row[f"mean_{metric}"] = float(group[metric].mean())
        rows.append(row)
    return pd.DataFrame(rows)


def calculate_cost_robustness(
    specification: CostRobustnessSpecification,
    economic: EconomicParticipationSpecification,
    grid: CostParameterGrid,
    markets: tuple[MarketArchetype, ...],
    ledger: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Calculate crossed costs and nested-draw diagnostics; perform no replay or I/O.

    The exporter verifies ledger provenance before calling this pure calculation.
    Tests can supply the already published CSV without downloading scenario data.
    """
    evaluation = economic.evaluation
    _validate_grid(economic, grid, markets)
    if evaluation.bootstrap_draws not in specification.bootstrap_draw_counts:
        raise ValueError("bootstrap grid must include the original draw count")
    if evaluation.primary_annual_event_count not in specification.annual_event_counts:
        raise ValueError("annual event grid must include the original primary coordinate")
    if not ledger["offer_fraction_of_technical_ceiling"].eq(1.0).all():
        raise ValueError("cost robustness cannot introduce uncertified fractional offers")
    if set(ledger["notice_h"]) != {evaluation.primary_notice_h}:
        raise ValueError("cost robustness requires the original notice coordinate")
    if not np.allclose(ledger["reliability_target"], evaluation.primary_reliability_target):
        raise ValueError("cost robustness requires the original reliability target")
    capital = next(c for c in grid.capital_cases if c.case_id == evaluation.primary_capital_case_id)
    operating = next(
        c for c in grid.operating_cases if c.case_id == evaluation.primary_operating_case_id
    )
    market = next(m for m in markets if m.archetype_id == evaluation.primary_market_archetype_id)
    if market.flexible_connection_value_per_year != (0.0,):
        raise ValueError("cost robustness requires the original zero connection-value coordinate")
    ledger = ledger.copy()
    ledger["technical_failure_indicator"] = (
        ~ledger["technical_success"].astype(bool)
    ).astype(float)
    surface: list[dict[str, Any]] = []
    stability: list[dict[str, Any]] = []
    for duration, group in ledger.groupby("duration_h", sort=True):
        duration_h = int(str(duration))
        if group["candidate_reduction_kw"].nunique() != 1:
            raise ValueError("each duration must have exactly one fixed candidate")
        candidate_kw = float(group["candidate_reduction_kw"].iloc[0])
        if not np.allclose(group["technical_capacity_ceiling_kw"], candidate_kw):
            raise ValueError("candidate must equal the independently certified ceiling")
        for calls in specification.annual_event_counts:
            draw_counts = (
                specification.bootstrap_draw_counts
                if calls == evaluation.primary_annual_event_count
                else (evaluation.bootstrap_draws,)
            )
            for draws in draw_counts:
                base_draws = draws == evaluation.bootstrap_draws
                means, samples = _group_metrics(
                    group, annual_event_count=calls, draws=draws,
                    seed=_stable_seed(
                        evaluation.bootstrap_seed,
                        (duration_h, evaluation.primary_notice_h, 1.0, calls),
                    ),
                )
                scales = (
                    grid.facility_site_scales_mw if base_draws
                    else (evaluation.primary_facility_site_scale_mw,)
                )
                delay_factors = specification.delay_cost_multipliers if base_draws else (1.0,)
                fixed_factors = specification.fixed_site_cost_multipliers if base_draws else (1.0,)
                for scale_mw in scales:
                    factor = scale_mw * 1000.0 / grid.reference_module_operating_peak_kw
                    scaled_means = {
                        key: value * factor if key in _SCALABLE_LEDGER_METRICS else value
                        for key, value in means.items()
                    }
                    scaled_samples = {
                        key: value * factor if key in _SCALABLE_LEDGER_METRICS else value
                        for key, value in samples.items()
                    }
                    for regime in grid.regimes:
                        reserve, exposure = evaluation.exposure_for(regime.regime)
                        base = _make_inputs(
                            regime=regime, reserved_fraction=reserve, opportunity_alpha=exposure,
                            candidate_capacity_kw=candidate_kw * factor,
                            technical_ceiling_kw=candidate_kw * factor,
                            annual_event_count=calls, metrics=scaled_means,
                            capital=capital, operating=operating, market=market,
                            capacity_payment=0.0,
                            performance_payment=evaluation.primary_performance_payment_per_mwh,
                            connection_value=0.0,
                        )
                        for delay_factor in delay_factors:
                            for fixed_factor in fixed_factors:
                                inputs = replace(
                                    base,
                                    delay_cost_per_gpu_h_h=(
                                        base.delay_cost_per_gpu_h_h * delay_factor
                                    ),
                                    fixed_site_enablement_annual_cost=(
                                        base.fixed_site_enablement_annual_cost * fixed_factor
                                    ),
                                )
                                accounting = annual_economic_value(inputs)
                                risk = _risk_statistics(
                                    inputs, scaled_samples, risk_quantile=evaluation.risk_quantile
                                )
                                row = {
                                    "analysis_id": specification.analysis_id,
                                    "analysis_role": specification.analysis_role,
                                    "currency_basis": economic.monetary_basis,
                                    "annualization_scope": evaluation.dispatch_sampling,
                                    "facility_scale_interpretation": (
                                        grid.facility_scale_interpretation
                                    ),
                                    "regime": regime.regime,
                                    "duration_h": duration_h,
                                    "notice_h": evaluation.primary_notice_h,
                                    "reliability_target": evaluation.primary_reliability_target,
                                    "annual_event_count": calls,
                                    "facility_site_scale_mw": scale_mw,
                                    "candidate_reduction_kw": candidate_kw,
                                    "scaled_accounting_candidate_reduction_kw": (
                                        inputs.offered_capacity_kw
                                    ),
                                    "bootstrap_draws": draws,
                                    "risk_quantile": evaluation.risk_quantile,
                                    "delay_cost_multiplier": delay_factor,
                                    "delay_cost_per_gpu_h_h": inputs.delay_cost_per_gpu_h_h,
                                    "fixed_site_cost_multiplier": fixed_factor,
                                    "fixed_site_enablement_annual_cost": (
                                        inputs.fixed_site_enablement_annual_cost
                                    ),
                                    "performance_payment_per_mwh": (
                                        inputs.performance_payment_per_mwh
                                    ),
                                    "reserved_capacity_fraction": reserve,
                                    "effective_displaced_compute_value_per_gpu_h": (
                                        exposure * operating.value_per_gpu_h
                                    ),
                                    "mean_delay_cost_per_offer_kw_year": (
                                        accounting["delay_cost"] / inputs.offered_capacity_kw
                                    ),
                                    "break_even_capacity_payment_per_kw_year": (
                                        accounting["break_even_capacity_payment_per_kw_year"]
                                    ),
                                    _RISK_COLUMN: risk[_RISK_COLUMN],
                                    # Retain the signed threshold: a floor at zero can hide
                                    # a cost contrast when performance credit already pays.
                                    "unclipped_risk_threshold_per_kw_year": (
                                        -risk["annual_net_value_p05"] / inputs.offered_capacity_kw
                                    ),
                                    "annual_net_value_at_zero_capacity_payment_p05": (
                                        risk["annual_net_value_p05"]
                                    ),
                                }
                                if base_draws:
                                    surface.append(row)
                                if (
                                    calls == evaluation.primary_annual_event_count
                                    and scale_mw == evaluation.primary_facility_site_scale_mw
                                    and delay_factor == 1.0 and fixed_factor == 1.0
                                ):
                                    stability.append(row.copy())
    surface_frame = pd.DataFrame(surface)
    stability_frame = pd.DataFrame(stability)
    keys = ["duration_h", "regime"]
    original = stability_frame.loc[
        stability_frame["bootstrap_draws"].eq(evaluation.bootstrap_draws),
        [*keys, _RISK_COLUMN],
    ].rename(columns={_RISK_COLUMN: "original_draw_count_threshold_per_kw_year"})
    stability_frame = stability_frame.merge(original, on=keys, validate="many_to_one")
    stability_frame["change_from_original_draw_count_per_kw_year"] = (
        stability_frame[_RISK_COLUMN] - stability_frame["original_draw_count_threshold_per_kw_year"]
    )
    return {
        "economic_cost_sensitivity.csv": surface_frame,
        "economic_bootstrap_stability.csv": stability_frame,
        "economic_service_outcomes.csv": _service_diagnostics(
            ledger, specification.work_zero_tolerance_gpu_h
        ),
    }


def reconcile_reference(
    surface: pd.DataFrame,
    reference: pd.DataFrame,
    economic: EconomicParticipationSpecification,
) -> pd.DataFrame:
    """Fail closed unless every published duration/regime point is reproduced."""
    evaluation = economic.evaluation
    selected = surface[
        surface["delay_cost_multiplier"].eq(1.0)
        & surface["fixed_site_cost_multiplier"].eq(1.0)
        & surface["annual_event_count"].eq(evaluation.primary_annual_event_count)
        & surface["facility_site_scale_mw"].eq(evaluation.primary_facility_site_scale_mw)
    ]
    keys = ["duration_h", "regime", "annual_event_count", "facility_site_scale_mw"]
    result = selected[[*keys, _RISK_COLUMN]].merge(
        reference[[*keys, _RISK_COLUMN]], on=keys, how="outer", validate="one_to_one",
        suffixes=("_recomputed", "_published"), indicator=True,
    )
    if len(result) != len(economic.technical.duration_hours) * 3:
        raise ValueError("reference reconciliation has missing or extra duration/regime cells")
    result["absolute_difference_per_kw_year"] = (
        result[f"{_RISK_COLUMN}_recomputed"] - result[f"{_RISK_COLUMN}_published"]
    ).abs()
    if (
        not result["_merge"].eq("both").all()
        or not np.isfinite(result["absolute_difference_per_kw_year"]).all()
        or result["absolute_difference_per_kw_year"].max() > 1e-8
    ):
        raise ValueError("cost robustness does not reproduce the published Figure 6 reference")
    return result.drop(columns="_merge")


def export_cost_robustness(specification_path: str | Path, output: str | Path) -> dict[str, Any]:
    """Verify inputs, calculate tables and atomically publish a new source bundle.

    Existing output directories are never overwritten. A dirty worktree is
    reported honestly together with exact input and executable-source hashes.
    """
    output_path = Path(output)
    if output_path.exists():
        raise FileExistsError(f"cost robustness output already exists: {output_path}")
    specification = load_cost_robustness_specification(specification_path)
    bound_inputs = {
        specification.economic_specification: specification.economic_specification_sha256,
        specification.ledger: specification.ledger_sha256,
        specification.reference_table: specification.reference_table_sha256,
    }
    for path, expected in bound_inputs.items():
        if sha256_file(Path(path)) != expected:
            raise ValueError(f"cost robustness input SHA-256 mismatch: {path}")
    economic = load_economic_participation_specification(specification.economic_specification)
    verified_economic_inputs = verify_economic_input_hashes(economic)
    ledger, ledger_manifest = _load_verified_ledger(specification.ledger, economic)
    grid = load_cost_parameter_grid(economic.inputs.cost_parameter_grid)
    markets = load_market_archetypes(economic.inputs.market_archetypes).archetypes
    tables = calculate_cost_robustness(specification, economic, grid, markets, ledger)
    tables["economic_reference_reconciliation.csv"] = reconcile_reference(
        tables["economic_cost_sensitivity.csv"],
        pd.read_csv(specification.reference_table), economic
    )
    runtime_paths = sorted({
        *(_ROOT / "src/aidrbench/economics").glob("*.py"),
        Path(__file__),
        _ROOT / "src/aidrbench/evaluation/economic_participation.py",
        _ROOT / "src/aidrbench/data/splits.py",
        _ROOT / "src/aidrbench/cli.py",
    })
    manifest: dict[str, Any] = {
        "schema_version": "aidrbench.economic_cost_robustness.v1",
        "analysis_id": specification.analysis_id,
        "analysis_role": specification.analysis_role,
        "software": _git_state(),
        "runtime_source_sha256": {
            str(path.relative_to(_ROOT)): sha256_file(path) for path in runtime_paths
        },
        "specification": {
            "path": str(specification_path),
            "sha256": sha256_file(Path(specification_path)),
        },
        "bound_input_sha256": bound_inputs,
        "economic_input_sha256": verified_economic_inputs,
        "ledger_manifest_sha256": sha256_file(
            Path(specification.ledger).with_name("ledger_manifest.json")
        ),
        "physical_ledger_contract_sha256": ledger_manifest["physical_ledger_contract_sha256"],
        "scenario_count": ledger["scenario_id"].nunique(),
        "paired_event_count": len(ledger),
        "locked_scenario_payloads_read": False,
        "technical_capacity_reselected": False,
        "original_figure6_tables_modified": False,
        "interpretation": {
            "cost_axes": "research_design_coordinates_not_observed_operator_prices",
            "draws": (
                "nested_common_random_draws_not_independent_validation_or_confidence_intervals"
            ),
            "service": "incremental_missed_and_terminal_work_not_operator_revenue_observations",
            "delay": "USD_per_GPU_hour_of_backlog_per_hour_of_waiting",
            "zero_floor": "signed_threshold_retained_separately_from_nonnegative_capacity_payment",
        },
        "tables": [],
    }
    # A new bundle is assembled away from its published path. Check input
    # integrity again before publishing, not merely before the calculation.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".cost-robustness-", dir=output_path.parent
    ) as temporary:
        stage = Path(temporary) / "bundle"
        stage.mkdir()
        for filename, frame in tables.items():
            target = stage / filename
            frame.to_csv(target, index=False, float_format="%.12g")
            manifest["tables"].append({
                "output": filename, "row_count": len(frame), "columns": list(frame.columns),
                "output_sha256": sha256_file(target),
            })
        for path, expected in bound_inputs.items():
            if sha256_file(Path(path)) != expected:
                raise ValueError(f"cost robustness input changed during export: {path}")
        (stage / "source_data_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        if output_path.exists():
            raise FileExistsError(f"cost robustness output already exists: {output_path}")
        stage.rename(output_path)
    return {
        "output": str(output_path), "analysis_role": specification.analysis_role,
        "table_count": len(tables), "rows": {name: len(frame) for name, frame in tables.items()},
        "maximum_reference_difference_per_kw_year": float(
            tables["economic_reference_reconciliation.csv"]["absolute_difference_per_kw_year"].max()
        ),
        "locked_scenario_payloads_read": False,
    }
