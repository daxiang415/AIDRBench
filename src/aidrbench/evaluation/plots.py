"""Deterministic representative-week figures for hourly benchmark results."""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

_matplotlib_cache = Path(tempfile.gettempdir()) / "aidrbench-matplotlib"
_matplotlib_cache.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_matplotlib_cache))

import matplotlib  # noqa: E402
import pandas as pd  # noqa: E402

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

_REQUIRED_COLUMNS = frozenset(
    {
        "hour",
        "pcc_power_kw",
        "baseline_pcc_power_kw",
        "pcc_limit_kw",
        "dc_power_kw",
        "backlog_gpu_h",
        "compute_debt_kwh",
        "event_active",
    }
)


def _episode_catalog(input_directory: Path) -> pd.DataFrame:
    episodes_path = input_directory / "episodes.parquet"
    if episodes_path.exists():
        catalog = pd.read_parquet(episodes_path)
        required = {"controller", "seed", "timeseries"}
        missing = sorted(required.difference(catalog.columns))
        if missing:
            raise ValueError(f"benchmark episodes.parquet is missing columns: {missing}")
        if catalog.empty:
            raise ValueError("benchmark episodes.parquet is empty")
        return catalog.loc[:, ["controller", "seed", "timeseries"]].copy()

    timeseries_path = input_directory / "timeseries.parquet"
    if not timeseries_path.exists():
        raise FileNotFoundError(
            f"expected {episodes_path} or {timeseries_path} under plot input"
        )
    frame = pd.read_parquet(timeseries_path, columns=["controller", "episode_seed"])
    if frame.empty:
        raise ValueError("rollout timeseries.parquet is empty")
    return pd.DataFrame.from_records(
        [
            {
                "controller": str(frame["controller"].iloc[0]),
                "seed": int(frame["episode_seed"].iloc[0]),
                "timeseries": str(timeseries_path),
            }
        ]
    )


def _resolve_timeseries_path(input_directory: Path, row: pd.Series) -> Path:
    controller = str(row["controller"])
    seed = int(row["seed"])
    configured = Path(str(row["timeseries"]))
    candidates = (
        configured,
        input_directory / configured,
        input_directory / "episodes" / controller / f"seed_{seed}" / "timeseries.parquet",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"timeseries for controller={controller}, seed={seed} was not found; "
        f"catalog value was {configured}"
    )


def _event_spans(frame: pd.DataFrame) -> list[tuple[float, float]]:
    active = frame["event_active"].astype(bool).to_numpy()
    hours = frame["hour"].astype(float).to_numpy()
    spans: list[tuple[float, float]] = []
    start: int | None = None
    for index, is_active in enumerate(active):
        if is_active and start is None:
            start = index
        if start is not None and (not is_active or index == len(active) - 1):
            stop = index - 1 if not is_active else index
            spans.append((float(hours[start] - 0.5), float(hours[stop] + 0.5)))
            start = None
    return spans


def _safe_label(value: str) -> str:
    label = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_.")
    return label or "controller"


def _plot_episode(
    frame: pd.DataFrame,
    *,
    controller: str,
    seed: int,
    output_path: Path,
) -> None:
    missing = sorted(_REQUIRED_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"hourly timeseries is missing plot columns: {missing}")
    if frame.empty:
        raise ValueError("cannot plot an empty hourly timeseries")

    hours = frame["hour"].astype(float)
    figure, axes = plt.subplots(
        3,
        1,
        figsize=(12.0, 8.5),
        sharex=True,
        gridspec_kw={"height_ratios": (1.25, 0.9, 1.0)},
        constrained_layout=True,
    )
    power_axis, dc_axis, backlog_axis = axes

    power_axis.plot(hours, frame["pcc_power_kw"], label="Controlled PCC", linewidth=1.5)
    power_axis.plot(
        hours,
        frame["baseline_pcc_power_kw"],
        label="No-control PCC",
        linewidth=1.1,
        linestyle="--",
    )
    power_axis.plot(hours, frame["pcc_limit_kw"], label="DR/PCC limit", linewidth=1.2)
    power_axis.set_ylabel("PCC power (kW)")
    power_axis.legend(loc="upper right", ncols=3, fontsize=8)

    dc_axis.plot(hours, frame["dc_power_kw"], color="tab:purple", label="Data center")
    dc_axis.set_ylabel("DC power (kW)")
    dc_axis.legend(loc="upper right", fontsize=8)

    backlog_axis.plot(
        hours,
        frame["backlog_gpu_h"],
        color="tab:orange",
        label="Backlog",
    )
    backlog_axis.set_ylabel("Backlog (GPU-h)")
    debt_axis = backlog_axis.twinx()
    debt_axis.plot(
        hours,
        frame["compute_debt_kwh"],
        color="tab:red",
        linestyle="--",
        label="Compute debt",
    )
    debt_axis.set_ylabel("Compute debt (kWh)")
    handles_a, labels_a = backlog_axis.get_legend_handles_labels()
    handles_b, labels_b = debt_axis.get_legend_handles_labels()
    backlog_axis.legend(handles_a + handles_b, labels_a + labels_b, loc="upper right", fontsize=8)
    backlog_axis.set_xlabel("Episode hour")

    for start, stop in _event_spans(frame):
        for axis in axes:
            axis.axvspan(start, stop, color="tab:blue", alpha=0.08, linewidth=0)
    for axis in axes:
        axis.grid(True, linewidth=0.4, alpha=0.35)
    power_axis.set_title(f"Representative week: {controller} (seed {seed})")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def plot_hourly_results(
    input_directory: str | Path,
    output_directory: str | Path,
    *,
    controllers: Sequence[str] | None = None,
    seed: int | None = None,
    include_clearance_tail: bool = False,
) -> dict[str, Any]:
    """Plot one deterministic representative episode for each selected controller.

    The default selection uses every controller and its minimum available seed.
    Formal locked-test selection is therefore never implicit in this utility.
    """

    input_path = Path(input_directory)
    output_path = Path(output_directory)
    catalog = _episode_catalog(input_path)
    available = tuple(dict.fromkeys(catalog["controller"].astype(str)))
    selected = tuple(controllers) if controllers is not None else available
    if not selected:
        raise ValueError("at least one plot controller is required")
    missing_controllers = sorted(set(selected).difference(available))
    if missing_controllers:
        raise ValueError(
            f"plot controllers not present in benchmark: {missing_controllers}; "
            f"available={list(available)}"
        )

    output_path.mkdir(parents=True, exist_ok=True)
    figure_records: list[dict[str, Any]] = []
    for controller in selected:
        rows = catalog.loc[catalog["controller"].astype(str) == controller].copy()
        rows["seed"] = rows["seed"].astype(int)
        selected_seed = int(rows["seed"].min()) if seed is None else seed
        selected_rows = rows.loc[rows["seed"] == selected_seed]
        if selected_rows.empty:
            raise ValueError(f"controller {controller} has no episode for seed {selected_seed}")
        timeseries_path = _resolve_timeseries_path(input_path, selected_rows.iloc[0])
        frame = pd.read_parquet(timeseries_path)
        if not include_clearance_tail and "is_clearance_tail" in frame:
            frame = frame.loc[~frame["is_clearance_tail"].astype(bool)].copy()
        figure_path = (
            output_path
            / f"representative_week_{_safe_label(controller)}_seed_{selected_seed}.png"
        )
        _plot_episode(
            frame,
            controller=controller,
            seed=selected_seed,
            output_path=figure_path,
        )
        figure_records.append(
            {
                "controller": controller,
                "seed": selected_seed,
                "hours": len(frame),
                "timeseries": str(timeseries_path),
                "figure": str(figure_path),
            }
        )

    manifest_path = output_path / "plot_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "input": str(input_path),
                "include_clearance_tail": include_clearance_tail,
                "figures": figure_records,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"figures": figure_records, "manifest": str(manifest_path)}
