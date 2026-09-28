from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

import aidrbench.evaluation.economic_participation as economic_participation_module
from aidrbench.cli import build_parser
from aidrbench.economics.accounting import AnnualEconomicInputs, annual_economic_value
from aidrbench.economics.capital import annualized_reserve_cost, capital_recovery_factor
from aidrbench.economics.specification import (
    annual_event_count_screening_class,
    load_cost_parameter_grid,
    load_economic_participation_specification,
    scenario_set_sha256,
    verify_economic_input_hashes,
    verify_physical_input_hashes,
)
from aidrbench.evaluation.economic_event_ledger import _criteria_document
from aidrbench.evaluation.economic_figures import plot_economic_participation_figure
from aidrbench.evaluation.economic_participation import evaluate_economic_participation
from aidrbench.evaluation.source_data import (
    export_manuscript_source_data,
    load_source_data_specification,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_capital_annualisation_has_correct_limits_and_zero_reserve() -> None:
    assert capital_recovery_factor(0.0, 4.0) == pytest.approx(0.25)
    assert capital_recovery_factor(0.08, 6.0) < capital_recovery_factor(0.08, 3.0)
    assert (
        annualized_reserve_cost(
            reserved_capacity_kw=0.0,
            installed_cost_per_reserved_kw=2_500.0,
            discount_rate=0.08,
            economic_life_years=4.0,
            salvage_fraction=0.10,
            annual_om_fraction=0.03,
        )
        == 0.0
    )


def test_declared_capital_sensitivities_are_orthogonal() -> None:
    grid = load_cost_parameter_grid("configs/economics/cost_parameter_grid_v1.yaml")
    assert grid.reserved_capacity_basis == "abstract_pcc_side_kw_sensitivity"
    reference = [case for case in grid.capital_cases if case.sensitivity_axis == "reference"]
    assert len(reference) == 1
    life_cases = [
        *[case for case in grid.capital_cases if case.sensitivity_axis == "economic_life"],
        reference[0],
    ]
    assert {case.economic_life_years for case in life_cases} == {3.0, 4.0, 5.0, 6.0}
    assert {case.discount_rate for case in life_cases} == {0.08}
    assert {case.salvage_fraction for case in life_cases} == {0.10}
    wacc_cases = [
        *[case for case in grid.capital_cases if case.sensitivity_axis == "discount_rate"],
        reference[0],
    ]
    assert {case.discount_rate for case in wacc_cases} == {0.04, 0.08, 0.12}
    assert {case.economic_life_years for case in wacc_cases} == {4.0}
    assert {case.salvage_fraction for case in wacc_cases} == {0.10}
    salvage_cases = [
        *[case for case in grid.capital_cases if case.sensitivity_axis == "salvage_fraction"],
        reference[0],
    ]
    assert {case.salvage_fraction for case in salvage_cases} == {0.0, 0.10, 0.20}
    assert {case.economic_life_years for case in salvage_cases} == {4.0}
    assert {case.discount_rate for case in salvage_cases} == {0.08}


def test_economic_source_register_has_a_stable_rectangular_schema() -> None:
    register = pd.read_csv("data/economics/source_register.csv")
    assert tuple(register.columns) == (
        "input_id",
        "description",
        "value_or_range",
        "unit",
        "currency_basis",
        "source_type",
        "source_reference",
        "source_url",
        "access_date",
        "status",
        "permitted_interpretation",
        "support_level",
        "replaceability",
        "original_currency_year",
        "external_evidence_reference",
        "external_evidence_url",
        "external_evidence_value_or_range",
        "forbidden_interpretation",
    )
    assert set(register["input_id"]) == {
        "technical_capacity_ceiling_q95",
        "reserved_cost_grid",
        "economic_lifetime_grid",
        "opportunity_cost_grid",
        "delay_cost_grid",
        "market_payment_grid",
        "energy_price_grid",
    }
    assert not register.isna().any().any()


def test_economic_event_count_classes_are_predeclared_and_exhaustive() -> None:
    assert annual_event_count_screening_class(1) == ("plausible_screening", False)
    assert annual_event_count_screening_class(12) == ("plausible_screening", False)
    assert annual_event_count_screening_class(50) == ("plausible_screening", False)
    assert annual_event_count_screening_class(100) == ("exposure_multiplier_stress", True)
    assert annual_event_count_screening_class(250) == ("exposure_multiplier_stress", True)
    with pytest.raises(ValueError, match="predeclared coordinates"):
        annual_event_count_screening_class(51)


def test_physical_ledger_contract_excludes_economics_only_inputs() -> None:
    specification = load_economic_participation_specification(
        "configs/economics/economic_participation_v1.yaml"
    )
    changed = replace(
        specification,
        inputs=replace(
            specification.inputs,
            external_parameter_evidence_sha256="0" * 64,
        ),
    )
    assert changed.sha256 != specification.sha256
    assert changed.physical_ledger_contract_sha256 == specification.physical_ledger_contract_sha256
    assert set(verify_economic_input_hashes(specification)) == {
        "cost_parameter_grid",
        "market_archetypes",
        "source_register",
        "external_parameter_evidence",
    }


def test_fixed_finance_life_increase_reduces_annual_reserve_cost() -> None:
    costs = [
        annualized_reserve_cost(
            reserved_capacity_kw=10.0,
            installed_cost_per_reserved_kw=2_500.0,
            discount_rate=0.08,
            economic_life_years=life,
            salvage_fraction=0.10,
            annual_om_fraction=0.03,
        )
        for life in (3.0, 4.0, 5.0, 6.0)
    ]
    assert costs == sorted(costs, reverse=True)


def test_economic_source_data_contract_has_one_table_per_figure_panel() -> None:
    specification = load_source_data_specification(
        "configs/paper/nature_economic_source_data_v1.yaml"
    )
    panels = {
        table.table_id: table.panels
        for table in specification.tables
        if table.table_id.startswith("fig6_")
    }
    assert panels["fig6_technical_economic_boundary"] == ("supporting",)
    assert panels["fig6_fixed_site_overlay_scale_sensitivity"] == ("a",)
    assert panels["fig6_mechanism_sensitivity"] == ("b",)
    assert panels["fig6_break_even_decomposition"] == ("c",)
    assert panels["fig6_duration_break_even"] == ("d",)
    assert panels["fig6_paired_event_ledger"] == ("supporting",)
    assert panels["fig6_paired_interval_ledger"] == ("supporting",)
    assert panels["fig6_economic_parameter_provenance"] == ("supporting",)
    assert panels["fig6_external_parameter_evidence"] == ("supporting",)
    assert panels["fig6_reserve_mapping_summary"] == ("supporting",)


def test_mainline_economic_protocol_replays_only_the_certified_ceiling() -> None:
    specification = load_economic_participation_specification(
        "configs/economics/economic_participation_v1.yaml"
    )
    assert specification.technical.offer_fractions == (1.0,)
    assert specification.technical.replay_runtime_mode == "certificate_git_commit"
    assert specification.technical.replay_git_commit == ("5889405427b8f00f3cdd12b961b79d621b122e65")
    assert specification.evaluation.primary_offer_fraction == 1.0
    assert specification.technical.qualification_for_offer_fraction(1.0) == (
        "independently_certified_ceiling"
    )


def test_economic_commands_are_registered() -> None:
    parser = build_parser()
    ledger = parser.parse_args(
        [
            "economics",
            "build-event-ledger",
            "--specification",
            "economic.yaml",
            "--output",
            "ledger",
        ]
    )
    figure = parser.parse_args(
        [
            "paper",
            "economic-figure",
            "--source-data",
            "source-data",
            "--output",
            "figure",
        ]
    )
    assert ledger.economics_command == "build-event-ledger"
    assert figure.paper_command == "economic-figure"


def test_accounting_rejects_double_count_and_preserves_identity() -> None:
    with pytest.raises(ValueError, match="cannot also charge displaced compute"):
        AnnualEconomicInputs(
            regime="reserved_headroom",
            offered_capacity_kw=10.0,
            technical_capacity_ceiling_kw=10.0,
            annual_event_count=12,
            annual_capped_delivered_energy_kwh=120.0,
            annual_shortfall_energy_kwh=0.0,
            annual_deferred_gpu_h=10.0,
            annual_backlog_area_gpu_h_h=0.0,
            annual_incremental_energy_kwh=0.0,
            annual_missed_gpu_h=0.0,
            annual_terminal_backlog_gpu_h=0.0,
            annual_failure_count=0.0,
            capacity_payment_per_kw_year=500.0,
            performance_payment_per_mwh=50.0,
            electricity_price_per_kwh=0.10,
            flexible_connection_value_per_year=0.0,
            fixed_site_enablement_annual_cost=0.0,
            variable_enablement_cost_per_offer_kw=0.0,
            checkpoint_cost_per_event=0.0,
            reserved_capacity_fraction=0.10,
            installed_cost_per_reserved_kw=2_500.0,
            discount_rate=0.08,
            economic_life_years=4.0,
            salvage_fraction=0.10,
            annual_om_fraction=0.03,
            opportunity_exposure_alpha=0.10,
            value_per_gpu_h=1.0,
            delay_cost_per_gpu_h_h=0.0,
            missed_work_cost_per_gpu_h=0.0,
            terminal_backlog_cost_per_gpu_h=0.0,
            shortfall_penalty_per_mwh=0.0,
            failure_penalty_per_event=0.0,
        )
    inputs = AnnualEconomicInputs(
        regime="slack_backed",
        offered_capacity_kw=10.0,
        technical_capacity_ceiling_kw=10.0,
        annual_event_count=12,
        annual_capped_delivered_energy_kwh=120.0,
        annual_shortfall_energy_kwh=0.0,
        annual_deferred_gpu_h=10.0,
        annual_backlog_area_gpu_h_h=4.0,
        annual_incremental_energy_kwh=-10.0,
        annual_missed_gpu_h=0.0,
        annual_terminal_backlog_gpu_h=0.0,
        annual_failure_count=0.0,
        capacity_payment_per_kw_year=500.0,
        performance_payment_per_mwh=50.0,
        electricity_price_per_kwh=0.10,
        flexible_connection_value_per_year=0.0,
        fixed_site_enablement_annual_cost=100.0,
        variable_enablement_cost_per_offer_kw=0.0,
        checkpoint_cost_per_event=0.0,
        reserved_capacity_fraction=0.0,
        installed_cost_per_reserved_kw=2_500.0,
        discount_rate=0.08,
        economic_life_years=4.0,
        salvage_fraction=0.10,
        annual_om_fraction=0.03,
        opportunity_exposure_alpha=0.0,
        value_per_gpu_h=1.0,
        delay_cost_per_gpu_h_h=0.01,
        missed_work_cost_per_gpu_h=0.0,
        terminal_backlog_cost_per_gpu_h=0.0,
        shortfall_penalty_per_mwh=0.0,
        failure_penalty_per_event=0.0,
    )
    result = annual_economic_value(inputs)
    assert result["accounting_identity_error"] == pytest.approx(0.0)
    assert result["reserve_annual_cost"] == pytest.approx(0.0)
    assert result["opportunity_cost"] == pytest.approx(0.0)


def test_performance_payment_is_capped_and_capacity_revenue_ignores_event_count() -> None:
    inputs = AnnualEconomicInputs(
        regime="slack_backed",
        offered_capacity_kw=10.0,
        technical_capacity_ceiling_kw=10.0,
        annual_event_count=1,
        annual_capped_delivered_energy_kwh=40.0,
        annual_shortfall_energy_kwh=0.0,
        annual_deferred_gpu_h=0.0,
        annual_backlog_area_gpu_h_h=0.0,
        annual_incremental_energy_kwh=0.0,
        annual_missed_gpu_h=0.0,
        annual_terminal_backlog_gpu_h=0.0,
        annual_failure_count=0.0,
        capacity_payment_per_kw_year=500.0,
        performance_payment_per_mwh=50.0,
        electricity_price_per_kwh=0.10,
        flexible_connection_value_per_year=0.0,
        fixed_site_enablement_annual_cost=0.0,
        variable_enablement_cost_per_offer_kw=0.0,
        checkpoint_cost_per_event=0.0,
        reserved_capacity_fraction=0.0,
        installed_cost_per_reserved_kw=2_500.0,
        discount_rate=0.08,
        economic_life_years=4.0,
        salvage_fraction=0.10,
        annual_om_fraction=0.03,
        opportunity_exposure_alpha=0.0,
        value_per_gpu_h=0.0,
        delay_cost_per_gpu_h_h=0.0,
        missed_work_cost_per_gpu_h=0.0,
        terminal_backlog_cost_per_gpu_h=0.0,
        shortfall_penalty_per_mwh=0.0,
        failure_penalty_per_event=0.0,
    )
    one_event = annual_economic_value(inputs)
    many_events = annual_economic_value(replace(inputs, annual_event_count=250))
    assert one_event["performance_revenue"] == pytest.approx(2.0)
    assert one_event["capacity_revenue"] == pytest.approx(5_000.0)
    assert many_events["capacity_revenue"] == pytest.approx(one_event["capacity_revenue"])


def _write_economic_inputs(
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path, Path, Path, Path]:
    controller = tmp_path / "controller.yaml"
    certificate = tmp_path / "certificate.parquet"
    certificate_manifest = tmp_path / "certificate_manifest.json"
    costs = tmp_path / "costs.yaml"
    markets = tmp_path / "markets.yaml"
    register = tmp_path / "source_register.csv"
    evidence = tmp_path / "external_parameter_evidence.csv"
    controller.write_text("controller: robust_mpc\n", encoding="utf-8")
    pd.DataFrame(
        {
            "duration_h": [4],
            "notice_h": [0],
            "reliability_target": [0.95],
            "confidence_level": [0.95],
            "candidate_reduction_kw": [10.0],
            "certified": [True],
        }
    ).to_parquet(certificate, index=False)
    certificate_manifest.write_text("{}\n", encoding="utf-8")
    costs.write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "currency_basis": "real_2026_usd",
                "analysis_status": "illustrative_parameterized_sensitivity",
                "reserved_capacity_basis": "abstract_pcc_side_kw_sensitivity",
                "reference_module_operating_peak_kw": 10.0,
                "facility_site_scales_mw": [0.2, 1.0, 5.0, 20.0],
                "facility_scale_interpretation": (
                    "proportional_reference_module_accounting_sensitivity_"
                    "no_portfolio_diversification"
                ),
                "capital_cases": [
                    {
                        "case_id": "base",
                        "sensitivity_axis": "reference",
                        "economic_life_years": 4,
                        "discount_rate": 0.08,
                        "salvage_fraction": 0.10,
                        "installed_cost_per_reserved_kw": 100.0,
                        "annual_om_fraction": 0.0,
                        "fixed_site_enablement_annual_cost": 10.0,
                        "variable_enablement_cost_per_offer_kw": 2.0,
                        "checkpoint_cost_per_event": 0.0,
                    },
                    {
                        "case_id": "life_3y",
                        "sensitivity_axis": "economic_life",
                        "economic_life_years": 3,
                        "discount_rate": 0.08,
                        "salvage_fraction": 0.10,
                        "installed_cost_per_reserved_kw": 100.0,
                        "annual_om_fraction": 0.0,
                        "fixed_site_enablement_annual_cost": 10.0,
                        "variable_enablement_cost_per_offer_kw": 2.0,
                        "checkpoint_cost_per_event": 0.0,
                    },
                ],
                "operating_cases": [
                    {
                        "case_id": "base",
                        "value_per_gpu_h": 1.0,
                        "delay_cost_per_gpu_h_h": 0.0,
                        "missed_work_cost_per_gpu_h": 0.0,
                        "terminal_backlog_cost_per_gpu_h": 0.0,
                        "electricity_price_per_kwh": 0.0,
                    }
                ],
                "regimes": [
                    {
                        "regime": "slack_backed",
                        "reserved_capacity_fractions": [0.0],
                        "opportunity_exposure_alphas": [0.0],
                    },
                    {
                        "regime": "reserved_headroom",
                        "reserved_capacity_fractions": [0.05, 0.15],
                        "opportunity_exposure_alphas": [0.0],
                    },
                    {
                        "regime": "throughput_displacing",
                        "reserved_capacity_fractions": [0.0],
                        "opportunity_exposure_alphas": [0.25, 0.50],
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    markets.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "currency_basis": "real_2026_usd",
                "analysis_status": "illustrative_parameterized_sensitivity",
                "archetypes": [
                    {
                        "archetype_id": "two_part",
                        "capacity_payment_per_kw_year": [0, 500],
                        "performance_payment_per_mwh": [50],
                        "flexible_connection_value_per_year": [0],
                        "shortfall_penalty_per_mwh": 0,
                        "failure_penalty_per_event": 0,
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    input_ids = (
        "technical_capacity_ceiling_q95",
        "reserved_cost_grid",
        "economic_lifetime_grid",
        "opportunity_cost_grid",
        "delay_cost_grid",
        "market_payment_grid",
        "energy_price_grid",
    )
    register.write_text(
        "input_id,external_evidence_reference\n"
        + "\n".join(f"{input_id},E_{index}" for index, input_id in enumerate(input_ids))
        + "\n",
        encoding="utf-8",
    )
    evidence_rows = [
        {
            "evidence_id": f"E_{index}",
            "input_id": input_id,
            "parameter_family": "test",
            "source_title": "test source",
            "source_organization": "test organization",
            "source_url": "https://example.invalid/test",
            "publication_or_reporting_year": "2026",
            "access_date": "2026-09-04",
            "observed_value": "test",
            "unit": "test_unit",
            "currency_year": "not_applicable",
            "support_level": "test_only",
            "replaceability": "test_only",
            "permitted_use": "test_only",
            "forbidden_interpretation": "test_only",
        }
        for index, input_id in enumerate(input_ids)
    ]
    pd.DataFrame(evidence_rows).to_csv(evidence, index=False)
    return controller, certificate, certificate_manifest, costs, markets, register, evidence


def _write_specification(
    tmp_path: Path,
    *,
    controller: Path,
    certificate: Path,
    certificate_manifest: Path,
    costs: Path,
    markets: Path,
    register: Path,
    evidence: Path,
) -> Path:
    selection = tmp_path / "selection.json"
    validation_receipt = tmp_path / "validation_receipt.yaml"
    locked_receipt = tmp_path / "locked_receipt.yaml"
    selection.write_text("{}\n", encoding="utf-8")
    validation_receipt.write_text("{}\n", encoding="utf-8")
    locked_receipt.write_text("{}\n", encoding="utf-8")
    scenario_records = [
        {
            "episode_seed": seed,
            "scenario_id": f"scenario_{seed}",
            "scenario_hash": f"{seed:064x}",
        }
        for seed in (1, 2)
    ]
    specification = {
        "schema_version": 2,
        "analysis_id": "test_economics",
        "analysis_role": "development_parameterized_screening",
        "monetary_basis": "real_2026_usd",
        "technical": {
            "scenario_directory": "development_scenarios",
            "expected_scenario_count": 2,
            "expected_episode_seed_range": [1, 2],
            "scenario_set_sha256": scenario_set_sha256(scenario_records),
            "controller": "robust_mpc",
            "controller_config": str(controller),
            "controller_config_sha256": _sha256(controller),
            "technical_certificate_path": str(certificate),
            "technical_certificate_sha256": _sha256(certificate),
            "technical_certificate_manifest": str(certificate_manifest),
            "technical_certificate_manifest_sha256": _sha256(certificate_manifest),
            "technical_selection_path": str(selection),
            "technical_selection_sha256": _sha256(selection),
            "validation_scenario_receipt": str(validation_receipt),
            "validation_scenario_receipt_sha256": _sha256(validation_receipt),
            "locked_id_receipt": str(locked_receipt),
            "locked_id_receipt_sha256": _sha256(locked_receipt),
            "replay_runtime_mode": "current_worktree",
            "replay_git_commit": None,
            "duration_hours": [4],
            "notice_hours": [0],
            "reliability_target": 0.95,
            "confidence_level": 0.95,
            "event_id": 0,
            "offer_fractions": [0.5, 1.0],
            "workers": 1,
            "criteria": {
                "min_delivery_ratio": 0.95,
                "min_interval_delivery_ratio": 0.95,
                "max_deadline_miss_rate": 0.01,
                "max_rebound_ratio": 0.25,
                "min_window_peak_relief_fraction": 0.50,
                "max_terminal_backlog_fraction": 0.02,
            },
        },
        "ledger": {
            "baseline_type": "paired_no_control_replay",
            "paired_pcc_tolerance_kw": 1e-8,
            "work_conservation_tolerance_gpu_h": 1e-6,
            "include_interval_ledger": False,
        },
        "evaluation": {
            "dispatch_sampling": "independent_fresh_event_screening_bootstrap",
            "bootstrap_draws": 100,
            "bootstrap_seed": 1,
            "risk_quantile": 0.05,
            "annual_event_counts": [1, 12, 50, 100, 250],
            "primary_duration_h": 4,
            "primary_notice_h": 0,
            "primary_reliability_target": 0.95,
            "primary_offer_fraction": 1.0,
            "primary_capital_case_id": "base",
            "primary_operating_case_id": "base",
            "primary_market_archetype_id": "two_part",
            "primary_annual_event_count": 50,
            "primary_facility_site_scale_mw": 1.0,
            "primary_capacity_payment_per_kw_year": 0,
            "primary_performance_payment_per_mwh": 50,
            "primary_regime_exposures": {
                "slack_backed": {
                    "reserved_capacity_fraction": 0.0,
                    "opportunity_exposure_alpha": 0.0,
                },
                "reserved_headroom": {
                    "reserved_capacity_fraction": 0.15,
                    "opportunity_exposure_alpha": 0.0,
                },
                "throughput_displacing": {
                    "reserved_capacity_fraction": 0.0,
                    "opportunity_exposure_alpha": 0.50,
                },
            },
        },
        "inputs": {
            "cost_parameter_grid": str(costs),
            "cost_parameter_grid_sha256": _sha256(costs),
            "market_archetypes": str(markets),
            "market_archetypes_sha256": _sha256(markets),
            "source_register": str(register),
            "source_register_sha256": _sha256(register),
            "external_parameter_evidence": str(evidence),
            "external_parameter_evidence_sha256": _sha256(evidence),
        },
    }
    path = tmp_path / "economic.yaml"
    path.write_text(yaml.safe_dump(specification, sort_keys=False), encoding="utf-8")
    return path


def test_economic_evaluation_caps_offer_at_technical_capacity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller, certificate, certificate_manifest, costs, markets, register, evidence = (
        _write_economic_inputs(tmp_path)
    )
    specification_path = _write_specification(
        tmp_path,
        controller=controller,
        certificate=certificate,
        certificate_manifest=certificate_manifest,
        costs=costs,
        markets=markets,
        register=register,
        evidence=evidence,
    )
    specification = load_economic_participation_specification(specification_path)
    ledger = pd.DataFrame(
        [
            {
                "evaluation_split": "development_parameterized_screening",
                "scenario_id": f"scenario_{seed}",
                "scenario_hash": f"{seed:064x}",
                "episode_seed": seed,
                "event_id": 0,
                "duration_h": 4,
                "notice_h": 0,
                "reliability_target": 0.95,
                "confidence_level": 0.95,
                "technical_capacity_ceiling_kw": 10.0,
                "offer_fraction_of_technical_ceiling": fraction,
                "candidate_reduction_kw": 10.0 * fraction,
                "technical_success": True,
                # Raw physical response may exceed the offer; only the capped
                # delivery is eligible for performance payment.
                "delivered_energy_kwh": 10.0 * fraction * 4.0 + 5.0,
                "capped_delivered_energy_kwh": 10.0 * fraction * 4.0,
                "shortfall_energy_kwh": 0.0,
                "deferred_gpu_h": 2.0 * fraction,
                "recovered_within_recovery_window_gpu_h": 1.0 * fraction,
                "recovered_through_episode_end_gpu_h": 2.0 * fraction,
                "incremental_backlog_area_within_recovery_gpu_h_h": 1.0,
                "incremental_backlog_area_through_episode_end_gpu_h_h": 2.0,
                "incremental_energy_within_recovery_kwh": -2.0,
                "incremental_energy_through_episode_end_kwh": -1.0,
                "missed_gpu_h": 0.0,
                "terminal_backlog_gpu_h": 0.0,
            }
            for fraction in (0.5, 1.0)
            for seed in (1, 2)
        ]
    )
    ledger_path = tmp_path / "episode_ledger.parquet"
    ledger.to_parquet(ledger_path, index=False)
    (tmp_path / "ledger_manifest.json").write_text(
        json.dumps(
            {
                "analysis_id": specification.analysis_id,
                "analysis_role": specification.analysis_role,
                "specification_sha256": specification.sha256,
                "physical_ledger_contract": specification.physical_ledger_contract(),
                "physical_ledger_contract_sha256": specification.physical_ledger_contract_sha256,
                "scenario_count": specification.technical.expected_scenario_count,
                "scenario_set_sha256": specification.technical.scenario_set_sha256,
                "physical_input_sha256": verify_physical_input_hashes(specification),
                "technical_provenance": {
                    "manifest_sha256": (
                        specification.technical.technical_certificate_manifest_sha256
                    ),
                    "controller_config_sha256": specification.technical.controller_config_sha256,
                },
                "event_ledger_sha256": _sha256(ledger_path),
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "economic_results"
    expected_git_state = {"git_commit": "e" * 40, "working_tree_dirty": False}
    git_state_calls = 0

    def capture_git_state() -> dict[str, object]:
        nonlocal git_state_calls
        git_state_calls += 1
        if git_state_calls <= 2:
            assert not output.exists()
            assert not list(tmp_path.glob(".economic_results.*.economic-evaluation.tmp"))
        return expected_git_state

    monkeypatch.setattr(economic_participation_module, "_git_state", capture_git_state)
    preexisting_output = tmp_path / "preexisting_output"
    preexisting_output.mkdir()
    with pytest.raises(FileExistsError, match="already exists"):
        evaluate_economic_participation(
            specification_path,
            ledger_path,
            preexisting_output,
        )
    summary = evaluate_economic_participation(specification_path, ledger_path, output)
    assert summary["annual_result_row_count"] > 0
    offers = pd.read_csv(output / "economic_offer_curve.csv")
    scaled_ceiling = offers["scaled_accounting_technical_capacity_ceiling_kw"]
    mean_offer = offers["economically_offerable_capacity_kw_mean"]
    risk_offer = offers["economically_offerable_capacity_kw_risk_adjusted"]
    assert (mean_offer <= scaled_ceiling).all()
    assert (risk_offer <= scaled_ceiling).all()
    assert (np.isclose(mean_offer, 0.0) | np.isclose(mean_offer, scaled_ceiling)).all()
    assert (np.isclose(risk_offer, 0.0) | np.isclose(risk_offer, scaled_ceiling)).all()
    assert offers["economic_offer_definition"].eq(
        "binary_0_or_independently_certified_reference_module_Kcert"
    ).all()
    results = pd.read_parquet(output / "annual_scenario_results.parquet")
    assert results["accounting_identity_error"].abs().max() == pytest.approx(0.0)
    assert set(results["offer_fraction_of_technical_ceiling"]) == {1.0}
    assert (
        results["annualization_scope"].eq("independent_fresh_events_not_continuous_programme").all()
    )
    paid = results[
        (results["regime"] == "slack_backed")
        & (results["candidate_reduction_kw"] == 10.0)
        & (results["annual_event_count"] == 50)
        & (results["capacity_payment_per_kw_year"] == 0.0)
    ]
    assert not paid.empty
    expected_performance_revenue = (
        paid["scaled_accounting_candidate_reduction_kw"]
        * 4.0
        / 1_000.0
        * 50.0
        * 50.0
    )
    assert paid["performance_revenue"].to_numpy() == pytest.approx(
        expected_performance_revenue.to_numpy()
    )
    diagnostics = pd.read_csv(output / "development_fraction_diagnostics.csv")
    assert set(diagnostics["offer_fraction_of_technical_ceiling"]) == {0.5}
    assert (
        diagnostics["technical_qualification"]
        .eq("development_screened_not_independently_certified")
        .all()
    )
    boundary = pd.read_csv(output / "technical_economic_boundary.csv")
    assert boundary["technical_qualification"].eq("independently_certified_ceiling").all()
    assert "risk_adjusted_break_even_capacity_payment_per_kw_year" in boundary
    mechanism = pd.read_csv(output / "mechanism_sensitivity.csv")
    for _, group in mechanism.groupby("regime"):
        positions = group["driver_normalized_position"].to_numpy()
        assert positions[0] == pytest.approx(0.0)
        assert positions[-1] == pytest.approx(1.0)
        assert (positions[1:] > positions[:-1]).all()
    components = pd.read_csv(output / "break_even_decomposition.csv")
    assert set(components["component_id"]) == {
        "fixed_site_enablement_cost",
        "variable_enablement_cost",
        "reserve_annual_cost",
        "opportunity_cost",
        "delay_cost",
        "sla_cost",
        "checkpoint_cost",
        "penalty_cost",
        "performance_credit",
        "energy_credit_or_cost",
        "connection_credit",
        "risk_buffer",
    }
    component_totals = components.groupby("regime")["contribution_per_kw_year"].sum()
    component_targets = components.groupby("regime")[
        "risk_adjusted_break_even_capacity_payment_per_kw_year"
    ].first()
    assert component_totals.to_numpy() == pytest.approx(component_targets.to_numpy())
    provenance = pd.read_csv(output / "economic_parameter_provenance.csv")
    assert provenance["specification_sha256"].eq(specification.sha256).all()
    assert provenance["formula"].notna().all()
    run_manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
    assert run_manifest["final_publish"] == "atomic_directory_rename"
    assert run_manifest["git_commit"] == expected_git_state["git_commit"]
    assert run_manifest["working_tree_dirty"] is False
    assert set(run_manifest["csv_row_count"]) == set(run_manifest["csv_sha256"])
    assert run_manifest["csv_row_count"]["economic_offer_curve.csv"] == len(offers)
    assert git_state_calls == 2
    assert not list(tmp_path.glob(".economic_results.*.economic-evaluation.tmp"))

    # The evaluation output, source-data projection and renderer form one
    # fail-closed contract: every plotted panel must consume its exact table.
    figure_specification = yaml.safe_load(
        Path("configs/paper/nature_economic_source_data_v1.yaml").read_text(encoding="utf-8")
    )
    figure_specification["tables"] = figure_specification["tables"][:4]
    for table in figure_specification["tables"]:
        filename = Path(table["inputs"][0]["path"]).name
        table["inputs"][0]["path"] = f"economic_results/{filename}"
    source_specification_path = tmp_path / "figure_source_data.yaml"
    source_specification_path.write_text(
        yaml.safe_dump(figure_specification, sort_keys=False), encoding="utf-8"
    )
    source_bundle = tmp_path / "source_bundle"
    export_manuscript_source_data(
        source_specification_path,
        source_bundle,
        repository_root=tmp_path,
    )
    figure_output = tmp_path / "figure_output"
    plot_economic_participation_figure(
        source_bundle,
        figure_output,
        formats=("svg", "pdf"),
    )
    assert (figure_output / "figure_6_economic_participation.svg").is_file()
    assert (figure_output / "figure_6_economic_participation.pdf").is_file()

    incomplete_directory = tmp_path / "incomplete_ledger"
    incomplete_directory.mkdir()
    incomplete_path = incomplete_directory / "episode_ledger.parquet"
    ledger.iloc[:-1].to_parquet(incomplete_path, index=False)
    (incomplete_directory / "ledger_manifest.json").write_text(
        json.dumps(
            {
                "analysis_id": specification.analysis_id,
                "analysis_role": specification.analysis_role,
                "specification_sha256": specification.sha256,
                "physical_ledger_contract": specification.physical_ledger_contract(),
                "physical_ledger_contract_sha256": specification.physical_ledger_contract_sha256,
                "scenario_count": specification.technical.expected_scenario_count,
                "scenario_set_sha256": specification.technical.scenario_set_sha256,
                "physical_input_sha256": verify_physical_input_hashes(specification),
                "technical_provenance": {
                    "manifest_sha256": (
                        specification.technical.technical_certificate_manifest_sha256
                    ),
                    "controller_config_sha256": specification.technical.controller_config_sha256,
                },
                "event_ledger_sha256": _sha256(incomplete_path),
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="protocol requires"):
        evaluate_economic_participation(
            specification_path,
            incomplete_path,
            tmp_path / "incomplete_output",
        )


def test_primary_boundary_rejects_an_assumed_nonzero_capacity_payment(tmp_path: Path) -> None:
    controller, certificate, certificate_manifest, costs, markets, register, evidence = (
        _write_economic_inputs(tmp_path)
    )
    specification_path = _write_specification(
        tmp_path,
        controller=controller,
        certificate=certificate,
        certificate_manifest=certificate_manifest,
        costs=costs,
        markets=markets,
        register=register,
        evidence=evidence,
    )
    document = yaml.safe_load(specification_path.read_text(encoding="utf-8"))
    document["evaluation"]["primary_capacity_payment_per_kw_year"] = 500
    specification_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="zero-payment reference"):
        load_economic_participation_specification(specification_path)


def test_replay_criteria_contains_frozen_reliability_and_confidence(tmp_path: Path) -> None:
    controller, certificate, certificate_manifest, costs, markets, register, evidence = (
        _write_economic_inputs(tmp_path)
    )
    specification_path = _write_specification(
        tmp_path,
        controller=controller,
        certificate=certificate,
        certificate_manifest=certificate_manifest,
        costs=costs,
        markets=markets,
        register=register,
        evidence=evidence,
    )
    criteria = _criteria_document(load_economic_participation_specification(specification_path))
    assert criteria["reliability_target"] == pytest.approx(0.95)
    assert criteria["confidence_level"] == pytest.approx(0.95)
    assert criteria["min_interval_delivery_ratio"] == pytest.approx(0.95)
