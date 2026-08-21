"""Reference-led Nature Communications figures for the frozen AIDRBench mainline.

The visual grammar follows the user-provided Nature Communications reference:
one dominant narrative or quantitative panel, a small number of subordinate
panels, restrained low-saturation colour, direct labels, and generous white
space. Scientific definitions and source-data provenance remain unchanged.
"""
# ruff: noqa: E501

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.image import AxesImage

from aidrbench.evaluation.nature_figures import (
    _COLORS,
    _FIGURE_WIDTH_IN,
    _bool_series,
    _finalize_figure,
    _float,
    _int,
    _load_manifest,
    _numeric,
    _panel_label,
    _publication_style,
    _require_columns,
    _verified_table,
    plot_nature_mainline_figure1_reference_style,
)


def _short_heading(axis: Axes, text: str) -> None:
    axis.text(
        0.0,
        1.035,
        text,
        transform=axis.transAxes,
        fontsize=7.5,
        fontweight="bold",
        color=_COLORS["ink"],
        ha="left",
        va="bottom",
    )


def _direct_label(
    axis: Axes,
    x_value: float,
    y_value: float,
    text: str,
    *,
    color: str,
    dx: float = 0.14,
    dy: float = 0.0,
    fontsize: float = 6.7,
) -> None:
    axis.text(
        x_value + dx,
        y_value + dy,
        text,
        color=color,
        fontsize=fontsize,
        ha="left",
        va="center",
        clip_on=False,
    )


def plot_nature_mainline_figure2_reference_style(
    source_data_directory: str | Path,
    output_directory: str | Path,
    *,
    formats: Sequence[str] = ("svg", "pdf", "tiff", "png"),
) -> dict[str, object]:
    """Plot the firm-flexibility surface with one dominant capacity panel."""

    _publication_style()
    manifest_path, manifest = _load_manifest(source_data_directory)
    pi = _verified_table(source_data_directory, manifest, "fig1_fig2_pi_firm_boundaries")
    na = _verified_table(source_data_directory, manifest, "fig2_restricted_na_surface")
    diagnostics = _verified_table(
        source_data_directory,
        manifest,
        "fig2_notice_mechanism_diagnostics",
    )
    certificates = _verified_table(
        source_data_directory,
        manifest,
        "fig2_fig5_locked_id_certificates",
    )

    q95_pi = pi[np.isclose(_numeric(pi, "reliability_target"), 0.95)].sort_values("duration_h")
    q95_na = na[
        np.isclose(_numeric(na, "ensemble_success_fraction_target"), 0.95)
        & np.isclose(_numeric(na, "notice_h"), 0)
    ].sort_values("duration_h")
    q95_cert = certificates[
        np.isclose(_numeric(certificates, "reliability_target"), 0.95)
        & np.isclose(_numeric(certificates, "notice_h"), 0)
    ].sort_values("duration_h")

    figure = plt.figure(figsize=(_FIGURE_WIDTH_IN, 4.65), constrained_layout=False)
    grid = figure.add_gridspec(
        2,
        12,
        width_ratios=(1,) * 12,
        height_ratios=(1.0, 0.88),
        hspace=0.58,
        wspace=1.05,
    )
    ax_a = figure.add_subplot(grid[:, :8])
    ax_b = figure.add_subplot(grid[0, 8:])
    ax_c = figure.add_subplot(grid[1, 8:])

    duration = _numeric(q95_pi, "duration_h").to_numpy(dtype=float)
    nominal = _numeric(q95_pi, "nominal_flexibility_kw").to_numpy(dtype=float)
    pi_capacity = _numeric(q95_pi, "perfect_information_firm_capacity_kw").to_numpy(dtype=float)
    na_capacity = _numeric(q95_na, "non_anticipative_capacity_kw").to_numpy(dtype=float)
    causal = _numeric(q95_cert, "candidate_reduction_kw").to_numpy(dtype=float)
    certified = _bool_series(q95_cert["certified"]).to_numpy(dtype=bool)

    ax_a.fill_between(
        duration,
        pi_capacity,
        nominal,
        color=_COLORS["pale_red"],
        linewidth=0,
        alpha=0.90,
    )
    ax_a.plot(
        duration,
        nominal,
        color=_COLORS["neutral"],
        linewidth=1.6,
        linestyle=(0, (2, 2)),
    )
    ax_a.plot(duration, pi_capacity, color=_COLORS["gold"], linewidth=2.0, marker="o")
    ax_a.plot(duration, na_capacity, color=_COLORS["purple"], linewidth=2.0, marker="s")
    ax_a.plot(duration, causal, color=_COLORS["blue"], linewidth=2.1)
    ax_a.scatter(
        duration[certified],
        causal[certified],
        color=_COLORS["blue"],
        s=28,
        zorder=4,
    )
    ax_a.scatter(
        duration[~certified],
        causal[~certified],
        facecolors="white",
        edgecolors=_COLORS["red"],
        marker="X",
        linewidths=1.1,
        s=42,
        zorder=5,
    )
    for y_value, label, color, y_offset in (
        (nominal[-1], "Nominal proxy", _COLORS["neutral"], 0.0),
        (pi_capacity[-1], "PI tolerance", _COLORS["gold"], -0.8),
        (na_capacity[-1], "Restricted NA", _COLORS["purple"], 1.5),
        (causal[-1], "Locked-ID", _COLORS["blue"], -2.0),
    ):
        ax_a.text(
            duration[-1] - 0.18,
            y_value + y_offset,
            label,
            color=color,
            fontsize=6.7,
            ha="right",
            va="center",
        )
    if (~certified).any():
        failed_index = int(np.flatnonzero(~certified)[0])
        ax_a.annotate(
            "H=1 not certified",
            xy=(duration[failed_index], causal[failed_index]),
            xytext=(1.75, 67.0),
            color=_COLORS["red"],
            fontsize=6.8,
            arrowprops={"arrowstyle": "->", "lw": 0.75, "color": _COLORS["red"]},
        )
    ax_a.set_xlim(0.7, 10.0)
    ax_a.set_ylim(30, 108)
    ax_a.set_xticks(duration)
    ax_a.set_xlabel("Event duration (h)")
    ax_a.set_ylabel("Firm reduction capacity (kW)")
    ax_a.grid(axis="y", color=_COLORS["grid"], linewidth=0.55)
    _short_heading(ax_a, "Duration separates nominal, feasible and certified capacity")
    _panel_label(ax_a, "a", x=-0.08, y=1.08)

    reliability_specs = (
        (0.90, _COLORS["flex"], "q=0.90"),
        (0.95, _COLORS["blue"], "q=0.95"),
        (0.99, _COLORS["red"], "q=0.99"),
    )
    label_offsets = {0.90: 1.5, 0.95: 0.0, 0.99: -1.2}
    for reliability, color, label in reliability_specs:
        subset = certificates[
            np.isclose(_numeric(certificates, "reliability_target"), reliability)
            & np.isclose(_numeric(certificates, "notice_h"), 0)
        ].sort_values("duration_h")
        values = _numeric(subset, "candidate_reduction_kw").to_numpy(dtype=float)
        flags = _bool_series(subset["certified"]).to_numpy(dtype=bool)
        x_values = _numeric(subset, "duration_h").to_numpy(dtype=float)
        ax_b.plot(x_values, values, color=color, linewidth=1.6)
        ax_b.scatter(x_values[flags], values[flags], color=color, s=19, zorder=3)
        ax_b.scatter(
            x_values[~flags],
            values[~flags],
            facecolors="white",
            edgecolors=color,
            s=23,
            linewidths=0.9,
            zorder=3,
        )
        _direct_label(
            ax_b,
            x_values[-1],
            values[-1],
            label,
            color=color,
            dx=0.08,
            dy=label_offsets[reliability],
            fontsize=6.4,
        )
    ax_b.set_xlim(0.7, 9.3)
    ax_b.set_xticks(duration)
    ax_b.set_xlabel("Duration (h)")
    ax_b.set_ylabel("Candidate (kW)")
    ax_b.grid(axis="y", color=_COLORS["grid"], linewidth=0.5)
    _short_heading(ax_b, "Reliability cost")
    _panel_label(ax_b, "b", x=-0.20, y=1.09)

    notice = diagnostics[np.isclose(_numeric(diagnostics, "notice_h"), 6)].sort_values("duration_h")
    eligible = _numeric(notice, "eligible_pre_execution_work_gpu_h_mean").to_numpy(dtype=float)
    spare = _numeric(notice, "pre_event_spare_capacity_gpu_h_mean").to_numpy(dtype=float)
    if np.any(eligible <= 0) or np.any(spare <= 0):
        raise ValueError("notice-mechanism quantities must be strictly positive")
    y_positions = np.arange(len(notice), dtype=float)
    ax_c.barh(
        y_positions + 0.15,
        eligible,
        height=0.25,
        color=_COLORS["pale_gold"],
        edgecolor=_COLORS["gold"],
        linewidth=0.7,
    )
    ax_c.barh(
        y_positions - 0.15,
        spare,
        height=0.25,
        color=_COLORS["pale_teal"],
        edgecolor=_COLORS["flex"],
        linewidth=0.7,
    )
    ax_c.set_xlim(0, float(eligible.max()) * 1.42)
    ax_c.set_yticks(
        y_positions,
        [f"H={_int(value)} h" for value in _numeric(notice, "duration_h")],
    )
    ax_c.set_xlabel("Pre-event work or headroom (GPU-h)")
    ax_c.grid(axis="x", color=_COLORS["grid"], linewidth=0.5)
    for y_value, eligible_value, spare_value, (_, row) in zip(
        y_positions,
        eligible,
        spare,
        notice.iterrows(),
        strict=True,
    ):
        ax_c.text(
            eligible_value + float(eligible.max()) * 0.025,
            y_value + 0.15,
            f"eligible {eligible_value:,.0f}",
            fontsize=6.0,
            color=_COLORS["gold"],
            va="center",
        )
        ax_c.text(
            spare_value + float(eligible.max()) * 0.025,
            y_value - 0.15,
            f"spare {spare_value:,.0f}",
            fontsize=6.0,
            color=_COLORS["flex"],
            va="center",
        )
        ax_c.text(
            0.98,
            y_value,
            f"ΔR={_float(row['na_notice_gain_kw']):.1f} kW",
            transform=ax_c.get_yaxis_transform(),
            ha="right",
            va="center",
            fontsize=6.4,
            color=_COLORS["red"],
            fontweight="bold",
        )
    _short_heading(ax_c, "Notice exposes work, but not usable capacity")
    _panel_label(ax_c, "c", x=-0.20, y=1.09)

    figure.subplots_adjust(left=0.075, right=0.95, bottom=0.11, top=0.94)
    return _finalize_figure(
        figure,
        figure_number=2,
        source_manifest_path=manifest_path,
        source_tables=(
            "fig1_fig2_pi_firm_boundaries",
            "fig2_restricted_na_surface",
            "fig2_notice_mechanism_diagnostics",
            "fig2_fig5_locked_id_certificates",
        ),
        output_directory=output_directory,
        stem="figure_2_duration_reliability_notice",
        formats=formats,
        core_conclusion=(
            "Duration and reliability shape firm capacity, whereas advance notice reveals "
            "eligible work but yields zero capacity gain under Model A."
        ),
        claim_boundaries=(
            "PI tolerance, restricted NA and locked-ID causal layers have different statistical interpretations.",
            "Certification is interval-wise rather than simultaneous over the complete surface.",
            "The q=0.95 H=1 candidate remains visibly not certified.",
        ),
        archetype="asymmetric quantitative figure",
    )


def _success_heatmap(
    axis: Axes,
    frame: pd.DataFrame,
    split: str,
    *,
    show_ylabel: bool,
) -> AxesImage:
    subset = frame[frame["evaluation_split"] == split].copy()
    pivot = subset.pivot(
        index="duration_h",
        columns="recovery_gap_h",
        values="joint_episode_success_fraction",
    ).sort_index()
    cmap = LinearSegmentedColormap.from_list(
        "aidr_reference_success",
        [_COLORS["pale_red"], _COLORS["pale_teal"], _COLORS["navy"]],
    )
    image = axis.imshow(
        pivot.to_numpy(dtype=float),
        vmin=0.0,
        vmax=1.0,
        aspect="auto",
        cmap=cmap,
    )
    for row_index in range(pivot.shape[0]):
        for column_index in range(pivot.shape[1]):
            value = _float(pivot.iloc[row_index, column_index])
            axis.text(
                column_index,
                row_index,
                f"{value:.2f}",
                ha="center",
                va="center",
                fontsize=6.4,
                color="white" if value >= 0.72 else _COLORS["ink"],
            )
    axis.set_xticks(range(len(pivot.columns)), [str(_int(value)) for value in pivot.columns])
    axis.set_yticks(range(len(pivot.index)), [str(_int(value)) for value in pivot.index])
    axis.set_xlabel("Recovery gap (h)")
    axis.set_ylabel("Event duration (h)" if show_ylabel else "")
    return image


def plot_nature_mainline_figure3_reference_style(
    source_data_directory: str | Path,
    output_directory: str | Path,
    *,
    formats: Sequence[str] = ("svg", "pdf", "tiff", "png"),
) -> dict[str, object]:
    """Plot compute-debt accumulation as the dominant repeated-event mechanism."""

    _publication_style()
    manifest_path, manifest = _load_manifest(source_data_directory)
    event = _verified_table(source_data_directory, manifest, "fig3_exhaustion_event_summary")
    joint = _verified_table(
        source_data_directory,
        manifest,
        "fig3_exhaustion_joint_episode_summary",
    )
    _require_columns(
        event,
        (
            "evaluation_split",
            "duration_h",
            "recovery_gap_h",
            "event_ordinal",
            "mean_paired_compute_debt_increment_kwh",
            "fixed_commitment_residual_flexibility_ratio",
        ),
        table_id="fig3_exhaustion_event_summary",
    )

    averaged = (
        event.groupby(["evaluation_split", "duration_h", "event_ordinal"], as_index=False)[
            [
                "mean_paired_compute_debt_increment_kwh",
                "fixed_commitment_residual_flexibility_ratio",
            ]
        ]
        .mean()
        .sort_values(["evaluation_split", "duration_h", "event_ordinal"])
    )

    figure = plt.figure(figsize=(_FIGURE_WIDTH_IN, 4.9), constrained_layout=False)
    grid = figure.add_gridspec(
        2,
        12,
        height_ratios=(1.0, 0.92),
        hspace=0.62,
        wspace=1.05,
    )
    ax_a = figure.add_subplot(grid[0, :8])
    ax_b = figure.add_subplot(grid[0, 8:])
    ax_c = figure.add_subplot(grid[1, :6])
    ax_d = figure.add_subplot(grid[1, 6:])

    for split, linestyle, alpha in (
        ("development", "--", 0.58),
        ("validation", "-", 1.0),
    ):
        for duration, color in ((4, _COLORS["blue"]), (8, _COLORS["red"])):
            subset = averaged[
                (averaged["evaluation_split"] == split)
                & np.isclose(_numeric(averaged, "duration_h"), duration)
            ]
            x_values = _numeric(subset, "event_ordinal").to_numpy(dtype=float)
            y_values = (
                _numeric(subset, "mean_paired_compute_debt_increment_kwh").to_numpy(dtype=float)
                / 1000.0
            )
            ax_a.plot(
                x_values,
                y_values,
                color=color,
                linewidth=2.0 if split == "validation" else 1.2,
                linestyle=linestyle,
                marker="o",
                markersize=4,
                alpha=alpha,
            )
            if split == "validation":
                _direct_label(
                    ax_a,
                    x_values[-1],
                    y_values[-1],
                    f"H={duration} h",
                    color=color,
                    dx=0.06,
                    fontsize=6.6,
                )
    ax_a.text(
        0.02,
        0.96,
        "solid: validation   dashed: development",
        transform=ax_a.transAxes,
        fontsize=6.2,
        color=_COLORS["neutral"],
        ha="left",
        va="top",
    )
    ax_a.set_xlim(0.8, 4.55)
    ax_a.set_xticks([1, 2, 3, 4])
    ax_a.set_xlabel("Event ordinal")
    ax_a.set_ylabel("Paired compute-debt increment (MWh)")
    ax_a.grid(axis="y", color=_COLORS["grid"], linewidth=0.55)
    _short_heading(ax_a, "Compute debt accumulates with repeated dispatch")
    _panel_label(ax_a, "a", x=-0.10, y=1.08)

    for split, linestyle, alpha in (
        ("development", "--", 0.58),
        ("validation", "-", 1.0),
    ):
        for duration, color in ((4, _COLORS["blue"]), (8, _COLORS["red"])):
            subset = averaged[
                (averaged["evaluation_split"] == split)
                & np.isclose(_numeric(averaged, "duration_h"), duration)
            ]
            ax_b.plot(
                _numeric(subset, "event_ordinal"),
                _numeric(subset, "fixed_commitment_residual_flexibility_ratio"),
                color=color,
                linewidth=1.7 if split == "validation" else 1.0,
                linestyle=linestyle,
                marker="o",
                markersize=3.5,
                alpha=alpha,
            )
    residual = _numeric(averaged, "fixed_commitment_residual_flexibility_ratio")
    ax_b.axhline(1.0, color=_COLORS["neutral"], linewidth=0.7, linestyle=":")
    ax_b.set_ylim(max(0.985, float(residual.min()) - 0.002), 1.0015)
    ax_b.set_xticks([1, 2, 3, 4])
    ax_b.set_xlabel("Event ordinal")
    ax_b.set_ylabel("Residual delivery ratio")
    ax_b.grid(axis="y", color=_COLORS["grid"], linewidth=0.5)
    ax_b.text(
        0.98,
        0.08,
        "power delivery\nremains near fresh-event level",
        transform=ax_b.transAxes,
        fontsize=6.2,
        color=_COLORS["neutral"],
        ha="right",
        va="bottom",
    )
    _short_heading(ax_b, "Delivery changes little")
    _panel_label(ax_b, "b", x=-0.20, y=1.09)

    _success_heatmap(ax_c, joint, "development", show_ylabel=True)
    _short_heading(ax_c, "Development")
    _panel_label(ax_c, "c", x=-0.14, y=1.10)
    _success_heatmap(ax_d, joint, "validation", show_ylabel=False)
    _short_heading(ax_d, "Independent validation")
    _panel_label(ax_d, "d", x=-0.14, y=1.10)
    figure.text(
        0.95,
        0.405,
        "colour: 0 → 1 joint success",
        fontsize=6.1,
        color=_COLORS["neutral"],
        ha="right",
        va="center",
    )

    figure.subplots_adjust(left=0.075, right=0.95, bottom=0.10, top=0.94)
    return _finalize_figure(
        figure,
        figure_number=3,
        source_manifest_path=manifest_path,
        source_tables=(
            "fig3_exhaustion_event_summary",
            "fig3_exhaustion_joint_episode_summary",
        ),
        output_directory=output_directory,
        stem="figure_3_compute_debt_exhaustion",
        formats=formats,
        core_conclusion=(
            "Repeated dispatch accumulates compute debt and joint service risk before the "
            "instantaneous power-delivery ratio materially collapses."
        ),
        claim_boundaries=(
            "The repeated-event study is a fixed-capacity mechanism diagnostic, not a repeated-event firm-capacity certificate.",
            "Recovery gaps help only when the intervening schedule contains sufficient compute headroom.",
        ),
        archetype="asymmetric quantitative figure",
    )


def _portfolio_compact_label(pv: bool, bess: bool) -> str:
    return f"PV {'on' if pv else 'off'} · BESS {'on' if bess else 'off'}"


def plot_nature_mainline_figure4_reference_style(
    source_data_directory: str | Path,
    output_directory: str | Path,
    *,
    formats: Sequence[str] = ("svg", "pdf", "tiff", "png"),
) -> dict[str, object]:
    """Plot hosting value as one dominant paired-capacity comparison."""

    _publication_style()
    manifest_path, manifest = _load_manifest(source_data_directory)
    summary = _verified_table(source_data_directory, manifest, "fig4_hosting_capacity_summary")
    contrasts = _verified_table(source_data_directory, manifest, "fig4_hosting_paired_contrasts")

    validation = summary[summary["evaluation_split"] == "validation"].copy()
    portfolio_keys = [(False, False), (False, True), (True, False), (True, True)]
    labels = [_portfolio_compact_label(pv, bess) for pv, bess in portfolio_keys]

    figure = plt.figure(figsize=(_FIGURE_WIDTH_IN, 5.0), constrained_layout=False)
    grid = figure.add_gridspec(2, 12, hspace=0.70, wspace=1.10)
    ax_a = figure.add_subplot(grid[:, :7])
    ax_b = figure.add_subplot(grid[0, 7:])
    ax_c = figure.add_subplot(grid[1, 7:])

    y_positions = np.arange(len(portfolio_keys), dtype=float)
    for y_value, ((pv, bess), label) in enumerate(zip(portfolio_keys, labels, strict=True)):
        rigid = validation[
            (validation["dc_operation"] == "rigid")
            & (_bool_series(validation["pv_enabled"]) == pv)
            & (_bool_series(validation["bess_enabled"]) == bess)
        ].iloc[0]
        flexible = validation[
            (validation["dc_operation"] == "flexible")
            & (_bool_series(validation["pv_enabled"]) == pv)
            & (_bool_series(validation["bess_enabled"]) == bess)
        ].iloc[0]
        rigid_mean = _float(rigid["mean_scenario_hosting_dc_peak_kw"])
        flexible_mean = _float(flexible["mean_scenario_hosting_dc_peak_kw"])
        ax_a.plot(
            [rigid_mean, flexible_mean],
            [y_value, y_value],
            color=_COLORS["grid"],
            linewidth=4.0,
            solid_capstyle="round",
            zorder=1,
        )
        ax_a.errorbar(
            rigid_mean,
            y_value,
            xerr=np.array(
                [
                    [rigid_mean - _float(rigid["q05_scenario_hosting_dc_peak_kw"])],
                    [_float(rigid["q95_scenario_hosting_dc_peak_kw"]) - rigid_mean],
                ]
            ),
            fmt="o",
            color=_COLORS["neutral"],
            capsize=2,
            markersize=5,
            zorder=3,
        )
        ax_a.errorbar(
            flexible_mean,
            y_value,
            xerr=np.array(
                [
                    [flexible_mean - _float(flexible["q05_scenario_hosting_dc_peak_kw"])],
                    [_float(flexible["q95_scenario_hosting_dc_peak_kw"]) - flexible_mean],
                ]
            ),
            fmt="o",
            color=_COLORS["flex"],
            capsize=2,
            markersize=5,
            zorder=3,
        )
        ax_a.text(
            flexible_mean - 12,
            y_value,
            f"+{flexible_mean - rigid_mean:.0f} kW",
            fontsize=6.6,
            color=_COLORS["flex"],
            fontweight="bold",
            ha="right",
            va="center",
        )
        ax_a.text(
            0.0,
            y_value,
            label,
            transform=ax_a.get_yaxis_transform(),
            fontsize=6.6,
            ha="right",
            va="center",
            color=_COLORS["ink"],
        )
    ax_a.set_yticks([])
    ax_a.invert_yaxis()
    ax_a.set_xlabel("Validation hosting capacity (kW; mean and q05–q95)")
    ax_a.grid(axis="x", color=_COLORS["grid"], linewidth=0.55)
    ax_a.text(
        0.02,
        0.04,
        "● rigid",
        transform=ax_a.transAxes,
        color=_COLORS["neutral"],
        fontsize=6.4,
        va="bottom",
    )
    ax_a.text(
        0.14,
        0.04,
        "● workload-flexible",
        transform=ax_a.transAxes,
        color=_COLORS["flex"],
        fontsize=6.4,
        va="bottom",
    )
    _short_heading(ax_a, "Workload flexibility expands community hosting capacity")
    _panel_label(ax_a, "a", x=-0.12, y=1.07)

    hosting = contrasts[contrasts["contrast"] == "AI_HOSTING_GAIN"].copy()
    x_positions = np.arange(len(portfolio_keys), dtype=float)
    for offset, split, color, marker in (
        (-0.09, "development", _COLORS["muted"], "o"),
        (0.09, "validation", _COLORS["blue"], "s"),
    ):
        subset = hosting[hosting["evaluation_split"] == split]
        values: list[float] = []
        lower: list[float] = []
        upper: list[float] = []
        for pv, bess in portfolio_keys:
            row = subset[subset["conditioning_level"] == f"pv={pv},bess={bess}"].iloc[0]
            estimate = _float(row["estimate_mean_kw"])
            values.append(estimate)
            lower.append(estimate - _float(row["simultaneous_ci_lower_kw"]))
            upper.append(_float(row["simultaneous_ci_upper_kw"]) - estimate)
        ax_b.errorbar(
            x_positions + offset,
            values,
            yerr=np.array([lower, upper]),
            fmt=marker,
            color=color,
            capsize=2,
            markersize=4,
            linewidth=1.0,
            label=split.capitalize(),
        )
    ax_b.set_xticks(x_positions, ["P0B0", "P0B1", "P1B0", "P1B1"])
    ax_b.set_ylabel("Paired gain (kW)")
    ax_b.grid(axis="y", color=_COLORS["grid"], linewidth=0.5)
    ax_b.legend(loc="lower left", ncol=2)
    _short_heading(ax_b, "Independent replication")
    _panel_label(ax_b, "b", x=-0.20, y=1.10)

    interactions = contrasts[contrasts["contrast"] != "AI_HOSTING_GAIN"].copy()
    interaction_order = (
        ("AI_BESS_INTERACTION", "False", "BESS | PV off"),
        ("AI_BESS_INTERACTION", "True", "BESS | PV on"),
        ("AI_PV_INTERACTION", "False", "PV | BESS off"),
        ("AI_PV_INTERACTION", "True", "PV | BESS on"),
    )
    y_positions = np.arange(len(interaction_order), dtype=float)
    margin = _float(_numeric(interactions, "equivalence_margin_kw").max())
    ax_c.axvspan(-margin, margin, color=_COLORS["light"], alpha=0.95)
    for offset, split, color, marker in (
        (-0.09, "development", _COLORS["muted"], "o"),
        (0.09, "validation", _COLORS["blue"], "s"),
    ):
        for interaction_y, (contrast_name, level, _) in zip(
            y_positions,
            interaction_order,
            strict=True,
        ):
            row = interactions[
                (interactions["evaluation_split"] == split)
                & (interactions["contrast"] == contrast_name)
                & (interactions["conditioning_level"].astype(str) == level)
            ].iloc[0]
            estimate = _float(row["estimate_mean_kw"])
            ax_c.errorbar(
                estimate,
                interaction_y + offset,
                xerr=np.array(
                    [
                        [estimate - _float(row["simultaneous_ci_lower_kw"])],
                        [_float(row["simultaneous_ci_upper_kw"]) - estimate],
                    ]
                ),
                fmt=marker,
                color=color,
                capsize=2,
                markersize=4,
                linewidth=1.0,
            )
    ax_c.axvline(0, color=_COLORS["neutral"], linewidth=0.7)
    ax_c.set_yticks(y_positions, [label for _, _, label in interaction_order])
    ax_c.invert_yaxis()
    ax_c.set_xlabel("Difference-in-differences (kW)")
    ax_c.grid(axis="x", color=_COLORS["grid"], linewidth=0.5)
    ax_c.text(
        0.98,
        0.04,
        "grey band: ± practical margin",
        transform=ax_c.transAxes,
        fontsize=6.0,
        color=_COLORS["neutral"],
        ha="right",
        va="bottom",
    )
    _short_heading(ax_c, "AI–DER interaction")
    _panel_label(ax_c, "c", x=-0.20, y=1.10)

    figure.subplots_adjust(left=0.12, right=0.97, bottom=0.10, top=0.94)
    return _finalize_figure(
        figure,
        figure_number=4,
        source_manifest_path=manifest_path,
        source_tables=("fig4_hosting_capacity_summary", "fig4_hosting_paired_contrasts"),
        output_directory=output_directory,
        stem="figure_4_hosting_capacity_interactions",
        formats=formats,
        core_conclusion=(
            "Workload flexibility increases community data-centre hosting capacity, while "
            "its value interacts non-additively with photovoltaic generation and batteries."
        ),
        claim_boundaries=(
            "Hosting calculations are planning-result ensembles rather than real-world causal effects.",
            "AI–BESS substitution replicates; with BESS, the validation AI–PV interaction is directionally positive but practically indeterminate.",
        ),
        archetype="asymmetric quantitative figure",
    )


def _sensitivity_range(
    frame: pd.DataFrame,
    *,
    case_column: str,
    value_column: str,
    duration: int,
) -> tuple[float, float, str, str]:
    subset = frame[
        (~frame[case_column].astype(str).eq("reference"))
        & np.isclose(_numeric(frame, "duration_h"), duration)
    ].copy()
    values = _numeric(subset, value_column)
    minimum_index = values.idxmin()
    maximum_index = values.idxmax()
    return (
        _float(values.loc[minimum_index]),
        _float(values.loc[maximum_index]),
        str(subset.loc[minimum_index, case_column]),
        str(subset.loc[maximum_index, case_column]),
    )


def plot_nature_mainline_figure5_reference_style(
    source_data_directory: str | Path,
    output_directory: str | Path,
    *,
    formats: Sequence[str] = ("svg", "pdf", "tiff", "png"),
) -> dict[str, object]:
    """Plot compact sensitivity ranges above a dominant generalization boundary."""

    _publication_style()
    manifest_path, manifest = _load_manifest(source_data_directory)
    power = _verified_table(source_data_directory, manifest, "fig5_power_case_sensitivity")
    workload = _verified_table(source_data_directory, manifest, "fig5_workload_sensitivity")
    criteria = _verified_table(source_data_directory, manifest, "fig5_success_criteria_sensitivity")
    infrastructure = _verified_table(
        source_data_directory,
        manifest,
        "fig5_infrastructure_sensitivity",
    )
    locked_id = _verified_table(
        source_data_directory,
        manifest,
        "fig2_fig5_locked_id_certificates",
    )
    locked_ood = _verified_table(
        source_data_directory,
        manifest,
        "fig5_locked_ood_certificates",
    )

    criteria_plot = criteria.copy()
    criteria_reference = criteria_plot[criteria_plot["criteria_case"] == "reference"].set_index(
        "duration_h"
    )
    criteria_plot["capacity_delta_kw"] = [
        _float(row.perfect_information_firm_capacity_kw)
        - _float(
            criteria_reference.loc[
                _int(row.duration_h),
                "perfect_information_firm_capacity_kw",
            ]
        )
        for row in criteria_plot.itertuples(index=False)
    ]

    figure = plt.figure(figsize=(_FIGURE_WIDTH_IN, 4.9), constrained_layout=False)
    grid = figure.add_gridspec(
        2,
        12,
        height_ratios=(0.85, 1.15),
        hspace=0.68,
        wspace=1.10,
    )
    ax_a = figure.add_subplot(grid[0, :4])
    ax_b = figure.add_subplot(grid[0, 4:])
    ax_c = figure.add_subplot(grid[1, :])

    q95_power = power[np.isclose(_numeric(power, "reliability_target"), 0.95)]
    for case, color, linestyle in (
        ("lower", _COLORS["gold"], "--"),
        ("nominal", _COLORS["blue"], "-"),
        ("upper", _COLORS["purple"], ":"),
    ):
        subset = q95_power[q95_power["power_case"] == case].sort_values("duration_h")
        x_values = _numeric(subset, "duration_h").to_numpy(dtype=float)
        y_values = _numeric(
            subset,
            "perfect_information_firm_capacity_kw",
        ).to_numpy(dtype=float)
        ax_a.plot(
            x_values,
            y_values,
            color=color,
            linestyle=linestyle,
            linewidth=1.6,
            marker="o",
            markersize=3.5,
            label=case.capitalize(),
        )
    ax_a.set_xlim(0.8, 9.0)
    ax_a.set_xticks([1, 2, 3, 4, 6, 8])
    ax_a.set_xlabel("Duration (h)")
    ax_a.set_ylabel("PI capacity (kW)")
    ax_a.grid(axis="y", color=_COLORS["grid"], linewidth=0.5)
    ax_a.legend(loc="lower left", handlelength=1.8)
    _short_heading(ax_a, "Power-model uncertainty")
    _panel_label(ax_a, "a", x=-0.22, y=1.10)

    groups = (
        (
            "Workload",
            workload,
            "workload_case",
            "firm_capacity_delta_from_reference_kw",
            _COLORS["blue"],
        ),
        (
            "Success criteria",
            criteria_plot,
            "criteria_case",
            "capacity_delta_kw",
            _COLORS["purple"],
        ),
        (
            "Infrastructure",
            infrastructure,
            "infrastructure_case",
            "firm_capacity_delta_from_reference_kw",
            _COLORS["gold"],
        ),
    )
    y_positions: list[float] = []
    y_labels: list[str] = []
    cursor = 0.0
    for group_name, frame, case_column, value_column, color in groups:
        for duration_h, offset in ((4, 0.0), (8, 0.32)):
            minimum, maximum, _minimum_case, _maximum_case = _sensitivity_range(
                frame,
                case_column=case_column,
                value_column=value_column,
                duration=duration_h,
            )
            y_value = cursor + offset
            ax_b.plot(
                [minimum, maximum],
                [y_value, y_value],
                color=color,
                linewidth=4.0,
                solid_capstyle="round",
                alpha=0.72 if duration_h == 4 else 1.0,
            )
            ax_b.scatter(
                [minimum, maximum],
                [y_value, y_value],
                color=color,
                s=18,
                zorder=3,
            )
            y_positions.append(y_value)
            y_labels.append(f"{group_name} · H={duration_h} h")
        cursor += 1.15
    ax_b.axvline(0, color=_COLORS["neutral"], linewidth=0.7)
    ax_b.set_yticks(y_positions, y_labels)
    ax_b.invert_yaxis()
    ax_b.set_xlabel("Range of capacity change from reference (kW)")
    ax_b.grid(axis="x", color=_COLORS["grid"], linewidth=0.5)
    _short_heading(ax_b, "Predeclared sensitivity envelope")
    _panel_label(ax_b, "b", x=-0.13, y=1.10)

    q95_id = locked_id[
        np.isclose(_numeric(locked_id, "reliability_target"), 0.95)
        & np.isclose(_numeric(locked_id, "notice_h"), 0)
    ].sort_values("duration_h")
    q95_ood = locked_ood[
        np.isclose(_numeric(locked_ood, "reliability_target"), 0.95)
        & np.isclose(_numeric(locked_ood, "notice_h"), 0)
    ].sort_values("duration_h")
    duration_values = _numeric(q95_id, "duration_h").to_numpy(dtype=float)
    id_lower = _numeric(q95_id, "wilson_lower_confidence_bound").to_numpy(dtype=float)
    ood_lower = _numeric(q95_ood, "wilson_lower_confidence_bound").to_numpy(dtype=float)
    id_flags = _bool_series(q95_id["certified"]).to_numpy(dtype=bool)

    ax_c.fill_between(
        duration_values,
        ood_lower,
        id_lower,
        color=_COLORS["pale_red"],
        alpha=0.90,
        linewidth=0,
    )
    ax_c.plot(
        duration_values,
        id_lower,
        color=_COLORS["blue"],
        linewidth=2.2,
        marker="o",
    )
    ax_c.plot(
        duration_values,
        ood_lower,
        color=_COLORS["red"],
        linewidth=2.2,
        marker="s",
    )
    ax_c.scatter(
        duration_values[~id_flags],
        id_lower[~id_flags],
        facecolors="white",
        edgecolors=_COLORS["red"],
        marker="X",
        s=38,
        linewidths=1.0,
        zorder=5,
    )
    ax_c.axhline(0.95, color=_COLORS["neutral"], linestyle="--", linewidth=1.0)
    _direct_label(
        ax_c,
        duration_values[-1],
        id_lower[-1],
        "Locked-ID",
        color=_COLORS["blue"],
        dx=0.12,
    )
    _direct_label(
        ax_c,
        duration_values[-1],
        ood_lower[-1],
        "Locked-OOD fixed replay",
        color=_COLORS["red"],
        dx=0.12,
    )
    ax_c.text(
        8.12,
        0.95,
        "target q=0.95",
        fontsize=6.3,
        color=_COLORS["neutral"],
        ha="left",
        va="center",
        clip_on=False,
    )
    ax_c.set_xlim(0.8, 9.8)
    ax_c.set_ylim(0.70, 1.005)
    ax_c.set_xticks(duration_values)
    ax_c.set_xlabel("Event duration (h)")
    ax_c.set_ylabel("One-sided 95% Wilson lower bound")
    ax_c.grid(axis="y", color=_COLORS["grid"], linewidth=0.55)
    ax_c.text(
        0.01,
        0.04,
        "OOD protocol replays validation-selected candidates; it does not re-estimate OOD capacity.",
        transform=ax_c.transAxes,
        fontsize=6.2,
        color=_COLORS["neutral"],
        ha="left",
        va="bottom",
    )
    _short_heading(ax_c, "Independent certification reveals the generalization boundary")
    _panel_label(ax_c, "c", x=-0.075, y=1.08)

    figure.subplots_adjust(left=0.11, right=0.95, bottom=0.10, top=0.94)
    return _finalize_figure(
        figure,
        figure_number=5,
        source_manifest_path=manifest_path,
        source_tables=(
            "fig5_power_case_sensitivity",
            "fig5_workload_sensitivity",
            "fig5_success_criteria_sensitivity",
            "fig5_infrastructure_sensitivity",
            "fig2_fig5_locked_id_certificates",
            "fig5_locked_ood_certificates",
        ),
        output_directory=output_directory,
        stem="figure_5_robustness_generalization",
        formats=formats,
        core_conclusion=(
            "The main mechanisms persist across predeclared parameter sensitivities, but "
            "validation-selected fixed candidates do not retain target reliability under "
            "the declared joint OOD shift."
        ),
        claim_boundaries=(
            "Sensitivity results are development PI planning bounds rather than causal certificates.",
            "Zero locked-OOD certified cells does not imply zero OOD firm capacity because OOD reselection was prohibited.",
            "The locked-ID H=1 q=0.95 candidate remains uncertified and is retained as a boundary result.",
        ),
        archetype="asymmetric quantitative figure",
    )


_REFERENCE_PLOTTERS: dict[int, Callable[..., dict[str, object]]] = {
    1: plot_nature_mainline_figure1_reference_style,
    2: plot_nature_mainline_figure2_reference_style,
    3: plot_nature_mainline_figure3_reference_style,
    4: plot_nature_mainline_figure4_reference_style,
    5: plot_nature_mainline_figure5_reference_style,
}


def _portable_figure_record(record: dict[str, object]) -> dict[str, object]:
    portable = dict(record)
    manifest = portable.get("manifest")
    if isinstance(manifest, str):
        portable["manifest"] = Path(manifest).name
    outputs = portable.get("outputs")
    if isinstance(outputs, list):
        portable_outputs: list[dict[str, object]] = []
        for output in outputs:
            if not isinstance(output, dict):
                raise ValueError("figure output record must be a mapping")
            portable_output = dict(output)
            path = portable_output.get("path")
            if isinstance(path, str):
                portable_output["path"] = Path(path).name
            portable_outputs.append(portable_output)
        portable["outputs"] = portable_outputs
    return portable


def plot_nature_mainline_figures_reference_style(
    source_data_directory: str | Path,
    output_directory: str | Path,
    *,
    figures: Sequence[int] = (1, 2, 3, 4, 5),
    formats: Sequence[str] = ("svg", "pdf", "tiff", "png"),
) -> dict[str, object]:
    """Generate selected reference-led figures and a portable bundle manifest."""

    requested = tuple(_int(value) for value in figures)
    if not requested:
        raise ValueError("at least one figure number is required")
    unsupported = sorted(set(requested).difference(_REFERENCE_PLOTTERS))
    if unsupported:
        raise ValueError(f"unsupported Nature mainline figures: {unsupported}")

    destination = Path(output_directory).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    records = [
        _REFERENCE_PLOTTERS[number](
            source_data_directory,
            destination,
            formats=formats,
        )
        for number in requested
    ]
    portable_records = [_portable_figure_record(record) for record in records]
    index: dict[str, object] = {
        "schema_version": "aidrbench.nature_figure_bundle.v2.reference_style",
        "figures": portable_records,
    }
    index_path = destination / "nature_mainline_figure_manifest.json"
    index_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "figure_count": len(records),
        "figures": records,
        "manifest": str(index_path),
        "output_directory": str(destination),
    }


# Public aliases used by focused tests and downstream scripts.
plot_nature_mainline_figure2 = plot_nature_mainline_figure2_reference_style
plot_nature_mainline_figures = plot_nature_mainline_figures_reference_style
