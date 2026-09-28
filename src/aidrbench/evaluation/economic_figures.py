"""Legacy local audit preview for parameterized economic participation screening.

The formal Figure 6 artwork is generated only by Web-GPT from the exact panel
package. This renderer is retained for code-contract regression checks and is
not an authorised manuscript-artwork path.
"""
# ruff: noqa: E402

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, cast

_matplotlib_cache = Path(tempfile.gettempdir()) / "aidrbench-economic-matplotlib"
_matplotlib_cache.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_matplotlib_cache))

import matplotlib

matplotlib.use("Agg", force=True)

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

_ALLOWED_FORMATS = frozenset({"svg", "pdf", "tiff", "png"})
_FORMAT_SUFFIXES = {
    "svg": ".svg",
    "pdf": ".pdf",
    "tiff": ".tiff",
    "png": ".png",
}
_FIGURE_WIDTH_MM = 183.0
_FIGURE_WIDTH_IN = _FIGURE_WIDTH_MM / 25.4
_MIN_FONT_PT = 6.5
_COLORS = {
    "ink": "#24313D",
    "neutral": "#75808A",
    "grid": "#DCE2E6",
    "slack": "#3D9B8F",
    "reserve": "#776FA3",
    "displace": "#D5634E",
    "revenue": "#3B7EA1",
    "performance": "#66A5C8",
    "energy": "#7CB9A8",
    "cost": "#D5634E",
    "cost_light": "#E5A07E",
    "pale": "#EEF2F4",
}
_REGIME_ORDER = ("slack_backed", "reserved_headroom", "throughput_displacing")
_REGIME_LABELS = {
    "slack_backed": "Slack-backed",
    "reserved_headroom": "Reserved headroom",
    "throughput_displacing": "Throughput-displacing",
}
_REGIME_SHORT_LABELS = {
    "slack_backed": "Slack-backed",
    "reserved_headroom": "Reserved",
    "throughput_displacing": "Displaced",
}
_BOUNDARY_LABELS = {
    "slack_backed": "Slack-\nbacked",
    "reserved_headroom": "Reserved\nheadroom",
    "throughput_displacing": "Throughput-\ndisplacing",
}
_REGIME_COLORS = {
    "slack_backed": _COLORS["slack"],
    "reserved_headroom": _COLORS["reserve"],
    "throughput_displacing": _COLORS["displace"],
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
            "svg.hashsalt": "aidrbench-economic-figure-v1",
        }
    )


def _panel_label(axis: Any, label: str) -> None:
    axis.text(
        -0.14,
        1.08,
        label,
        transform=axis.transAxes,
        fontsize=9,
        fontweight="bold",
        va="top",
        ha="left",
    )


def _load_manifest(source_data_directory: str | Path) -> tuple[Path, dict[str, Any]]:
    source_directory = Path(source_data_directory).resolve()
    manifest_path = source_directory / "source_data_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("tables"), list):
        raise ValueError("invalid economic source-data manifest")
    return manifest_path, document


def _verified_table(
    source_data_directory: str | Path,
    manifest: dict[str, Any],
    table_id: str,
) -> tuple[pd.DataFrame, Path, dict[str, Any]]:
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
        raise ValueError(f"invalid economic source-data record: {table_id}")
    path = (source_directory / output).resolve()
    try:
        path.relative_to(source_directory)
    except ValueError as error:
        raise ValueError(f"economic source-data output escapes bundle: {output}") from error
    if not path.is_file():
        raise FileNotFoundError(path)
    if _sha256(path) != expected_hash:
        raise ValueError(f"economic source-data hash mismatch: {table_id}")
    frame = pd.read_csv(path)
    declared = record.get("columns")
    if isinstance(declared, list):
        missing = sorted(set(str(column) for column in declared).difference(frame.columns))
        if missing:
            raise ValueError(
                f"economic source-data table is missing declared columns: {table_id}: "
                + ", ".join(missing)
            )
    if frame.empty:
        raise ValueError(f"economic source-data table is empty: {table_id}")
    return frame, path, record


def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...], *, table_id: str) -> None:
    missing = sorted(set(columns).difference(frame.columns))
    if missing:
        raise ValueError(f"{table_id}: missing required columns: {', '.join(missing)}")


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_numeric(frame[column], errors="raise")
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError(f"economic figure data have non-finite values: {column}")
    return values


def _spread_label_positions(
    values: list[float],
    *,
    lower: float,
    upper: float,
    minimum_gap: float,
) -> list[float]:
    """Deterministically separate endpoint labels without changing the data."""

    if not values:
        return []
    order = np.argsort(np.asarray(values, dtype=float), kind="stable")
    placed = np.asarray(values, dtype=float).copy()
    placed[order[0]] = max(placed[order[0]], lower)
    for previous, current in zip(order[:-1], order[1:], strict=True):
        placed[current] = max(placed[current], placed[previous] + minimum_gap)
    if placed[order[-1]] > upper:
        placed[order] -= placed[order[-1]] - upper
    for current, following in zip(order[-2::-1], order[:0:-1], strict=True):
        placed[current] = min(placed[current], placed[following] - minimum_gap)
    if placed[order[0]] < lower:
        placed[order] += lower - placed[order[0]]
    return placed.tolist()


def _validate_analysis_context(frames: dict[str, pd.DataFrame]) -> None:
    for table_id, frame in frames.items():
        _require_columns(
            frame,
            (
                "analysis_role",
                "annualization_scope",
                "performance_payment_basis",
                "reserved_capacity_basis",
            ),
            table_id=table_id,
        )
        roles = set(frame["analysis_role"].astype(str))
        if roles != {"development_parameterized_screening"}:
            raise ValueError(
                "economic Figure 6 accepts only the declared parameterized development "
                f"screening role; found {sorted(roles)} in {table_id}"
            )
        expected = {
            "annualization_scope": "independent_fresh_events_not_continuous_programme",
            "performance_payment_basis": (
                "interval_delivery_capped_at_scaled_accounting_offered_kW"
            ),
            "reserved_capacity_basis": "abstract_pcc_side_kw_sensitivity",
        }
        for column, value in expected.items():
            observed = set(frame[column].astype(str))
            if observed != {value}:
                raise ValueError(f"{table_id}: expected {column}={value}; found {sorted(observed)}")


def _record_outputs(
    figure: Figure,
    *,
    output_directory: Path,
    stem: str,
    formats: tuple[str, ...],
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
        output_path = output_directory / f"{stem}{_FORMAT_SUFFIXES[extension]}"
        dpi = 600 if extension == "tiff" else 300
        if extension == "svg":
            figure.savefig(output_path, dpi=dpi, metadata={"Creator": "AIDRBench", "Date": None})
            svg_text = output_path.read_text(encoding="utf-8")
            output_path.write_text(
                "\n".join(line.rstrip() for line in svg_text.splitlines()) + "\n",
                encoding="utf-8",
            )
        elif extension == "pdf":
            figure.savefig(
                output_path,
                dpi=dpi,
                metadata={"Creator": "AIDRBench", "CreationDate": None, "ModDate": None},
            )
        elif extension == "tiff":
            figure.savefig(output_path, dpi=dpi, pil_kwargs={"compression": "tiff_lzw"})
        else:
            figure.savefig(output_path, dpi=dpi)
        records.append(
            {
                "format": extension,
                "path": output_path.name,
                "bytes": output_path.stat().st_size,
                "sha256": _sha256(output_path),
            }
        )
    return records


def _copy_panel_data(
    source_paths: dict[str, Path],
    output_directory: Path,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for panel, source_path in sorted(source_paths.items()):
        destination = output_directory / f"figure_6_panel_{panel}.csv"
        shutil.copyfile(source_path, destination)
        records.append(
            {
                "panel": panel,
                "path": destination.name,
                "bytes": destination.stat().st_size,
                "sha256": _sha256(destination),
                "source_sha256": _sha256(source_path),
            }
        )
    return records


def _assert_certified_full_offer(frame: pd.DataFrame, *, table_id: str) -> None:
    _require_columns(
        frame,
        (
            "technical_capacity_ceiling_kw",
            "candidate_reduction_kw",
            "technical_qualification",
        ),
        table_id=table_id,
    )
    ceiling = _numeric(frame, "technical_capacity_ceiling_kw").to_numpy(dtype=float)
    offered = _numeric(frame, "candidate_reduction_kw").to_numpy(dtype=float)
    if not np.allclose(offered, ceiling, rtol=0.0, atol=1e-9):
        raise ValueError(f"{table_id}: main-figure rows must evaluate the full Kcert")
    if set(frame["technical_qualification"].astype(str)) != {"independently_certified_ceiling"}:
        raise ValueError(f"{table_id}: lower development-screened offers are not admissible")


def _plot_boundary(axis: Any, boundary: pd.DataFrame) -> None:
    _require_columns(
        boundary,
        (
            "regime",
            "duration_h",
            "reliability_target",
            "technical_capacity_ceiling_kw",
            "break_even_capacity_payment_per_kw_year",
            "risk_adjusted_break_even_capacity_payment_per_kw_year",
        ),
        table_id="fig6_technical_economic_boundary",
    )
    if set(boundary["regime"].astype(str)) != set(_REGIME_ORDER) or len(boundary) != 3:
        raise ValueError("Figure 6a requires exactly one primary row per participation regime")
    durations = set(_numeric(boundary, "duration_h").astype(int))
    reliabilities = set(np.round(_numeric(boundary, "reliability_target"), 12))
    if len(durations) != 1 or len(reliabilities) != 1:
        raise ValueError("Figure 6a requires one fixed duration and reliability target")

    _assert_certified_full_offer(boundary, table_id="fig6_technical_economic_boundary")
    ordered = boundary.set_index("regime").loc[list(_REGIME_ORDER)].reset_index()
    y_values = np.arange(len(ordered), dtype=float)
    mean_payment = _numeric(ordered, "break_even_capacity_payment_per_kw_year").to_numpy(
        dtype=float
    )
    risk_payment = _numeric(
        ordered, "risk_adjusted_break_even_capacity_payment_per_kw_year"
    ).to_numpy(dtype=float)
    if np.any(risk_payment + 1e-9 < mean_payment):
        raise ValueError("Figure 6a risk-adjusted break-even cannot be below the mean value")
    axis.hlines(
        y_values,
        mean_payment,
        risk_payment,
        color=[_REGIME_COLORS[str(value)] for value in ordered["regime"]],
        linewidth=2.2,
        alpha=0.65,
    )
    axis.scatter(
        mean_payment,
        y_values,
        facecolors="white",
        edgecolors=[_REGIME_COLORS[str(value)] for value in ordered["regime"]],
        linewidths=1.1,
        s=28,
        marker="o",
        zorder=3,
        label="Mean break-even",
    )
    axis.scatter(
        risk_payment,
        y_values,
        c=[_REGIME_COLORS[str(value)] for value in ordered["regime"]],
        edgecolors=_COLORS["ink"],
        linewidths=0.45,
        s=30,
        marker="D",
        zorder=4,
        label="Risk rule (5th percentile)",
    )
    maximum = max(float(risk_payment.max()), 1.0)
    for index, regime in enumerate(ordered["regime"].astype(str)):
        axis.text(
            risk_payment[index] + 0.025 * maximum,
            y_values[index],
            f"{risk_payment[index]:.0f}",
            va="center",
            ha="left",
            fontsize=6.3,
            color=_REGIME_COLORS[regime],
        )
    axis.set_yticks(y_values, [_BOUNDARY_LABELS[str(value)] for value in ordered["regime"]])
    axis.invert_yaxis()
    axis.set_xlim(-0.04 * maximum, maximum * 1.22)
    axis.set_xlabel("Break-even capacity payment (USD/kW-year)")
    axis.set_title(
        f"Compensation required at certified Kcert\nH = {next(iter(durations))} h, "
        f"q = {next(iter(reliabilities)):.2f}",
        loc="left",
    )
    axis.grid(axis="x", color=_COLORS["grid"], linewidth=0.5, zorder=0)
    axis.legend(loc="upper left", ncol=1, handlelength=1.2)
    _panel_label(axis, "a")


def _plot_mechanism_sensitivity(axis: Any, sensitivity: pd.DataFrame) -> None:
    _require_columns(
        sensitivity,
        (
            "regime",
            "driver_id",
            "driver_label",
            "driver_value",
            "driver_unit",
            "driver_value_display",
            "driver_normalized_position",
            "duration_h",
            "reliability_target",
            "risk_adjusted_break_even_capacity_payment_per_kw_year",
            "technical_capacity_ceiling_kw",
            "candidate_reduction_kw",
            "technical_qualification",
        ),
        table_id="fig6_mechanism_sensitivity",
    )
    if set(sensitivity["regime"].astype(str)) != set(_REGIME_ORDER):
        raise ValueError("Figure 6b requires one mechanism-specific driver per regime")
    _assert_certified_full_offer(sensitivity, table_id="fig6_mechanism_sensitivity")
    durations = set(_numeric(sensitivity, "duration_h").astype(int))
    reliabilities = set(np.round(_numeric(sensitivity, "reliability_target"), 12))
    if durations != {4} or reliabilities != {0.95}:
        raise ValueError("Figure 6b is predeclared for H = 4 h and q = 0.95")
    normalized = _numeric(sensitivity, "driver_normalized_position")
    if ((normalized < 0.0) | (normalized > 1.0)).any():
        raise ValueError("Figure 6b normalized driver coordinates must lie in [0, 1]")
    payment = _numeric(sensitivity, "risk_adjusted_break_even_capacity_payment_per_kw_year")
    if (payment < 0.0).any():
        raise ValueError("Figure 6b break-even payments must be non-negative")
    endpoint_annotations: list[tuple[str, float, str]] = []
    for regime in _REGIME_ORDER:
        subset = sensitivity[sensitivity["regime"].astype(str) == regime].copy()
        if subset["driver_id"].astype(str).nunique() != 1:
            raise ValueError("Figure 6b requires exactly one declared main-text driver per regime")
        subset = subset.sort_values("driver_normalized_position", kind="stable")
        x = _numeric(subset, "driver_normalized_position").to_numpy(dtype=float)
        driver_value = _numeric(subset, "driver_value").to_numpy(dtype=float)
        y = _numeric(subset, "risk_adjusted_break_even_capacity_payment_per_kw_year").to_numpy(
            dtype=float
        )
        if len(x) < 2 or np.any(np.diff(x) <= 0.0) or np.any(np.diff(driver_value) <= 0.0):
            raise ValueError("Figure 6b driver coordinates must be unique and increasing")
        if subset["driver_unit"].astype(str).nunique() != 1:
            raise ValueError("Figure 6b requires one machine-readable unit per driver")
        low = str(subset["driver_value_display"].iloc[0])
        high = str(subset["driver_value_display"].iloc[-1])
        axis.plot(
            x,
            y,
            color=_REGIME_COLORS[regime],
            linewidth=1.5,
            marker="o",
            markersize=3.2,
        )
        compact_label = {
            "annual_event_count": "Events",
            "economic_life_years": "Life",
            "opportunity_exposure_alpha": "Exposure α",
        }.get(str(subset["driver_id"].iloc[0]), str(subset["driver_label"].iloc[0]))
        endpoint_annotations.append(
            (
                regime,
                float(y[-1]),
                f"{compact_label}\n"
                f"{low.replace(' events/year', '/yr').replace(' years', ' yr')} → "
                f"{high.replace(' events/year', '/yr').replace(' years', ' yr')}",
            )
        )
    span = max(float(payment.max() - payment.min()), 1.0)
    lower = float(payment.min()) - 0.10 * span
    upper = float(payment.max()) + 0.18 * span
    axis.set_xlim(-0.02, 1.48)
    axis.set_ylim(lower, upper)
    label_y = _spread_label_positions(
        [item[1] for item in endpoint_annotations],
        lower=lower + 0.05 * span,
        upper=upper - 0.05 * span,
        minimum_gap=0.12 * span,
    )
    for (regime, endpoint_y, label), position_y in zip(endpoint_annotations, label_y, strict=True):
        axis.plot(
            [1.0, 1.025],
            [endpoint_y, position_y],
            color=_REGIME_COLORS[regime],
            linewidth=0.7,
        )
        axis.text(
            1.04,
            position_y,
            label,
            color=_REGIME_COLORS[regime],
            fontsize=5.8,
            va="center",
            ha="left",
        )
    axis.set_xticks((0.0, 0.5, 1.0), ("Low", "Mid", "High"))
    axis.set_xlabel("Declared mechanism-specific range")
    axis.set_ylabel("Risk-adjusted break-even\ncapacity payment (USD/kW-year)")
    axis.set_title("Regime-specific economic drivers", loc="left")
    axis.grid(axis="y", color=_COLORS["grid"], linewidth=0.5)
    _panel_label(axis, "b")


def _plot_break_even_decomposition(axis: Any, decomposition: pd.DataFrame) -> None:
    _require_columns(
        decomposition,
        (
            "regime",
            "component_id",
            "component_label",
            "contribution_per_kw_year",
            "risk_adjusted_break_even_capacity_payment_per_kw_year",
            "technical_capacity_ceiling_kw",
            "candidate_reduction_kw",
            "technical_qualification",
        ),
        table_id="fig6_break_even_decomposition",
    )
    if set(decomposition["regime"].astype(str)) != set(_REGIME_ORDER):
        raise ValueError("Figure 6c requires every participation regime")
    _assert_certified_full_offer(decomposition, table_id="fig6_break_even_decomposition")
    component_colors = {
        "enablement_cost": "#E5A07E",
        "reserve_annual_cost": "#776FA3",
        "opportunity_cost": "#D5634E",
        "delay_cost": "#C98265",
        "sla_cost": "#AA6256",
        "checkpoint_cost": "#E7B6A5",
        "penalty_cost": "#8E3E37",
        "performance_credit": "#66A5C8",
        "energy_credit_or_cost": "#7CB9A8",
        "connection_credit": "#3D9B8F",
        "risk_buffer": "#24313D",
    }
    component_order = tuple(component_colors)
    positions = np.arange(len(_REGIME_ORDER), dtype=float)
    positive_bottom = np.zeros(len(_REGIME_ORDER), dtype=float)
    negative_bottom = np.zeros(len(_REGIME_ORDER), dtype=float)
    legend_handles: list[Patch] = []
    for component in component_order:
        values: list[float] = []
        label: str | None = None
        for regime in _REGIME_ORDER:
            matches = decomposition[
                (decomposition["regime"].astype(str) == regime)
                & (decomposition["component_id"].astype(str) == component)
            ]
            if len(matches) > 1:
                raise ValueError("Figure 6c has duplicated regime/component rows")
            values.append(
                float(_numeric(matches, "contribution_per_kw_year").iloc[0])
                if len(matches) == 1
                else 0.0
            )
            if len(matches) == 1:
                label = str(matches["component_label"].iloc[0])
        array = np.asarray(values, dtype=float)
        if not np.any(np.abs(array) > 1e-12):
            continue
        positive = np.maximum(array, 0.0)
        negative = np.minimum(array, 0.0)
        color = component_colors[component]
        axis.bar(
            positions,
            positive,
            bottom=positive_bottom,
            color=color,
            width=0.64,
            linewidth=0.0,
        )
        axis.bar(
            positions,
            negative,
            bottom=negative_bottom,
            color=color,
            width=0.64,
            linewidth=0.0,
        )
        positive_bottom += positive
        negative_bottom += negative
        legend_handles.append(Patch(facecolor=color, label=label or component))
    totals = np.asarray(
        [
            float(
                _numeric(
                    decomposition[decomposition["regime"].astype(str) == regime],
                    "risk_adjusted_break_even_capacity_payment_per_kw_year",
                ).iloc[0]
            )
            for regime in _REGIME_ORDER
        ]
    )
    component_totals = np.asarray(
        [
            float(
                _numeric(
                    decomposition[decomposition["regime"].astype(str) == regime],
                    "contribution_per_kw_year",
                ).sum()
            )
            for regime in _REGIME_ORDER
        ]
    )
    if not np.allclose(component_totals, totals, rtol=0.0, atol=1e-6):
        raise ValueError("Figure 6c component contributions do not close to break-even payment")
    axis.scatter(
        positions,
        totals,
        marker="D",
        s=28,
        facecolor="white",
        edgecolor=_COLORS["ink"],
        linewidth=0.8,
        zorder=5,
        label="Total break-even",
    )
    axis.axhline(0.0, color=_COLORS["ink"], linewidth=0.7)
    axis.set_xticks(positions)
    axis.set_xticklabels(
        [_BOUNDARY_LABELS[regime] for regime in _REGIME_ORDER],
        rotation=0,
        rotation_mode="anchor",
    )
    axis.set_ylabel("Contribution to break-even\ncapacity payment (USD/kW-year)")
    axis.set_title("Incremental cost and non-capacity credits", loc="left")
    axis.grid(axis="y", color=_COLORS["grid"], linewidth=0.5, zorder=0)
    lower = min(float(negative_bottom.min()), 0.0)
    upper = max(float(positive_bottom.max()), float(totals.max()), 1.0)
    axis.set_ylim(lower - 0.05 * upper, upper * 1.42)
    axis.legend(
        handles=[
            *legend_handles,
            Line2D(
                [],
                [],
                marker="D",
                markerfacecolor="white",
                markeredgecolor=_COLORS["ink"],
                linestyle="none",
                label="Total break-even",
            ),
        ],
        loc="upper left",
        ncol=2,
        columnspacing=0.8,
        handlelength=1.0,
    )
    _panel_label(axis, "c")


def _plot_duration_break_even(axis: Any, duration_rows: pd.DataFrame) -> None:
    required = (
        "regime",
        "duration_h",
        "break_even_capacity_payment_per_kw_year",
        "risk_adjusted_break_even_capacity_payment_per_kw_year",
        "technical_capacity_ceiling_kw",
        "candidate_reduction_kw",
        "technical_qualification",
    )
    _require_columns(duration_rows, required, table_id="fig6_duration_break_even")
    if set(duration_rows["regime"].astype(str)) != set(_REGIME_ORDER):
        raise ValueError("Figure 6d requires every participation regime")
    _assert_certified_full_offer(duration_rows, table_id="fig6_duration_break_even")
    durations = sorted(_numeric(duration_rows, "duration_h").astype(int).unique())
    endpoint_annotations: list[tuple[str, float]] = []
    all_values: list[float] = []
    for regime in _REGIME_ORDER:
        subset = duration_rows[duration_rows["regime"].astype(str) == regime].copy()
        subset = subset.sort_values("duration_h", kind="stable")
        if list(_numeric(subset, "duration_h").astype(int)) != durations:
            raise ValueError("Figure 6d duration grid must be complete for every regime")
        x = _numeric(subset, "duration_h").to_numpy(dtype=float)
        mean = _numeric(subset, "break_even_capacity_payment_per_kw_year").to_numpy(dtype=float)
        risk = _numeric(subset, "risk_adjusted_break_even_capacity_payment_per_kw_year").to_numpy(
            dtype=float
        )
        if np.any(risk + 1e-9 < mean):
            raise ValueError("Figure 6d risk-adjusted break-even cannot be below the mean")
        all_values.extend(mean.tolist())
        all_values.extend(risk.tolist())
        axis.vlines(x, mean, risk, color=_REGIME_COLORS[regime], linewidth=1.0, alpha=0.55)
        axis.plot(
            x,
            risk,
            color=_REGIME_COLORS[regime],
            marker="D",
            markersize=3.2,
            linewidth=1.4,
        )
        axis.scatter(
            x,
            mean,
            facecolors="white",
            edgecolors=_REGIME_COLORS[regime],
            linewidths=0.8,
            s=22,
            marker="o",
            zorder=4,
        )
        endpoint_annotations.append((regime, float(risk[-1])))
    axis.set_xticks(durations)
    value_span = max(max(all_values) - min(all_values), 1.0)
    lower = min(all_values) - 0.10 * value_span
    upper = max(all_values) + 0.15 * value_span
    axis.set_xlim(min(durations) - 0.15, max(durations) + 2.25)
    axis.set_ylim(lower, upper)
    label_y = _spread_label_positions(
        [item[1] for item in endpoint_annotations],
        lower=lower + 0.05 * value_span,
        upper=upper - 0.05 * value_span,
        minimum_gap=0.10 * value_span,
    )
    for (regime, endpoint_y), position_y in zip(endpoint_annotations, label_y, strict=True):
        axis.plot(
            [durations[-1], durations[-1] + 0.16],
            [endpoint_y, position_y],
            color=_REGIME_COLORS[regime],
            linewidth=0.7,
        )
        axis.text(
            durations[-1] + 0.21,
            position_y,
            _REGIME_SHORT_LABELS[regime],
            color=_REGIME_COLORS[regime],
            fontsize=5.8,
            va="center",
            ha="left",
        )
    axis.set_xlabel("Certified event duration (h)")
    axis.set_ylabel("Break-even capacity payment (USD/kW-year)")
    axis.set_title("Duration changes the cost of a certified commitment", loc="left")
    axis.grid(axis="y", color=_COLORS["grid"], linewidth=0.5)
    axis.legend(
        handles=[
            Line2D(
                [],
                [],
                marker="o",
                markerfacecolor="white",
                markeredgecolor=_COLORS["ink"],
                linestyle="none",
                label="Mean",
            ),
            Line2D(
                [],
                [],
                marker="D",
                color=_COLORS["ink"],
                linestyle="none",
                label="Risk rule (5th percentile)",
            ),
        ],
        loc="upper left",
        ncol=2,
        columnspacing=0.7,
        handlelength=1.2,
    )
    _panel_label(axis, "d")


def _plot_economic_participation_figure_into(
    source_data_directory: str | Path,
    output_directory: str | Path,
    *,
    formats: tuple[str, ...] = ("svg", "pdf", "tiff", "png"),
) -> dict[str, object]:
    """Render a legacy audit preview, never the formal manuscript artwork."""

    _publication_style()
    manifest_path, manifest = _load_manifest(source_data_directory)
    loaded = {
        table_id: _verified_table(source_data_directory, manifest, table_id)
        for table_id in (
            "fig6_technical_economic_boundary",
            "fig6_mechanism_sensitivity",
            "fig6_break_even_decomposition",
            "fig6_duration_break_even",
        )
    }
    frames = {table_id: item[0] for table_id, item in loaded.items()}
    source_paths = {
        "a": loaded["fig6_technical_economic_boundary"][1],
        "b": loaded["fig6_mechanism_sensitivity"][1],
        "c": loaded["fig6_break_even_decomposition"][1],
        "d": loaded["fig6_duration_break_even"][1],
    }
    _validate_analysis_context(frames)

    figure = plt.figure(figsize=(_FIGURE_WIDTH_IN, 5.9))
    grid = figure.add_gridspec(
        2,
        2,
        width_ratios=(1.0, 1.0),
        height_ratios=(1.0, 1.0),
        left=0.105,
        right=0.985,
        bottom=0.115,
        top=0.95,
        wspace=0.32,
        hspace=0.48,
    )
    axis_a = figure.add_subplot(grid[0, 0])
    axis_b = figure.add_subplot(grid[0, 1])
    axis_c = figure.add_subplot(grid[1, 0])
    axis_d = figure.add_subplot(grid[1, 1])

    _plot_boundary(axis_a, frames["fig6_technical_economic_boundary"])
    _plot_mechanism_sensitivity(axis_b, frames["fig6_mechanism_sensitivity"])
    _plot_break_even_decomposition(axis_c, frames["fig6_break_even_decomposition"])
    _plot_duration_break_even(axis_d, frames["fig6_duration_break_even"])
    figure.text(
        0.5,
        0.012,
        "Real-2026 USD sensitivity coordinates; fresh-event development screening.\n"
        "Not a chronological dispatch programme or an economic certificate.",
        ha="center",
        va="bottom",
        fontsize=6.5,
        color=_COLORS["neutral"],
    )

    destination = Path(output_directory).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    outputs = _record_outputs(
        figure,
        output_directory=destination,
        stem="figure_6_economic_participation",
        formats=formats,
    )
    plt.close(figure)
    panel_data = _copy_panel_data(source_paths, destination)
    manifest_document: dict[str, object] = {
        "schema_version": "aidrbench.economic_figure_manifest.v1",
        "artwork_status": "local_audit_preview_not_formal_manuscript_artwork",
        "figure": 6,
        "title": "Economic participation is bounded by the cost of reserved or displaced compute",
        "backend": "python_matplotlib",
        "archetype": "asymmetric_mixed_modality_figure",
        "physical_size_inches": [_FIGURE_WIDTH_IN, 5.9],
        "minimum_configured_font_pt": _MIN_FONT_PT,
        "core_conclusion": (
            "A technically certified DR ceiling becomes economically offerable only when "
            "natural workload slack or grid compensation covers the incremental cost of "
            "reserved or displaced compute."
        ),
        "analysis_role": "development_parameterized_screening",
        "claim_boundaries": [
            "The result is not an independent economic locked-ID certificate.",
            "Payment and cost values are declared sensitivity coordinates, not named-market "
            "tariffs.",
            "Main-figure economics evaluates only zero or the independently certified Kcert; "
            "lower development-screened offers are excluded.",
            "p05 refers to an independent fresh-event bootstrap, not a chronological repeated "
            "dispatch programme.",
        ],
        "source_data_manifest_sha256": _sha256(manifest_path),
        "source_tables": {
            table_id: {
                "output": str(record[2]["output"]),
                "output_sha256": str(record[2]["output_sha256"]),
                "row_count": int(len(record[0])),
            }
            for table_id, record in loaded.items()
        },
        "outputs": outputs,
        "exact_panel_data_exports": panel_data,
    }
    output_manifest = destination / "figure_6_manifest.json"
    output_manifest.write_text(
        json.dumps(manifest_document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    qa = {
        "panels": {
            "a": "mean and p05-rule break-even payment at the certified 4-h commitment",
            "b": "one predeclared mechanism-specific sensitivity driver per regime",
            "c": "signed per-kW-year cost and non-capacity-credit decomposition",
            "d": "mean and p05-rule break-even payment across certified durations",
        },
        "source_table_row_counts": {
            table_id: int(len(frame)) for table_id, frame in frames.items()
        },
        "excluded_rows": "none; each panel consumes all rows in its declared source-data table",
        "uncertainty": "p05 annual net-value bootstrap rule is shown where applicable",
        "image_integrity": "no raster experimental images or image processing are used",
        "interpretation": manifest_document["claim_boundaries"],
    }
    qa_path = destination / "figure_6_qa.json"
    qa_path.write_text(
        json.dumps(qa, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "figure": 6,
        "outputs": [
            {**record, "path": str(destination / str(record["path"]))} for record in outputs
        ],
        "manifest": str(output_manifest),
        "qa": str(qa_path),
        "panel_data": [
            {**record, "path": str(destination / str(record["path"]))} for record in panel_data
        ],
    }


def plot_economic_participation_figure(
    source_data_directory: str | Path,
    output_directory: str | Path,
    *,
    formats: tuple[str, ...] = ("svg", "pdf", "tiff", "png"),
) -> dict[str, object]:
    """Atomically publish Figure 6 and its exact panel data into a new directory."""

    destination = Path(output_directory).resolve()
    if destination.exists():
        raise FileExistsError(
            f"economic figure output already exists; use a new output directory: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.",
            suffix=".economic-figure.tmp",
            dir=destination.parent,
        )
    )
    try:
        summary = _plot_economic_participation_figure_into(
            source_data_directory,
            staging,
            formats=formats,
        )
        os.replace(staging, destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    output_records = cast(list[dict[str, object]], summary["outputs"])
    panel_records = cast(list[dict[str, object]], summary["panel_data"])
    summary["outputs"] = [
        {**record, "path": str(destination / Path(str(record["path"])).name)}
        for record in output_records
    ]
    summary["panel_data"] = [
        {**record, "path": str(destination / Path(str(record["path"])).name)}
        for record in panel_records
    ]
    summary["manifest"] = str(destination / "figure_6_manifest.json")
    summary["qa"] = str(destination / "figure_6_qa.json")
    summary["final_publish"] = "atomic_directory_rename"
    return summary
