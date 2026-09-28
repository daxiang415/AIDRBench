from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from aidrbench.evaluation.economic_figures import plot_economic_participation_figure


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frame_rows() -> dict[str, pd.DataFrame]:
    regimes = ("slack_backed", "reserved_headroom", "throughput_displacing")
    boundary = pd.DataFrame(
        [
            {
                "analysis_role": "development_parameterized_screening",
                "annualization_scope": "independent_fresh_events_not_continuous_programme",
                "performance_payment_basis": (
                    "interval_delivery_capped_at_scaled_accounting_offered_kW"
                ),
                "reserved_capacity_basis": "abstract_pcc_side_kw_sensitivity",
                "regime": regime,
                "duration_h": 4,
                "reliability_target": 0.95,
                "technical_capacity_ceiling_kw": 40.0,
                "candidate_reduction_kw": 40.0,
                "technical_qualification": "independently_certified_ceiling",
                "break_even_capacity_payment_per_kw_year": mean,
                "risk_adjusted_break_even_capacity_payment_per_kw_year": risk,
            }
            for regime, mean, risk in (
                ("slack_backed", 620.0, 650.0),
                ("reserved_headroom", 720.0, 760.0),
                ("throughput_displacing", 780.0, 820.0),
            )
        ]
    )
    sensitivity_rows: list[dict[str, object]] = []
    for regime, driver_id, label, displays, values in (
        (
            "slack_backed",
            "annual_event_count",
            "Annual events",
            ("1/yr", "12/yr", "50/yr", "250/yr"),
            (800.0, 720.0, 650.0, 600.0),
        ),
        (
            "reserved_headroom",
            "economic_life_years",
            "Economic life",
            ("3 yr", "4 yr", "5 yr", "6 yr"),
            (900.0, 820.0, 760.0, 720.0),
        ),
        (
            "throughput_displacing",
            "opportunity_exposure_alpha",
            "Displaced-work exposure",
            ("alpha 0.1", "alpha 0.25", "alpha 0.5", "alpha 1.0"),
            (650.0, 710.0, 820.0, 980.0),
        ),
    ):
        driver_values = (1.0, 12.0, 50.0, 250.0)
        driver_unit = "fresh_events_per_year"
        if driver_id == "economic_life_years":
            driver_values = (3.0, 4.0, 5.0, 6.0)
            driver_unit = "years"
        elif driver_id == "opportunity_exposure_alpha":
            driver_values = (0.1, 0.25, 0.5, 1.0)
            driver_unit = "fraction"
        for position, (display, value, driver_value) in enumerate(
            zip(displays, values, driver_values, strict=True)
        ):
            sensitivity_rows.append(
                {
                    "analysis_role": "development_parameterized_screening",
                    "annualization_scope": ("independent_fresh_events_not_continuous_programme"),
                    "performance_payment_basis": (
                        "interval_delivery_capped_at_scaled_accounting_offered_kW"
                    ),
                    "reserved_capacity_basis": "abstract_pcc_side_kw_sensitivity",
                    "regime": regime,
                    "driver_id": driver_id,
                    "driver_label": label,
                    "driver_value": driver_value,
                    "driver_unit": driver_unit,
                    "driver_value_display": display,
                    "driver_normalized_position": position / (len(values) - 1),
                    "duration_h": 4,
                    "reliability_target": 0.95,
                    "technical_capacity_ceiling_kw": 40.0,
                    "candidate_reduction_kw": 40.0,
                    "technical_qualification": "independently_certified_ceiling",
                    "risk_adjusted_break_even_capacity_payment_per_kw_year": value,
                }
            )
    decomposition_rows: list[dict[str, object]] = []
    decomposition = {
        "slack_backed": {
            "enablement_cost": ("Enablement", 630.0),
            "delay_cost": ("Delay", 30.0),
            "energy_credit_or_cost": ("Net energy change", 5.0),
            "performance_credit": ("Performance credit", -15.0),
        },
        "reserved_headroom": {
            "enablement_cost": ("Enablement", 630.0),
            "reserve_annual_cost": ("Reserved headroom", 120.0),
            "delay_cost": ("Delay", 30.0),
            "energy_credit_or_cost": ("Net energy change", -5.0),
            "performance_credit": ("Performance credit", -15.0),
        },
        "throughput_displacing": {
            "enablement_cost": ("Enablement", 630.0),
            "opportunity_cost": ("Displaced compute", 180.0),
            "delay_cost": ("Delay", 30.0),
            "energy_credit_or_cost": ("Net energy change", -5.0),
            "performance_credit": ("Performance credit", -15.0),
        },
    }
    totals = {"slack_backed": 650.0, "reserved_headroom": 760.0, "throughput_displacing": 820.0}
    for regime, components in decomposition.items():
        for component_id, (label, contribution) in components.items():
            decomposition_rows.append(
                {
                    "analysis_role": "development_parameterized_screening",
                    "annualization_scope": ("independent_fresh_events_not_continuous_programme"),
                    "performance_payment_basis": (
                        "interval_delivery_capped_at_scaled_accounting_offered_kW"
                    ),
                    "reserved_capacity_basis": "abstract_pcc_side_kw_sensitivity",
                    "regime": regime,
                    "component_id": component_id,
                    "component_label": label,
                    "contribution_per_kw_year": contribution,
                    "risk_adjusted_break_even_capacity_payment_per_kw_year": totals[regime],
                    "technical_capacity_ceiling_kw": 40.0,
                    "candidate_reduction_kw": 40.0,
                    "technical_qualification": "independently_certified_ceiling",
                }
            )
    duration_rows: list[dict[str, object]] = []
    technical_by_duration = {2: 46.0, 4: 40.0, 8: 37.0}
    mean_by_regime = {
        "slack_backed": (590.0, 620.0, 680.0),
        "reserved_headroom": (690.0, 720.0, 790.0),
        "throughput_displacing": (740.0, 780.0, 880.0),
    }
    risk_by_regime = {
        "slack_backed": (620.0, 650.0, 720.0),
        "reserved_headroom": (730.0, 760.0, 840.0),
        "throughput_displacing": (780.0, 820.0, 930.0),
    }
    for regime in regimes:
        for duration, technical in technical_by_duration.items():
            index = tuple(technical_by_duration).index(duration)
            duration_rows.append(
                {
                    "analysis_role": "development_parameterized_screening",
                    "annualization_scope": ("independent_fresh_events_not_continuous_programme"),
                    "performance_payment_basis": (
                        "interval_delivery_capped_at_scaled_accounting_offered_kW"
                    ),
                    "reserved_capacity_basis": "abstract_pcc_side_kw_sensitivity",
                    "regime": regime,
                    "duration_h": duration,
                    "technical_capacity_ceiling_kw": technical,
                    "candidate_reduction_kw": technical,
                    "technical_qualification": "independently_certified_ceiling",
                    "break_even_capacity_payment_per_kw_year": mean_by_regime[regime][index],
                    "risk_adjusted_break_even_capacity_payment_per_kw_year": risk_by_regime[regime][
                        index
                    ],
                }
            )
    return {
        "fig6_technical_economic_boundary": boundary,
        "fig6_mechanism_sensitivity": pd.DataFrame(sensitivity_rows),
        "fig6_break_even_decomposition": pd.DataFrame(decomposition_rows),
        "fig6_duration_break_even": pd.DataFrame(duration_rows),
    }


def _write_source_bundle(directory: Path) -> dict[str, Path]:
    directory.mkdir()
    outputs: dict[str, Path] = {}
    manifest_tables: list[dict[str, object]] = []
    for table_id, frame in _frame_rows().items():
        output = f"{table_id}.csv"
        path = directory / output
        frame.to_csv(path, index=False)
        outputs[table_id] = path
        manifest_tables.append(
            {
                "table_id": table_id,
                "output": output,
                "output_sha256": _sha256(path),
                "columns": list(frame.columns),
            }
        )
    (directory / "source_data_manifest.json").write_text(
        json.dumps({"tables": manifest_tables}), encoding="utf-8"
    )
    return outputs


def test_economic_figure_exports_exact_panel_data(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source_paths = _write_source_bundle(source)
    output = tmp_path / "figure"
    summary = plot_economic_participation_figure(
        source,
        output,
        formats=("svg", "pdf", "png"),
    )
    assert summary["final_publish"] == "atomic_directory_rename"
    assert (output / "figure_6_economic_participation.svg").is_file()
    assert (output / "figure_6_economic_participation.pdf").is_file()
    assert (output / "figure_6_economic_participation.png").is_file()
    assert Path(str(summary["manifest"])).is_file()
    panel_sources = {
        "a": "fig6_technical_economic_boundary",
        "b": "fig6_mechanism_sensitivity",
        "c": "fig6_break_even_decomposition",
        "d": "fig6_duration_break_even",
    }
    for panel, table_id in panel_sources.items():
        assert (output / f"figure_6_panel_{panel}.csv").read_bytes() == source_paths[
            table_id
        ].read_bytes()
    with pytest.raises(FileExistsError, match="already exists"):
        plot_economic_participation_figure(source, output, formats=("png",))


def test_economic_figure_fails_closed_on_tampered_source_data(tmp_path: Path) -> None:
    source = tmp_path / "source"
    paths = _write_source_bundle(source)
    paths["fig6_mechanism_sensitivity"].write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        plot_economic_participation_figure(source, tmp_path / "figure", formats=("png",))
