"""Evaluate operator-economic participation from a paired event ledger.

This module implements a parameterized *development screening*.  It keeps the
prior causal certificate as a technical ceiling and never relabels the output
as an independent economic certificate.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from aidrbench.data.splits import sha256_file
from aidrbench.economics.accounting import AnnualEconomicInputs, annual_economic_value
from aidrbench.economics.specification import (
    CapitalCase,
    CostParameterGrid,
    EconomicParticipationSpecification,
    MarketArchetype,
    OperatingCase,
    RegimeCase,
    annual_event_count_screening_class,
    load_cost_parameter_grid,
    load_economic_participation_specification,
    load_market_archetypes,
    scenario_set_sha256,
    verify_economic_input_hashes,
    verify_physical_input_hashes,
)

_ROOT = Path(__file__).resolve().parents[3]
_LEDGER_METRICS = (
    "delivered_energy_kwh",
    "capped_delivered_energy_kwh",
    "shortfall_energy_kwh",
    "deferred_gpu_h",
    "recovered_within_recovery_window_gpu_h",
    "recovered_through_episode_end_gpu_h",
    "incremental_backlog_area_within_recovery_gpu_h_h",
    "incremental_backlog_area_through_episode_end_gpu_h_h",
    "incremental_energy_within_recovery_kwh",
    "incremental_energy_through_episode_end_kwh",
    "missed_gpu_h",
    "terminal_backlog_gpu_h",
    "technical_failure_indicator",
)
_LEDGER_REQUIRED = {
    "evaluation_split",
    "scenario_id",
    "scenario_hash",
    "episode_seed",
    "event_id",
    "duration_h",
    "notice_h",
    "reliability_target",
    "confidence_level",
    "technical_capacity_ceiling_kw",
    "offer_fraction_of_technical_ceiling",
    "candidate_reduction_kw",
    "technical_success",
    *_LEDGER_METRICS[:-1],
}
_SCALABLE_LEDGER_METRICS = frozenset(_LEDGER_METRICS).difference(
    {"technical_failure_indicator"}
)


def _proportional_reference_module_scale_factor(
    *,
    facility_site_scale_mw: float,
    reference_module_operating_peak_kw: float,
) -> float:
    """Return a no-diversification accounting scale from the frozen module.

    This deliberately rescales the reference-module event ledger without
    claiming that the scaled facility has been technically certified.  The
    binary technical-success indicator remains one site call, rather than a
    count of independently diversified module failures.
    """

    factor = facility_site_scale_mw * 1_000.0 / reference_module_operating_peak_kw
    if not np.isfinite(factor) or factor <= 0.0:
        raise ValueError("facility/site proportional-reference scale factor is invalid")
    return float(factor)


def _scale_ledger_metrics(
    metrics: dict[str, float] | dict[str, np.ndarray],
    *,
    scale_factor: float,
) -> dict[str, float] | dict[str, np.ndarray]:
    """Scale physical quantities while preserving a non-diversified failure call."""

    scaled = {
        metric: value * scale_factor if metric in _SCALABLE_LEDGER_METRICS else value
        for metric, value in metrics.items()
    }
    return cast(dict[str, float] | dict[str, np.ndarray], scaled)


def _git_state() -> dict[str, object]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "git_commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "working_tree_dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
    }


def _stable_seed(base_seed: int, parts: Iterable[object]) -> int:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int((base_seed + int.from_bytes(digest[:8], "big")) % (2**63 - 1))


def _load_verified_ledger(
    ledger_path: str | Path,
    specification: EconomicParticipationSpecification,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    path = Path(ledger_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    manifest_path = path.with_name("ledger_manifest.json")
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"economic evaluation requires the sibling ledger manifest: {manifest_path}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("economic ledger manifest must be a mapping")
    if manifest.get("analysis_id") != specification.analysis_id:
        raise ValueError("economic ledger analysis ID does not match evaluation protocol")
    if manifest.get("analysis_role") != specification.analysis_role:
        raise ValueError("economic ledger analysis role does not match evaluation protocol")
    if (
        manifest.get("physical_ledger_contract_sha256")
        != specification.physical_ledger_contract_sha256
    ):
        raise ValueError(
            "economic ledger physical-contract hash does not match evaluation protocol"
        )
    if manifest.get("physical_ledger_contract") != specification.physical_ledger_contract():
        raise ValueError(
            "economic ledger physical-contract document does not match evaluation protocol"
        )
    if manifest.get("scenario_count") != specification.technical.expected_scenario_count:
        raise ValueError("economic ledger scenario count does not match evaluation protocol")
    if manifest.get("scenario_set_sha256") != specification.technical.scenario_set_sha256:
        raise ValueError("economic ledger scenario hash set does not match evaluation protocol")
    if manifest.get("physical_input_sha256") != verify_physical_input_hashes(specification):
        raise ValueError("economic ledger physical-input hashes do not match evaluation protocol")
    technical_provenance = manifest.get("technical_provenance")
    if not isinstance(technical_provenance, dict):
        raise ValueError("economic ledger is missing fixed-controller provenance")
    if (
        technical_provenance.get("manifest_sha256")
        != specification.technical.technical_certificate_manifest_sha256
    ):
        raise ValueError("economic ledger certificate-manifest hash does not match the protocol")
    if (
        technical_provenance.get("controller_config_sha256")
        != specification.technical.controller_config_sha256
    ):
        raise ValueError("economic ledger controller provenance does not match the protocol")
    if manifest.get("event_ledger_sha256") != sha256_file(path):
        raise ValueError("economic ledger SHA-256 does not match its manifest")
    ledger = pd.read_parquet(path)
    missing = sorted(_LEDGER_REQUIRED.difference(ledger.columns))
    if missing:
        raise ValueError(f"economic ledger is missing columns: {', '.join(missing)}")
    if ledger.empty:
        raise ValueError("economic ledger must not be empty")
    ledger = ledger.copy()
    ledger["technical_failure_indicator"] = (~ledger["technical_success"].astype(bool)).astype(
        float
    )
    _validate_ledger_contract(ledger, specification)
    return ledger, {str(key): value for key, value in manifest.items()}


def _certificate_capacities(
    specification: EconomicParticipationSpecification,
) -> dict[tuple[int, int], float]:
    """Read the exact certified ceilings required by the economic protocol."""

    certificate = pd.read_parquet(specification.technical.technical_certificate_path)
    required = {
        "duration_h",
        "notice_h",
        "reliability_target",
        "confidence_level",
        "candidate_reduction_kw",
        "certified",
    }
    missing = sorted(required.difference(certificate.columns))
    if missing:
        raise ValueError(f"technical certificate is missing columns: {', '.join(missing)}")
    capacities: dict[tuple[int, int], float] = {}
    for duration_h in specification.technical.duration_hours:
        for notice_h in specification.technical.notice_hours:
            matches = certificate[
                (pd.to_numeric(certificate["duration_h"], errors="raise") == duration_h)
                & (pd.to_numeric(certificate["notice_h"], errors="raise") == notice_h)
                & np.isclose(
                    pd.to_numeric(certificate["reliability_target"], errors="raise"),
                    specification.technical.reliability_target,
                )
                & np.isclose(
                    pd.to_numeric(certificate["confidence_level"], errors="raise"),
                    specification.technical.confidence_level,
                )
                & certificate["certified"].astype(bool)
            ]
            if len(matches) != 1:
                raise ValueError(
                    "economic ledger requires exactly one certified technical ceiling for "
                    f"H={duration_h}, N={notice_h}"
                )
            capacity = float(matches["candidate_reduction_kw"].iloc[0])
            if not np.isfinite(capacity) or capacity <= 0.0:
                raise ValueError("technical certificate has an invalid positive capacity")
            capacities[(duration_h, notice_h)] = capacity
    return capacities


def _validate_ledger_contract(
    ledger: pd.DataFrame,
    specification: EconomicParticipationSpecification,
) -> None:
    """Reject incomplete, duplicated or off-protocol physical ledger rows."""

    technical = specification.technical
    expected_rows = (
        technical.expected_scenario_count
        * len(technical.duration_hours)
        * len(technical.notice_hours)
        * len(technical.offer_fractions)
    )
    if len(ledger) != expected_rows:
        raise ValueError(
            f"economic ledger has {len(ledger)} rows; protocol requires {expected_rows}"
        )
    if set(ledger["evaluation_split"].astype(str)) != {specification.analysis_role}:
        raise ValueError("economic ledger has an unexpected evaluation split")
    if set(pd.to_numeric(ledger["event_id"], errors="raise").astype(int)) != {technical.event_id}:
        raise ValueError("economic ledger has an unexpected event ID")
    if set(pd.to_numeric(ledger["duration_h"], errors="raise").astype(int)) != set(
        technical.duration_hours
    ):
        raise ValueError("economic ledger duration cells do not match the protocol")
    if set(pd.to_numeric(ledger["notice_h"], errors="raise").astype(int)) != set(
        technical.notice_hours
    ):
        raise ValueError("economic ledger notice cells do not match the protocol")
    if not np.allclose(
        pd.to_numeric(ledger["reliability_target"], errors="raise"),
        technical.reliability_target,
        rtol=0.0,
        atol=1e-12,
    ) or not np.allclose(
        pd.to_numeric(ledger["confidence_level"], errors="raise"),
        technical.confidence_level,
        rtol=0.0,
        atol=1e-12,
    ):
        raise ValueError("economic ledger criteria do not match the protocol")

    scenario_records = (
        ledger.loc[:, ["episode_seed", "scenario_id", "scenario_hash"]]
        .drop_duplicates()
        .to_dict(orient="records")
    )
    if len(scenario_records) != technical.expected_scenario_count:
        raise ValueError("economic ledger does not contain the declared frozen scenario set")
    if scenario_set_sha256(scenario_records) != technical.scenario_set_sha256:
        raise ValueError("economic ledger scenario hashes do not match the protocol")

    identity_columns = [
        "scenario_hash",
        "duration_h",
        "notice_h",
        "offer_fraction_of_technical_ceiling",
    ]
    if bool(ledger.duplicated(identity_columns).any()):
        raise ValueError("economic ledger has duplicate scenario/capacity cells")
    observed_fractions = tuple(
        sorted(
            pd.to_numeric(ledger["offer_fraction_of_technical_ceiling"], errors="raise").unique()
        )
    )
    if len(observed_fractions) != len(technical.offer_fractions) or not np.allclose(
        observed_fractions,
        technical.offer_fractions,
        rtol=0.0,
        atol=1e-12,
    ):
        raise ValueError("economic ledger offer fractions do not match the protocol")

    capacities = _certificate_capacities(specification)
    for (duration_h, notice_h), group in ledger.groupby(["duration_h", "notice_h"], sort=True):
        duration = int(str(duration_h))
        notice = int(str(notice_h))
        ceiling = capacities.get((duration, notice))
        if ceiling is None:
            raise ValueError("economic ledger contains an undeclared certificate cell")
        if not np.allclose(
            pd.to_numeric(group["technical_capacity_ceiling_kw"], errors="raise"),
            ceiling,
            rtol=0.0,
            atol=1e-9,
        ):
            raise ValueError("economic ledger technical ceiling differs from the certificate")
        candidate = pd.to_numeric(group["candidate_reduction_kw"], errors="raise").to_numpy(
            dtype=float
        )
        fractions = pd.to_numeric(
            group["offer_fraction_of_technical_ceiling"], errors="raise"
        ).to_numpy(dtype=float)
        if not np.allclose(candidate, ceiling * fractions, rtol=0.0, atol=1e-9):
            raise ValueError("economic ledger candidate capacity differs from ceiling × fraction")
        group_records = (
            group.loc[:, ["episode_seed", "scenario_id", "scenario_hash"]]
            .drop_duplicates()
            .to_dict(orient="records")
        )
        if len(group_records) != technical.expected_scenario_count:
            raise ValueError("economic ledger capacity cell is missing frozen scenarios")
        if scenario_set_sha256(group_records) != technical.scenario_set_sha256:
            raise ValueError("economic ledger capacity cell has an unexpected frozen scenario set")

    raw_delivery = pd.to_numeric(ledger["delivered_energy_kwh"], errors="raise").to_numpy(
        dtype=float
    )
    paid_delivery = pd.to_numeric(ledger["capped_delivered_energy_kwh"], errors="raise").to_numpy(
        dtype=float
    )
    shortfall = pd.to_numeric(ledger["shortfall_energy_kwh"], errors="raise").to_numpy(dtype=float)
    obligation = pd.to_numeric(ledger["candidate_reduction_kw"], errors="raise").to_numpy(
        dtype=float
    ) * pd.to_numeric(ledger["duration_h"], errors="raise").to_numpy(dtype=float)
    if not np.isfinite(np.column_stack((raw_delivery, paid_delivery, shortfall))).all():
        raise ValueError("economic ledger delivery quantities must be finite")
    if bool((raw_delivery + 1e-9 < paid_delivery).any()):
        raise ValueError("capped delivery cannot exceed raw physical delivery")
    if bool((paid_delivery > obligation + 1e-9).any()):
        raise ValueError("paid delivery cannot exceed the declared event obligation")
    if not np.allclose(paid_delivery + shortfall, obligation, rtol=0.0, atol=1e-8):
        raise ValueError("capped delivery plus shortfall must equal the declared obligation")


def _validate_grid(
    specification: EconomicParticipationSpecification,
    cost_grid: CostParameterGrid,
    market_archetypes: tuple[MarketArchetype, ...],
) -> None:
    if cost_grid.schema_version != 2:
        raise ValueError("unsupported cost-parameter-grid schema version")
    if cost_grid.currency_basis != specification.monetary_basis:
        raise ValueError("cost grid monetary basis does not match economic protocol")
    if cost_grid.analysis_status != "illustrative_parameterized_sensitivity":
        raise ValueError("economic v1 requires explicit illustrative parameter sensitivity")
    if not {case.case_id for case in cost_grid.capital_cases} >= {
        specification.evaluation.primary_capital_case_id
    }:
        raise ValueError("primary capital case is absent from the cost grid")
    if not {case.case_id for case in cost_grid.operating_cases} >= {
        specification.evaluation.primary_operating_case_id
    }:
        raise ValueError("primary operating case is absent from the cost grid")
    if not {item.archetype_id for item in market_archetypes} >= {
        specification.evaluation.primary_market_archetype_id
    }:
        raise ValueError("primary market archetype is absent from the market grid")
    if not any(
        np.isclose(
            specification.evaluation.primary_facility_site_scale_mw,
            scale_mw,
            rtol=0.0,
            atol=1e-12,
        )
        for scale_mw in cost_grid.facility_site_scales_mw
    ):
        raise ValueError("primary facility/site scale is absent from the cost grid")


def _group_metrics(
    group: pd.DataFrame,
    *,
    annual_event_count: int,
    draws: int,
    seed: int,
) -> tuple[dict[str, float], dict[str, np.ndarray]]:
    values = group.loc[:, list(_LEDGER_METRICS)].astype(float).to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("economic ledger contains non-finite physical metrics")
    means = dict(zip(_LEDGER_METRICS, values.mean(axis=0) * annual_event_count, strict=True))
    generator = np.random.default_rng(seed)
    indices = generator.integers(0, len(values), size=(draws, annual_event_count))
    draws_by_metric = {
        metric: values[indices, column_index].sum(axis=1)
        for column_index, metric in enumerate(_LEDGER_METRICS)
    }
    return means, draws_by_metric


def _make_inputs(
    *,
    regime: RegimeCase,
    reserved_fraction: float,
    opportunity_alpha: float,
    candidate_capacity_kw: float,
    technical_ceiling_kw: float,
    annual_event_count: int,
    metrics: dict[str, float],
    capital: CapitalCase,
    operating: OperatingCase,
    market: MarketArchetype,
    capacity_payment: float,
    performance_payment: float,
    connection_value: float,
) -> AnnualEconomicInputs:
    return AnnualEconomicInputs(
        regime=regime.regime,
        offered_capacity_kw=candidate_capacity_kw,
        technical_capacity_ceiling_kw=technical_ceiling_kw,
        annual_event_count=annual_event_count,
        annual_capped_delivered_energy_kwh=metrics["capped_delivered_energy_kwh"],
        annual_shortfall_energy_kwh=metrics["shortfall_energy_kwh"],
        annual_deferred_gpu_h=metrics["deferred_gpu_h"],
        annual_backlog_area_gpu_h_h=metrics["incremental_backlog_area_through_episode_end_gpu_h_h"],
        annual_incremental_energy_kwh=metrics["incremental_energy_through_episode_end_kwh"],
        annual_missed_gpu_h=metrics["missed_gpu_h"],
        annual_terminal_backlog_gpu_h=metrics["terminal_backlog_gpu_h"],
        annual_failure_count=metrics["technical_failure_indicator"],
        capacity_payment_per_kw_year=capacity_payment,
        performance_payment_per_mwh=performance_payment,
        electricity_price_per_kwh=operating.electricity_price_per_kwh,
        flexible_connection_value_per_year=connection_value,
        fixed_site_enablement_annual_cost=capital.fixed_site_enablement_annual_cost,
        variable_enablement_cost_per_offer_kw=(
            capital.variable_enablement_cost_per_offer_kw
        ),
        checkpoint_cost_per_event=capital.checkpoint_cost_per_event,
        reserved_capacity_fraction=reserved_fraction,
        installed_cost_per_reserved_kw=capital.installed_cost_per_reserved_kw,
        discount_rate=capital.discount_rate,
        economic_life_years=capital.economic_life_years,
        salvage_fraction=capital.salvage_fraction,
        annual_om_fraction=capital.annual_om_fraction,
        opportunity_exposure_alpha=opportunity_alpha,
        value_per_gpu_h=operating.value_per_gpu_h,
        delay_cost_per_gpu_h_h=operating.delay_cost_per_gpu_h_h,
        missed_work_cost_per_gpu_h=operating.missed_work_cost_per_gpu_h,
        terminal_backlog_cost_per_gpu_h=operating.terminal_backlog_cost_per_gpu_h,
        shortfall_penalty_per_mwh=market.shortfall_penalty_per_mwh,
        failure_penalty_per_event=market.failure_penalty_per_event,
    )


def _parameter_values(
    *,
    capital: CapitalCase,
    operating: OperatingCase,
    regime: RegimeCase,
    reserve_fraction: float,
    opportunity_alpha: float,
    market: MarketArchetype,
    capacity_payment: float,
    performance_payment: float,
    connection_value: float,
) -> dict[str, Any]:
    return {
        "capital_case_id": capital.case_id,
        "capital_sensitivity_axis": capital.sensitivity_axis,
        "operating_case_id": operating.case_id,
        "market_archetype_id": market.archetype_id,
        "regime": regime.regime,
        "economic_life_years": capital.economic_life_years,
        "discount_rate": capital.discount_rate,
        "salvage_fraction": capital.salvage_fraction,
        "installed_cost_per_reserved_kw": capital.installed_cost_per_reserved_kw,
        "annual_om_fraction": capital.annual_om_fraction,
        "fixed_site_enablement_annual_cost": capital.fixed_site_enablement_annual_cost,
        "variable_enablement_cost_per_offer_kw": (
            capital.variable_enablement_cost_per_offer_kw
        ),
        "checkpoint_cost_per_event": capital.checkpoint_cost_per_event,
        "reserved_capacity_fraction": reserve_fraction,
        "opportunity_exposure_alpha": opportunity_alpha,
        "value_per_gpu_h": operating.value_per_gpu_h,
        "effective_displaced_compute_value_per_gpu_h": (
            opportunity_alpha * operating.value_per_gpu_h
        ),
        "delay_cost_per_gpu_h_h": operating.delay_cost_per_gpu_h_h,
        "missed_work_cost_per_gpu_h": operating.missed_work_cost_per_gpu_h,
        "terminal_backlog_cost_per_gpu_h": operating.terminal_backlog_cost_per_gpu_h,
        "electricity_price_per_kwh": operating.electricity_price_per_kwh,
        "capacity_payment_per_kw_year": capacity_payment,
        "performance_payment_per_mwh": performance_payment,
        "flexible_connection_value_per_year": connection_value,
        "shortfall_penalty_per_mwh": market.shortfall_penalty_per_mwh,
        "failure_penalty_per_event": market.failure_penalty_per_event,
    }


def _per_event_metric_values(
    mean_metrics: dict[str, float], annual_event_count: int
) -> dict[str, float]:
    return {
        "mean_raw_delivered_energy_per_event_kwh": (
            mean_metrics["delivered_energy_kwh"] / annual_event_count
        ),
        "mean_capped_delivered_energy_per_event_kwh": (
            mean_metrics["capped_delivered_energy_kwh"] / annual_event_count
        ),
        "mean_shortfall_energy_per_event_kwh": (
            mean_metrics["shortfall_energy_kwh"] / annual_event_count
        ),
        "mean_deferred_compute_per_event_gpu_h": (
            mean_metrics["deferred_gpu_h"] / annual_event_count
        ),
        "mean_recovered_within_recovery_window_per_event_gpu_h": (
            mean_metrics["recovered_within_recovery_window_gpu_h"] / annual_event_count
        ),
        "mean_recovered_through_episode_end_per_event_gpu_h": (
            mean_metrics["recovered_through_episode_end_gpu_h"] / annual_event_count
        ),
        "mean_incremental_backlog_area_within_recovery_per_event_gpu_h_h": (
            mean_metrics["incremental_backlog_area_within_recovery_gpu_h_h"] / annual_event_count
        ),
        "mean_incremental_backlog_area_through_episode_end_per_event_gpu_h_h": (
            mean_metrics["incremental_backlog_area_through_episode_end_gpu_h_h"]
            / annual_event_count
        ),
        "mean_incremental_energy_within_recovery_per_event_kwh": (
            mean_metrics["incremental_energy_within_recovery_kwh"] / annual_event_count
        ),
        "mean_incremental_energy_through_episode_end_per_event_kwh": (
            mean_metrics["incremental_energy_through_episode_end_kwh"] / annual_event_count
        ),
        "mean_missed_work_per_event_gpu_h": (mean_metrics["missed_gpu_h"] / annual_event_count),
        "mean_terminal_backlog_per_event_gpu_h": (
            mean_metrics["terminal_backlog_gpu_h"] / annual_event_count
        ),
    }


def _group_float(value: object, *, name: str) -> float:
    """Parse a pandas group key without accepting non-finite values."""

    parsed = float(str(value))
    if not np.isfinite(parsed):
        raise ValueError(f"economic group key {name} must be finite")
    return parsed


def _annual_net_draws(inputs: AnnualEconomicInputs, metrics: dict[str, np.ndarray]) -> np.ndarray:
    """Vectorised annual net values for independent fresh-event screening draws."""

    reserve_cost = annual_economic_value(
        _make_inputs(
            regime=RegimeCase(
                regime=inputs.regime,
                reserved_capacity_fractions=(inputs.reserved_capacity_fraction,),
                opportunity_exposure_alphas=(inputs.opportunity_exposure_alpha,),
            ),
            reserved_fraction=inputs.reserved_capacity_fraction,
            opportunity_alpha=inputs.opportunity_exposure_alpha,
            candidate_capacity_kw=inputs.offered_capacity_kw,
            technical_ceiling_kw=inputs.technical_capacity_ceiling_kw,
            annual_event_count=inputs.annual_event_count,
            metrics={metric: 0.0 for metric in _LEDGER_METRICS},
            capital=CapitalCase(
                case_id="draw_fixed",
                sensitivity_axis="reference",
                economic_life_years=inputs.economic_life_years,
                discount_rate=inputs.discount_rate,
                salvage_fraction=inputs.salvage_fraction,
                installed_cost_per_reserved_kw=inputs.installed_cost_per_reserved_kw,
                annual_om_fraction=inputs.annual_om_fraction,
                fixed_site_enablement_annual_cost=(
                    inputs.fixed_site_enablement_annual_cost
                ),
                variable_enablement_cost_per_offer_kw=(
                    inputs.variable_enablement_cost_per_offer_kw
                ),
                checkpoint_cost_per_event=inputs.checkpoint_cost_per_event,
            ),
            operating=OperatingCase(
                case_id="draw_fixed",
                value_per_gpu_h=inputs.value_per_gpu_h,
                delay_cost_per_gpu_h_h=inputs.delay_cost_per_gpu_h_h,
                missed_work_cost_per_gpu_h=inputs.missed_work_cost_per_gpu_h,
                terminal_backlog_cost_per_gpu_h=inputs.terminal_backlog_cost_per_gpu_h,
                electricity_price_per_kwh=inputs.electricity_price_per_kwh,
            ),
            market=MarketArchetype(
                archetype_id="draw_fixed",
                capacity_payment_per_kw_year=(inputs.capacity_payment_per_kw_year,),
                performance_payment_per_mwh=(inputs.performance_payment_per_mwh,),
                flexible_connection_value_per_year=(inputs.flexible_connection_value_per_year,),
                shortfall_penalty_per_mwh=inputs.shortfall_penalty_per_mwh,
                failure_penalty_per_event=inputs.failure_penalty_per_event,
            ),
            capacity_payment=inputs.capacity_payment_per_kw_year,
            performance_payment=inputs.performance_payment_per_mwh,
            connection_value=inputs.flexible_connection_value_per_year,
        )
    )
    # The fixed call has zero physical metrics and exposes the all-fixed terms.
    fixed_net = reserve_cost["annual_net_value"]
    return (
        fixed_net
        + metrics["capped_delivered_energy_kwh"] / 1_000.0 * inputs.performance_payment_per_mwh
        - metrics["incremental_energy_through_episode_end_kwh"] * inputs.electricity_price_per_kwh
        - metrics["deferred_gpu_h"] * inputs.opportunity_exposure_alpha * inputs.value_per_gpu_h
        - metrics["incremental_backlog_area_through_episode_end_gpu_h_h"]
        * inputs.delay_cost_per_gpu_h_h
        - metrics["missed_gpu_h"] * inputs.missed_work_cost_per_gpu_h
        - metrics["terminal_backlog_gpu_h"] * inputs.terminal_backlog_cost_per_gpu_h
        - metrics["shortfall_energy_kwh"] / 1_000.0 * inputs.shortfall_penalty_per_mwh
        - metrics["technical_failure_indicator"] * inputs.failure_penalty_per_event
    )


def _risk_statistics(
    inputs: AnnualEconomicInputs,
    metrics: dict[str, np.ndarray],
    *,
    risk_quantile: float,
) -> dict[str, float]:
    values = _annual_net_draws(inputs, metrics)
    fixed_site_enablement = (
        inputs.fixed_site_enablement_annual_cost if inputs.offered_capacity_kw > 0.0 else 0.0
    )
    values_excluding_fixed_site = values + fixed_site_enablement
    p05 = float(np.quantile(values, risk_quantile))
    p95 = float(np.quantile(values, 1.0 - risk_quantile))
    capacity_revenue = inputs.offered_capacity_kw * inputs.capacity_payment_per_kw_year
    no_capacity = values - capacity_revenue
    no_capacity_excluding_fixed_site = values_excluding_fixed_site - capacity_revenue
    risk_break_even_capacity = max(
        -float(np.quantile(no_capacity, risk_quantile)) / inputs.offered_capacity_kw,
        0.0,
    )
    delivered_mwh = metrics["capped_delivered_energy_kwh"] / 1_000.0
    no_performance = values - delivered_mwh * inputs.performance_payment_per_mwh
    no_performance_excluding_fixed_site = (
        values_excluding_fixed_site - delivered_mwh * inputs.performance_payment_per_mwh
    )
    required_performance = np.divide(
        -no_performance,
        delivered_mwh,
        out=np.full_like(no_performance, np.inf),
        where=delivered_mwh > 0.0,
    )
    required_performance_excluding_fixed_site = np.divide(
        -no_performance_excluding_fixed_site,
        delivered_mwh,
        out=np.full_like(no_performance_excluding_fixed_site, np.inf),
        where=delivered_mwh > 0.0,
    )
    return {
        "annual_net_value_p05": p05,
        "annual_net_value_p95": p95,
        "annual_net_value_median": float(np.median(values)),
        "negative_value_probability": float((values < 0.0).mean()),
        "risk_adjusted_break_even_capacity_payment_per_kw_year": risk_break_even_capacity,
        "annual_net_value_excluding_fixed_site_p05": float(
            np.quantile(values_excluding_fixed_site, risk_quantile)
        ),
        "annual_net_value_excluding_fixed_site_p95": float(
            np.quantile(values_excluding_fixed_site, 1.0 - risk_quantile)
        ),
        "annual_net_value_excluding_fixed_site_median": float(
            np.median(values_excluding_fixed_site)
        ),
        "negative_value_probability_excluding_fixed_site": float(
            (values_excluding_fixed_site < 0.0).mean()
        ),
        "risk_adjusted_break_even_capacity_payment_excluding_fixed_site_per_kw_year": (
            max(
                -float(
                    np.quantile(no_capacity_excluding_fixed_site, risk_quantile)
                )
                / inputs.offered_capacity_kw,
                0.0,
            )
            if inputs.offered_capacity_kw > 0.0
            else float("inf")
        ),
        "risk_adjusted_break_even_performance_payment_per_mwh": max(
            float(np.quantile(required_performance, 1.0 - risk_quantile)), 0.0
        ),
        "risk_adjusted_break_even_performance_payment_excluding_fixed_site_per_mwh": max(
            float(
                np.quantile(required_performance_excluding_fixed_site, 1.0 - risk_quantile)
            ),
            0.0,
        ),
    }


def _result_rows(
    specification: EconomicParticipationSpecification,
    ledger: pd.DataFrame,
    cost_grid: CostParameterGrid,
    markets: tuple[MarketArchetype, ...],
) -> list[dict[str, Any]]:
    group_columns = [
        "duration_h",
        "notice_h",
        "reliability_target",
        "confidence_level",
        "technical_capacity_ceiling_kw",
        "offer_fraction_of_technical_ceiling",
        "candidate_reduction_kw",
    ]
    rows: list[dict[str, Any]] = []
    for group_key, group in ledger.groupby(group_columns, sort=True, dropna=False):
        if not isinstance(group_key, tuple) or len(group_key) != len(group_columns):
            raise RuntimeError("economic ledger grouping did not yield the declared key")
        duration_h = int(_group_float(group_key[0], name="duration_h"))
        notice_h = int(_group_float(group_key[1], name="notice_h"))
        reliability_target = _group_float(group_key[2], name="reliability_target")
        confidence_level = _group_float(group_key[3], name="confidence_level")
        technical_ceiling_kw = _group_float(group_key[4], name="technical_capacity_ceiling_kw")
        offer_fraction = _group_float(group_key[5], name="offer_fraction_of_technical_ceiling")
        candidate_kw = _group_float(group_key[6], name="candidate_reduction_kw")
        if not np.isclose(offer_fraction, 1.0, rtol=0.0, atol=1e-12):
            # Sub-Kcert trajectories remain available as physical development
            # diagnostics, but are not annualised as economically qualified
            # offers because they lack an independent technical certificate.
            continue
        success_rate = float(group["technical_success"].astype(bool).mean())
        for annual_event_count in specification.evaluation.annual_event_counts:
            mean_metrics, draw_metrics = _group_metrics(
                group,
                annual_event_count=annual_event_count,
                draws=specification.evaluation.bootstrap_draws,
                seed=_stable_seed(
                    specification.evaluation.bootstrap_seed,
                    (
                        duration_h,
                        notice_h,
                        offer_fraction,
                        annual_event_count,
                    ),
                ),
            )
            annual_event_count_class, annual_event_count_is_stress = (
                annual_event_count_screening_class(annual_event_count)
            )
            for facility_site_scale_mw in cost_grid.facility_site_scales_mw:
                scale_factor = _proportional_reference_module_scale_factor(
                    facility_site_scale_mw=facility_site_scale_mw,
                    reference_module_operating_peak_kw=(
                        cost_grid.reference_module_operating_peak_kw
                    ),
                )
                scaled_mean_metrics = {
                    metric: value * scale_factor
                    if metric in _SCALABLE_LEDGER_METRICS
                    else value
                    for metric, value in mean_metrics.items()
                }
                scaled_draw_metrics = {
                    metric: value * scale_factor
                    if metric in _SCALABLE_LEDGER_METRICS
                    else value
                    for metric, value in draw_metrics.items()
                }
                scaled_candidate_kw = candidate_kw * scale_factor
                scaled_technical_ceiling_kw = technical_ceiling_kw * scale_factor
                for capital in cost_grid.capital_cases:
                    for operating in cost_grid.operating_cases:
                        for regime in cost_grid.regimes:
                            for reserve_fraction in regime.reserved_capacity_fractions:
                                for opportunity_alpha in regime.opportunity_exposure_alphas:
                                    for market in markets:
                                        for capacity_payment in market.capacity_payment_per_kw_year:
                                            for (
                                                performance_payment
                                            ) in market.performance_payment_per_mwh:
                                                for (
                                                    connection_value
                                                ) in market.flexible_connection_value_per_year:
                                                    inputs = _make_inputs(
                                                        regime=regime,
                                                        reserved_fraction=reserve_fraction,
                                                        opportunity_alpha=opportunity_alpha,
                                                        candidate_capacity_kw=scaled_candidate_kw,
                                                        technical_ceiling_kw=(
                                                            scaled_technical_ceiling_kw
                                                        ),
                                                        annual_event_count=annual_event_count,
                                                        metrics=scaled_mean_metrics,
                                                        capital=capital,
                                                        operating=operating,
                                                        market=market,
                                                        capacity_payment=capacity_payment,
                                                        performance_payment=performance_payment,
                                                        connection_value=connection_value,
                                                    )
                                                    accounting = annual_economic_value(inputs)
                                                    risk = _risk_statistics(
                                                        inputs,
                                                        scaled_draw_metrics,
                                                        risk_quantile=(
                                                            specification.evaluation.risk_quantile
                                                        ),
                                                    )
                                                    identity = {
                                                        "analysis_id": (
                                                            specification.analysis_id
                                                        ),
                                                        "analysis_role": (
                                                            specification.analysis_role
                                                        ),
                                                        "currency_basis": (
                                                            specification.monetary_basis
                                                        ),
                                                        "dispatch_sampling": (
                                                            specification.evaluation.dispatch_sampling
                                                        ),
                                                        "annualization_scope": (
                                                            "independent_fresh_events_not_"
                                                            "continuous_programme"
                                                        ),
                                                        "facility_scale_interpretation": (
                                                            cost_grid.facility_scale_interpretation
                                                        ),
                                                        "technical_certificate_scope": (
                                                            "reference_module_only_not_scaled_"
                                                            "facility_certificate"
                                                        ),
                                                        "reference_module_operating_peak_kw": (
                                                            cost_grid.reference_module_operating_peak_kw
                                                        ),
                                                        "facility_site_scale_mw": (
                                                            facility_site_scale_mw
                                                        ),
                                                        (
                                                            "proportional_reference_module_"
                                                            "scale_factor"
                                                        ): (
                                                            scale_factor
                                                        ),
                                                        "duration_h": duration_h,
                                                        "notice_h": notice_h,
                                                        "reliability_target": reliability_target,
                                                        "confidence_level": confidence_level,
                                                        "technical_capacity_ceiling_kw": (
                                                            technical_ceiling_kw
                                                        ),
                                                        "candidate_reduction_kw": candidate_kw,
                                                        (
                                                            "scaled_accounting_technical_"
                                                            "capacity_ceiling_kw"
                                                        ): (
                                                            scaled_technical_ceiling_kw
                                                        ),
                                                        (
                                                            "scaled_accounting_candidate_"
                                                            "reduction_kw"
                                                        ): (
                                                            scaled_candidate_kw
                                                        ),
                                                        "offer_fraction_of_technical_ceiling": (
                                                            offer_fraction
                                                        ),
                                                        "technical_qualification": (
                                                            specification.technical.qualification_for_offer_fraction(
                                                                offer_fraction
                                                            )
                                                        ),
                                                        "eligible_for_primary_economic_offer": (
                                                            abs(offer_fraction - 1.0) <= 1e-12
                                                        ),
                                                        "economic_offer_definition": (
                                                            "binary_0_or_independently_"
                                                            "certified_reference_module_Kcert"
                                                        ),
                                                        "performance_payment_basis": (
                                                            "interval_delivery_capped_at_"
                                                            "scaled_accounting_offered_kW"
                                                        ),
                                                        "reserved_capacity_basis": (
                                                            cost_grid.reserved_capacity_basis
                                                        ),
                                                        "technical_success_rate": success_rate,
                                                        "annual_event_count": annual_event_count,
                                                        "annual_event_count_class": (
                                                            annual_event_count_class
                                                        ),
                                                        "annual_event_count_is_stress": (
                                                            annual_event_count_is_stress
                                                        ),
                                                    }
                                                    parameter_values = _parameter_values(
                                                        capital=capital,
                                                        operating=operating,
                                                        regime=regime,
                                                        reserve_fraction=reserve_fraction,
                                                        opportunity_alpha=opportunity_alpha,
                                                        market=market,
                                                        capacity_payment=capacity_payment,
                                                        performance_payment=performance_payment,
                                                        connection_value=connection_value,
                                                    )
                                                    per_event_metrics = _per_event_metric_values(
                                                        scaled_mean_metrics,
                                                        annual_event_count,
                                                    )
                                                    rows.append(
                                                        {
                                                            **identity,
                                                            **parameter_values,
                                                            **per_event_metrics,
                                                            **accounting,
                                                            **risk,
                                                        }
                                                    )
    return rows


def _offer_curve(results: pd.DataFrame) -> pd.DataFrame:
    group_columns = [
        "analysis_id",
        "analysis_role",
        "currency_basis",
        "dispatch_sampling",
        "annualization_scope",
        "facility_scale_interpretation",
        "technical_certificate_scope",
        "reference_module_operating_peak_kw",
        "facility_site_scale_mw",
        "proportional_reference_module_scale_factor",
        "duration_h",
        "notice_h",
        "reliability_target",
        "confidence_level",
        "technical_capacity_ceiling_kw",
        "scaled_accounting_technical_capacity_ceiling_kw",
        "annual_event_count",
        "annual_event_count_class",
        "annual_event_count_is_stress",
        "capital_case_id",
        "capital_sensitivity_axis",
        "operating_case_id",
        "market_archetype_id",
        "regime",
        "reserved_capacity_basis",
        "performance_payment_basis",
        "economic_life_years",
        "discount_rate",
        "salvage_fraction",
        "installed_cost_per_reserved_kw",
        "annual_om_fraction",
        "fixed_site_enablement_annual_cost",
        "variable_enablement_cost_per_offer_kw",
        "checkpoint_cost_per_event",
        "reserved_capacity_fraction",
        "opportunity_exposure_alpha",
        "value_per_gpu_h",
        "effective_displaced_compute_value_per_gpu_h",
        "delay_cost_per_gpu_h_h",
        "missed_work_cost_per_gpu_h",
        "terminal_backlog_cost_per_gpu_h",
        "electricity_price_per_kwh",
        "capacity_payment_per_kw_year",
        "performance_payment_per_mwh",
        "flexible_connection_value_per_year",
        "shortfall_penalty_per_mwh",
        "failure_penalty_per_event",
    ]
    rows: list[dict[str, Any]] = []
    for key, group in results.groupby(group_columns, sort=True, dropna=False):
        frame = group.sort_values("candidate_reduction_kw", kind="stable")
        row: dict[str, Any] = dict(zip(group_columns, key, strict=True))
        technical_ceiling_kw = float(
            pd.to_numeric(frame["technical_capacity_ceiling_kw"], errors="raise").iloc[0]
        )
        scaled_accounting_ceiling_kw = float(
            pd.to_numeric(
                frame["scaled_accounting_technical_capacity_ceiling_kw"], errors="raise"
            ).iloc[0]
        )
        certified = frame.loc[frame["eligible_for_primary_economic_offer"].astype(bool)]
        if len(certified) != 1:
            raise ValueError(
                "economic offer decision requires exactly one independently certified Kcert row"
            )
        certified_row = certified.iloc[0]
        if certified_row["technical_qualification"] != "independently_certified_ceiling":
            raise ValueError("primary economic offer row lacks independent technical qualification")
        certified_capacity_kw = float(certified_row["candidate_reduction_kw"])
        certified_scaled_capacity_kw = float(
            certified_row["scaled_accounting_candidate_reduction_kw"]
        )
        if not np.isclose(certified_capacity_kw, technical_ceiling_kw, rtol=0.0, atol=1e-9):
            raise ValueError("primary economic offer row is not the certified technical ceiling")
        if not np.isclose(
            certified_scaled_capacity_kw,
            scaled_accounting_ceiling_kw,
            rtol=0.0,
            atol=1e-9,
        ):
            raise ValueError(
                "primary economic offer row is not the scaled accounting capacity ceiling"
            )
        mean_offer = (
            scaled_accounting_ceiling_kw
            if float(certified_row["annual_net_value"]) >= -1e-9
            else 0.0
        )
        risk_offer = (
            scaled_accounting_ceiling_kw
            if float(certified_row["annual_net_value_p05"]) >= -1e-9
            else 0.0
        )
        row.update(
            {
                "economic_offer_definition": (
                    "binary_0_or_independently_certified_reference_module_Kcert"
                ),
                "economically_offerable_capacity_kw_mean": mean_offer,
                "economically_offerable_capacity_kw_risk_adjusted": risk_offer,
                "economically_offerable_reference_module_capacity_kw_mean": (
                    technical_ceiling_kw if mean_offer > 0.0 else 0.0
                ),
                "economically_offerable_reference_module_capacity_kw_risk_adjusted": (
                    technical_ceiling_kw if risk_offer > 0.0 else 0.0
                ),
                "certified_offer_technical_success_rate_development_diagnostic": float(
                    certified_row["technical_success_rate"]
                ),
                "offer_grid_point_count": int(len(frame)),
                "offer_grid_step_max_kw": float(
                    frame["candidate_reduction_kw"].sort_values().diff().max()
                )
                if len(frame) > 1
                else 0.0,
            }
        )
        if (
            float(row["economically_offerable_capacity_kw_mean"])
            > scaled_accounting_ceiling_kw + 1e-9
        ):
            raise RuntimeError("economic offer curve exceeds scaled accounting capacity ceiling")
        rows.append(row)
    return pd.DataFrame.from_records(rows)


def _primary_rows(
    results: pd.DataFrame,
    specification: EconomicParticipationSpecification,
) -> pd.DataFrame:
    evaluation = specification.evaluation
    base = results[
        np.isclose(
            results["facility_site_scale_mw"], evaluation.primary_facility_site_scale_mw
        )
        & (results["duration_h"] == evaluation.primary_duration_h)
        & (results["notice_h"] == evaluation.primary_notice_h)
        & np.isclose(results["reliability_target"], evaluation.primary_reliability_target)
        & np.isclose(
            results["offer_fraction_of_technical_ceiling"], evaluation.primary_offer_fraction
        )
        & (results["capital_case_id"] == evaluation.primary_capital_case_id)
        & (results["operating_case_id"] == evaluation.primary_operating_case_id)
        & (results["market_archetype_id"] == evaluation.primary_market_archetype_id)
        & (results["annual_event_count"] == evaluation.primary_annual_event_count)
        & np.isclose(
            results["capacity_payment_per_kw_year"],
            evaluation.primary_capacity_payment_per_kw_year,
        )
        & np.isclose(
            results["performance_payment_per_mwh"],
            evaluation.primary_performance_payment_per_mwh,
        )
    ].copy()
    selected: list[pd.DataFrame] = []
    for regime in ("slack_backed", "reserved_headroom", "throughput_displacing"):
        reserve, alpha = evaluation.exposure_for(regime)
        matching = base[
            (base["regime"] == regime)
            & np.isclose(base["reserved_capacity_fraction"], reserve)
            & np.isclose(base["opportunity_exposure_alpha"], alpha)
        ]
        if len(matching) != 1:
            raise ValueError(
                "primary economic decomposition requires exactly one declared row for "
                f"{regime}; configure the matching v1 exposure grid"
            )
        selected.append(matching)
    output = pd.concat(selected, ignore_index=True)
    if set(output["technical_qualification"].astype(str)) != {"independently_certified_ceiling"}:
        raise ValueError("primary economic boundary contains a non-certified offer fraction")
    return output


def _break_even_surface(
    results: pd.DataFrame,
    specification: EconomicParticipationSpecification,
) -> pd.DataFrame:
    evaluation = specification.evaluation
    primary = results[
        np.isclose(
            results["facility_site_scale_mw"], evaluation.primary_facility_site_scale_mw
        )
        & (results["duration_h"] == evaluation.primary_duration_h)
        & (results["notice_h"] == evaluation.primary_notice_h)
        & np.isclose(results["reliability_target"], evaluation.primary_reliability_target)
        & np.isclose(
            results["offer_fraction_of_technical_ceiling"], evaluation.primary_offer_fraction
        )
        & (results["operating_case_id"] == evaluation.primary_operating_case_id)
        & (results["market_archetype_id"] == evaluation.primary_market_archetype_id)
        & (results["annual_event_count"] == evaluation.primary_annual_event_count)
        & np.isclose(
            results["capacity_payment_per_kw_year"],
            evaluation.primary_capacity_payment_per_kw_year,
        )
        & np.isclose(
            results["performance_payment_per_mwh"],
            evaluation.primary_performance_payment_per_mwh,
        )
    ].copy()
    primary["exposure_fraction"] = np.where(
        primary["regime"] == "reserved_headroom",
        primary["reserved_capacity_fraction"],
        primary["opportunity_exposure_alpha"],
    )
    return primary.sort_values(
        ["regime", "exposure_fraction", "economic_life_years"], kind="stable"
    )


def _fixed_site_overlay_scale_sensitivity(
    results: pd.DataFrame,
    specification: EconomicParticipationSpecification,
) -> pd.DataFrame:
    """Expose lower-bound and fixed-site-overlay accounting across scale points.

    The rows are deliberately not technical certificates for 0.2--20 MW sites.
    They are proportional reference-module accounting coordinates with no
    portfolio-diversification assumption.
    """

    evaluation = specification.evaluation
    base = results[
        (results["duration_h"] == evaluation.primary_duration_h)
        & (results["notice_h"] == evaluation.primary_notice_h)
        & np.isclose(results["reliability_target"], evaluation.primary_reliability_target)
        & np.isclose(
            results["offer_fraction_of_technical_ceiling"], evaluation.primary_offer_fraction
        )
        & (results["capital_case_id"] == evaluation.primary_capital_case_id)
        & (results["operating_case_id"] == evaluation.primary_operating_case_id)
        & (results["market_archetype_id"] == evaluation.primary_market_archetype_id)
        & (results["annual_event_count"] == evaluation.primary_annual_event_count)
        & np.isclose(
            results["capacity_payment_per_kw_year"],
            evaluation.primary_capacity_payment_per_kw_year,
        )
        & np.isclose(
            results["performance_payment_per_mwh"],
            evaluation.primary_performance_payment_per_mwh,
        )
    ].copy()
    selected: list[pd.DataFrame] = []
    for regime in ("slack_backed", "reserved_headroom", "throughput_displacing"):
        reserve, alpha = evaluation.exposure_for(regime)
        selected.append(
            base[
                (base["regime"] == regime)
                & np.isclose(base["reserved_capacity_fraction"], reserve)
                & np.isclose(base["opportunity_exposure_alpha"], alpha)
            ]
        )
    wide = pd.concat(selected, ignore_index=True)
    expected_rows = 3 * int(wide["facility_site_scale_mw"].nunique())
    if len(wide) != expected_rows:
        raise ValueError(
            "fixed-site overlay sensitivity requires one primary row per regime and scale"
        )
    if set(wide["technical_qualification"].astype(str)) != {
        "independently_certified_ceiling"
    }:
        raise ValueError("fixed-site overlay sensitivity contains a non-certified offer")

    common_columns = [
        "analysis_id",
        "analysis_role",
        "currency_basis",
        "annualization_scope",
        "performance_payment_basis",
        "reserved_capacity_basis",
        "facility_scale_interpretation",
        "technical_certificate_scope",
        "reference_module_operating_peak_kw",
        "facility_site_scale_mw",
        "proportional_reference_module_scale_factor",
        "regime",
        "duration_h",
        "notice_h",
        "reliability_target",
        "annual_event_count",
        "annual_event_count_class",
        "annual_event_count_is_stress",
        "technical_capacity_ceiling_kw",
        "candidate_reduction_kw",
        "scaled_accounting_technical_capacity_ceiling_kw",
        "scaled_accounting_candidate_reduction_kw",
        "technical_qualification",
        "fixed_site_enablement_annual_cost",
        "variable_enablement_cost_per_offer_kw",
        "fixed_site_enablement_cost",
        "variable_enablement_cost",
        "enablement_cost",
        "fixed_site_enablement_cost_per_offer_kw",
    ]
    records: list[dict[str, Any]] = []
    for _, row in wide.iterrows():
        common = {column: row[column] for column in common_columns}
        for perspective, suffix in (
            ("excluding_fixed_site_lower_bound", "excluding_fixed_site"),
            ("including_fixed_site_overlay", ""),
        ):
            prefix = "annual_net_value" if not suffix else f"annual_net_value_{suffix}"
            break_even = (
                "break_even_capacity_payment_per_kw_year"
                if not suffix
                else "break_even_capacity_payment_excluding_fixed_site_per_kw_year"
            )
            risk_break_even = (
                "risk_adjusted_break_even_capacity_payment_per_kw_year"
                if not suffix
                else (
                    "risk_adjusted_break_even_capacity_payment_"
                    "excluding_fixed_site_per_kw_year"
                )
            )
            records.append(
                {
                    **common,
                    "accounting_perspective": perspective,
                    "annual_net_value_usd_per_year": float(row[prefix]),
                    "annual_net_value_p05_usd_per_year": float(row[f"{prefix}_p05"]),
                    "break_even_capacity_payment_per_kw_year": float(row[break_even]),
                    "risk_adjusted_break_even_capacity_payment_per_kw_year": float(
                        row[risk_break_even]
                    ),
                }
            )
    return pd.DataFrame.from_records(records).sort_values(
        ["regime", "facility_site_scale_mw", "accounting_perspective"],
        kind="stable",
    )


def _primary_offer_curves(
    offer_curve: pd.DataFrame,
    specification: EconomicParticipationSpecification,
) -> pd.DataFrame:
    evaluation = specification.evaluation
    base = offer_curve[
        np.isclose(
            offer_curve["facility_site_scale_mw"], evaluation.primary_facility_site_scale_mw
        )
        & (offer_curve["notice_h"] == evaluation.primary_notice_h)
        & np.isclose(offer_curve["reliability_target"], evaluation.primary_reliability_target)
        & (offer_curve["capital_case_id"] == evaluation.primary_capital_case_id)
        & (offer_curve["operating_case_id"] == evaluation.primary_operating_case_id)
        & (offer_curve["market_archetype_id"] == evaluation.primary_market_archetype_id)
        & (offer_curve["annual_event_count"] == evaluation.primary_annual_event_count)
        & np.isclose(
            offer_curve["performance_payment_per_mwh"],
            evaluation.primary_performance_payment_per_mwh,
        )
    ].copy()
    selected: list[pd.DataFrame] = []
    for regime in ("slack_backed", "reserved_headroom", "throughput_displacing"):
        reserve, alpha = evaluation.exposure_for(regime)
        selected.append(
            base[
                (base["regime"] == regime)
                & np.isclose(base["reserved_capacity_fraction"], reserve)
                & np.isclose(base["opportunity_exposure_alpha"], alpha)
            ]
        )
    output = pd.concat(selected, ignore_index=True)
    if output.empty:
        raise ValueError("primary economic offer curve is empty")
    return output.sort_values(
        ["regime", "duration_h", "capacity_payment_per_kw_year"], kind="stable"
    )


def _duration_break_even(
    results: pd.DataFrame,
    specification: EconomicParticipationSpecification,
) -> pd.DataFrame:
    """Return one independently certified break-even row per regime and duration."""

    evaluation = specification.evaluation
    base = results[
        np.isclose(
            results["facility_site_scale_mw"], evaluation.primary_facility_site_scale_mw
        )
        & (results["notice_h"] == evaluation.primary_notice_h)
        & np.isclose(results["reliability_target"], evaluation.primary_reliability_target)
        & np.isclose(results["offer_fraction_of_technical_ceiling"], 1.0)
        & (results["capital_case_id"] == evaluation.primary_capital_case_id)
        & (results["operating_case_id"] == evaluation.primary_operating_case_id)
        & (results["market_archetype_id"] == evaluation.primary_market_archetype_id)
        & (results["annual_event_count"] == evaluation.primary_annual_event_count)
        & np.isclose(results["capacity_payment_per_kw_year"], 0.0)
        & np.isclose(
            results["performance_payment_per_mwh"],
            evaluation.primary_performance_payment_per_mwh,
        )
    ].copy()
    selected: list[pd.DataFrame] = []
    for regime in ("slack_backed", "reserved_headroom", "throughput_displacing"):
        reserve, alpha = evaluation.exposure_for(regime)
        selected.append(
            base[
                (base["regime"] == regime)
                & np.isclose(base["reserved_capacity_fraction"], reserve)
                & np.isclose(base["opportunity_exposure_alpha"], alpha)
            ]
        )
    output = pd.concat(selected, ignore_index=True)
    expected_rows = 3 * len(specification.technical.duration_hours)
    if len(output) != expected_rows:
        raise ValueError(
            "duration break-even table requires one certified row per regime and duration"
        )
    if set(output["technical_qualification"].astype(str)) != {"independently_certified_ceiling"}:
        raise ValueError("duration break-even table contains a non-certified offer fraction")
    columns = [
        "analysis_id",
        "analysis_role",
        "currency_basis",
        "annualization_scope",
        "performance_payment_basis",
        "reserved_capacity_basis",
        "facility_scale_interpretation",
        "technical_certificate_scope",
        "reference_module_operating_peak_kw",
        "facility_site_scale_mw",
        "proportional_reference_module_scale_factor",
        "regime",
        "duration_h",
        "notice_h",
        "reliability_target",
        "annual_event_count",
        "annual_event_count_class",
        "annual_event_count_is_stress",
        "technical_capacity_ceiling_kw",
        "candidate_reduction_kw",
        "scaled_accounting_technical_capacity_ceiling_kw",
        "scaled_accounting_candidate_reduction_kw",
        "technical_qualification",
        "break_even_capacity_payment_per_kw_year",
        "risk_adjusted_break_even_capacity_payment_per_kw_year",
        "break_even_capacity_payment_excluding_fixed_site_per_kw_year",
        "risk_adjusted_break_even_capacity_payment_excluding_fixed_site_per_kw_year",
    ]
    return output.loc[:, columns].sort_values(["regime", "duration_h"], kind="stable")


def _mechanism_sensitivity(
    results: pd.DataFrame,
    specification: EconomicParticipationSpecification,
) -> pd.DataFrame:
    """Build tidy, regime-specific one-coordinate sensitivity rows."""

    evaluation = specification.evaluation
    base = results[
        np.isclose(
            results["facility_site_scale_mw"], evaluation.primary_facility_site_scale_mw
        )
        & (results["duration_h"] == evaluation.primary_duration_h)
        & (results["notice_h"] == evaluation.primary_notice_h)
        & np.isclose(results["reliability_target"], evaluation.primary_reliability_target)
        & np.isclose(results["offer_fraction_of_technical_ceiling"], 1.0)
        & (results["operating_case_id"] == evaluation.primary_operating_case_id)
        & (results["market_archetype_id"] == evaluation.primary_market_archetype_id)
        & np.isclose(results["capacity_payment_per_kw_year"], 0.0)
        & np.isclose(
            results["performance_payment_per_mwh"],
            evaluation.primary_performance_payment_per_mwh,
        )
    ].copy()
    frames: list[pd.DataFrame] = []
    definitions = {
        "slack_backed": ("annual_event_count", "Fresh events per year"),
        "reserved_headroom": (
            "economic_life_years",
            "Economic life",
        ),
        "throughput_displacing": (
            "effective_displaced_compute_value_per_gpu_h",
            "Effective displaced-compute value",
        ),
    }
    for regime, (driver, label) in definitions.items():
        reserve, alpha = evaluation.exposure_for(regime)
        selected = base[base["regime"] == regime].copy()
        if regime == "slack_backed":
            selected = selected[
                np.isclose(selected["reserved_capacity_fraction"], reserve)
                & np.isclose(selected["opportunity_exposure_alpha"], alpha)
                & (selected["capital_case_id"] == evaluation.primary_capital_case_id)
            ]
        elif regime == "reserved_headroom":
            selected = selected[
                np.isclose(selected["reserved_capacity_fraction"], reserve)
                & np.isclose(selected["opportunity_exposure_alpha"], alpha)
                & selected["capital_sensitivity_axis"].isin(("reference", "economic_life"))
                & (selected["annual_event_count"] == evaluation.primary_annual_event_count)
            ]
        else:
            selected = selected[
                np.isclose(selected["reserved_capacity_fraction"], reserve)
                & (selected["capital_case_id"] == evaluation.primary_capital_case_id)
                & (selected["annual_event_count"] == evaluation.primary_annual_event_count)
            ]
        selected = selected.sort_values(driver, kind="stable").reset_index(drop=True)
        driver_values = pd.to_numeric(selected[driver], errors="raise").to_numpy(dtype=float)
        if len(driver_values) < 2 or bool(np.diff(driver_values).min() <= 0.0):
            raise ValueError(f"{regime} mechanism driver must be strictly increasing")
        selected["driver_id"] = driver
        selected["driver_label"] = label
        selected["driver_value"] = driver_values
        if regime == "slack_backed":
            selected["driver_value_display"] = [
                f"{int(value)} events/year" for value in driver_values
            ]
            selected["driver_unit"] = "fresh_events_per_year"
        elif regime == "reserved_headroom":
            selected["driver_value_display"] = [f"{value:g} years" for value in driver_values]
            selected["driver_unit"] = "years"
        else:
            selected["driver_value_display"] = [f"${value:g}/GPU-h" for value in driver_values]
            selected["driver_unit"] = "real_2026_USD_per_GPU_hour"
        selected["driver_normalized_position"] = np.linspace(0.0, 1.0, len(selected))
        frames.append(selected)
    output = pd.concat(frames, ignore_index=True)
    if output.empty:
        raise ValueError("mechanism sensitivity table is empty")
    columns = [
        "analysis_id",
        "analysis_role",
        "currency_basis",
        "annualization_scope",
        "performance_payment_basis",
        "reserved_capacity_basis",
        "facility_scale_interpretation",
        "technical_certificate_scope",
        "reference_module_operating_peak_kw",
        "facility_site_scale_mw",
        "proportional_reference_module_scale_factor",
        "regime",
        "driver_id",
        "driver_label",
        "driver_value",
        "driver_unit",
        "driver_value_display",
        "driver_normalized_position",
        "duration_h",
        "annual_event_count",
        "annual_event_count_class",
        "annual_event_count_is_stress",
        "reliability_target",
        "risk_adjusted_break_even_capacity_payment_per_kw_year",
        "technical_capacity_ceiling_kw",
        "candidate_reduction_kw",
        "scaled_accounting_technical_capacity_ceiling_kw",
        "scaled_accounting_candidate_reduction_kw",
        "technical_qualification",
        "opportunity_exposure_alpha",
        "value_per_gpu_h",
        "effective_displaced_compute_value_per_gpu_h",
    ]
    return output.loc[:, columns].sort_values(
        ["regime", "driver_normalized_position"], kind="stable"
    )


def _orthogonal_capital_sensitivity(
    results: pd.DataFrame,
    specification: EconomicParticipationSpecification,
) -> pd.DataFrame:
    """Expose life, WACC and salvage as separate predeclared coordinates."""

    evaluation = specification.evaluation
    reserve, alpha = evaluation.exposure_for("reserved_headroom")
    output = results[
        np.isclose(
            results["facility_site_scale_mw"], evaluation.primary_facility_site_scale_mw
        )
        & (results["duration_h"] == evaluation.primary_duration_h)
        & (results["notice_h"] == evaluation.primary_notice_h)
        & np.isclose(results["reliability_target"], evaluation.primary_reliability_target)
        & np.isclose(results["offer_fraction_of_technical_ceiling"], 1.0)
        & (results["operating_case_id"] == evaluation.primary_operating_case_id)
        & (results["market_archetype_id"] == evaluation.primary_market_archetype_id)
        & (results["annual_event_count"] == evaluation.primary_annual_event_count)
        & np.isclose(results["capacity_payment_per_kw_year"], 0.0)
        & np.isclose(
            results["performance_payment_per_mwh"],
            evaluation.primary_performance_payment_per_mwh,
        )
        & (results["regime"] == "reserved_headroom")
        & np.isclose(results["reserved_capacity_fraction"], reserve)
        & np.isclose(results["opportunity_exposure_alpha"], alpha)
    ].copy()
    if output.empty:
        raise ValueError("orthogonal capital sensitivity table is empty")
    reference = output[output["capital_sensitivity_axis"] == "reference"]
    if len(reference) != 1:
        raise ValueError("orthogonal capital sensitivity requires exactly one reference row")
    expanded_reference: list[pd.DataFrame] = []
    for axis, column in (
        ("economic_life", "economic_life_years"),
        ("discount_rate", "discount_rate"),
        ("salvage_fraction", "salvage_fraction"),
    ):
        item = reference.copy()
        item["capital_sensitivity_axis"] = axis
        item["sensitivity_coordinate"] = pd.to_numeric(item[column], errors="raise")
        item["is_reference_coordinate"] = True
        expanded_reference.append(item)
    non_reference = output[output["capital_sensitivity_axis"] != "reference"].copy()
    non_reference["sensitivity_coordinate"] = np.select(
        [
            non_reference["capital_sensitivity_axis"].eq("economic_life"),
            non_reference["capital_sensitivity_axis"].eq("discount_rate"),
            non_reference["capital_sensitivity_axis"].eq("salvage_fraction"),
        ],
        [
            non_reference["economic_life_years"],
            non_reference["discount_rate"],
            non_reference["salvage_fraction"],
        ],
        default=np.nan,
    )
    non_reference["is_reference_coordinate"] = False
    combined = pd.concat([non_reference, *expanded_reference], ignore_index=True)
    if bool(combined["sensitivity_coordinate"].isna().any()):
        raise ValueError("capital sensitivity has an unclassified coordinate")
    return combined.sort_values(
        ["capital_sensitivity_axis", "sensitivity_coordinate"], kind="stable"
    )


def _break_even_decomposition(decomposition: pd.DataFrame) -> pd.DataFrame:
    """Return additive contributions that close exactly to risk-adjusted BE."""

    components = (
        (
            "fixed_site_enablement_cost",
            "Fixed site enablement",
            "fixed_site_enablement_cost",
            1.0,
        ),
        (
            "variable_enablement_cost",
            "Variable offer enablement",
            "variable_enablement_cost",
            1.0,
        ),
        (
            "reserve_annual_cost",
            "Abstract PCC reserve coordinate",
            "reserve_annual_cost",
            1.0,
        ),
        ("opportunity_cost", "Displaced compute", "opportunity_cost", 1.0),
        ("delay_cost", "Compute delay", "delay_cost", 1.0),
        ("sla_cost", "Service loss", "sla_cost", 1.0),
        ("checkpoint_cost", "Checkpoint/restart", "checkpoint_cost", 1.0),
        ("penalty_cost", "Non-performance penalty", "penalty_cost", 1.0),
        ("performance_credit", "Performance payment", "performance_revenue", -1.0),
        ("energy_credit_or_cost", "Net energy change", "energy_value", -1.0),
        ("connection_credit", "Connection value", "flexible_connection_value", -1.0),
    )
    rows: list[dict[str, Any]] = []
    for _, row in decomposition.iterrows():
        capacity_kw = float(row["scaled_accounting_technical_capacity_ceiling_kw"])
        if not np.isfinite(capacity_kw) or capacity_kw <= 0.0:
            raise ValueError("break-even decomposition requires a positive accounting capacity")
        identity = {
            "analysis_id": row["analysis_id"],
            "analysis_role": row["analysis_role"],
            "currency_basis": row["currency_basis"],
            "annualization_scope": row["annualization_scope"],
            "performance_payment_basis": row["performance_payment_basis"],
            "reserved_capacity_basis": row["reserved_capacity_basis"],
            "facility_scale_interpretation": row["facility_scale_interpretation"],
            "technical_certificate_scope": row["technical_certificate_scope"],
            "reference_module_operating_peak_kw": row["reference_module_operating_peak_kw"],
            "facility_site_scale_mw": row["facility_site_scale_mw"],
            "proportional_reference_module_scale_factor": row[
                "proportional_reference_module_scale_factor"
            ],
            "regime": row["regime"],
            "duration_h": row["duration_h"],
            "notice_h": row["notice_h"],
            "reliability_target": row["reliability_target"],
            "annual_event_count": row["annual_event_count"],
            "annual_event_count_class": row["annual_event_count_class"],
            "annual_event_count_is_stress": row["annual_event_count_is_stress"],
            "technical_capacity_ceiling_kw": row["technical_capacity_ceiling_kw"],
            "candidate_reduction_kw": float(row["candidate_reduction_kw"]),
            "scaled_accounting_technical_capacity_ceiling_kw": capacity_kw,
            "scaled_accounting_candidate_reduction_kw": row[
                "scaled_accounting_candidate_reduction_kw"
            ],
            "technical_qualification": row["technical_qualification"],
            "risk_adjusted_break_even_capacity_payment_per_kw_year": row[
                "risk_adjusted_break_even_capacity_payment_per_kw_year"
            ],
        }
        subtotal = 0.0
        for component_id, label, column, sign in components:
            annual_value = float(row[column])
            contribution = sign * annual_value / capacity_kw
            subtotal += contribution
            rows.append(
                {
                    **identity,
                    "component_id": component_id,
                    "component_label": label,
                    "contribution_per_kw_year": contribution,
                }
            )
        target = float(row["risk_adjusted_break_even_capacity_payment_per_kw_year"])
        rows.append(
            {
                **identity,
                "component_id": "risk_buffer",
                "component_label": "Risk adjustment",
                "contribution_per_kw_year": target - subtotal,
            }
        )
    output = pd.DataFrame.from_records(rows)
    totals = output.groupby(["regime", "facility_site_scale_mw"], sort=True)[
        "contribution_per_kw_year"
    ].sum()
    targets = output.groupby(["regime", "facility_site_scale_mw"], sort=True)[
        "risk_adjusted_break_even_capacity_payment_per_kw_year"
    ].first()
    if not np.allclose(totals.to_numpy(), targets.to_numpy(), rtol=0.0, atol=1e-9):
        raise RuntimeError("break-even component contributions do not close to the risk boundary")
    return output


def _development_fraction_diagnostics(
    ledger: pd.DataFrame,
    specification: EconomicParticipationSpecification,
) -> pd.DataFrame:
    """Keep sub-Kcert replays auditable without labelling them certified offers."""

    columns = [
        "evaluation_split",
        "scenario_id",
        "scenario_hash",
        "episode_seed",
        "duration_h",
        "notice_h",
        "reliability_target",
        "confidence_level",
        "technical_capacity_ceiling_kw",
        "offer_fraction_of_technical_ceiling",
        "candidate_reduction_kw",
        "technical_qualification",
        "technical_success",
        "delivered_energy_kwh",
        "capped_delivered_energy_kwh",
        "shortfall_energy_kwh",
        "deferred_gpu_h",
        "recovered_through_episode_end_gpu_h",
        "incremental_backlog_area_through_episode_end_gpu_h_h",
        "incremental_energy_through_episode_end_kwh",
        "missed_gpu_h",
        "terminal_backlog_gpu_h",
    ]
    output = ledger.loc[
        ledger["offer_fraction_of_technical_ceiling"] < 1.0 - 1e-12,
        [column for column in columns if column != "technical_qualification"],
    ].copy()
    output["technical_qualification"] = output["offer_fraction_of_technical_ceiling"].map(
        specification.technical.qualification_for_offer_fraction
    )
    output["permitted_use"] = "physical_development_diagnostic_only"
    columns.extend(["permitted_use"])
    return output.sort_values(
        ["duration_h", "offer_fraction_of_technical_ceiling", "episode_seed"],
        kind="stable",
    ).loc[:, columns]


def _write_csv(frame: pd.DataFrame, path: Path) -> str:
    frame.to_csv(path, index=False)
    return sha256_file(path)


def _parameter_provenance_frame(
    specification: EconomicParticipationSpecification,
    *,
    input_hashes: dict[str, str],
    ledger_path: Path,
) -> pd.DataFrame:
    """Make inputs, units, formulas and exact provenance source-data exportable."""

    register = pd.read_csv(specification.inputs.source_register)
    if register.empty or "input_id" not in register.columns:
        raise ValueError("economic source register must contain non-empty input_id rows")
    if register["input_id"].isna().any() or register["input_id"].duplicated().any():
        raise ValueError("economic source register input_id values must be unique and non-empty")
    if "external_evidence_reference" not in register.columns:
        raise ValueError(
            "economic source register must identify its external-evidence references"
        )
    external_evidence = pd.read_csv(specification.inputs.external_parameter_evidence)
    required_evidence_columns = {
        "evidence_id",
        "input_id",
        "parameter_family",
        "source_title",
        "source_organization",
        "source_url",
        "publication_or_reporting_year",
        "access_date",
        "observed_value",
        "unit",
        "currency_year",
        "support_level",
        "replaceability",
        "permitted_use",
        "forbidden_interpretation",
    }
    missing_evidence_columns = sorted(
        required_evidence_columns.difference(external_evidence.columns)
    )
    if missing_evidence_columns:
        raise ValueError(
            "external parameter evidence is missing columns: "
            + ", ".join(missing_evidence_columns)
        )
    if external_evidence.empty or external_evidence["evidence_id"].isna().any():
        raise ValueError("external parameter evidence must contain non-empty evidence IDs")
    if external_evidence["evidence_id"].duplicated().any():
        raise ValueError("external parameter evidence IDs must be unique")
    evidence_input_by_id = dict(
        zip(
            external_evidence["evidence_id"].astype(str),
            external_evidence["input_id"].astype(str),
            strict=True,
        )
    )
    for _, registered in register.iterrows():
        input_id = str(registered["input_id"])
        reference = str(registered["external_evidence_reference"])
        if reference in {
            "not_applicable_internal_certificate",
            "no_transferable_external_cost_evidence_identified",
        }:
            continue
        for evidence_id in (item.strip() for item in reference.split(";")):
            if not evidence_id:
                continue
            evidence_input_id = evidence_input_by_id.get(evidence_id)
            if evidence_input_id is None:
                raise ValueError(
                    "economic source register references an absent external evidence ID: "
                    f"{evidence_id}"
                )
            if evidence_input_id != input_id:
                raise ValueError(
                    "economic source register external evidence ID belongs to a different "
                    f"input: {evidence_id}"
                )

    input_locations = {
        "technical_capacity_ceiling_q95": (
            specification.technical.technical_certificate_path,
            input_hashes["technical_certificate"],
        ),
        "reserved_cost_grid": (
            specification.inputs.cost_parameter_grid,
            input_hashes["cost_parameter_grid"],
        ),
        "economic_lifetime_grid": (
            specification.inputs.cost_parameter_grid,
            input_hashes["cost_parameter_grid"],
        ),
        "opportunity_cost_grid": (
            specification.inputs.cost_parameter_grid,
            input_hashes["cost_parameter_grid"],
        ),
        "delay_cost_grid": (
            specification.inputs.cost_parameter_grid,
            input_hashes["cost_parameter_grid"],
        ),
        "market_payment_grid": (
            specification.inputs.market_archetypes,
            input_hashes["market_archetypes"],
        ),
        "energy_price_grid": (
            specification.inputs.cost_parameter_grid,
            input_hashes["cost_parameter_grid"],
        ),
    }
    formulas = {
        "technical_capacity_ceiling_q95": "K_econ <= K_cert",
        "reserved_cost_grid": (
            "C_enable = I(K_offer>0)*C_fixed_site + c_variable_per_offer_kw*K_offer; "
            "C_fixed_site/K_offer is reported only after proportional-reference-module "
            "accounting scaling. C_reserve = (K_offer_PCC*f_abstract*C_coordinate - "
            "PV(salvage))*CRF(r,n) + K_offer_PCC*f_abstract*C_coordinate*O&M; no "
            "GPU-purchase inference"
        ),
        "economic_lifetime_grid": (
            "CRF(r,n) = r(1+r)^n / ((1+r)^n - 1); life axis fixes r=8% and "
            "salvage=10%, with separate one-factor WACC and salvage axes"
        ),
        "opportunity_cost_grid": (
            "C_opp = deferred_GPU_h * effective_displaced_compute_value_per_GPU_h, "
            "where effective_displaced_compute_value_per_GPU_h = alpha * value_per_GPU_h"
        ),
        "delay_cost_grid": "C_delay = backlog_area_GPU_h_h * delay_cost_per_GPU_h_h",
        "market_payment_grid": (
            "Revenue = K_offer*p_cap + capped_delivered_MWh*p_perf + declared_connection_value"
        ),
        "energy_price_grid": (
            "Energy_value = -incremental_energy_through_episode_end_kWh * electricity_price_per_kWh"
        ),
    }
    unknown = sorted(set(register["input_id"].astype(str)).difference(input_locations))
    if unknown:
        raise ValueError(
            "economic source register has inputs without a provenance mapping: "
            + ", ".join(unknown)
        )

    provenance = register.copy()
    provenance["analysis_id"] = specification.analysis_id
    provenance["analysis_role"] = specification.analysis_role
    provenance["monetary_basis"] = specification.monetary_basis
    provenance["specification_sha256"] = specification.sha256
    provenance["physical_ledger_contract_sha256"] = specification.physical_ledger_contract_sha256
    provenance["controller_config_sha256"] = specification.technical.controller_config_sha256
    provenance["technical_certificate_manifest_sha256"] = (
        specification.technical.technical_certificate_manifest_sha256
    )
    provenance["ledger_event_sha256"] = sha256_file(ledger_path)
    provenance["ledger_manifest_sha256"] = sha256_file(
        ledger_path.with_name("ledger_manifest.json")
    )
    provenance["external_parameter_evidence_path"] = (
        specification.inputs.external_parameter_evidence
    )
    provenance["external_parameter_evidence_sha256"] = input_hashes[
        "external_parameter_evidence"
    ]
    provenance["input_source_path"] = provenance["input_id"].map(
        lambda item: input_locations[str(item)][0]
    )
    provenance["input_source_sha256"] = provenance["input_id"].map(
        lambda item: input_locations[str(item)][1]
    )
    provenance["formula"] = provenance["input_id"].map(lambda item: formulas[str(item)])
    return provenance


def evaluate_economic_participation(
    specification_path: str | Path,
    ledger_path: str | Path,
    output_directory: str | Path,
) -> dict[str, object]:
    """Screen independent fresh events over declared economic and market grids."""

    # Snapshot Git provenance before creating a staging directory.  The
    # evaluation output is often inside the repository and must not turn a
    # clean input run into a self-reported dirty worktree.
    run_git_state = _git_state()
    specification = load_economic_participation_specification(specification_path)
    physical_input_hashes = verify_physical_input_hashes(specification)
    economic_input_hashes = verify_economic_input_hashes(specification)
    input_hashes = {**physical_input_hashes, **economic_input_hashes}
    ledger, ledger_manifest = _load_verified_ledger(ledger_path, specification)
    cost_grid = load_cost_parameter_grid(specification.inputs.cost_parameter_grid)
    markets_document = load_market_archetypes(specification.inputs.market_archetypes)
    if markets_document.schema_version != 1:
        raise ValueError("unsupported market-archetype schema version")
    if markets_document.currency_basis != specification.monetary_basis:
        raise ValueError("market grid monetary basis does not match economic protocol")
    if markets_document.analysis_status != "illustrative_parameterized_sensitivity":
        raise ValueError("economic v1 requires an explicit illustrative market sensitivity")
    _validate_grid(specification, cost_grid, markets_document.archetypes)
    destination = Path(output_directory)
    if destination.exists():
        raise FileExistsError(
            f"economic evaluation output already exists; use a new output directory: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    result_rows = _result_rows(specification, ledger, cost_grid, markets_document.archetypes)
    results = pd.DataFrame.from_records(result_rows)
    if results.empty:
        raise RuntimeError("economic evaluation generated no annual result rows")
    if float(results["accounting_identity_error"].abs().max()) > 1e-8:
        raise RuntimeError("economic annual accounting identity failed")
    offer_curve = _offer_curve(results)
    if bool(
        (
            offer_curve["economically_offerable_capacity_kw_mean"]
            > offer_curve["scaled_accounting_technical_capacity_ceiling_kw"] + 1e-9
        ).any()
    ):
        raise RuntimeError("mean economic offer capacity exceeds the scaled accounting ceiling")
    if bool(
        (
            offer_curve["economically_offerable_capacity_kw_risk_adjusted"]
            > offer_curve["scaled_accounting_technical_capacity_ceiling_kw"] + 1e-9
        ).any()
    ):
        raise RuntimeError(
            "risk-adjusted economic offer capacity exceeds the scaled accounting ceiling"
        )
    decomposition = _primary_rows(results, specification)
    surface = _break_even_surface(results, specification)
    primary_offers = _primary_offer_curves(offer_curve, specification)
    mechanism_sensitivity = _mechanism_sensitivity(results, specification)
    duration_break_even = _duration_break_even(results, specification)
    capital_sensitivity = _orthogonal_capital_sensitivity(results, specification)
    break_even_decomposition = _break_even_decomposition(decomposition)
    fixed_site_overlay_scale_sensitivity = _fixed_site_overlay_scale_sensitivity(
        results, specification
    )
    fraction_diagnostics = _development_fraction_diagnostics(ledger, specification)
    boundary = decomposition.loc[
        :,
        [
            "analysis_id",
            "analysis_role",
            "currency_basis",
            "annualization_scope",
            "performance_payment_basis",
            "reserved_capacity_basis",
            "facility_scale_interpretation",
            "technical_certificate_scope",
            "reference_module_operating_peak_kw",
            "facility_site_scale_mw",
            "proportional_reference_module_scale_factor",
            "regime",
            "duration_h",
            "notice_h",
            "reliability_target",
            "annual_event_count",
            "annual_event_count_class",
            "annual_event_count_is_stress",
            "technical_capacity_ceiling_kw",
            "candidate_reduction_kw",
            "scaled_accounting_technical_capacity_ceiling_kw",
            "scaled_accounting_candidate_reduction_kw",
            "technical_qualification",
            "economic_offer_definition",
            "break_even_capacity_payment_per_kw_year",
            "risk_adjusted_break_even_capacity_payment_per_kw_year",
            "break_even_capacity_payment_excluding_fixed_site_per_kw_year",
            "risk_adjusted_break_even_capacity_payment_excluding_fixed_site_per_kw_year",
            "break_even_performance_payment_per_mwh",
            "risk_adjusted_break_even_performance_payment_per_mwh",
            "break_even_performance_payment_excluding_fixed_site_per_mwh",
            "risk_adjusted_break_even_performance_payment_excluding_fixed_site_per_mwh",
            "fixed_site_enablement_cost",
            "variable_enablement_cost",
            "enablement_cost",
            "fixed_site_enablement_cost_per_offer_kw",
            "annual_net_value",
            "annual_net_value_excluding_fixed_site",
            "annual_net_value_p05",
            "annual_net_value_excluding_fixed_site_p05",
        ],
    ].copy()
    output = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.",
            suffix=".economic-evaluation.tmp",
            dir=destination.parent,
        )
    )
    annual_path = output / "annual_scenario_results.parquet"
    results.to_parquet(annual_path, index=False)
    break_even_capacity = results.loc[
        :,
        [
            "duration_h",
            "notice_h",
            "reliability_target",
            "regime",
            "economic_life_years",
            "reserved_capacity_fraction",
            "opportunity_exposure_alpha",
            "annual_event_count",
            "annual_event_count_class",
            "annual_event_count_is_stress",
            "facility_scale_interpretation",
            "technical_certificate_scope",
            "reference_module_operating_peak_kw",
            "facility_site_scale_mw",
            "proportional_reference_module_scale_factor",
            "candidate_reduction_kw",
            "technical_capacity_ceiling_kw",
            "scaled_accounting_candidate_reduction_kw",
            "scaled_accounting_technical_capacity_ceiling_kw",
            "market_archetype_id",
            "capacity_payment_per_kw_year",
            "performance_payment_per_mwh",
            "break_even_capacity_payment_per_kw_year",
            "risk_adjusted_break_even_capacity_payment_per_kw_year",
            "break_even_capacity_payment_excluding_fixed_site_per_kw_year",
            "risk_adjusted_break_even_capacity_payment_excluding_fixed_site_per_kw_year",
        ],
    ].sort_values(
        ["duration_h", "regime", "economic_life_years", "candidate_reduction_kw"], kind="stable"
    )
    break_even_performance = results.loc[
        :,
        [
            "duration_h",
            "notice_h",
            "reliability_target",
            "regime",
            "economic_life_years",
            "reserved_capacity_fraction",
            "opportunity_exposure_alpha",
            "annual_event_count",
            "annual_event_count_class",
            "annual_event_count_is_stress",
            "facility_scale_interpretation",
            "technical_certificate_scope",
            "reference_module_operating_peak_kw",
            "facility_site_scale_mw",
            "proportional_reference_module_scale_factor",
            "candidate_reduction_kw",
            "technical_capacity_ceiling_kw",
            "scaled_accounting_candidate_reduction_kw",
            "scaled_accounting_technical_capacity_ceiling_kw",
            "market_archetype_id",
            "capacity_payment_per_kw_year",
            "performance_payment_per_mwh",
            "break_even_performance_payment_per_mwh",
            "risk_adjusted_break_even_performance_payment_per_mwh",
            "break_even_performance_payment_excluding_fixed_site_per_mwh",
            "risk_adjusted_break_even_performance_payment_excluding_fixed_site_per_mwh",
        ],
    ].sort_values(
        ["duration_h", "regime", "economic_life_years", "candidate_reduction_kw"], kind="stable"
    )
    parameter_provenance = _parameter_provenance_frame(
        specification,
        input_hashes=input_hashes,
        ledger_path=Path(ledger_path),
    )
    csv_hashes = {
        "break_even_capacity_payment.csv": _write_csv(
            break_even_capacity, output / "break_even_capacity_payment.csv"
        ),
        "break_even_performance_payment.csv": _write_csv(
            break_even_performance, output / "break_even_performance_payment.csv"
        ),
        "economic_offer_curve.csv": _write_csv(offer_curve, output / "economic_offer_curve.csv"),
        "economic_cost_decomposition.csv": _write_csv(
            decomposition, output / "economic_cost_decomposition.csv"
        ),
        "technical_economic_boundary.csv": _write_csv(
            boundary, output / "technical_economic_boundary.csv"
        ),
        "break_even_surface.csv": _write_csv(surface, output / "break_even_surface.csv"),
        "primary_economic_offer_curve.csv": _write_csv(
            primary_offers, output / "primary_economic_offer_curve.csv"
        ),
        "mechanism_sensitivity.csv": _write_csv(
            mechanism_sensitivity, output / "mechanism_sensitivity.csv"
        ),
        "break_even_decomposition.csv": _write_csv(
            break_even_decomposition, output / "break_even_decomposition.csv"
        ),
        "duration_break_even.csv": _write_csv(
            duration_break_even, output / "duration_break_even.csv"
        ),
        "orthogonal_capital_sensitivity.csv": _write_csv(
            capital_sensitivity, output / "orthogonal_capital_sensitivity.csv"
        ),
        "fixed_site_overlay_scale_sensitivity.csv": _write_csv(
            fixed_site_overlay_scale_sensitivity,
            output / "fixed_site_overlay_scale_sensitivity.csv",
        ),
        "development_fraction_diagnostics.csv": _write_csv(
            fraction_diagnostics, output / "development_fraction_diagnostics.csv"
        ),
        "economic_parameter_provenance.csv": _write_csv(
            parameter_provenance,
            output / "economic_parameter_provenance.csv",
        ),
    }
    csv_row_counts = {
        "break_even_capacity_payment.csv": len(break_even_capacity),
        "break_even_performance_payment.csv": len(break_even_performance),
        "economic_offer_curve.csv": len(offer_curve),
        "economic_cost_decomposition.csv": len(decomposition),
        "technical_economic_boundary.csv": len(boundary),
        "break_even_surface.csv": len(surface),
        "primary_economic_offer_curve.csv": len(primary_offers),
        "mechanism_sensitivity.csv": len(mechanism_sensitivity),
        "break_even_decomposition.csv": len(break_even_decomposition),
        "duration_break_even.csv": len(duration_break_even),
        "orthogonal_capital_sensitivity.csv": len(capital_sensitivity),
        "fixed_site_overlay_scale_sensitivity.csv": len(fixed_site_overlay_scale_sensitivity),
        "development_fraction_diagnostics.csv": len(fraction_diagnostics),
        "economic_parameter_provenance.csv": len(parameter_provenance),
    }
    if set(csv_row_counts) != set(csv_hashes):
        raise RuntimeError("economic CSV manifest inventory is incomplete")
    parameter_manifest = {
        "schema_version": 2,
        "analysis_status": "illustrative_parameterized_sensitivity",
        "interpretation": (
            "Parameter ranges are declared research-design sensitivities, not a claim "
            "that any named market currently pays these values."
        ),
        "cost_parameter_grid": asdict(cost_grid),
        "market_archetypes": asdict(markets_document),
        "physical_ledger_contract_sha256": specification.physical_ledger_contract_sha256,
        "physical_input_sha256": physical_input_hashes,
        "economic_input_sha256": economic_input_hashes,
    }
    parameter_path = output / "parameter_manifest.json"
    parameter_path.write_text(
        json.dumps(parameter_manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    if verify_economic_input_hashes(specification) != economic_input_hashes:
        raise RuntimeError(
            "economic input changed while evaluation was running; refusing to publish"
        )
    run_manifest = {
        "schema_version": 2,
        "analysis_id": specification.analysis_id,
        "analysis_role": specification.analysis_role,
        "interpretation": (
            "independent-fresh-event parameterized economic screening using development "
            "paired trajectories; not a continuous annual DR programme, a new locked "
            "economic certificate, or a real-market profitability claim"
        ),
        "economic_offer_definition": (
            "binary_0_or_independently_certified_reference_module_Kcert"
        ),
        "sub_kcert_fraction_status": "development_diagnostic_not_independently_certified",
        "reserved_capacity_basis": cost_grid.reserved_capacity_basis,
        "performance_payment_basis": "interval_delivery_capped_at_scaled_accounting_offered_kW",
        "final_publish": "atomic_directory_rename",
        "specification_path": str(specification_path),
        "specification_sha256": specification.sha256,
        "physical_ledger_contract": specification.physical_ledger_contract(),
        "physical_ledger_contract_sha256": specification.physical_ledger_contract_sha256,
        "ledger_path": str(ledger_path),
        "ledger_manifest_sha256": sha256_file(Path(ledger_path).with_name("ledger_manifest.json")),
        "ledger_event_sha256": sha256_file(Path(ledger_path)),
        "ledger_source_manifest": ledger_manifest,
        "physical_input_sha256": physical_input_hashes,
        "economic_input_sha256": economic_input_hashes,
        "annual_result_row_count": len(results),
        "annual_result_sha256": sha256_file(annual_path),
        "csv_row_count": csv_row_counts,
        "csv_sha256": csv_hashes,
        "source_sha256": {
            "economic_participation.py": sha256_file(Path(__file__)),
            "accounting.py": sha256_file(_ROOT / "src/aidrbench/economics/accounting.py"),
            "capital.py": sha256_file(_ROOT / "src/aidrbench/economics/capital.py"),
            "opportunity_cost.py": sha256_file(
                _ROOT / "src/aidrbench/economics/opportunity_cost.py"
            ),
            "tariffs.py": sha256_file(_ROOT / "src/aidrbench/economics/tariffs.py"),
        },
        **run_git_state,
    }
    run_path = output / "run_manifest.json"
    run_path.write_text(
        json.dumps(run_manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(output, destination)
    annual_path = destination / "annual_scenario_results.parquet"
    run_path = destination / "run_manifest.json"
    return {
        "annual_scenario_results": str(annual_path),
        "economic_offer_curve": str(destination / "economic_offer_curve.csv"),
        "economic_cost_decomposition": str(destination / "economic_cost_decomposition.csv"),
        "technical_economic_boundary": str(destination / "technical_economic_boundary.csv"),
        "economic_parameter_provenance": str(destination / "economic_parameter_provenance.csv"),
        "fixed_site_overlay_scale_sensitivity": str(
            destination / "fixed_site_overlay_scale_sensitivity.csv"
        ),
        "run_manifest": str(run_path),
        "annual_result_row_count": len(results),
        "offer_curve_row_count": len(offer_curve),
    }
