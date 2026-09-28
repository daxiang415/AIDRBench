from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
import yaml

import aidrbench.evaluation.economic_cost_robustness as robustness
from aidrbench.cli import build_parser
from aidrbench.data.splits import sha256_file
from aidrbench.economics.specification import (
    load_cost_parameter_grid,
    load_economic_participation_specification,
    load_market_archetypes,
)
from aidrbench.evaluation.economic_participation import _group_metrics, _stable_seed

_SPEC = "configs/economics/cost_robustness_v1.yaml"
_RISK = "risk_adjusted_break_even_capacity_payment_per_kw_year"


def _inputs() -> tuple[Any, Any, Any, Any, pd.DataFrame]:
    specification = robustness.load_cost_robustness_specification(_SPEC)
    economic = load_economic_participation_specification(specification.economic_specification)
    grid = load_cost_parameter_grid(economic.inputs.cost_parameter_grid)
    markets = load_market_archetypes(economic.inputs.market_archetypes).archetypes
    ledger = pd.read_csv("manuscript/source_data/nature_economic_v1/fig6_paired_event_ledger.csv")
    return specification, economic, grid, markets, ledger


@pytest.fixture(scope="module")
def tables() -> dict[str, pd.DataFrame]:
    return robustness.calculate_cost_robustness(*_inputs())


def test_cost_robustness_cli_and_explicit_post_hoc_scope() -> None:
    args = build_parser().parse_args([
        "economics", "cost-robustness", "--specification", _SPEC, "--output", "new-bundle"
    ])
    assert args.economics_command == "cost-robustness"
    specification = robustness.load_cost_robustness_specification(_SPEC)
    assert specification.analysis_role == "post_hoc_development_parameterized_sensitivity"
    assert specification.bootstrap_draw_counts == (200, 2000, 10000)


@pytest.mark.parametrize("changes", [
    {"delay_cost_multipliers": (0.0, float("nan"), 1.0)},
    {"delay_cost_multipliers": (-1.0, 1.0)},
    {"delay_cost_multipliers": ("unknown", 1.0)},
    {"schema_version": True},
    {"fixed_site_cost_multipliers": (0.0, 2.0)},
    {"fixed_site_cost_multipliers": (1.0, 1.0)},
    {"annual_event_counts": (51,)},
    {"annual_event_counts": (1, True, 50)},
    {"bootstrap_draw_counts": (99, 200)},
    {"bootstrap_draw_counts": (200, 200)},
    {"analysis_role": "independently_validated"},
    {"work_zero_tolerance_gpu_h": 0.0},
])
def test_cost_robustness_rejects_invalid_design(changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        replace(robustness.load_cost_robustness_specification(_SPEC), **changes)


def test_original_nine_economic_thresholds_reproduce(tables: dict[str, pd.DataFrame]) -> None:
    specification, economic, *_ = _inputs()
    result = robustness.reconcile_reference(
        tables["economic_cost_sensitivity.csv"],
        pd.read_csv(specification.reference_table), economic
    )
    assert len(result) == 9
    assert result["absolute_difference_per_kw_year"].max() < 1e-8
    assert len(tables["economic_cost_sensitivity.csv"]) == 1728
    assert len(tables["economic_bootstrap_stability.csv"]) == 27
    assert len(tables["economic_service_outcomes.csv"]) == 3


def test_reference_mismatch_is_not_silently_accepted(tables: dict[str, pd.DataFrame]) -> None:
    specification, economic, *_ = _inputs()
    reference = pd.read_csv(specification.reference_table)
    reference.loc[0, _RISK] += 0.01
    with pytest.raises(ValueError, match="does not reproduce"):
        robustness.reconcile_reference(tables["economic_cost_sensitivity.csv"], reference, economic)


def test_published_tables_reproduce_from_versioned_event_csv(
    tables: dict[str, pd.DataFrame],
) -> None:
    root = Path("manuscript/source_data/nature_economic_robustness_v1")
    for filename, calculated in tables.items():
        published = pd.read_csv(root / filename)
        pd.testing.assert_frame_equal(
            published, calculated, check_dtype=False, check_exact=False,
            rtol=1e-10, atol=1e-8,
        )


def test_fixed_site_contrast_equals_analytic_cost_per_offer(
    tables: dict[str, pd.DataFrame],
) -> None:
    frame = tables["economic_cost_sensitivity.csv"]
    keys = ["duration_h", "regime", "annual_event_count", "facility_site_scale_mw",
            "delay_cost_multiplier"]
    for _, group in frame.groupby(keys):
        group = group.sort_values("fixed_site_cost_multiplier")
        changes = group["unclipped_risk_threshold_per_kw_year"].diff().dropna().to_numpy()
        expected = (
            group["fixed_site_enablement_annual_cost"].diff()
            / group["scaled_accounting_candidate_reduction_kw"]
        ).dropna().to_numpy()
        np.testing.assert_allclose(changes, expected, atol=1e-9, rtol=1e-10)
        assert (group[_RISK].diff().dropna() >= -1e-9).all()


def test_delay_monotonicity_and_explicit_zero_floor(tables: dict[str, pd.DataFrame]) -> None:
    frame = tables["economic_cost_sensitivity.csv"]
    keys = ["duration_h", "regime", "annual_event_count", "facility_site_scale_mw",
            "fixed_site_cost_multiplier"]
    for _, group in frame.groupby(keys):
        assert (group.sort_values("delay_cost_multiplier")[_RISK].diff().dropna() >= -1e-9).all()
    np.testing.assert_allclose(
        frame[_RISK], frame["unclipped_risk_threshold_per_kw_year"].clip(lower=0.0)
    )
    zero_cost = frame[
        frame["regime"].eq("slack_backed") & frame["delay_cost_multiplier"].eq(0)
        & frame["fixed_site_cost_multiplier"].eq(0)
    ]
    assert zero_cost[_RISK].eq(0.0).all()
    assert (zero_cost["unclipped_risk_threshold_per_kw_year"] < 0.0).all()


def test_larger_draw_counts_preserve_original_paired_draws() -> None:
    _, economic, _, _, ledger = _inputs()
    group = ledger[ledger["duration_h"].eq(4)].copy()
    group["technical_failure_indicator"] = (~group["technical_success"]).astype(float)
    seed = _stable_seed(economic.evaluation.bootstrap_seed, (4, 0, 1.0, 50))
    _, original = _group_metrics(group, annual_event_count=50, draws=200, seed=seed)
    _, expanded = _group_metrics(group, annual_event_count=50, draws=2000, seed=seed)
    for metric in original:
        np.testing.assert_array_equal(original[metric], expanded[metric][:200])


def test_service_diagnostics_do_not_label_deferred_work_as_lost_revenue(
    tables: dict[str, pd.DataFrame],
) -> None:
    service = tables["economic_service_outcomes.csv"]
    assert service["scenario_count"].eq(100).all()
    assert service["incremental_missed_gpu_h_above_tolerance_count"].eq(0).all()
    assert service["incremental_terminal_backlog_gpu_h_above_tolerance_count"].eq(0).all()
    assert (service["mean_deferred_gpu_h"] > 0).all()
    assert service["opportunity_cost_interpretation"].eq(
        "conditional_exposure_not_observed_revenue_loss"
    ).all()


def test_fractional_offers_are_not_introduced() -> None:
    specification, economic, grid, markets, ledger = _inputs()
    ledger["offer_fraction_of_technical_ceiling"] = (
        ledger["offer_fraction_of_technical_ceiling"].astype(float)
    )
    ledger.loc[0, "offer_fraction_of_technical_ceiling"] = 0.5
    with pytest.raises(ValueError, match="uncertified fractional"):
        robustness.calculate_cost_robustness(specification, economic, grid, markets, ledger)


def test_export_has_verifiable_manifest_and_refuses_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    specification, economic, _, _, ledger = _inputs()
    local_ledger = tmp_path / "episode_ledger.parquet"
    ledger.to_parquet(local_ledger, index=False)
    local_manifest = local_ledger.with_name("ledger_manifest.json")
    manifest = {"physical_ledger_contract_sha256": economic.physical_ledger_contract_sha256}
    local_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    specification = replace(
        specification, ledger=str(local_ledger), ledger_sha256=sha256_file(local_ledger)
    )
    local_specification = tmp_path / "specification.yaml"
    local_specification.write_text(yaml.safe_dump(asdict(specification)), encoding="utf-8")
    # The existing ledger verifier has dedicated fail-closed integration tests.
    # Here isolate publication without requiring untracked production Parquet.
    monkeypatch.setattr(robustness, "_load_verified_ledger", lambda *_: (ledger, manifest))
    output = tmp_path / "bundle"
    summary = robustness.export_cost_robustness(local_specification, output)
    assert summary["table_count"] == 4
    published = json.loads((output / "source_data_manifest.json").read_text())
    assert published["locked_scenario_payloads_read"] is False
    assert published["original_figure6_tables_modified"] is False
    for table in published["tables"]:
        path = output / table["output"]
        assert sha256_file(path) == table["output_sha256"]
        frame = pd.read_csv(path)
        assert len(frame) == table["row_count"]
        assert list(frame.columns) == table["columns"]
    with pytest.raises(FileExistsError):
        robustness.export_cost_robustness(local_specification, output)
    local_ledger.write_bytes(b"modified input")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        robustness.export_cost_robustness(local_specification, tmp_path / "rejected")
    assert not (tmp_path / "rejected").exists()


def test_published_robustness_bundle_and_frozen_runtime_hashes() -> None:
    root = Path("manuscript/source_data/nature_economic_robustness_v1")
    manifest = json.loads((root / "source_data_manifest.json").read_text())
    assert manifest["analysis_role"] == "post_hoc_development_parameterized_sensitivity"
    assert manifest["paired_event_count"] == 300
    assert sum(table["row_count"] for table in manifest["tables"]) == 1767
    for table in manifest["tables"]:
        path = root / table["output"]
        frame = pd.read_csv(path)
        assert sha256_file(path) == table["output_sha256"]
        assert len(frame) == table["row_count"]
        assert list(frame.columns) == table["columns"]
    for path, expected in manifest["runtime_source_sha256"].items():
        # The archived calculation predates the additive GPU cost helpers.
        # Verify its exact runtime; numerical tests above separately require
        # today's implementation to reproduce every published table.
        assert sha256_file(root / "frozen_runtime" / path) == expected
    specification = robustness.load_cost_robustness_specification(_SPEC)
    assert manifest["specification"] == {"path": _SPEC, "sha256": sha256_file(Path(_SPEC))}
    assert manifest["bound_input_sha256"] == {
        specification.economic_specification: specification.economic_specification_sha256,
        specification.ledger: specification.ledger_sha256,
        specification.reference_table: specification.reference_table_sha256,
    }
    for path in (specification.economic_specification, specification.reference_table):
        assert sha256_file(Path(path)) == manifest["bound_input_sha256"][path]

    # A fresh checkout contains the hash-bound CSV publication, not the ignored
    # production Parquet. Verify its lineage and payload without making CI
    # depend on a research workstation. The production exporter still requires
    # and re-hashes the original Parquet and verifies its full ledger contract.
    economic_root = Path("manuscript/source_data/nature_economic_v1")
    economic_manifest = json.loads((economic_root / "source_data_manifest.json").read_text())
    ledger_table = next(
        table for table in economic_manifest["tables"]
        if table["table_id"] == "fig6_paired_event_ledger"
    )
    assert ledger_table["inputs"] == [{
        "labels": {}, "path": specification.ledger,
        "rows_read": manifest["paired_event_count"], "sha256": specification.ledger_sha256,
    }]
    ledger_csv = economic_root / ledger_table["output"]
    assert sha256_file(ledger_csv) == ledger_table["output_sha256"]
    ledger = pd.read_csv(ledger_csv)
    assert len(ledger) == ledger_table["row_count"] == manifest["paired_event_count"]
    assert list(ledger.columns) == ledger_table["columns"]
    economic = load_economic_participation_specification(specification.economic_specification)
    assert manifest["economic_input_sha256"] == robustness.verify_economic_input_hashes(economic)


def test_historical_supplementary_cost_tables_match_calculated_values(
    tables: dict[str, pd.DataFrame],
) -> None:
    # These ledgers belong to the archived 75% workload configuration. Do not
    # require its prices to reappear in the new five-configuration manuscript.
    supplement = Path(
        "manuscript/revisions/workload_composition_2026-09-09/"
        "before/supplementary_information.md"
    ).read_text()
    frame = tables["economic_cost_sensitivity.csv"]
    main = frame[
        frame["duration_h"].eq(4) & frame["annual_event_count"].eq(50)
        & frame["facility_site_scale_mw"].eq(1)
    ]
    labels = {
        "slack_backed": "Slack-backed", "reserved_headroom": "Reserved headroom",
        "throughput_displacing": "Throughput-displacing exposure",
    }
    for regime, label in labels.items():
        values = main[
            main["regime"].eq(regime) & main["fixed_site_cost_multiplier"].eq(1)
        ].sort_values("delay_cost_multiplier")[_RISK]
        row = "| " + label + " | " + " | ".join(f"{value:.2f}" for value in values) + " |"
        assert row in supplement
    for cost, group in main[main["regime"].eq("slack_backed")].groupby(
        "fixed_site_enablement_annual_cost"
    ):
        values = group.sort_values("delay_cost_multiplier")[_RISK]
        row = f"| {float(str(cost)):,.0f} | " + " | ".join(f"{v:.2f}" for v in values) + " |"
        assert row in supplement
    for (duration, regime), group in tables["economic_bootstrap_stability.csv"].groupby(
        ["duration_h", "regime"]
    ):
        values = group.sort_values("bootstrap_draws")[_RISK]
        row = (
            f"| {duration} | {labels[regime]} | "
            + " | ".join(f"{value:.2f}" for value in values) + " |"
        )
        assert row in supplement


def test_nominal_gap_percentages_state_the_correct_denominator() -> None:
    article = Path("manuscript/nature_communications_article.md").read_text()
    assert "overstated supported capacity by 47.3" not in article
    assert "overstated the q = 0.95 PI tolerance lower bound by 47.3" not in article
    # Preserve the historical denominator without requiring old results to be
    # repeated in a manuscript that now uses different workload configurations.
    bounds = pd.read_csv(
        "manuscript/source_data/nature_mainline_v1/fig1_fig2_pi_firm_boundaries.csv"
    )
    selected = bounds.loc[bounds["reliability_target"] == 0.95]
    gap = 100 * (
        selected["nominal_flexibility_kw"] - selected["perfect_information_firm_capacity_kw"]
    ) / selected["nominal_flexibility_kw"]
    assert round(float(gap.min()), 1) == 47.3
    assert round(float(gap.max()), 1) == 62.4
