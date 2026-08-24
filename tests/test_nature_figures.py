from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from aidrbench.evaluation.nature_figures_reference import (
    plot_nature_mainline_figure2,
    plot_nature_mainline_figures,
)

_DURATIONS = (1, 2, 3, 4, 6, 8)
_NOTICES = (0, 2, 6)
_RELIABILITIES = (0.90, 0.95, 0.99)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_repository_web_preview_manifests_match_tracked_pngs() -> None:
    """Keep the GitHub preview bundle consistent after a figure is revised."""

    root = Path(__file__).resolve().parents[1] / "docs/figures/nature_mainline_v1"
    bundle = json.loads((root / "nature_mainline_figure_manifest.json").read_text())

    for figure in bundle["figures"]:
        per_figure = json.loads((root / figure["manifest"]).read_text())
        assert figure["outputs"] == per_figure["outputs"]
        png = next(output for output in figure["outputs"] if output["format"] == "png")
        png_path = root / png["path"]
        assert png_path.stat().st_size == png["bytes"]
        assert _sha256(png_path) == png["sha256"]


def _write_table(
    root: Path,
    table_id: str,
    records: list[dict[str, object]],
) -> dict[str, object]:
    frame = pd.DataFrame.from_records(records)
    output = f"{table_id}.csv"
    path = root / output
    frame.to_csv(path, index=False)
    return {
        "table_id": table_id,
        "output": output,
        "output_sha256": _sha256(path),
        "columns": frame.columns.tolist(),
    }


def _pi_records() -> list[dict[str, object]]:
    return [
        {
            "duration_h": duration,
            "reliability_target": reliability,
            "perfect_information_firm_capacity_kw": (
                59.0 - 2.2 * duration - 75.0 * (reliability - 0.90)
            ),
            "nominal_flexibility_kw": 100.0,
            "physical_gap_kw": (41.0 + 2.2 * duration + 75.0 * (reliability - 0.90)),
        }
        for reliability in _RELIABILITIES
        for duration in _DURATIONS
    ]


def _certificate_records(*, ood: bool) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for reliability in _RELIABILITIES:
        for notice in _NOTICES:
            for duration in _DURATIONS:
                candidate = 61.0 - 2.5 * duration - 80.0 * (reliability - 0.90)
                certified = not ood and duration > 1 and not (reliability == 0.99 and duration < 4)
                bound = (
                    reliability + 0.02 if certified else reliability - (0.015 if not ood else 0.12)
                )
                records.append(
                    {
                        "duration_h": duration,
                        "notice_h": notice,
                        "reliability_target": reliability,
                        "candidate_reduction_kw": candidate,
                        "wilson_lower_confidence_bound": bound,
                        "certified": certified,
                    }
                )
    return records


def _exhaustion_event_records() -> list[dict[str, object]]:
    return [
        {
            "evaluation_split": split,
            "duration_h": duration,
            "recovery_gap_h": gap,
            "event_ordinal": event,
            "mean_paired_compute_debt_increment_kwh": (
                (event - 1) * duration * 45.0 + (15.0 if split == "validation" else 0.0)
            ),
            "fixed_commitment_residual_flexibility_ratio": 1.0
            - 0.0005 * (event - 1) * duration / 4.0,
        }
        for split in ("development", "validation")
        for duration in (4, 8)
        for gap in (2, 4, 8, 12, 24)
        for event in (1, 2, 3, 4)
    ]


def _joint_records() -> list[dict[str, object]]:
    return [
        {
            "evaluation_split": split,
            "duration_h": duration,
            "recovery_gap_h": gap,
            "joint_episode_success_fraction": max(
                0.0,
                min(
                    0.98,
                    0.90
                    - 0.035 * (duration - 4)
                    - 0.006 * abs(gap - 8)
                    + (0.02 if split == "validation" else 0.0),
                ),
            ),
        }
        for split in ("development", "validation")
        for duration in (4, 8)
        for gap in (2, 4, 8, 12, 24)
    ]


def _hosting_summary_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for split in ("development", "validation"):
        split_offset = 40.0 if split == "validation" else 0.0
        for pv in (False, True):
            for bess in (False, True):
                for operation in ("rigid", "flexible"):
                    rigid = 300.0 + 80.0 * pv + 55.0 * bess + split_offset
                    mean = rigid + (
                        285.0 + 45.0 * pv - 35.0 * bess if operation == "flexible" else 0.0
                    )
                    records.append(
                        {
                            "evaluation_split": split,
                            "dc_operation": operation,
                            "pv_enabled": pv,
                            "bess_enabled": bess,
                            "mean_scenario_hosting_dc_peak_kw": mean,
                            "q05_scenario_hosting_dc_peak_kw": mean - 35.0,
                            "q95_scenario_hosting_dc_peak_kw": mean + 40.0,
                        }
                    )
    return records


def _hosting_contrast_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for split in ("development", "validation"):
        offset = 18.0 if split == "validation" else 0.0
        for pv in (False, True):
            for bess in (False, True):
                estimate = 280.0 + offset + 40.0 * pv - 35.0 * bess
                records.append(
                    {
                        "evaluation_split": split,
                        "contrast": "AI_HOSTING_GAIN",
                        "conditioning_level": f"pv={pv},bess={bess}",
                        "estimate_mean_kw": estimate,
                        "simultaneous_ci_lower_kw": estimate - 12.0,
                        "simultaneous_ci_upper_kw": estimate + 12.0,
                        "equivalence_margin_kw": 0.0,
                    }
                )
        for contrast, values in (
            ("AI_BESS_INTERACTION", (-50.0, -75.0)),
            ("AI_PV_INTERACTION", (48.0, 9.0)),
        ):
            for level, estimate in zip(("False", "True"), values, strict=True):
                estimate += 2.0 if split == "validation" else 0.0
                records.append(
                    {
                        "evaluation_split": split,
                        "contrast": contrast,
                        "conditioning_level": level,
                        "estimate_mean_kw": estimate,
                        "simultaneous_ci_lower_kw": estimate - 7.0,
                        "simultaneous_ci_upper_kw": estimate + 7.0,
                        "equivalence_margin_kw": 10.0,
                    }
                )
    return records


def _pv_hosting_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for split in ("development", "validation"):
        split_offset = 20.0 if split == "validation" else 0.0
        for scale in (0.5, 1.0, 2.0, 3.0):
            for operation in ("rigid", "flexible"):
                for bess in (False, True):
                    firm = not (scale >= 2.0 and operation == "rigid" and not bess)
                    value = (
                        300.0
                        + 175.0 * scale
                        + 55.0 * (operation == "flexible")
                        + 45.0 * bess
                        + split_offset
                    )
                    records.append(
                        {
                            "evaluation_split": split,
                            "analysis_variant": "headline_pv_hosting_envelope",
                            "dc_operation": operation,
                            "bess_enabled": bess,
                            "dc_scale_of_reference_mix": scale,
                            "target_dc_peak_kw": 201.0 * scale,
                            "all_scenarios_feasible": firm,
                            "feasible_scenario_count": 100 if firm else 88,
                            "simultaneous_feasible_pv_hosting_kw": value if firm else float("nan"),
                            "minimum_scenario_pv_hosting_kw": value,
                        }
                    )
    return records


def _pv_hosting_gain_records() -> list[dict[str, object]]:
    return [
        {
            "evaluation_split": split,
            "conditioning_level": str(bess),
            "estimate_mean": 48.0 - 5.0 * bess + (2.0 if split == "validation" else 0.0),
            "simultaneous_ci_lower": 40.0 - 5.0 * bess,
            "simultaneous_ci_upper": 56.0 - 5.0 * bess,
        }
        for split in ("development", "validation")
        for bess in (False, True)
    ]


def _pv_operation_contrast_records() -> list[dict[str, object]]:
    values = {
        "total_pv_curtailed_kwh": (-190.0, -90.0),
        "pv_utilisation_fraction": (0.0075, 0.0035),
        "total_grid_import_kwh": (-345.0, -260.0),
    }
    return [
        {
            "evaluation_split": split,
            "conditioning_level": str(bess),
            "metric": metric,
            "estimate_mean": estimate
            + (5.0 if split == "validation" and abs(estimate) > 1 else 0.0),
            "simultaneous_ci_lower": estimate - abs(estimate) * 0.25 - 0.001,
            "simultaneous_ci_upper": estimate + abs(estimate) * 0.25 + 0.001,
        }
        for split in ("development", "validation")
        for metric, estimates in values.items()
        for bess, estimate in zip((False, True), estimates, strict=True)
    ]


def _write_bundle(root: Path) -> None:
    root.mkdir()
    records: list[dict[str, object]] = []
    records.append(_write_table(root, "fig1_fig2_pi_firm_boundaries", _pi_records()))
    records.append(
        _write_table(
            root,
            "fig1_calibration_run_means",
            [
                {
                    "mode": mode,
                    "gpu_count": gpu_count,
                    "repeat": repeat,
                    "gpu_index": gpu_index,
                    "mean_power_w": 75.0 + 32.0 * (mode == "training") + 6.0 * gpu_count + repeat,
                }
                for mode in ("training", "offline_inference")
                for gpu_count in (1, 4)
                for repeat in (1, 2, 3)
                for gpu_index in range(gpu_count)
            ],
        )
    )
    records.append(
        _write_table(
            root,
            "fig2_restricted_na_surface",
            [
                {
                    "duration_h": duration,
                    "notice_h": notice,
                    "ensemble_success_fraction_target": 0.95,
                    "non_anticipative_capacity_kw": 58.0 - 2.0 * duration,
                }
                for notice in _NOTICES
                for duration in _DURATIONS
            ],
        )
    )
    records.append(
        _write_table(
            root,
            "fig2_notice_mechanism_diagnostics",
            [
                {
                    "duration_h": duration,
                    "notice_h": notice,
                    "eligible_pre_execution_work_gpu_h_mean": 0.0 if notice == 0 else 1800.0,
                    "pre_event_spare_capacity_gpu_h_mean": 0.0 if notice == 0 else 130.0,
                    "pi_notice_gain_kw": 0.0,
                    "na_notice_gain_kw": 0.0,
                }
                for duration in (4, 8)
                for notice in (0, 6)
            ],
        )
    )
    records.append(
        _write_table(
            root,
            "fig2_fig5_locked_id_certificates",
            _certificate_records(ood=False),
        )
    )
    records.append(
        _write_table(
            root,
            "fig5_locked_ood_certificates",
            _certificate_records(ood=True),
        )
    )
    records.append(_write_table(root, "fig3_exhaustion_event_summary", _exhaustion_event_records()))
    records.append(_write_table(root, "fig3_exhaustion_joint_episode_summary", _joint_records()))
    records.append(_write_table(root, "fig4_hosting_capacity_summary", _hosting_summary_records()))
    records.append(_write_table(root, "fig4_hosting_paired_contrasts", _hosting_contrast_records()))
    records.append(_write_table(root, "fig4_pv_hosting_summary", _pv_hosting_records()))
    records.append(
        _write_table(root, "fig4_pv_hosting_contrasts", _pv_hosting_gain_records())
    )
    records.append(
        _write_table(
            root,
            "fig4_pv_operation_contrasts",
            _pv_operation_contrast_records(),
        )
    )
    records.append(
        _write_table(
            root,
            "fig5_power_case_sensitivity",
            [
                {
                    "power_case": case,
                    "duration_h": duration,
                    "reliability_target": 0.95,
                    "perfect_information_firm_capacity_kw": 52.0 - 1.7 * duration + shift,
                }
                for case, shift in (("lower", -5.0), ("nominal", 0.0), ("upper", 5.0))
                for duration in _DURATIONS
            ],
        )
    )
    records.append(
        _write_table(
            root,
            "fig5_workload_sensitivity",
            [
                {
                    "workload_case": case,
                    "duration_h": duration,
                    "firm_capacity_delta_from_reference_kw": shift,
                }
                for case, shift in (
                    ("reference", 0.0),
                    ("flexible_arrival_low", -9.0),
                    ("flexible_arrival_high", 18.0),
                    ("deadline_tight", 0.0),
                    ("deadline_loose", 0.0),
                )
                for duration in (4, 8)
            ],
        )
    )
    records.append(
        _write_table(
            root,
            "fig5_success_criteria_sensitivity",
            [
                {
                    "criteria_case": case,
                    "duration_h": duration,
                    "perfect_information_firm_capacity_kw": 41.0 + shift - 0.7 * (duration - 4),
                }
                for case, shift in (
                    ("reference", 0.0),
                    ("delivery_090", 2.2),
                    ("delivery_098", -1.2),
                    ("rebound_010", 0.0),
                    ("window_relief_075", 0.0),
                )
                for duration in (4, 8)
            ],
        )
    )
    records.append(
        _write_table(
            root,
            "fig5_infrastructure_sensitivity",
            [
                {
                    "infrastructure_case": case,
                    "duration_h": duration,
                    "firm_capacity_delta_from_reference_kw": shift,
                }
                for case, shift in (
                    ("reference", 0.0),
                    ("pue_low", -3.3),
                    ("pue_high", 3.3),
                    ("node_overhead_lower", 0.0),
                    ("node_overhead_upper", 0.0),
                )
                for duration in (4, 8)
            ],
        )
    )
    (root / "source_data_manifest.json").write_text(
        json.dumps({"tables": records}),
        encoding="utf-8",
    )


def test_plot_all_nature_mainline_figures_write_editable_svg(tmp_path: Path) -> None:
    source_data = tmp_path / "source_data"
    _write_bundle(source_data)

    summary = plot_nature_mainline_figures(
        source_data,
        tmp_path / "figures",
        formats=("svg",),
    )

    assert summary["figure_count"] == 5
    for record in summary["figures"]:
        svg_path = Path(str(record["outputs"][0]["path"]))
        assert svg_path.stat().st_size > 10_000
        assert "<text" in svg_path.read_text(encoding="utf-8")
        figure_manifest = json.loads(Path(str(record["manifest"])).read_text())
        assert figure_manifest["minimum_configured_font_pt"] >= 6.5
        assert figure_manifest["source_data_manifest_sha256"] == _sha256(
            source_data / "source_data_manifest.json"
        )

    replay_summary = plot_nature_mainline_figures(
        source_data,
        tmp_path / "figures_replay",
        formats=("svg",),
    )
    assert (
        Path(str(summary["manifest"])).read_bytes()
        == Path(str(replay_summary["manifest"])).read_bytes()
    )
    for record, replay_record in zip(summary["figures"], replay_summary["figures"], strict=True):
        assert (
            Path(str(record["manifest"])).read_bytes()
            == Path(str(replay_record["manifest"])).read_bytes()
        )


def test_plot_nature_mainline_figure2_rejects_source_hash_mismatch(
    tmp_path: Path,
) -> None:
    source_data = tmp_path / "source_data"
    _write_bundle(source_data)
    with (source_data / "fig2_notice_mechanism_diagnostics.csv").open("a") as handle:
        handle.write("tampered\n")

    with pytest.raises(ValueError, match="source-data hash mismatch"):
        plot_nature_mainline_figure2(
            source_data,
            tmp_path / "figures",
            formats=("svg",),
        )


def test_plot_nature_mainline_figure2_writes_all_submission_formats(
    tmp_path: Path,
) -> None:
    source_data = tmp_path / "source_data"
    _write_bundle(source_data)

    result = plot_nature_mainline_figure2(
        source_data,
        tmp_path / "figures",
        formats=("svg", "pdf", "tiff", "png"),
    )

    outputs = {str(item["format"]): Path(str(item["path"])) for item in result["outputs"]}
    assert set(outputs) == {"svg", "pdf", "tiff", "png"}
    assert all(path.stat().st_size > 10_000 for path in outputs.values())
    assert outputs["tiff"].stat().st_size < 10_000_000

    replay = plot_nature_mainline_figure2(
        source_data,
        tmp_path / "figures_replay",
        formats=("svg", "pdf", "tiff", "png"),
    )
    replay_outputs = {str(item["format"]): Path(str(item["path"])) for item in replay["outputs"]}
    assert {extension: _sha256(path) for extension, path in outputs.items()} == {
        extension: _sha256(path) for extension, path in replay_outputs.items()
    }
    assert Path(str(result["manifest"])).read_bytes() == Path(str(replay["manifest"])).read_bytes()
