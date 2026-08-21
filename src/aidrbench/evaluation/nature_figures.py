"""Submission-grade figures for the frozen Nature Communications mainline."""
# ruff: noqa: E402, E501

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

_matplotlib_cache = Path(tempfile.gettempdir()) / "aidrbench-matplotlib"
_matplotlib_cache.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_matplotlib_cache))

import matplotlib

matplotlib.use("Agg", force=True)

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle
from matplotlib.ticker import NullFormatter, StrMethodFormatter

_COLORS = {
    "ink": "#24313D",
    "neutral": "#5E6973",
    "muted": "#87929B",
    "blue": "#3B7EA1",
    "navy": "#31516E",
    "flex": "#3D9B8F",
    "gold": "#E1A23A",
    "red": "#D5634E",
    "purple": "#776FA3",
    "light": "#EEF2F4",
    "pale_blue": "#DDEAF1",
    "pale_teal": "#DCEFEB",
    "pale_gold": "#F5E8CC",
    "pale_red": "#F3E0DB",
    "grid": "#DCE2E6",
}
_ALLOWED_FORMATS = frozenset({"svg", "pdf", "tiff", "png"})
_FIGURE_WIDTH_MM = 183.0
_FIGURE_WIDTH_IN = _FIGURE_WIDTH_MM / 25.4
# Export contract: figure.svg, figure.pdf, figure.tiff, and figure.png.
_MIN_FONT_PT = 6.5


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest(source_data_directory: str | Path) -> tuple[Path, dict[str, Any]]:
    source_directory = Path(source_data_directory).resolve()
    manifest_path = source_directory / "source_data_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("tables"), list):
        raise ValueError("invalid source-data manifest")
    return manifest_path, document


def _verified_table(
    source_data_directory: str | Path,
    manifest: dict[str, Any],
    table_id: str,
) -> pd.DataFrame:
    source_directory = Path(source_data_directory).resolve()
    records = [
        record
        for record in manifest["tables"]
        if isinstance(record, dict) and record.get("table_id") == table_id
    ]
    if len(records) != 1:
        raise ValueError(f"source-data table must appear exactly once: {table_id}")
    record = records[0]
    output = record.get("output")
    expected_hash = record.get("output_sha256")
    if not isinstance(output, str) or not isinstance(expected_hash, str):
        raise ValueError(f"invalid source-data manifest record: {table_id}")
    path = (source_directory / output).resolve()
    try:
        path.relative_to(source_directory)
    except ValueError as error:
        raise ValueError(f"source-data output escapes bundle: {output}") from error
    if not path.is_file():
        raise FileNotFoundError(path)
    actual_hash = _sha256(path)
    if actual_hash != expected_hash:
        raise ValueError(
            f"source-data hash mismatch for {table_id}: expected {expected_hash}, got {actual_hash}"
        )
    frame = pd.read_csv(path)
    declared_columns = record.get("columns")
    if isinstance(declared_columns, list):
        missing = sorted(set(str(column) for column in declared_columns).difference(frame.columns))
        if missing:
            raise ValueError(f"{table_id}: exported CSV is missing columns: {', '.join(missing)}")
    return frame


def _require_columns(frame: pd.DataFrame, columns: Sequence[str], *, table_id: str) -> None:
    missing = sorted(set(columns).difference(frame.columns))
    if missing:
        raise ValueError(f"{table_id}: missing required columns: {', '.join(missing)}")


def _publication_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Arial",
                "Liberation Sans",
                "Helvetica",
                "Nimbus Sans",
                "DejaVu Sans",
                "sans-serif",
            ],
            "font.size": 7.0,
            "axes.titlesize": 7.5,
            "axes.labelsize": 7.0,
            "xtick.labelsize": 6.5,
            "ytick.labelsize": 6.5,
            "legend.fontsize": 6.5,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.7,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "xtick.major.size": 2.5,
            "ytick.major.size": 2.5,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": "aidrbench-nature-mainline-v1",
        }
    )


def _panel_label(
    axis: Axes,
    label: str,
    *,
    x: float = -0.12,
    y: float = 1.06,
) -> None:
    axis.text(
        x,
        y,
        label,
        transform=axis.transAxes,
        fontsize=9,
        fontweight="bold",
        va="top",
        ha="left",
    )


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="raise")


def _float(value: object) -> float:
    return float(str(value))


def _int(value: object) -> int:
    return int(float(str(value)))


def _as_bool(value: object) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes"}


def _bool_series(series: pd.Series) -> pd.Series:
    return series.map(_as_bool)


def _portfolio_label(pv: object, bess: object) -> str:
    return f"PV {'on' if _as_bool(pv) else 'off'}\nBESS {'on' if _as_bool(bess) else 'off'}"


def _format_outputs(
    figure: Figure,
    *,
    output_directory: Path,
    stem: str,
    formats: Sequence[str],
) -> list[dict[str, object]]:
    normalized = tuple(str(item).lower() for item in formats)
    unsupported = sorted(set(normalized).difference(_ALLOWED_FORMATS))
    if unsupported:
        raise ValueError(f"unsupported figure formats: {', '.join(unsupported)}")
    if not normalized:
        raise ValueError("at least one figure format is required")
    output_directory.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    for extension in normalized:
        path = output_directory / f"{stem}.{extension}"
        dpi = 600 if extension == "tiff" else 300
        if extension == "svg":
            figure.savefig(
                path,
                dpi=dpi,
                metadata={"Creator": "AIDRBench", "Date": None},
            )
        elif extension == "pdf":
            figure.savefig(
                path,
                dpi=dpi,
                metadata={
                    "Creator": "AIDRBench",
                    "CreationDate": None,
                    "ModDate": None,
                },
            )
        elif extension == "tiff":
            figure.savefig(
                path,
                dpi=dpi,
                pil_kwargs={"compression": "tiff_lzw"},
            )
        else:
            figure.savefig(path, dpi=dpi)
        records.append(
            {
                "format": extension,
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return records


def _write_figure_manifest(
    *,
    figure_number: int,
    output_directory: Path,
    source_manifest_path: Path,
    source_tables: Sequence[str],
    outputs: list[dict[str, object]],
    physical_size_inches: Sequence[float],
    core_conclusion: str,
    claim_boundaries: Sequence[str],
    archetype: str,
) -> dict[str, object]:
    manifest: dict[str, object] = {
        "schema_version": "aidrbench.nature_figure_manifest.v1",
        "figure": figure_number,
        "backend": "python_matplotlib",
        "archetype": archetype,
        "core_conclusion": core_conclusion,
        "claim_boundaries": list(claim_boundaries),
        "physical_size_inches": list(physical_size_inches),
        "minimum_configured_font_pt": _MIN_FONT_PT,
        "source_tables": list(source_tables),
        "source_data_manifest_sha256": _sha256(source_manifest_path),
        "outputs": outputs,
    }
    path = output_directory / f"figure_{figure_number}_manifest.json"
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    runtime_outputs: list[dict[str, object]] = []
    for output in outputs:
        filename = output.get("path")
        if not isinstance(filename, str):
            raise ValueError("figure output manifest path must be a filename")
        runtime_output = dict(output)
        runtime_output["path"] = str(output_directory / filename)
        runtime_outputs.append(runtime_output)
    return {
        "figure": figure_number,
        "outputs": runtime_outputs,
        "manifest": str(path),
    }


def _finalize_figure(
    figure: Figure,
    *,
    figure_number: int,
    source_manifest_path: Path,
    source_tables: Sequence[str],
    output_directory: str | Path,
    stem: str,
    formats: Sequence[str],
    core_conclusion: str,
    claim_boundaries: Sequence[str],
    archetype: str,
) -> dict[str, object]:
    destination = Path(output_directory).resolve()
    size = tuple(float(value) for value in figure.get_size_inches())
    outputs = _format_outputs(
        figure,
        output_directory=destination,
        stem=stem,
        formats=formats,
    )
    plt.close(figure)
    return _write_figure_manifest(
        figure_number=figure_number,
        output_directory=destination,
        source_manifest_path=source_manifest_path,
        source_tables=source_tables,
        outputs=outputs,
        physical_size_inches=size,
        core_conclusion=core_conclusion,
        claim_boundaries=claim_boundaries,
        archetype=archetype,
    )


def plot_nature_mainline_figure1(
    source_data_directory: str | Path,
    output_directory: str | Path,
    *,
    formats: Sequence[str] = ("svg", "pdf", "tiff", "png"),
) -> dict[str, object]:
    """Plot nominal-to-job-derived physical gap and the measurement anchor."""

    _publication_style()
    manifest_path, manifest = _load_manifest(source_data_directory)
    pi = _verified_table(source_data_directory, manifest, "fig1_fig2_pi_firm_boundaries")
    calibration = _verified_table(source_data_directory, manifest, "fig1_calibration_run_means")
    _require_columns(
        pi,
        (
            "duration_h",
            "reliability_target",
            "perfect_information_firm_capacity_kw",
            "nominal_flexibility_kw",
            "physical_gap_kw",
        ),
        table_id="fig1_fig2_pi_firm_boundaries",
    )
    _require_columns(
        calibration,
        ("mode", "gpu_count", "repeat", "gpu_index", "mean_power_w"),
        table_id="fig1_calibration_run_means",
    )

    q95 = pi[np.isclose(_numeric(pi, "reliability_target"), 0.95)].copy()
    q95 = q95.sort_values("duration_h")
    durations = _numeric(q95, "duration_h").to_numpy(dtype=float)
    nominal = _numeric(q95, "nominal_flexibility_kw").to_numpy(dtype=float)
    firm = _numeric(q95, "perfect_information_firm_capacity_kw").to_numpy(dtype=float)
    gap_pct = 100.0 * (nominal - firm) / nominal

    figure = plt.figure(figsize=(_FIGURE_WIDTH_IN, 4.55), constrained_layout=True)
    grid = figure.add_gridspec(2, 2, width_ratios=(1.25, 1.0), height_ratios=(1.0, 0.9))
    ax_a = figure.add_subplot(grid[0, 0])
    ax_b = figure.add_subplot(grid[1, 0])
    ax_c = figure.add_subplot(grid[0, 1])
    ax_d = figure.add_subplot(grid[1, 1])

    ax_a.plot(durations, nominal, color=_COLORS["neutral"], marker="o", label="Nominal proxy")
    ax_a.plot(durations, firm, color=_COLORS["blue"], marker="o", label="PI firm boundary")
    ax_a.fill_between(durations, firm, nominal, color=_COLORS["light"], alpha=0.8)
    ax_a.set_xlabel("Event duration (h)")
    ax_a.set_ylabel("Capacity (kW)")
    ax_a.set_title("Job constraints remove nearly half of nominal flexibility", loc="left")
    ax_a.set_xticks(durations)
    ax_a.grid(axis="y", color=_COLORS["grid"], linewidth=0.5)
    ax_a.legend(loc="lower left")
    _panel_label(ax_a, "a")

    ax_b.plot(durations, gap_pct, color=_COLORS["red"], marker="o")
    ax_b.fill_between(durations, 0, gap_pct, color=_COLORS["red"], alpha=0.10)
    for x_value, y_value in zip(durations, gap_pct, strict=True):
        ax_b.text(x_value, y_value + 1.1, f"{y_value:.1f}%", ha="center", va="bottom")
    ax_b.set_ylim(0, max(70.0, float(gap_pct.max()) + 8.0))
    ax_b.set_xticks(durations)
    ax_b.set_xlabel("Event duration (h)")
    ax_b.set_ylabel("Overstatement (% of nominal)")
    ax_b.set_title("Overstatement grows with event duration", loc="left")
    ax_b.grid(axis="y", color=_COLORS["grid"], linewidth=0.5)
    _panel_label(ax_b, "b")

    grouped: pd.DataFrame = (
        calibration.groupby(["mode", "gpu_count", "repeat"], as_index=False)
        .mean(numeric_only=True)
        .sort_values(["mode", "gpu_count", "repeat"])
    )
    categories = [
        ("training", 1),
        ("training", 4),
        ("offline_inference", 1),
        ("offline_inference", 4),
    ]
    labels = ["Training\n1 GPU", "Training\n4 GPUs", "Inference\n1 GPU", "Inference\n4 GPUs"]
    for index, (mode, count) in enumerate(categories):
        subset = grouped[(grouped["mode"] == mode) & (_numeric(grouped, "gpu_count") == count)]
        values = _numeric(subset, "mean_power_w").to_numpy(dtype=float)
        offsets = np.linspace(-0.10, 0.10, len(values)) if len(values) > 1 else np.array([0.0])
        color = _COLORS["purple"] if mode == "training" else _COLORS["flex"]
        ax_c.scatter(index + offsets, values, s=18, color=color, zorder=3)
        ax_c.hlines(
            float(values.mean()), index - 0.18, index + 0.18, color=_COLORS["neutral"], lw=1.4
        )
    ax_c.set_xticks(range(len(labels)), labels)
    ax_c.set_ylabel("Mean GPU-board power (W)")
    ax_c.set_title("Measured four-GPU runs anchor class-aware power", loc="left")
    ax_c.grid(axis="y", color=_COLORS["grid"], linewidth=0.5)
    _panel_label(ax_c, "c")

    ax_d.set_axis_off()
    layers = [
        ("Nominal", "Fixed fraction\nof operating peak", _COLORS["neutral"]),
        ("PI", "Job-feasible\nphysical upper bound", _COLORS["gold"]),
        ("Restricted NA", "Finite-scenario\ninformation bound", _COLORS["purple"]),
        ("Causal", "Independent locked-ID\ncapacity test", _COLORS["blue"]),
    ]
    y_positions = np.linspace(0.82, 0.15, len(layers))
    for index, ((title, subtitle, color), y_value) in enumerate(
        zip(layers, y_positions, strict=True)
    ):
        box = FancyBboxPatch(
            (0.12, y_value - 0.08),
            0.76,
            0.14,
            boxstyle="round,pad=0.015,rounding_size=0.02",
            linewidth=1.0,
            edgecolor=color,
            facecolor="white",
            transform=ax_d.transAxes,
        )
        ax_d.add_patch(box)
        ax_d.text(0.18, y_value, title, transform=ax_d.transAxes, fontweight="bold", va="center")
        ax_d.text(0.42, y_value, subtitle, transform=ax_d.transAxes, va="center")
        if index < len(layers) - 1:
            arrow = FancyArrowPatch(
                (0.50, y_value - 0.09),
                (0.50, y_positions[index + 1] + 0.08),
                arrowstyle="-|>",
                mutation_scale=8,
                linewidth=0.8,
                color=_COLORS["neutral"],
                transform=ax_d.transAxes,
            )
            ax_d.add_patch(arrow)
    ax_d.set_title("Four evidence layers prevent nominal capacity claims", loc="left")
    _panel_label(ax_d, "d")

    return _finalize_figure(
        figure,
        figure_number=1,
        source_manifest_path=manifest_path,
        source_tables=("fig1_fig2_pi_firm_boundaries", "fig1_calibration_run_means"),
        output_directory=output_directory,
        stem="figure_1_nominal_job_derived_gap",
        formats=formats,
        core_conclusion=(
            "A fixed nominal flexibility fraction substantially overstates the job-derived "
            "firm boundary across all tested event durations."
        ),
        claim_boundaries=(
            "PI is a perfect-information planning upper bound, not an independently certified capacity.",
            "The four-GPU measurements anchor class-aware board power; they do not directly represent a megawatt-scale data centre.",
        ),
        archetype="schematic-led composite",
    )


def plot_nature_mainline_figure2(
    source_data_directory: str | Path,
    output_directory: str | Path,
    *,
    formats: Sequence[str] = ("svg", "pdf", "tiff", "png"),
) -> dict[str, object]:
    """Plot duration, reliability and notice effects with locked-ID certification."""

    _publication_style()
    manifest_path, manifest = _load_manifest(source_data_directory)
    pi = _verified_table(source_data_directory, manifest, "fig1_fig2_pi_firm_boundaries")
    na = _verified_table(source_data_directory, manifest, "fig2_restricted_na_surface")
    diagnostics = _verified_table(
        source_data_directory, manifest, "fig2_notice_mechanism_diagnostics"
    )
    certificates = _verified_table(
        source_data_directory, manifest, "fig2_fig5_locked_id_certificates"
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

    figure = plt.figure(figsize=(_FIGURE_WIDTH_IN, 5.20), constrained_layout=True)
    grid = figure.add_gridspec(2, 2, height_ratios=(1.1, 1.0), width_ratios=(1.15, 1.0))
    ax_a = figure.add_subplot(grid[0, 0])
    ax_b = figure.add_subplot(grid[0, 1])
    ax_c = figure.add_subplot(grid[1, 0])
    ax_d = figure.add_subplot(grid[1, 1])

    duration = _numeric(q95_pi, "duration_h").to_numpy(dtype=float)
    ax_a.plot(
        duration,
        _numeric(q95_pi, "nominal_flexibility_kw"),
        marker="o",
        color=_COLORS["neutral"],
        label="Nominal",
    )
    ax_a.plot(
        duration,
        _numeric(q95_pi, "perfect_information_firm_capacity_kw"),
        marker="o",
        color=_COLORS["gold"],
        label="PI tolerance bound",
    )
    ax_a.plot(
        _numeric(q95_na, "duration_h"),
        _numeric(q95_na, "non_anticipative_capacity_kw"),
        marker="s",
        color=_COLORS["purple"],
        label="Restricted NA",
    )
    certified = _bool_series(q95_cert["certified"])
    ax_a.plot(
        _numeric(q95_cert, "duration_h"),
        _numeric(q95_cert, "candidate_reduction_kw"),
        color=_COLORS["blue"],
        linewidth=1.2,
        label="Fixed causal candidate",
    )
    ax_a.scatter(
        _numeric(q95_cert.loc[certified], "duration_h"),
        _numeric(q95_cert.loc[certified], "candidate_reduction_kw"),
        color=_COLORS["blue"],
        s=25,
        zorder=4,
    )
    ax_a.scatter(
        _numeric(q95_cert.loc[~certified], "duration_h"),
        _numeric(q95_cert.loc[~certified], "candidate_reduction_kw"),
        facecolors="white",
        edgecolors=_COLORS["red"],
        marker="X",
        s=35,
        linewidths=1.0,
        zorder=5,
    )
    if (~certified).any():
        failed = q95_cert.loc[~certified].iloc[0]
        ax_a.annotate(
            "Not certified on locked-ID",
            xy=(float(failed["duration_h"]), float(failed["candidate_reduction_kw"])),
            xytext=(2.0, 67.0),
            arrowprops={"arrowstyle": "->", "lw": 0.7, "color": _COLORS["red"]},
            color=_COLORS["red"],
        )
    ax_a.set_xticks(duration)
    ax_a.set_xlabel("Event duration (h)")
    ax_a.set_ylabel("Capacity (kW)")
    ax_a.set_title("Capacity falls as events lengthen", loc="left")
    ax_a.grid(axis="y", color=_COLORS["grid"], linewidth=0.5)
    ax_a.legend(ncol=2, loc="upper right")
    _panel_label(ax_a, "a")

    for reliability, color, marker in (
        (0.90, _COLORS["flex"], "o"),
        (0.95, _COLORS["blue"], "s"),
        (0.99, _COLORS["red"], "^"),
    ):
        subset = certificates[
            np.isclose(_numeric(certificates, "reliability_target"), reliability)
            & np.isclose(_numeric(certificates, "notice_h"), 0)
        ].sort_values("duration_h")
        flags = _bool_series(subset["certified"])
        ax_b.plot(
            _numeric(subset, "duration_h"),
            _numeric(subset, "candidate_reduction_kw"),
            color=color,
            linewidth=1.0,
            label=f"q={reliability:.2f}",
        )
        ax_b.scatter(
            _numeric(subset.loc[flags], "duration_h"),
            _numeric(subset.loc[flags], "candidate_reduction_kw"),
            color=color,
            marker=marker,
            s=24,
            zorder=3,
        )
        ax_b.scatter(
            _numeric(subset.loc[~flags], "duration_h"),
            _numeric(subset.loc[~flags], "candidate_reduction_kw"),
            facecolors="white",
            edgecolors=color,
            marker=marker,
            s=28,
            linewidths=1.0,
            zorder=3,
        )
    ax_b.set_xticks(duration)
    ax_b.set_xlabel("Event duration (h)")
    ax_b.set_ylabel("Validation-selected candidate (kW)")
    ax_b.set_title("Higher reliability reduces selectable capacity", loc="left")
    ax_b.grid(axis="y", color=_COLORS["grid"], linewidth=0.5)
    ax_b.legend(loc="upper right")
    ax_b.text(
        0.02,
        0.03,
        "Filled: certified\nOpen: not certified",
        transform=ax_b.transAxes,
        va="bottom",
    )
    _panel_label(ax_b, "b")

    heat = certificates[np.isclose(_numeric(certificates, "reliability_target"), 0.95)].copy()
    pivot = heat.pivot(index="notice_h", columns="duration_h", values="candidate_reduction_kw")
    pivot = pivot.sort_index().sort_index(axis=1)
    image = ax_c.imshow(
        pivot.to_numpy(dtype=float),
        aspect="auto",
        cmap=LinearSegmentedColormap.from_list(
            "aidr_capacity", [_COLORS["light"], _COLORS["blue"]]
        ),
    )
    for row_index in range(pivot.shape[0]):
        for column_index in range(pivot.shape[1]):
            value = _float(pivot.iloc[row_index, column_index])
            ax_c.text(
                column_index,
                row_index,
                f"{value:.1f}",
                ha="center",
                va="center",
                fontsize=6.5,
            )
    ax_c.set_xticks(range(len(pivot.columns)), [str(int(value)) for value in pivot.columns])
    ax_c.set_yticks(range(len(pivot.index)), [str(int(value)) for value in pivot.index])
    ax_c.set_xlabel("Event duration (h)")
    ax_c.set_ylabel("Advance notice (h)")
    ax_c.set_title("Notice changes no selected capacity in Model A", loc="left")
    colorbar = figure.colorbar(image, ax=ax_c, fraction=0.045, pad=0.03)
    colorbar.set_label("Candidate reduction (kW)")
    _panel_label(ax_c, "c")

    notice = diagnostics[np.isclose(_numeric(diagnostics, "notice_h"), 6)].sort_values("duration_h")
    y_positions = np.arange(len(notice), dtype=float)
    eligible = _numeric(notice, "eligible_pre_execution_work_gpu_h_mean").to_numpy(dtype=float)
    spare = _numeric(notice, "pre_event_spare_capacity_gpu_h_mean").to_numpy(dtype=float)
    ax_d.barh(
        y_positions + 0.16,
        eligible,
        height=0.28,
        color=_COLORS["gold"],
        label="Eligible work",
    )
    ax_d.barh(
        y_positions - 0.16,
        spare,
        height=0.28,
        color=_COLORS["flex"],
        label="Spare capacity",
    )
    if np.any(eligible <= 0) or np.any(spare <= 0):
        raise ValueError("notice-mechanism quantities must be strictly positive on a log axis")
    ax_d.set_xscale("log")
    ax_d.xaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax_d.xaxis.set_minor_formatter(NullFormatter())
    ax_d.set_yticks(
        y_positions,
        [f"H={int(value)} h" for value in _numeric(notice, "duration_h")],
    )
    ax_d.set_xlabel("Pre-event quantity (GPU-h, log scale)")
    ax_d.set_title("Eligible work exceeds usable pre-execution headroom", loc="left")
    ax_d.grid(axis="x", color=_COLORS["grid"], linewidth=0.5)
    ax_d.legend(loc="lower right")
    for y_value, (_, row) in zip(y_positions, notice.iterrows(), strict=True):
        ax_d.text(
            0.98,
            y_value + 0.36,
            f"ΔPI={_float(row['pi_notice_gain_kw']):.1f} kW; "
            f"ΔNA={_float(row['na_notice_gain_kw']):.1f} kW",
            transform=ax_d.get_yaxis_transform(),
            ha="right",
            va="center",
            color=_COLORS["neutral"],
        )
    _panel_label(ax_d, "d")

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
            "Duration and reliability shape firm capacity, whereas advance notice alters "
            "available scheduling information but produces zero capacity gain under Model A."
        ),
        claim_boundaries=(
            "PI tolerance, restricted NA and locked-ID causal layers have different statistical interpretations.",
            "Certification is interval-wise rather than simultaneous over the complete surface.",
            "The q=0.95 H=1 candidate remains visibly not certified.",
        ),
        archetype="quantitative grid",
    )


def _exhaustion_heatmap(axis: Axes, frame: pd.DataFrame, split: str, title: str) -> None:
    subset = frame[frame["evaluation_split"] == split].copy()
    pivot = subset.pivot(
        index="duration_h",
        columns="recovery_gap_h",
        values="joint_episode_success_fraction",
    ).sort_index()
    cmap = LinearSegmentedColormap.from_list(
        "aidr_success", ["#F4F5F5", _COLORS["flex"], _COLORS["blue"]]
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
            text_color = "white" if value >= 0.65 else _COLORS["neutral"]
            axis.text(
                column_index,
                row_index,
                f"{value:.2f}",
                ha="center",
                va="center",
                color=text_color,
            )
    axis.set_xticks(range(len(pivot.columns)), [str(int(value)) for value in pivot.columns])
    axis.set_yticks(range(len(pivot.index)), [str(int(value)) for value in pivot.index])
    axis.set_xlabel("Recovery gap (h)")
    axis.set_ylabel("Event duration (h)")
    axis.set_title(title, loc="left")
    colorbar = axis.figure.colorbar(image, ax=axis, fraction=0.045, pad=0.03)
    colorbar.set_label("Joint success fraction")


def plot_nature_mainline_figure3(
    source_data_directory: str | Path,
    output_directory: str | Path,
    *,
    formats: Sequence[str] = ("svg", "pdf", "tiff", "png"),
) -> dict[str, object]:
    """Plot compute-debt accumulation and repeated-event service outcomes."""

    _publication_style()
    manifest_path, manifest = _load_manifest(source_data_directory)
    event = _verified_table(source_data_directory, manifest, "fig3_exhaustion_event_summary")
    joint = _verified_table(
        source_data_directory, manifest, "fig3_exhaustion_joint_episode_summary"
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

    figure = plt.figure(figsize=(_FIGURE_WIDTH_IN, 4.75), constrained_layout=True)
    grid = figure.add_gridspec(2, 2)
    ax_a = figure.add_subplot(grid[0, 0])
    ax_b = figure.add_subplot(grid[0, 1])
    ax_c = figure.add_subplot(grid[1, 0])
    ax_d = figure.add_subplot(grid[1, 1])

    for split, linestyle in (("development", "--"), ("validation", "-")):
        for duration, color in ((4, _COLORS["blue"]), (8, _COLORS["red"])):
            subset = averaged[
                (averaged["evaluation_split"] == split)
                & np.isclose(_numeric(averaged, "duration_h"), duration)
            ]
            ax_a.plot(
                _numeric(subset, "event_ordinal"),
                _numeric(subset, "mean_paired_compute_debt_increment_kwh") / 1000.0,
                marker="o",
                linestyle=linestyle,
                color=color,
                label=f"{split.capitalize()}, H={duration} h",
            )
    ax_a.set_xticks([1, 2, 3, 4])
    ax_a.set_xlabel("Event ordinal")
    ax_a.set_ylabel("Paired compute-debt increment (MWh)")
    ax_a.set_title("Compute debt accumulates across repeated calls", loc="left")
    ax_a.grid(axis="y", color=_COLORS["grid"], linewidth=0.5)
    ax_a.legend(ncol=2, loc="upper left")
    _panel_label(ax_a, "a")

    for split, linestyle in (("development", "--"), ("validation", "-")):
        for duration, color in ((4, _COLORS["blue"]), (8, _COLORS["red"])):
            subset = averaged[
                (averaged["evaluation_split"] == split)
                & np.isclose(_numeric(averaged, "duration_h"), duration)
            ]
            ax_b.plot(
                _numeric(subset, "event_ordinal"),
                _numeric(subset, "fixed_commitment_residual_flexibility_ratio"),
                marker="o",
                linestyle=linestyle,
                color=color,
            )
    ax_b.axhline(1.0, color=_COLORS["neutral"], linewidth=0.7, linestyle=":")
    residual = _numeric(averaged, "fixed_commitment_residual_flexibility_ratio")
    ax_b.set_ylim(max(0.97, float(residual.min()) - 0.004), 1.002)
    ax_b.set_xticks([1, 2, 3, 4])
    ax_b.set_xlabel("Event ordinal")
    ax_b.set_ylabel("Residual flexibility ratio")
    ax_b.set_title("Power delivery remains near the fresh-event counterfactual", loc="left")
    ax_b.grid(axis="y", color=_COLORS["grid"], linewidth=0.5)
    _panel_label(ax_b, "b", x=-0.18)

    _exhaustion_heatmap(ax_c, joint, "development", "Development joint-episode success")
    _panel_label(ax_c, "c")
    _exhaustion_heatmap(
        ax_d,
        joint,
        "validation",
        "Independent validation joint-episode success",
    )
    _panel_label(ax_d, "d")

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
            "The repeated-event study is a fixed-capacity mechanism diagnostic, not a "
            "repeated-event firm-capacity certificate.",
            "Recovery gaps help only when the intervening schedule contains sufficient "
            "compute headroom.",
        ),
        archetype="quantitative grid",
    )


def _portfolio_order(frame: pd.DataFrame) -> pd.DataFrame:
    ordered = frame.copy()
    ordered["pv_sort"] = _bool_series(ordered["pv_enabled"]).astype(int)
    ordered["bess_sort"] = _bool_series(ordered["bess_enabled"]).astype(int)
    return ordered.sort_values(["pv_sort", "bess_sort", "dc_operation"])


def plot_nature_mainline_figure4(
    source_data_directory: str | Path,
    output_directory: str | Path,
    *,
    formats: Sequence[str] = ("svg", "pdf", "tiff", "png"),
) -> dict[str, object]:
    """Plot hosting capacity gains and non-additive DER interactions."""

    _publication_style()
    manifest_path, manifest = _load_manifest(source_data_directory)
    summary = _verified_table(source_data_directory, manifest, "fig4_hosting_capacity_summary")
    contrasts = _verified_table(source_data_directory, manifest, "fig4_hosting_paired_contrasts")

    validation = _portfolio_order(summary[summary["evaluation_split"] == "validation"])
    portfolios = (
        validation[["pv_enabled", "bess_enabled"]]
        .drop_duplicates()
        .sort_values(["pv_enabled", "bess_enabled"])
    )
    portfolio_keys = [
        (_as_bool(row.pv_enabled), _as_bool(row.bess_enabled))
        for row in portfolios.itertuples(index=False)
    ]
    labels = [_portfolio_label(pv, bess) for pv, bess in portfolio_keys]

    figure = plt.figure(figsize=(_FIGURE_WIDTH_IN, 5.0), constrained_layout=True)
    grid = figure.add_gridspec(2, 2, width_ratios=(1.05, 1.0), height_ratios=(1.0, 1.0))
    ax_a = figure.add_subplot(grid[0, 0])
    ax_b = figure.add_subplot(grid[0, 1])
    ax_c = figure.add_subplot(grid[1, 0])
    ax_d = figure.add_subplot(grid[1, 1])

    x_positions = np.arange(len(portfolio_keys), dtype=float)
    width = 0.34
    for offset, operation, color in (
        (-width / 2, "rigid", _COLORS["neutral"]),
        (width / 2, "flexible", _COLORS["flex"]),
    ):
        means: list[float] = []
        lower: list[float] = []
        upper: list[float] = []
        for pv, bess in portfolio_keys:
            row = validation[
                (validation["dc_operation"] == operation)
                & (_bool_series(validation["pv_enabled"]) == pv)
                & (_bool_series(validation["bess_enabled"]) == bess)
            ].iloc[0]
            mean_value = float(row["mean_scenario_hosting_dc_peak_kw"])
            means.append(mean_value)
            lower.append(mean_value - float(row["q05_scenario_hosting_dc_peak_kw"]))
            upper.append(float(row["q95_scenario_hosting_dc_peak_kw"]) - mean_value)
        ax_a.bar(
            x_positions + offset,
            means,
            width=width,
            color=color,
            label=operation.capitalize(),
        )
        ax_a.errorbar(
            x_positions + offset,
            means,
            yerr=np.array([lower, upper]),
            fmt="none",
            ecolor="black",
            elinewidth=0.7,
            capsize=2,
        )
    ax_a.set_xticks(x_positions, labels)
    ax_a.set_ylabel("Scenario hosting capacity (kW)")
    ax_a.set_title("Workload flexibility raises validation hosting capacity", loc="left")
    ax_a.grid(axis="y", color=_COLORS["grid"], linewidth=0.5)
    ax_a.legend(loc="upper left")
    _panel_label(ax_a, "a")

    hosting = contrasts[contrasts["contrast"] == "AI_HOSTING_GAIN"].copy()
    for offset, split, color, marker in (
        (-0.10, "development", _COLORS["neutral"], "o"),
        (0.10, "validation", _COLORS["blue"], "s"),
    ):
        subset = hosting[hosting["evaluation_split"] == split].copy()
        values: list[float] = []
        low_errors: list[float] = []
        high_errors: list[float] = []
        for pv, bess in portfolio_keys:
            condition = f"pv={pv},bess={bess}"
            row = subset[subset["conditioning_level"] == condition].iloc[0]
            estimate = _float(row["estimate_mean_kw"])
            values.append(estimate)
            low_errors.append(estimate - _float(row["simultaneous_ci_lower_kw"]))
            high_errors.append(_float(row["simultaneous_ci_upper_kw"]) - estimate)
        ax_b.errorbar(
            x_positions + offset,
            values,
            yerr=np.array([low_errors, high_errors]),
            fmt=marker,
            color=color,
            capsize=2,
            label=split.capitalize(),
        )
    ax_b.axhline(0, color=_COLORS["neutral"], linewidth=0.7)
    ax_b.set_xticks(x_positions, labels)
    ax_b.set_ylabel("Paired AI hosting gain (kW)")
    ax_b.set_title("Positive paired gains replicate independently", loc="left")
    ax_b.grid(axis="y", color=_COLORS["grid"], linewidth=0.5)
    ax_b.legend(loc="lower left")
    _panel_label(ax_b, "b")

    interactions = contrasts[contrasts["contrast"] != "AI_HOSTING_GAIN"].copy()
    interaction_order = [
        ("AI_BESS_INTERACTION", "False", "BESS | PV off"),
        ("AI_BESS_INTERACTION", "True", "BESS | PV on"),
        ("AI_PV_INTERACTION", "False", "PV | BESS off"),
        ("AI_PV_INTERACTION", "True", "PV | BESS on"),
    ]
    y_positions = np.arange(len(interaction_order), dtype=float)
    margin = float(_numeric(interactions, "equivalence_margin_kw").max())
    ax_c.axvspan(
        -margin,
        margin,
        color=_COLORS["light"],
        alpha=0.8,
        label="Practical-equivalence region",
    )
    for offset, split, color, marker in (
        (-0.10, "development", _COLORS["neutral"], "o"),
        (0.10, "validation", _COLORS["blue"], "s"),
    ):
        for y_value, (contrast, level, _) in zip(
            y_positions,
            interaction_order,
            strict=True,
        ):
            row = interactions[
                (interactions["evaluation_split"] == split)
                & (interactions["contrast"] == contrast)
                & (interactions["conditioning_level"].astype(str) == level)
            ].iloc[0]
            estimate = _float(row["estimate_mean_kw"])
            ax_c.errorbar(
                estimate,
                y_value + offset,
                xerr=np.array(
                    [
                        [estimate - _float(row["simultaneous_ci_lower_kw"])],
                        [_float(row["simultaneous_ci_upper_kw"]) - estimate],
                    ]
                ),
                fmt=marker,
                color=color,
                capsize=2,
            )
    ax_c.axvline(0, color=_COLORS["neutral"], linewidth=0.7)
    ax_c.set_yticks(y_positions, [label for _, _, label in interaction_order])
    ax_c.invert_yaxis()
    ax_c.set_xlabel("Difference-in-differences (kW)")
    ax_c.set_title("AI–DER interactions are non-additive", loc="left")
    ax_c.grid(axis="x", color=_COLORS["grid"], linewidth=0.5)
    ax_c.text(0.02, 0.03, "○ Development   ■ Validation", transform=ax_c.transAxes)
    _panel_label(ax_c, "c")

    development_gain = hosting[hosting["evaluation_split"] == "development"].set_index(
        "conditioning_level"
    )
    validation_gain = hosting[hosting["evaluation_split"] == "validation"].set_index(
        "conditioning_level"
    )
    for pv, bess in portfolio_keys:
        key = f"pv={pv},bess={bess}"
        x_value = _float(development_gain.loc[key, "estimate_mean_kw"])
        y_value = _float(validation_gain.loc[key, "estimate_mean_kw"])
        ax_d.scatter(x_value, y_value, color=_COLORS["blue"], s=28)
        ax_d.annotate(
            _portfolio_label(pv, bess).replace("\n", ", "),
            (x_value, y_value),
            xytext=(3, 3),
            textcoords="offset points",
        )
    all_values = np.concatenate(
        [
            _numeric(development_gain.reset_index(), "estimate_mean_kw").to_numpy(dtype=float),
            _numeric(validation_gain.reset_index(), "estimate_mean_kw").to_numpy(dtype=float),
        ]
    )
    plot_min = float(all_values.min()) - 20.0
    plot_max = float(all_values.max()) + 20.0
    ax_d.plot(
        [plot_min, plot_max],
        [plot_min, plot_max],
        color=_COLORS["neutral"],
        linestyle="--",
        linewidth=0.8,
    )
    ax_d.set_xlim(plot_min, plot_max)
    ax_d.set_ylim(plot_min, plot_max)
    ax_d.set_xlabel("Development paired gain (kW)")
    ax_d.set_ylabel("Validation paired gain (kW)")
    ax_d.set_title("Effect direction persists across independent ensembles", loc="left")
    ax_d.grid(color=_COLORS["grid"], linewidth=0.5)
    _panel_label(ax_d, "d")

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
            "Hosting calculations are planning-result ensembles rather than real-world "
            "causal effects.",
            "AI–BESS substitution replicates; with BESS, the validation AI–PV interaction "
            "is directionally positive but practically indeterminate.",
        ),
        archetype="quantitative grid",
    )


def _case_label(value: str) -> str:
    replacements = {
        "reference": "Reference",
        "flexible_arrival_low": "Arrival low",
        "flexible_arrival_high": "Arrival high",
        "rigid_utilization_low": "Rigid util. low",
        "rigid_utilization_high": "Rigid util. high",
        "deadline_tight": "Deadline tight",
        "deadline_loose": "Deadline loose",
        "high_arrival_tight_deadline": "High arrival + tight DL",
        "low_arrival_loose_deadline": "Low arrival + loose DL",
        "delivery_090": "Delivery 0.90",
        "delivery_098": "Delivery 0.98",
        "deadline_000": "Miss 0.00",
        "deadline_002": "Miss 0.02",
        "rebound_010": "Rebound 0.10",
        "rebound_050": "Rebound 0.50",
        "window_relief_025": "Relief 0.25",
        "window_relief_075": "Relief 0.75",
        "pue_low": "PUE 1.10",
        "pue_high": "PUE 1.30",
        "node_overhead_lower": "Node overhead 150 W",
        "node_overhead_upper": "Node overhead 450 W",
    }
    return replacements.get(value, value.replace("_", " ").capitalize())


def _paired_case_panel(
    axis: Axes,
    frame: pd.DataFrame,
    *,
    case_column: str,
    value_column: str,
    title: str,
    xlabel: str,
) -> None:
    case_order = frame[case_column].drop_duplicates().astype(str).tolist()
    y_positions = np.arange(len(case_order), dtype=float)
    for offset, duration, color, marker in (
        (-0.12, 4, _COLORS["blue"], "o"),
        (0.12, 8, _COLORS["red"], "s"),
    ):
        values: list[float] = []
        for case in case_order:
            row = frame[
                (frame[case_column].astype(str) == case)
                & np.isclose(_numeric(frame, "duration_h"), duration)
            ].iloc[0]
            values.append(float(row[value_column]))
        axis.scatter(
            values,
            y_positions + offset,
            color=color,
            marker=marker,
            s=18,
            label=f"H={duration} h",
        )
    axis.axvline(0, color=_COLORS["neutral"], linewidth=0.7)
    axis.set_yticks(y_positions, [_case_label(case) for case in case_order])
    axis.invert_yaxis()
    axis.set_xlabel(xlabel)
    axis.set_title(title, loc="left")
    axis.grid(axis="x", color=_COLORS["grid"], linewidth=0.5)
    axis.legend(loc="lower right")


def plot_nature_mainline_figure5(
    source_data_directory: str | Path,
    output_directory: str | Path,
    *,
    formats: Sequence[str] = ("svg", "pdf", "tiff", "png"),
) -> dict[str, object]:
    """Plot robustness, independent certification and the OOD boundary."""

    _publication_style()
    manifest_path, manifest = _load_manifest(source_data_directory)
    power = _verified_table(source_data_directory, manifest, "fig5_power_case_sensitivity")
    workload = _verified_table(source_data_directory, manifest, "fig5_workload_sensitivity")
    criteria = _verified_table(source_data_directory, manifest, "fig5_success_criteria_sensitivity")
    infrastructure = _verified_table(
        source_data_directory, manifest, "fig5_infrastructure_sensitivity"
    )
    locked_id = _verified_table(source_data_directory, manifest, "fig2_fig5_locked_id_certificates")
    locked_ood = _verified_table(source_data_directory, manifest, "fig5_locked_ood_certificates")

    figure = plt.figure(figsize=(_FIGURE_WIDTH_IN, 7.0), constrained_layout=False)
    grid = figure.add_gridspec(3, 6, height_ratios=(1.0, 1.0, 1.05))
    ax_a = figure.add_subplot(grid[0, 0:2])
    ax_b = figure.add_subplot(grid[0, 2:6])
    ax_c = figure.add_subplot(grid[1, 0:3])
    ax_d = figure.add_subplot(grid[1, 3:6])
    ax_e = figure.add_subplot(grid[2, 0:6])

    q95_power = power[np.isclose(_numeric(power, "reliability_target"), 0.95)].copy()
    for case, color, marker in (
        ("lower", _COLORS["gold"], "v"),
        ("nominal", _COLORS["blue"], "o"),
        ("upper", _COLORS["purple"], "^"),
    ):
        subset = q95_power[q95_power["power_case"] == case].sort_values("duration_h")
        ax_a.plot(
            _numeric(subset, "duration_h"),
            _numeric(subset, "perfect_information_firm_capacity_kw"),
            marker=marker,
            color=color,
            label=case.capitalize(),
        )
    ax_a.set_xticks([1, 2, 3, 4, 6, 8])
    ax_a.set_xlabel("Event duration (h)")
    ax_a.set_ylabel("PI firm capacity (kW)")
    ax_a.set_title("Power uncertainty shifts capacity", loc="left")
    ax_a.grid(axis="y", color=_COLORS["grid"], linewidth=0.5)
    ax_a.legend(loc="upper right")
    _panel_label(ax_a, "a")

    _paired_case_panel(
        ax_b,
        workload,
        case_column="workload_case",
        value_column="firm_capacity_delta_from_reference_kw",
        title="Workload arrivals dominate sensitivity",
        xlabel="Capacity change from reference (kW)",
    )
    _panel_label(ax_b, "b")

    criteria_plot = criteria.copy()
    reference = criteria_plot[criteria_plot["criteria_case"] == "reference"].set_index("duration_h")
    criteria_plot["capacity_delta_kw"] = [
        _float(row.perfect_information_firm_capacity_kw)
        - _float(reference.loc[_int(row.duration_h), "perfect_information_firm_capacity_kw"])
        for row in criteria_plot.itertuples(index=False)
    ]
    _paired_case_panel(
        ax_c,
        criteria_plot,
        case_column="criteria_case",
        value_column="capacity_delta_kw",
        title="Delivery thresholds bind the success definition",
        xlabel="Capacity change from reference (kW)",
    )
    _panel_label(ax_c, "c")

    _paired_case_panel(
        ax_d,
        infrastructure,
        case_column="infrastructure_case",
        value_column="firm_capacity_delta_from_reference_kw",
        title="PUE rescales kW; fixed node overhead cancels in reduction",
        xlabel="Capacity change from reference (kW)",
    )
    _panel_label(ax_d, "d")

    q95_id = locked_id[
        np.isclose(_numeric(locked_id, "reliability_target"), 0.95)
        & np.isclose(_numeric(locked_id, "notice_h"), 0)
    ].sort_values("duration_h")
    q95_ood = locked_ood[
        np.isclose(_numeric(locked_ood, "reliability_target"), 0.95)
        & np.isclose(_numeric(locked_ood, "notice_h"), 0)
    ].sort_values("duration_h")
    ax_e.plot(
        _numeric(q95_id, "duration_h"),
        _numeric(q95_id, "wilson_lower_confidence_bound"),
        marker="o",
        color=_COLORS["blue"],
        label="Locked-ID",
    )
    ax_e.plot(
        _numeric(q95_ood, "duration_h"),
        _numeric(q95_ood, "wilson_lower_confidence_bound"),
        marker="s",
        color=_COLORS["red"],
        label="Locked-OOD fixed-candidate replay",
    )
    ax_e.axhline(
        0.95,
        color=_COLORS["neutral"],
        linestyle="--",
        linewidth=0.9,
        label="Target q=0.95",
    )
    id_flags = _bool_series(q95_id["certified"])
    ax_e.scatter(
        _numeric(q95_id.loc[~id_flags], "duration_h"),
        _numeric(q95_id.loc[~id_flags], "wilson_lower_confidence_bound"),
        facecolors="white",
        edgecolors=_COLORS["red"],
        marker="X",
        s=35,
        zorder=5,
    )
    ax_e.set_xticks([1, 2, 3, 4, 6, 8])
    ax_e.set_ylim(0.70, 1.005)
    ax_e.set_xlabel("Event duration (h)")
    ax_e.set_ylabel("One-sided 95% Wilson lower bound")
    ax_e.set_title(
        "Main-distribution certification does not survive the declared joint OOD shift",
        loc="left",
    )
    ax_e.grid(axis="y", color=_COLORS["grid"], linewidth=0.5)
    ax_e.legend(ncol=3, loc="lower left")
    _panel_label(ax_e, "e")
    figure.subplots_adjust(
        left=0.11,
        right=0.99,
        bottom=0.07,
        top=0.96,
        wspace=1.25,
        hspace=0.80,
    )

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
            "Sensitivity results are development PI planning bounds rather than causal "
            "certificates.",
            "Zero locked-OOD certified cells does not imply zero OOD firm capacity because "
            "OOD reselection was prohibited.",
            "The locked-ID H=1 q=0.95 candidate remains uncertified and is retained as a "
            "boundary result.",
        ),
        archetype="asymmetric mixed-modality figure",
    )


def _draw_v2_server_rack(axis: Axes, x: float, y: float, width: float, height: float) -> None:
    axis.add_patch(
        Rectangle(
            (x, y),
            width,
            height,
            facecolor="white",
            edgecolor=_COLORS["navy"],
            linewidth=1.0,
            transform=axis.transAxes,
        )
    )
    for index in range(5):
        slot_y = y + height * (0.12 + index * 0.16)
        axis.add_patch(
            Rectangle(
                (x + width * 0.12, slot_y),
                width * 0.76,
                height * 0.095,
                facecolor=_COLORS["pale_blue"],
                edgecolor="none",
                transform=axis.transAxes,
            )
        )
        axis.add_patch(
            Circle(
                (x + width * 0.79, slot_y + height * 0.047),
                height * 0.012,
                facecolor=_COLORS["blue"],
                edgecolor="none",
                transform=axis.transAxes,
            )
        )


def _draw_v2_house(axis: Axes, x: float, y: float, scale: float) -> None:
    axis.add_patch(
        Rectangle(
            (x, y),
            0.105 * scale,
            0.075 * scale,
            facecolor="white",
            edgecolor=_COLORS["navy"],
            linewidth=0.9,
            transform=axis.transAxes,
        )
    )
    axis.add_patch(
        Polygon(
            [
                (x - 0.008 * scale, y + 0.075 * scale),
                (x + 0.052 * scale, y + 0.125 * scale),
                (x + 0.113 * scale, y + 0.075 * scale),
            ],
            closed=True,
            facecolor=_COLORS["pale_gold"],
            edgecolor=_COLORS["navy"],
            linewidth=0.9,
            transform=axis.transAxes,
        )
    )
    axis.add_patch(
        Rectangle(
            (x + 0.044 * scale, y),
            0.023 * scale,
            0.045 * scale,
            facecolor=_COLORS["pale_blue"],
            edgecolor=_COLORS["navy"],
            linewidth=0.5,
            transform=axis.transAxes,
        )
    )


def _draw_v2_solar(axis: Axes, x: float, y: float, scale: float) -> None:
    panel = Polygon(
        [
            (x, y),
            (x + 0.11 * scale, y),
            (x + 0.095 * scale, y + 0.065 * scale),
            (x - 0.015 * scale, y + 0.065 * scale),
        ],
        closed=True,
        facecolor=_COLORS["blue"],
        edgecolor=_COLORS["navy"],
        linewidth=0.7,
        transform=axis.transAxes,
    )
    axis.add_patch(panel)
    for fraction in (0.33, 0.66):
        axis.plot(
            [x + 0.11 * scale * fraction, x - 0.015 * scale + 0.11 * scale * fraction],
            [y, y + 0.065 * scale],
            color="white",
            linewidth=0.45,
            transform=axis.transAxes,
            clip_on=False,
        )
    axis.plot(
        [x - 0.007 * scale, x + 0.102 * scale],
        [y + 0.032 * scale, y + 0.032 * scale],
        color="white",
        linewidth=0.45,
        transform=axis.transAxes,
        clip_on=False,
    )
    axis.plot(
        [x + 0.045 * scale, x + 0.045 * scale],
        [y, y - 0.035 * scale],
        color=_COLORS["neutral"],
        linewidth=0.8,
        transform=axis.transAxes,
        clip_on=False,
    )


def plot_nature_mainline_figure1_reference_style(
    source_data_directory: str | Path,
    output_directory: str | Path,
    *,
    formats: Sequence[str] = ("svg", "pdf", "tiff", "png"),
) -> dict[str, object]:
    """Plot the reference-style schematic and nominal-to-firm capacity gap."""

    _publication_style()
    manifest_path, manifest = _load_manifest(source_data_directory)
    pi = _verified_table(source_data_directory, manifest, "fig1_fig2_pi_firm_boundaries")
    calibration = _verified_table(source_data_directory, manifest, "fig1_calibration_run_means")
    _require_columns(
        pi,
        (
            "duration_h",
            "reliability_target",
            "perfect_information_firm_capacity_kw",
            "nominal_flexibility_kw",
            "physical_gap_kw",
        ),
        table_id="fig1_fig2_pi_firm_boundaries",
    )
    _require_columns(
        calibration,
        ("mode", "gpu_count", "repeat", "gpu_index", "mean_power_w"),
        table_id="fig1_calibration_run_means",
    )

    q95 = pi[np.isclose(_numeric(pi, "reliability_target"), 0.95)].copy()
    q95 = q95.sort_values("duration_h")
    durations = _numeric(q95, "duration_h").to_numpy(dtype=float)
    nominal = _numeric(q95, "nominal_flexibility_kw").to_numpy(dtype=float)
    firm = _numeric(q95, "perfect_information_firm_capacity_kw").to_numpy(dtype=float)
    gap_pct = 100.0 * (nominal - firm) / nominal

    figure = plt.figure(figsize=(_FIGURE_WIDTH_IN, 5.25), constrained_layout=False)
    grid = figure.add_gridspec(
        3,
        12,
        height_ratios=(1.18, 0.72, 0.34),
        hspace=0.50,
        wspace=0.90,
    )
    ax_a = figure.add_subplot(grid[0, :])
    ax_b = figure.add_subplot(grid[1:, :8])
    ax_c = figure.add_subplot(grid[1, 8:])
    ax_d = figure.add_subplot(grid[2, 8:])

    # Panel a: one narrative schematic rather than four equal dashboard cards.
    ax_a.set_axis_off()
    ax_a.set_xlim(0, 1)
    ax_a.set_ylim(0, 1)
    zone_specs = (
        (0.015, 0.30, _COLORS["pale_blue"], "Nominal representation"),
        (0.35, 0.30, _COLORS["pale_teal"], "Job-derived scheduling"),
        (0.685, 0.30, _COLORS["pale_gold"], "Firm grid resource"),
    )
    for x_value, width, facecolor, heading in zone_specs:
        ax_a.add_patch(
            Rectangle(
                (x_value, 0.10),
                width,
                0.78,
                facecolor=facecolor,
                edgecolor="none",
                transform=ax_a.transAxes,
            )
        )
        ax_a.text(
            x_value + 0.02,
            0.82,
            heading,
            transform=ax_a.transAxes,
            fontsize=8.2,
            fontweight="bold",
            color=_COLORS["ink"],
            va="center",
        )

    # Nominal representation: one static percentage attached to a data-centre rack.
    _draw_v2_server_rack(ax_a, 0.055, 0.28, 0.10, 0.39)
    ax_a.text(
        0.205,
        0.57,
        "50%",
        transform=ax_a.transAxes,
        fontsize=22,
        fontweight="bold",
        color=_COLORS["navy"],
        ha="center",
        va="center",
    )
    ax_a.text(
        0.205,
        0.40,
        "fixed share of\noperating peak",
        transform=ax_a.transAxes,
        fontsize=7.2,
        color=_COLORS["neutral"],
        ha="center",
        va="center",
    )
    ax_a.plot(
        [0.055, 0.255],
        [0.22, 0.22],
        color=_COLORS["navy"],
        linewidth=5.5,
        solid_capstyle="butt",
        transform=ax_a.transAxes,
        clip_on=False,
    )
    ax_a.plot(
        [0.055, 0.155],
        [0.22, 0.22],
        color=_COLORS["red"],
        linewidth=5.5,
        solid_capstyle="butt",
        transform=ax_a.transAxes,
        clip_on=False,
    )
    ax_a.text(
        0.055,
        0.155,
        "assumed flexible load",
        transform=ax_a.transAxes,
        fontsize=6.5,
        color=_COLORS["red"],
        va="center",
    )

    # Job-derived view: release times, deadlines and a DR interval jointly constrain execution.
    timeline_x0, timeline_x1 = 0.385, 0.615
    ax_a.plot(
        [timeline_x0, timeline_x1],
        [0.28, 0.28],
        color=_COLORS["neutral"],
        linewidth=0.8,
        transform=ax_a.transAxes,
        clip_on=False,
    )
    for tick_index, label in enumerate(("release", "event", "deadline")):
        tick_x = timeline_x0 + (timeline_x1 - timeline_x0) * (tick_index / 2)
        ax_a.plot(
            [tick_x, tick_x],
            [0.255, 0.305],
            color=_COLORS["neutral"],
            linewidth=0.7,
            transform=ax_a.transAxes,
            clip_on=False,
        )
        ax_a.text(
            tick_x,
            0.21,
            label,
            transform=ax_a.transAxes,
            fontsize=6.3,
            ha="center",
            color=_COLORS["neutral"],
        )
    ax_a.add_patch(
        Rectangle(
            (0.485, 0.34),
            0.055,
            0.37,
            facecolor=_COLORS["pale_red"],
            edgecolor="none",
            transform=ax_a.transAxes,
        )
    )
    ax_a.text(
        0.512,
        0.73,
        "DR",
        transform=ax_a.transAxes,
        fontsize=6.5,
        fontweight="bold",
        color=_COLORS["red"],
        ha="center",
    )
    job_specs = (
        (0.385, 0.465, 0.62, _COLORS["purple"], "training"),
        (0.415, 0.515, 0.52, _COLORS["blue"], "offline inference"),
        (0.505, 0.600, 0.42, _COLORS["flex"], "deferred work"),
    )
    for start, end, y_value, color, label in job_specs:
        ax_a.plot(
            [start, end],
            [y_value, y_value],
            color=color,
            linewidth=7,
            solid_capstyle="butt",
            transform=ax_a.transAxes,
            clip_on=False,
        )
        ax_a.text(
            end + 0.008,
            y_value,
            label,
            transform=ax_a.transAxes,
            fontsize=6.3,
            va="center",
            color=_COLORS["ink"],
        )
    ax_a.add_patch(
        FancyArrowPatch(
            (0.468, 0.62),
            (0.545, 0.42),
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=1.0,
            color=_COLORS["red"],
            connectionstyle="arc3,rad=0.18",
            transform=ax_a.transAxes,
        )
    )
    ax_a.text(
        0.49,
        0.34,
        "compute debt",
        transform=ax_a.transAxes,
        fontsize=6.5,
        color=_COLORS["red"],
        ha="center",
    )

    # Firm grid resource: connect workload shifting to the community PCC.
    _draw_v2_solar(ax_a, 0.72, 0.50, 0.75)
    _draw_v2_house(ax_a, 0.805, 0.35, 0.72)
    ax_a.add_patch(
        Rectangle(
            (0.900, 0.37),
            0.045,
            0.19,
            facecolor="white",
            edgecolor=_COLORS["navy"],
            linewidth=0.9,
            transform=ax_a.transAxes,
        )
    )
    ax_a.add_patch(
        Rectangle(
            (0.911, 0.405),
            0.023,
            0.11,
            facecolor=_COLORS["pale_teal"],
            edgecolor=_COLORS["flex"],
            linewidth=0.6,
            transform=ax_a.transAxes,
        )
    )
    ax_a.text(
        0.922,
        0.59,
        "BESS",
        transform=ax_a.transAxes,
        fontsize=6.2,
        ha="center",
        color=_COLORS["ink"],
    )
    ax_a.plot(
        [0.725, 0.950],
        [0.29, 0.29],
        color=_COLORS["navy"],
        linewidth=1.0,
        transform=ax_a.transAxes,
        clip_on=False,
    )
    ax_a.add_patch(
        FancyArrowPatch(
            (0.790, 0.70),
            (0.790, 0.34),
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=1.3,
            color=_COLORS["blue"],
            transform=ax_a.transAxes,
        )
    )
    ax_a.text(
        0.806,
        0.63,
        "firm reduction R",
        transform=ax_a.transAxes,
        fontsize=6.6,
        color=_COLORS["blue"],
        va="center",
    )
    ax_a.text(
        0.835,
        0.18,
        "PCC capacity + service reliability q",
        transform=ax_a.transAxes,
        fontsize=6.5,
        color=_COLORS["neutral"],
        ha="center",
    )

    for start_x, end_x in ((0.315, 0.345), (0.650, 0.680)):
        ax_a.add_patch(
            FancyArrowPatch(
                (start_x, 0.49),
                (end_x, 0.49),
                arrowstyle="-|>",
                mutation_scale=11,
                linewidth=1.1,
                color=_COLORS["neutral"],
                transform=ax_a.transAxes,
            )
        )
    ax_a.text(
        0.500,
        0.055,
        "A static load fraction becomes a grid resource only after job feasibility, recovery and reliability are enforced.",
        transform=ax_a.transAxes,
        fontsize=7.2,
        color=_COLORS["ink"],
        ha="center",
        va="center",
    )
    _panel_label(ax_a, "a", x=-0.005, y=1.00)

    # Panel b: retain one dominant quantitative result and label the series directly.
    ax_b.fill_between(
        durations,
        firm,
        nominal,
        color=_COLORS["pale_red"],
        alpha=0.95,
        linewidth=0,
    )
    ax_b.plot(
        durations,
        nominal,
        color=_COLORS["neutral"],
        linewidth=2.0,
        marker="o",
        markersize=4,
    )
    ax_b.plot(
        durations,
        firm,
        color=_COLORS["blue"],
        linewidth=2.2,
        marker="o",
        markersize=4,
    )
    ax_b.text(
        durations[-1] - 0.16,
        nominal[-1],
        "Nominal proxy",
        color=_COLORS["neutral"],
        fontsize=7.0,
        ha="right",
        va="center",
    )
    ax_b.text(
        durations[-1] - 0.16,
        firm[-1],
        "Job-derived PI bound",
        color=_COLORS["blue"],
        fontsize=7.0,
        ha="right",
        va="center",
    )
    for index in (0, len(durations) - 1):
        ax_b.annotate(
            f"{gap_pct[index]:.1f}%\noverstatement",
            xy=(durations[index], (nominal[index] + firm[index]) / 2),
            xytext=(durations[index] + (0.45 if index == 0 else -0.80), 77 if index == 0 else 70),
            ha="center",
            color=_COLORS["red"],
            fontsize=6.8,
            arrowprops={"arrowstyle": "-", "lw": 0.8, "color": _COLORS["red"]},
        )
    ax_b.set_xlim(0.7, 9.2)
    ax_b.set_ylim(30, 108)
    ax_b.set_xticks(durations)
    ax_b.set_xlabel("Event duration (h)")
    ax_b.set_ylabel("Firm reduction capacity (kW)")
    ax_b.set_title("Nominal versus job-derived firm capacity", loc="left", fontweight="bold")
    ax_b.grid(axis="y", color=_COLORS["grid"], linewidth=0.55)
    _panel_label(ax_b, "b", x=-0.10, y=1.04)

    # Panel c: measurement anchor, kept visually subordinate to the headline result.
    grouped: pd.DataFrame = (
        calibration.groupby(["mode", "gpu_count", "repeat"], as_index=False)
        .mean(numeric_only=True)
        .sort_values(["mode", "gpu_count", "repeat"])
    )
    categories = (
        ("training", 1, "Train\n1 GPU", _COLORS["purple"]),
        ("training", 4, "Train\n4 GPU", _COLORS["purple"]),
        ("offline_inference", 1, "Infer\n1 GPU", _COLORS["flex"]),
        ("offline_inference", 4, "Infer\n4 GPU", _COLORS["flex"]),
    )
    for index, (mode, count, _label, color) in enumerate(categories):
        subset = grouped[(grouped["mode"] == mode) & (_numeric(grouped, "gpu_count") == count)]
        values = _numeric(subset, "mean_power_w").to_numpy(dtype=float)
        offsets = np.linspace(-0.08, 0.08, len(values)) if len(values) > 1 else np.array([0.0])
        ax_c.scatter(index + offsets, values, s=17, color=color, zorder=3)
        ax_c.hlines(float(values.mean()), index - 0.18, index + 0.18, color=_COLORS["ink"], lw=1.3)
    ax_c.set_xticks(range(len(categories)), [item[2] for item in categories])
    ax_c.set_ylabel("GPU-board power (W)")
    ax_c.set_title("Measured power anchor", loc="left", fontweight="bold")
    ax_c.grid(axis="y", color=_COLORS["grid"], linewidth=0.5)
    _panel_label(ax_c, "c", x=-0.22, y=1.06)

    # Panel d: a single horizontal evidence hierarchy rather than stacked dashboard cards.
    ax_d.set_axis_off()
    layer_specs = (
        (0.00, 0.22, "Nominal", _COLORS["neutral"]),
        (0.25, 0.22, "PI", _COLORS["gold"]),
        (0.50, 0.22, "NA", _COLORS["purple"]),
        (0.75, 0.25, "Causal", _COLORS["blue"]),
    )
    for x_value, width, label, color in layer_specs:
        ax_d.add_patch(
            Rectangle(
                (x_value, 0.38),
                width,
                0.22,
                facecolor=color,
                edgecolor="none",
                transform=ax_d.transAxes,
            )
        )
        ax_d.text(
            x_value + width / 2,
            0.49,
            label,
            transform=ax_d.transAxes,
            fontsize=6.4,
            color="white" if label != "PI" else _COLORS["ink"],
            fontweight="bold",
            ha="center",
            va="center",
        )
    ax_d.text(
        0.00,
        0.92,
        "Evidence hierarchy",
        transform=ax_d.transAxes,
        fontsize=7.5,
        fontweight="bold",
        color=_COLORS["ink"],
        va="top",
    )
    ax_d.text(
        0.00,
        0.08,
        "assumption  →  physics  →  information  →  test",
        transform=ax_d.transAxes,
        fontsize=6.1,
        color=_COLORS["neutral"],
        va="bottom",
    )
    _panel_label(ax_d, "d", x=-0.22, y=1.05)

    figure.subplots_adjust(left=0.07, right=0.97, bottom=0.08, top=0.97)
    return _finalize_figure(
        figure,
        figure_number=1,
        source_manifest_path=manifest_path,
        source_tables=("fig1_fig2_pi_firm_boundaries", "fig1_calibration_run_means"),
        output_directory=output_directory,
        stem="figure_1_nominal_job_derived_gap",
        formats=formats,
        core_conclusion=(
            "A fixed nominal flexibility fraction substantially overstates the job-derived "
            "firm boundary across all tested event durations."
        ),
        claim_boundaries=(
            "PI is a perfect-information planning upper bound, not an independently certified capacity.",
            "The four-GPU measurements anchor class-aware board power; they do not directly represent a megawatt-scale data centre.",
        ),
        archetype="schematic-led composite",
    )


_FIGURE_PLOTTERS: dict[int, Callable[..., dict[str, object]]] = {
    1: plot_nature_mainline_figure1_reference_style,
    2: plot_nature_mainline_figure2,
    3: plot_nature_mainline_figure3,
    4: plot_nature_mainline_figure4,
    5: plot_nature_mainline_figure5,
}


def plot_nature_mainline_figures(
    source_data_directory: str | Path,
    output_directory: str | Path,
    *,
    figures: Sequence[int] = (1, 2, 3, 4, 5),
    formats: Sequence[str] = ("svg", "pdf", "tiff", "png"),
) -> dict[str, object]:
    """Generate selected frozen mainline figures and an index manifest."""

    requested = tuple(int(value) for value in figures)
    if not requested:
        raise ValueError("at least one figure number is required")
    unsupported = sorted(set(requested).difference(_FIGURE_PLOTTERS))
    if unsupported:
        raise ValueError(f"unsupported Nature mainline figures: {unsupported}")
    destination = Path(output_directory).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    records = [
        _FIGURE_PLOTTERS[number](
            source_data_directory,
            destination,
            formats=formats,
        )
        for number in requested
    ]
    portable_records: list[dict[str, object]] = []
    for record in records:
        runtime_outputs = record.get("outputs")
        manifest_path = record.get("manifest")
        if not isinstance(runtime_outputs, list) or not isinstance(manifest_path, str):
            raise ValueError("invalid runtime figure record")
        portable_outputs: list[dict[str, object]] = []
        for output in runtime_outputs:
            if not isinstance(output, dict):
                raise ValueError("invalid runtime figure output record")
            portable_output = dict(output)
            portable_output["path"] = Path(str(output["path"])).name
            portable_outputs.append(portable_output)
        portable_records.append(
            {
                "figure": record["figure"],
                "outputs": portable_outputs,
                "manifest": Path(manifest_path).name,
            }
        )
    index: dict[str, object] = {
        "schema_version": "aidrbench.nature_figure_bundle.v1",
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
