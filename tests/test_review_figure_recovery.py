"""Check frozen-input refusal and actual plotted coordinates for portable drafts."""

from __future__ import annotations

import json
import runpy
from pathlib import Path
from typing import Any

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = {
    "figure6": ROOT / "results/exports/AIDRBench_Figure6_WebGPT_v2.zip",
    "s5": ROOT / "results/exports/AIDRBench_Supplementary_Figure_S5_WebGPT_v1.zip",
}


@pytest.fixture(scope="module")
def drawing() -> dict[str, Any]:
    return runpy.run_path(str(ROOT / "scripts/draw_review_figures.py"))


@pytest.fixture(scope="module")
def panels(drawing: dict[str, Any]) -> dict[str, Any]:
    return {kind: drawing["load_package"](path, kind)[0] for kind, path in PACKAGES.items()}


@pytest.mark.parametrize("kind", ["figure6", "s5"])
def test_changed_input_package_is_rejected_before_drawing(
    drawing: dict[str, Any], tmp_path: Path, kind: str
) -> None:
    changed = tmp_path / "changed.zip"
    changed.write_bytes(PACKAGES[kind].read_bytes() + b"unreviewed change")
    with pytest.raises(ValueError, match="package SHA-256 mismatch"):
        drawing["load_package"](changed, kind)


@pytest.mark.parametrize("fault", ["component_sum", "invented_duration"])
def test_semantic_guards_reject_wrong_scientific_coordinates(
    drawing: dict[str, Any], panels: dict[str, Any], fault: str
) -> None:
    econ = {p: frame.copy() for p, frame in panels["figure6"].items()}
    s5 = {p: frame.copy() for p, frame in panels["s5"].items()}
    if fault == "component_sum":
        econ["c"].loc[0, "contribution_per_kw_year"] += 1
        message = "signed component identity"
    else:
        s5["b"].loc[s5["b"].duration_h == 5, "perfect_information_firm_capacity_kw"] = 40
        message = "unevaluated S5 duration"
    with pytest.raises(ValueError, match=message):
        drawing["check_semantics"](econ, s5)


def _marked_pairs(axis: Any) -> list[tuple[float, float]]:
    pairs = []
    for line in axis.lines:
        if line.get_marker() in {"None", "", " "}:
            continue
        for x, y in zip(line.get_xdata(), line.get_ydata(), strict=True):
            if np.isfinite(x) and np.isfinite(y):
                pairs.append((float(x), float(y)))
    return sorted(pairs)


def test_actual_marks_and_row_trace_use_every_frozen_panel_row(
    drawing: dict[str, Any], panels: dict[str, Any]
) -> None:
    drawing["style"]()
    trace: list[dict[str, Any]] = []
    econ, s5 = panels["figure6"], panels["s5"]
    main = drawing["draw_economic"](econ, trace)
    supp = drawing["draw_s5"](s5, trace)
    risk, mean = drawing["RISK"], drawing["MEAN"]
    try:
        expected = sorted(zip(econ["a"].facility_site_scale_mw, econ["a"][risk], strict=True))
        np.testing.assert_allclose(_marked_pairs(main.axes[0]), expected, rtol=0, atol=0)
        drivers = [
            "annual_event_count",
            "driver_value",
            "effective_displaced_compute_value_per_gpu_h",
        ]
        for axis, regime, driver in zip(main.axes[1:4], drawing["REGIMES"], drivers, strict=True):
            frame = econ["b"].loc[econ["b"].regime == regime]
            expected = sorted(zip(frame[driver], frame[risk], strict=True))
            np.testing.assert_allclose(_marked_pairs(axis), expected, rtol=0, atol=0)
        durations = {2: 0, 4: 1, 8: 2}
        expected = sorted(
            (durations[row.duration_h], float(row[field]))
            for _, row in econ["d"].iterrows()
            for field in (mean, risk)
        )
        np.testing.assert_allclose(_marked_pairs(main.axes[-1]), expected, rtol=0, atol=0)
        # Signed stack heights recover all nonzero accounting entries without clipping or abs().
        expected_heights = sorted(v for v in econ["c"].contribution_per_kw_year if v != 0)
        # Matplotlib reconstructs rectangle heights from cumulative endpoints;
        # permit only floating-point subtraction error (observed < 3e-14).
        np.testing.assert_allclose(
            sorted(p.get_height() for p in main.axes[4].patches),
            expected_heights,
            rtol=0,
            atol=1e-12,
        )
        # Curves preserve every hourly vertex; missing durations remain absent from numeric marks.
        actual = sorted(
            (float(x), float(y))
            for line in supp.axes[0].lines
            for x, y in zip(line.get_xdata(), line.get_ydata(), strict=True)
        )
        expected = sorted(zip(s5["a"].elapsed_day, s5["a"].net_community_load_kw, strict=True))
        np.testing.assert_allclose(actual, expected, rtol=0, atol=0)
        valid = s5["b"].loc[s5["b"].duration_grid_status == "evaluated"]
        expected = sorted(
            zip(valid.duration_h, valid.perfect_information_firm_capacity_kw, strict=True)
        )
        np.testing.assert_allclose(_marked_pairs(supp.axes[1]), expected, rtol=0, atol=0)
        expected = sorted(
            float(row[field])
            for _, row in s5["c"].iterrows()
            for field in ("empirical_success_fraction", "wilson_lower_confidence_bound")
        )
        np.testing.assert_allclose(
            sorted(y for _, y in _marked_pairs(supp.axes[2])), expected, rtol=0, atol=0
        )
        np.testing.assert_allclose(
            sorted(x for x, _ in _marked_pairs(supp.axes[3])),
            sorted(s5["d"].simultaneous_feasible_pv_hosting_kw),
            rtol=0,
            atol=0,
        )
        assert len(trace) == 628
        assert len({(r["figure"], r["panel"], r["csv_line"]) for r in trace}) == 628
        for kind, data in panels.items():
            for panel, frame in data.items():
                records = [r for r in trace if r["figure"] == kind and r["panel"] == panel]
                assert {r["csv_line"] for r in records} == set(range(2, len(frame) + 2))
    finally:
        drawing["plt"].close(main)
        drawing["plt"].close(supp)


@pytest.mark.parametrize("fault", ["changed_pdf", "formal_status"])
def test_manuscript_refuses_changed_or_mislabelled_draft(tmp_path: Path, fault: str) -> None:
    import hashlib

    validator = runpy.run_path(str(ROOT / "scripts/review_figure_inputs.py"))[
        "validated_review_pdf"
    ]
    pdf = tmp_path / "figure6_local_review.pdf"
    pdf.write_bytes(b"fixture bytes for hash validation")
    manifest = {
        "status": "local_review_draft_only",
        "formal_artwork_route": "web_gpt_required_by_user",
        "figures": {
            "figure6": {"output_sha256": {pdf.name: hashlib.sha256(pdf.read_bytes()).hexdigest()}}
        },
    }
    if fault == "changed_pdf":
        pdf.write_bytes(b"changed")
    else:
        manifest["status"] = "formal_artwork"
    (tmp_path / "review_manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        validator(tmp_path, "figure6", tmp_path)


def test_duration_annotation_guard_accepts_spacing_and_rejects_v4_collision(
    drawing: dict[str, Any], panels: dict[str, Any]
) -> None:
    drawing["style"]()
    fig = drawing["draw_economic"](panels["figure6"], [])
    try:
        fig.canvas.draw()
        assert drawing["check_scope_annotations"](fig, fig.canvas.get_renderer()) == 3
        axis = fig.axes[-1]
        # Recreate the independently observed v4 defect using the real data and artists.
        axis.set_ylim(0, 920)
        for label in axis.texts:
            if label.get_gid() == "duration_scope_annotation":
                label.set_transform(axis.transData)
                label.set_y(890)
        fig.canvas.draw()
        with pytest.raises(ValueError, match="duration scope annotation overlaps plotted data"):
            drawing["check_scope_annotations"](fig, fig.canvas.get_renderer())
    finally:
        drawing["plt"].close(fig)


def test_scope_guard_rejects_reviewed_diamond_clearance_counterexample(
    drawing: dict[str, Any], panels: dict[str, Any]
) -> None:
    drawing["style"]()
    fig = drawing["draw_economic"](panels["figure6"], [])
    try:
        axis = fig.axes[-1]
        highest = max(max(line.get_ydata()) for line in axis.lines)
        x, y = axis.transData.transform((2, highest))
        label = axis.texts[-1]
        label.set_transform(drawing["matplotlib"].transforms.IdentityTransform())
        label.set_position((x, y + 4.8))
        label.set_va("bottom")
        fig.canvas.draw()
        # Reviewer A's actual-artist counterexample: the v5 half-size approximation
        # accepted 4.8 pixels, although the diamond's ink had less than 1 pt clearance.
        assert label.get_window_extent(fig.canvas.get_renderer()).y0 - y == pytest.approx(4.8)
        with pytest.raises(ValueError, match="duration scope annotation overlaps plotted data"):
            drawing["check_scope_annotations"](fig, fig.canvas.get_renderer())
    finally:
        drawing["plt"].close(fig)
