"""Draw reproducible local review drafts; formal artwork remains Web-GPT-only.

Standalone: uses only the supplied original ZIPs and scientific Python packages.
It never imports AIDRBench, replays experiments, or edits input data.
"""

# ruff: noqa: E402
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import io
import json
import os
import platform
import sys
import tempfile
import zipfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "aidrbench-review-mpl"))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.markers import MarkerStyle
from matplotlib.patches import Rectangle
from matplotlib.text import Text

PACKAGE_HASHES = {
    "figure6": "9ae8b2812cff57cd94c3f00e805a392ada81ef73d65a3c559fe93428ad4f5cb2",
    "s5": "3f691c45d4b6a3e6c26e804e547062b984ae4fa239183ab9719d8779768ae4c9",
}
REGIMES = ("slack_backed", "reserved_headroom", "throughput_displacing")
LABELS = ("Slack-backed", "Reserved headroom", "Throughput-displacing")
SHORT = ("Slack", "Reserved", "Displaced")
ZONES = ("3A", "3C", "5A")
COLORS = ("#3D9B8F", "#776FA3", "#D5634E")
INK, GREY, GRID = "#24313D", "#75808A", "#DCE2E6"
RISK = "risk_adjusted_break_even_capacity_payment_per_kw_year"
MEAN = "break_even_capacity_payment_excluding_fixed_site_per_kw_year"
WIDTH_MM = 183.0
PANELS = {
    "figure6": dict(
        zip(
            "abcd",
            (
                "fig6_fixed_site_overlay_scale_sensitivity.csv",
                "fig6_mechanism_sensitivity.csv",
                "fig6_break_even_decomposition.csv",
                "fig6_duration_break_even.csv",
            ),
            strict=True,
        )
    ),
    "s5": {p: f"figure_s5_panel_{p}.csv" for p in "abcd"},
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_package(path: Path, kind: str) -> tuple[dict[str, pd.DataFrame], dict]:
    """Verify all frozen inputs before returning any panel to a renderer."""
    payload = path.read_bytes()
    if sha(payload) != PACKAGE_HASHES[kind]:
        raise ValueError(f"{kind}: original package SHA-256 mismatch")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = archive.namelist()
        if len(set(names)) != len(names) or archive.testzip() is not None:
            raise ValueError("duplicate archive paths or failed CRC")
        checks = archive.read("CHECKSUMS_SHA256.txt").decode().splitlines()
        for line in checks:
            if not line.strip():
                continue
            digest, name = line.split(maxsplit=1)
            name = name.lstrip("*").removeprefix("./")
            if sha(archive.read(name)) != digest:
                raise ValueError(f"internal checksum mismatch: {name}")
        manifest_name = (
            "source_data_manifest.json" if kind == "figure6" else "s5_panel_data_manifest.json"
        )
        manifest_bytes = archive.read("source_data/" + manifest_name)
        manifest = json.loads(manifest_bytes)
        if kind == "figure6" and manifest["software"]["git"]["working_tree_dirty"] is not False:
            raise ValueError("economic Source Data was not generated from a clean source")
        records = manifest["tables" if kind == "figure6" else "panels"]
        frames, verified = {}, []
        for record in records:
            data = archive.read("source_data/" + record["output"])
            frame = pd.read_csv(io.BytesIO(data))
            if (
                sha(data) != record["output_sha256"]
                or len(frame) != record["row_count"]
                or list(frame.columns) != record["columns"]
            ):
                raise ValueError(f"CSV integrity mismatch: {record['output']}")
            verified.append({"file": record["output"], "sha256": sha(data), "rows": len(frame)})
            for panel, filename in PANELS[kind].items():
                if record["output"] == filename:
                    assigned = record["panels"] if kind == "figure6" else [record["panel"]]
                    if assigned != [panel]:
                        raise ValueError(f"wrong panel assignment: {filename}")
                    frames[panel] = frame
        if set(frames) != set("abcd"):
            raise ValueError("missing required panel")
        return frames, {
            "package_sha256": sha(payload),
            "internal_checksums": len(checks),
            "manifest_sha256": sha(manifest_bytes),
            "verified_csvs": verified,
        }


def check_semantics(econ: dict, s5: dict) -> dict:
    residuals = {}
    for regime in REGIMES:
        frame = econ["c"].loc[econ["c"].regime == regime]
        if len(frame) != 12 or frame.component_id.nunique() != 12 or frame[RISK].nunique() != 1:
            raise ValueError("incomplete/ambiguous component accounting")
        residuals[regime] = float(frame.contribution_per_kw_year.sum() - frame[RISK].iloc[0])
        if abs(residuals[regime]) > 1e-6:
            raise ValueError("signed component identity does not close")
    for _, frame in econ["d"].groupby("duration_h"):
        for column in (
            "technical_capacity_ceiling_kw",
            "scaled_accounting_technical_capacity_ceiling_kw",
        ):
            if frame[column].nunique() != 1:
                raise ValueError("duration certificate differs across regimes")
    for panel, columns in {
        "a": ["facility_site_scale_mw", RISK],
        "b": ["driver_value", RISK],
        "c": ["contribution_per_kw_year", RISK],
        "d": ["duration_h", MEAN, RISK],
    }.items():
        if not np.isfinite(econ[panel][columns].to_numpy(dtype=float)).all():
            raise ValueError(f"nonfinite economic coordinates: {panel}")
    if (econ["a"].facility_site_scale_mw <= 0).any():
        raise ValueError("logarithmic site scale must be positive")
    missing = s5["b"].loc[s5["b"].duration_grid_status == "not_evaluated"]
    evaluated = s5["b"].loc[s5["b"].duration_grid_status == "evaluated"]
    if (
        len(missing) != 6
        or set(missing.duration_h) != {5, 7}
        or missing.perfect_information_firm_capacity_kw.notna().any()
        or len(evaluated) != 18
    ):
        raise ValueError("unevaluated S5 duration contract violated")
    if not np.isfinite(evaluated.perfect_information_firm_capacity_kw).all():
        raise ValueError("nonfinite evaluated S5 capacity")
    return {
        "signed_sum_residuals": residuals,
        "s5_evaluated_capacity_rows": 18,
        "s5_explicit_unevaluated_rows": 6,
    }


def style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans"],
            "font.size": 7.0,
            "axes.labelsize": 7.0,
            "axes.titlesize": 8.0,
            "xtick.labelsize": 6.5,
            "ytick.labelsize": 6.5,
            "legend.fontsize": 6.5,
            "legend.frameon": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.6,
            "text.color": INK,
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "svg.hashsalt": "aidrbench-local-review-v1",
            "hatch.linewidth": 0.45,
        }
    )


def panel_title(fig, ax, letter: str, title: str) -> None:
    box = ax.get_position()
    fig.text(box.x0 - 0.035, box.y1 + 0.017, letter, weight="bold", fontsize=9)
    fig.text(box.x0, box.y1 + 0.017, title, weight="bold", fontsize=8)


def axes(fig, bounds, *, grid=True):
    ax = fig.add_axes(bounds)
    if grid:
        ax.grid(axis="y", color=GRID, linewidth=0.45)
        ax.set_axisbelow(True)
    return ax


def trace_rows(
    trace: list, kind: str, panel: str, frame: pd.DataFrame, fields: list[str], role: str
):
    for index, row in frame.iterrows():
        trace.append(
            {
                "figure": kind,
                "panel": panel,
                "source_file": PANELS[kind][panel],
                "csv_line": int(index) + 2,
                "role": role,
                "values": {key: None if pd.isna(row[key]) else row[key] for key in fields},
            }
        )


def draw_economic(data: dict, trace: list):
    fig = plt.figure(figsize=(WIDTH_MM / 25.4, 235 / 25.4))
    fig.text(
        0.5,
        0.981,
        "LOCAL REVIEW DRAFT · Figure 6 · Formal Web-GPT artwork pending",
        ha="center",
        fontsize=7,
        weight="bold",
        color=GREY,
    )
    a = axes(fig, [0.10, 0.665, 0.47, 0.245])
    panel_title(fig, a, "a", "Fixed site cost changes the scale threshold")
    for regime, color, label in zip(REGIMES, COLORS, LABELS, strict=True):
        for perspective, line, fill in [
            ("including_fixed_site_overlay", "-", color),
            ("excluding_fixed_site_lower_bound", "--", "none"),
        ]:
            frame = (
                data["a"]
                .loc[
                    (data["a"].regime == regime) & (data["a"].accounting_perspective == perspective)
                ]
                .sort_values("facility_site_scale_mw")
            )
            a.plot(
                frame.facility_site_scale_mw,
                frame[RISK],
                line,
                marker="o",
                ms=3.7,
                color=color,
                mfc=fill,
                lw=1.15,
            )
        # The label uses the exact last coordinate; text alone is displaced for legibility.
        a.annotate(
            label.replace("Throughput-displacing", "Throughput-\ndisplacing"),
            (frame.facility_site_scale_mw.iloc[-1], frame[RISK].iloc[-1]),
            xytext=(5, 0),
            textcoords="offset points",
            color=color,
            fontsize=6.5,
            va="center",
        )
    a.set_xscale("log")
    a.set_xticks([0.2, 1, 5, 20], ["0.2", "1", "5", "20"])
    a.set_xlim(0.15, 32)
    a.set_xlabel("Proportional accounting site scale (MW)")
    a.set_ylabel("Risk-adjusted capacity payment\n(real 2026 USD kW⁻¹ year⁻¹)")
    a.legend(
        handles=[
            Line2D([], [], color=INK, marker="o", ms=3.5, label="Including fixed site cost"),
            Line2D(
                [],
                [],
                color=INK,
                ls="--",
                marker="o",
                mfc="none",
                ms=3.5,
                label="Excluding fixed site cost",
            ),
        ],
        loc="upper right",
    )
    trace_rows(
        trace,
        "figure6",
        "a",
        data["a"],
        ["regime", "accounting_perspective", "facility_site_scale_mw", RISK],
        "point_and_guide",
    )

    lanes = [
        (0.852, "Fresh events per year", "annual_event_count"),
        (0.745, "Economic life (years)", "driver_value"),
        (
            0.638,
            "Effective displaced value (USD GPU-h⁻¹)",
            "effective_displaced_compute_value_per_gpu_h",
        ),
    ]
    for i, (bottom, label, field) in enumerate(lanes):
        b = axes(fig, [0.745, bottom, 0.225, 0.065])
        if i == 0:
            panel_title(fig, b, "b", "Mechanism sensitivities")
        frame = data["b"].loc[data["b"].regime == REGIMES[i]].sort_values(field)
        b.plot(frame[field], frame[RISK], color=COLORS[i], lw=1)
        for _, row in frame.iterrows():
            stress = bool(row.annual_event_count_is_stress)
            b.plot(row[field], row[RISK], "x" if stress else "o", color=COLORS[i], ms=4)
        b.set_xlabel(label, fontsize=6.5, labelpad=2)
        if i in (0, 2):
            if (frame[field] <= 0).any():
                raise ValueError("logarithmic mechanism coordinates must be positive")
            b.set_xscale("log")
        b.set_xticks(frame[field].to_list(), [f"{value:g}" for value in frame[field]])
        b.minorticks_off()
        b.tick_params(axis="both", labelsize=6.5, pad=2)
        b.text(0, 1.03, LABELS[i], transform=b.transAxes, color=COLORS[i], fontsize=6.5)
        if i == 0:
            b.text(
                0.99, 1.03, "× = stress (100, 250)", transform=b.transAxes, ha="right", fontsize=6.5
            )
        trace_rows(
            trace,
            "figure6",
            "b",
            frame,
            ["regime", field, RISK, "annual_event_count_is_stress"],
            "point_and_guide",
        )
    fig.text(
        0.693,
        0.778,
        "Risk-adjusted payment\n(USD kW⁻¹ year⁻¹)",
        rotation=90,
        rotation_mode="anchor",
        ha="center",
        va="center",
        fontsize=7,
    )

    c = axes(fig, [0.10, 0.368, 0.33, 0.185])
    panel_title(fig, c, "c", "Signed cost and credit accounting")
    components = [
        ("fixed_site_enablement_cost", "Fixed site", ""),
        ("variable_enablement_cost", "Variable enablement", "//"),
        ("delay_cost", "Compute delay", "///"),
        ("reserve_annual_cost", "PCC reserve", "\\\\"),
        ("opportunity_cost", "Displaced compute", "xx"),
        ("energy_credit_or_cost", "Net energy", "oo"),
        ("performance_credit", "Performance credit", ".."),
        ("connection_credit", "Connection credit", "++"),
        ("sla_cost", "Service loss", "--"),
        ("checkpoint_cost", "Checkpoint/restart", "||"),
        ("penalty_cost", "Non-performance", "**"),
        ("risk_buffer", "Risk adjustment", "OO"),
    ]
    for i, regime in enumerate(REGIMES):
        frame = data["c"].loc[data["c"].regime == regime].set_index("component_id")
        positive, negative = 0.0, 0.0
        for component, _, hatch in components:
            value = float(frame.loc[component, "contribution_per_kw_year"])
            base = positive if value >= 0 else negative
            if value != 0:
                c.bar(
                    i,
                    value,
                    bottom=base,
                    width=0.53,
                    color=COLORS[i],
                    edgecolor=INK,
                    linewidth=0.35,
                    hatch=hatch,
                )
            if value >= 0:
                positive += value
            else:
                negative += value
        total = float(frame[RISK].iloc[0])
        c.plot(i, total, "D", mfc="white", mec=INK, ms=4)
        c.text(i, positive + 13, f"{total:.2f}", ha="center", fontsize=6.5)
    c.axhline(0, color=INK, lw=0.7)
    c.set_xticks(range(3), SHORT)
    c.set_xlim(-0.65, 2.65)
    c.set_ylim(-25, 470)
    c.set_ylabel("Contribution (USD kW⁻¹ year⁻¹)")
    c.text(0, -0.19, "◇  Total risk-adjusted threshold", transform=c.transAxes, fontsize=6.5)
    table = fig.add_axes([0.535, 0.349, 0.438, 0.218])
    table.axis("off")
    xs = [0.58, 0.76, 0.95]
    table.text(0.05, 1.02, "Component / exact zeros retained", fontsize=6.5, weight="bold")
    for x, short, color in zip(xs, SHORT, COLORS, strict=True):
        table.text(x, 0.95, short, color=color, ha="right", fontsize=6.5, weight="bold")
    for j, (component, label, hatch) in enumerate(components):
        y = 0.88 - j * 0.075
        table.add_patch(
            Rectangle(
                (0, y - 0.017), 0.04, 0.043, facecolor="white", edgecolor=INK, lw=0.35, hatch=hatch
            )
        )
        table.text(0.055, y, label, va="center", fontsize=6.5)
        for x, regime in zip(xs, REGIMES, strict=True):
            row = (
                data["c"]
                .loc[(data["c"].regime == regime) & (data["c"].component_id == component)]
                .iloc[0]
            )
            value = float(row.contribution_per_kw_year)
            table.text(
                x, y, "0" if value == 0 else f"{value:.3f}", ha="right", va="center", fontsize=6.5
            )
    trace_rows(
        trace,
        "figure6",
        "c",
        data["c"],
        ["regime", "component_id", "contribution_per_kw_year", RISK],
        "signed_stack_and_component_table_including_zero",
    )

    d = axes(fig, [0.10, 0.125, 0.87, 0.15])
    panel_title(fig, d, "d", "Duration raises the reference-cost participation threshold")
    durations = sorted(data["d"].duration_h.unique())
    for i, regime in enumerate(REGIMES):
        frame = data["d"].loc[data["d"].regime == regime].sort_values("duration_h")
        for field, marker, face, line in [(MEAN, "o", "none", "--"), (RISK, "D", COLORS[i], "-")]:
            d.plot(
                range(len(frame)),
                frame[field],
                marker=marker,
                mfc=face,
                color=COLORS[i],
                lw=1,
                ls=line,
                ms=4,
                label=LABELS[i] if field == RISK else None,
            )
    for i, duration in enumerate(durations):
        row = data["d"].loc[data["d"].duration_h == duration].iloc[0]
        d.text(
            i,
            0.96,
            f"Reference certificate: {row.technical_capacity_ceiling_kw:.2f} kW\n"
            f"1 MW accounting: {row.scaled_accounting_technical_capacity_ceiling_kw:.2f} kW",
            transform=d.get_xaxis_transform(),
            gid="duration_scope_annotation",
            ha="center",
            va="top",
            fontsize=6.5,
        )
    d.set_xticks(range(len(durations)), [str(int(x)) for x in durations])
    d.set_xlim(-0.35, 2.35)
    # Reserve a top annotation band without changing any scientific coordinate.
    data_top = float(data["d"][[MEAN, RISK]].to_numpy().max())
    d.set_ylim(0, 1.5 * data_top)
    d.set_yticks([0, 200, 400, 600, 800])
    d.set_xlabel("Independently certified reference-module event duration (h)")
    d.set_ylabel("Capacity payment\n(USD kW⁻¹ year⁻¹)")
    fig.text(
        0.535,
        0.062,
        "○ Mean, excluding fixed site cost     ◆ Risk-adjusted, including fixed site cost",
        ha="center",
        fontsize=6.5,
    )
    trace_rows(
        trace,
        "figure6",
        "d",
        data["d"],
        [
            "regime",
            "duration_h",
            MEAN,
            RISK,
            "technical_capacity_ceiling_kw",
            "scaled_accounting_technical_capacity_ceiling_kw",
        ],
        "two_payment_marks_and_scope_annotations",
    )
    fig.text(
        0.5,
        0.018,
        "Fresh-event screening; real 2026 USD. "
        "Technical certificates apply only to the reference module.\n"
        "The 1 MW and other site-scale coordinates are "
        "proportional-reference-module accounting sensitivities\n"
        "with no assumed portfolio diversification.",
        ha="center",
        va="bottom",
        fontsize=6.5,
        color=GREY,
    )
    return fig


def draw_s5(data: dict, trace: list):
    fig = plt.figure(figsize=(WIDTH_MM / 25.4, 195 / 25.4))
    fig.text(
        0.5,
        0.978,
        "LOCAL REVIEW DRAFT · Figure S5 · Formal Web-GPT artwork pending",
        ha="center",
        fontsize=7,
        color=GREY,
        weight="bold",
    )
    a = axes(fig, [0.10, 0.715, 0.87, 0.19])
    panel_title(fig, a, "a", "Paired community profiles differ in net demand")
    for zone, color, line in zip(ZONES, COLORS, ("-", "--", ":"), strict=True):
        frame = data["a"].loc[data["a"].climate_zone == zone].sort_values("elapsed_hour")
        a.plot(
            frame.elapsed_day,
            frame.net_community_load_kw,
            color=color,
            ls=line,
            lw=0.85,
            label=zone,
        )
    a.set_xlabel("Elapsed day (first 168 chronological hours)")
    a.set_ylabel("Net community demand (kW)")
    a.set_xlim(0, 7)
    a.legend(loc="lower right", bbox_to_anchor=(1, 1.015), ncol=3, borderaxespad=0)
    trace_rows(
        trace,
        "s5",
        "a",
        data["a"],
        ["climate_zone", "elapsed_day", "net_community_load_kw"],
        "hourly_curve_vertex",
    )

    b = axes(fig, [0.10, 0.414, 0.39, 0.185])
    panel_title(fig, b, "b", "Firm capacity is unchanged")
    for zone, color, size in zip(ZONES, COLORS, (8, 5.7, 3.4), strict=True):
        frame = data["b"].loc[data["b"].climate_zone == zone].sort_values("duration_h")
        # NaNs deliberately break lines at H=5,7; no estimated value is inserted.
        b.plot(
            frame.duration_h,
            frame.perfect_information_firm_capacity_kw,
            color=color,
            marker="o",
            ms=size,
            mfc="none",
            mew=0.9,
            lw=0.8,
            label=zone,
        )
    for duration in (5, 7):
        b.text(duration, 34.8, "Not\nevaluated", ha="center", fontsize=6.5, color=GREY)
    b.set_xticks(range(1, 9))
    b.set_ylim(32, 56)
    b.set_xlabel("Event duration (h)")
    b.set_ylabel("PI tolerance lower bound (kW)")
    b.text(
        0.98,
        0.97,
        "q = 0.95; n = 100 scenarios / zone\nNested rings: all three series coincide",
        transform=b.transAxes,
        ha="right",
        va="top",
        fontsize=6.5,
    )
    trace_rows(
        trace,
        "s5",
        "b",
        data["b"],
        [
            "climate_zone",
            "duration_h",
            "duration_grid_status",
            "perfect_information_firm_capacity_kw",
        ],
        "nested_capacity_mark_or_explicit_unevaluated_label",
    )

    c = axes(fig, [0.68, 0.414, 0.29, 0.185])
    panel_title(fig, c, "c", "Fixed-candidate replay")
    for i, duration in enumerate((4, 8)):
        for j, (zone, color) in enumerate(zip(ZONES, COLORS, strict=True)):
            row = (
                data["c"]
                .loc[(data["c"].climate_zone == zone) & (data["c"].duration_h == duration)]
                .iloc[0]
            )
            x = i * 4 + j
            c.plot(x, row.empirical_success_fraction, "o", color=color, ms=4)
            c.plot(x, row.wilson_lower_confidence_bound, "o", color=color, mfc="none", ms=4)
        c.text(
            i * 4 + 1,
            -0.25,
            f"{duration} h",
            transform=c.get_xaxis_transform(),
            ha="center",
            fontsize=7,
        )
    c.axhline(0.95, color=GREY, ls="--", lw=0.7)
    c.text(6.3, 0.951, "q = 0.95", ha="right", fontsize=6.5, va="bottom")
    c.set_ylim(0.90, 1.012)
    c.set_xlim(-0.6, 6.6)
    c.set_xticks([0, 1, 2, 4, 5, 6], list(ZONES) * 2)
    c.set_ylabel("Success fraction / lower bound")
    c.text(0.02, 0.97, "n = 100 episodes / point", transform=c.transAxes, va="top", fontsize=6.5)
    c.text(
        0.5,
        -0.41,
        "● Empirical fraction\n○ One-sided 95% Wilson bound",
        transform=c.transAxes,
        ha="center",
        fontsize=6.5,
    )
    trace_rows(
        trace,
        "s5",
        "c",
        data["c"],
        [
            "climate_zone",
            "duration_h",
            "trial_count",
            "empirical_success_fraction",
            "wilson_lower_confidence_bound",
        ],
        "separate_fraction_and_lower_bound_marks",
    )

    d = axes(fig, [0.19, 0.12, 0.78, 0.164], grid=False)
    panel_title(fig, d, "d", "Community profile conditions PV-hosting value")
    labels = []
    for i, zone in enumerate(ZONES):
        for j, bess in enumerate((False, True)):
            y = 5 - (2 * i + j)
            frame = data["d"].loc[
                (data["d"].climate_zone == zone) & (data["d"].bess_enabled == bess)
            ]
            rigid = frame.loc[
                frame.dc_operation == "rigid", "simultaneous_feasible_pv_hosting_kw"
            ].iloc[0]
            flexible = frame.loc[
                frame.dc_operation == "flexible", "simultaneous_feasible_pv_hosting_kw"
            ].iloc[0]
            marker = "s" if bess else "o"
            d.plot([rigid, flexible], [y, y], color=COLORS[i], lw=1.5)
            d.plot(rigid, y, marker, color=COLORS[i], mfc="white", ms=5)
            d.plot(flexible, y, marker, color=COLORS[i], ms=5)
            labels.append(f"{zone} / {'BESS' if bess else 'no BESS'}")
    d.set_yticks(range(5, -1, -1), labels)
    d.set_ylim(-0.6, 5.6)
    d.set_xlim(400, 755)
    d.set_xlabel("PV hosting feasible in all 100 scenarios (kW)")
    d.grid(axis="x", color=GRID, lw=0.45)
    fig.text(
        0.58,
        0.055,
        "Open: rigid    Filled: flexible    Circle: no BESS    Square: BESS",
        ha="center",
        fontsize=6.5,
    )
    trace_rows(
        trace,
        "s5",
        "d",
        data["d"],
        [
            "climate_zone",
            "bess_enabled",
            "dc_operation",
            "scenario_count",
            "simultaneous_feasible_pv_hosting_kw",
        ],
        "paired_boundary_endpoint",
    )
    fig.text(
        0.5,
        0.010,
        "Panels b–c: paired non-locked development diagnostics. "
        "Panel d: perfect-information planning.\n"
        "Climate-zone labels denote profile archetypes, "
        "not measured or geographically identified sites.",
        ha="center",
        va="bottom",
        fontsize=6.5,
        color=GREY,
    )
    return fig


def data_clearance_padding_points(line) -> float:
    """Enclose the reviewed circle/diamond ink and line stroke, plus a one-point gap."""
    radius_pt = line.get_linewidth() / 2
    if line.get_marker() not in {None, "None", "", " "}:
        if line.get_marker() not in {"o", "D"}:
            raise ValueError("duration annotation guard needs reviewed circle/diamond geometry")
        marker = MarkerStyle(line.get_marker(), fillstyle=line.get_fillstyle())
        bounds = marker.get_path().transformed(marker.get_transform()).get_extents()
        marker_radius = max(abs(v) for v in (bounds.x0, bounds.x1, bounds.y0, bounds.y1))
        # One full edge width exceeds both the circle half-stroke and the
        # diamond miter extension (sqrt(2)/2 times the edge width).
        marker_ink_radius = marker_radius * line.get_markersize() + line.get_markeredgewidth()
        radius_pt = max(radius_pt, marker_ink_radius)
    return float(radius_pt + 1)


def check_scope_annotations(fig, renderer) -> int:
    """Reject duration-scope labels intersecting data lines or marker extents.

    This targeted guard covers the v4 failure, not every possible visual collision.
    Actual transformed marker bounds, edge width and a one-point gap enlarge each bbox.
    """
    checked = 0
    for ax in fig.axes:
        for label in ax.texts:
            if label.get_gid() != "duration_scope_annotation":
                continue
            checked += 1
            bbox = label.get_window_extent(renderer)
            for line in ax.lines:
                has_marker = line.get_marker() not in {None, "None", "", " "}
                padded = bbox.padded(data_clearance_padding_points(line) * fig.dpi / 72)
                path = line.get_path().transformed(line.get_transform())
                points = path.vertices
                marker_inside = has_marker and any(padded.contains(x, y) for x, y in points)
                if marker_inside or path.intersects_bbox(padded, filled=False):
                    raise ValueError(
                        f"duration scope annotation overlaps plotted data: {label.get_text()}"
                    )
    return checked


def export(fig, destination: Path, stem: str) -> dict:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    scope_annotations_checked = check_scope_annotations(fig, renderer)
    overflow, fonts = [], []
    inactive_tick_labels = set()
    for ax in fig.axes:
        for axis, limits in ((ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())):
            low, high = sorted(limits)
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                if not low <= tick.get_loc() <= high:
                    inactive_tick_labels.update((tick.label1, tick.label2))
    for text in fig.findobj(Text):
        if text in inactive_tick_labels or not text.get_visible() or not text.get_text().strip():
            continue
        bbox = text.get_window_extent(renderer)
        fonts.append(float(text.get_fontsize()))
        if bbox.x0 < -1 or bbox.y0 < -1 or bbox.x1 > fig.bbox.x1 + 1 or bbox.y1 > fig.bbox.y1 + 1:
            overflow.append(text.get_text())
    if overflow:
        raise ValueError(f"text outside figure canvas: {overflow}")
    if min(fonts) < 6.5:
        raise ValueError("configured font smaller than 6.5 pt")
    # Keep format and resolution explicit for portable review and source audits.
    fig.savefig(destination / f"{stem}.svg", metadata={"Date": None})
    fig.savefig(destination / f"{stem}.pdf", metadata={"CreationDate": None, "ModDate": None})
    fig.savefig(destination / f"{stem}.png", dpi=300)
    fig.savefig(destination / f"{stem}.tiff", dpi=600, pil_kwargs={"compression": "tiff_lzw"})
    outputs = {
        f"{stem}.{extension}": sha((destination / f"{stem}.{extension}").read_bytes())
        for extension in ("svg", "pdf", "png", "tiff")
    }
    plt.close(fig)
    return {
        "width_mm": WIDTH_MM,
        "height_mm": float(fig.get_figheight() * 25.4),
        "minimum_configured_text_pt": min(fonts),
        "outside_canvas_text": overflow,
        "duration_scope_annotations_checked": scope_annotations_checked,
        "output_sha256": outputs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figure6-package", type=Path, required=True)
    parser.add_argument("--s5-package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("use a new output directory; previous review versions are preserved")
    econ, econ_checks = load_package(args.figure6_package, "figure6")
    s5, s5_checks = load_package(args.s5_package, "s5")
    semantic = check_semantics(econ, s5)
    style()
    trace = []
    figures = {"figure6": draw_economic(econ, trace), "s5": draw_s5(s5, trace)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".aidrbench-review-", dir=args.output.parent) as temp:
        staging = Path(temp) / "outputs"
        staging.mkdir()
        write_outputs(figures, trace, staging, econ_checks, s5_checks, semantic)
        staging.rename(args.output)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "traced_rows": len(trace),
                "status": "local_review_draft_only",
            }
        )
    )


def write_outputs(figures, trace, destination, econ_checks, s5_checks, semantic):
    outputs = {
        kind: export(fig, destination, f"{kind}_local_review") for kind, fig in figures.items()
    }
    if len(trace) != 628:
        raise ValueError(f"incomplete row trace: {len(trace)}")
    (destination / "row_to_mark.json").write_text(
        json.dumps(trace, indent=2, default=str, allow_nan=False) + "\n"
    )
    manifest = {
        "schema": "aidrbench.local_review_figures.v1",
        "status": "local_review_draft_only",
        "formal_artwork_route": "web_gpt_required_by_user",
        "script_sha256": sha(Path(__file__).read_bytes()),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "font": {
                "family": "DejaVu Sans",
                "sha256": sha(Path(matplotlib.font_manager.findfont("DejaVu Sans")).read_bytes()),
            },
            "packages": {
                name: importlib.metadata.version(name)
                for name in ("matplotlib", "numpy", "pandas", "Pillow")
            },
        },
        "inputs": {"figure6": econ_checks, "s5": s5_checks},
        "semantic_checks": semantic,
        "figures": outputs,
        "trace_rows": len(trace),
        "row_trace_sha256": sha((destination / "row_to_mark.json").read_bytes()),
        "recalculated_scientific_results": False,
        "claim": "Drafts for independent review and redraw; not formal artwork.",
    }
    (destination / "review_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
