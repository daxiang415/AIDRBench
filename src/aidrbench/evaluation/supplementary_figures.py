"""Reproducible Supplementary Figures for the Nature Communications manuscript."""
# ruff: noqa: E402, E501

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

_matplotlib_cache = Path(tempfile.gettempdir()) / "aidrbench-matplotlib"
_matplotlib_cache.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_matplotlib_cache))

import matplotlib

matplotlib.use("Agg", force=True)

import numpy as np
import pandas as pd
import yaml
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

from aidrbench.controllers.hourly import make_hourly_controller
from aidrbench.controllers.robust_mpc_spec import load_robust_mpc_specification
from aidrbench.data.frozen_scenarios import load_frozen_hourly_scenario
from aidrbench.data.splits import sha256_file
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv
from aidrbench.evaluation.frozen_causal_certificate import _environment_document
from aidrbench.evaluation.hourly_rollout import rollout_hourly_episode
from aidrbench.evaluation.nature_figures import (
    _COLORS,
    _MIN_FONT_PT,
    _format_outputs,
    _panel_label,
    _publication_style,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_VERSION = "aidrbench.supplementary_figure_specification.v1"
_FIGURE_WIDTH_MM = 183.0
_FIGURE_WIDTH_IN = _FIGURE_WIDTH_MM / 25.4
_EXPORT_SUFFIXES = (".svg", ".pdf", ".tiff", ".png")
_TIFF_DPI = 600


def _supplementary_publication_style() -> None:
    """Declare the local final-size typography contract before shared styling."""

    _publication_style()
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Liberation Sans", "Helvetica", "sans-serif"],
            "font.size": 7.0,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
        }
    )
    if _TIFF_DPI < 600 or set(_EXPORT_SUFFIXES) != {".svg", ".pdf", ".tiff", ".png"}:
        raise RuntimeError("supplementary export contract is invalid")


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_specification(path: str | Path) -> dict[str, Any]:
    document = _mapping(yaml.safe_load(Path(path).read_text(encoding="utf-8")), "specification")
    expected = {
        "schema_version",
        "evidence_scope",
        "locked_sets_used",
        "environment_flow",
        "calibration",
        "observation_and_trajectory",
        "export",
    }
    if set(document) != expected:
        raise ValueError("supplementary figure specification fields mismatch")
    if document["schema_version"] != 1:
        raise ValueError("supplementary figure schema_version must be 1")
    if document["locked_sets_used"] is not False:
        raise ValueError("supplementary figures must not use locked scenarios")
    trajectory = _mapping(document["observation_and_trajectory"], "observation_and_trajectory")
    scenario_set = Path(str(trajectory["scenario_set"]))
    if "locked" in str(scenario_set).lower() or "validation" not in scenario_set.name.lower():
        raise ValueError("representative trajectory must use the non-locked validation set")
    export = _mapping(document["export"], "export")
    if float(export["width_mm"]) != 183.0 or float(export["minimum_font_pt"]) < 5.0:
        raise ValueError("supplementary figure export contract mismatch")
    return document


def _source_record(path: str | Path) -> dict[str, object]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    return {"path": str(source), "sha256": sha256_file(source), "bytes": source.stat().st_size}


def _write_csv(frame: pd.DataFrame, path: Path) -> dict[str, object]:
    frame.to_csv(path, index=False, lineterminator="\n", float_format="%.12g")
    return {
        "path": path.name,
        "sha256": _sha256(path),
        "rows": len(frame),
        "columns": frame.columns.tolist(),
    }


def _finalize(
    figure: Figure,
    *,
    number: int,
    output_directory: Path,
    formats: Sequence[str],
    source_records: Sequence[dict[str, object]],
    source_data: Sequence[dict[str, object]],
    conclusion: str,
    boundaries: Sequence[str],
    archetype: str,
) -> dict[str, object]:
    size = [float(value) for value in figure.get_size_inches()]
    stem = f"supplementary_figure_{number}"
    outputs = _format_outputs(
        figure,
        output_directory=output_directory,
        stem=stem,
        formats=formats,
    )
    plt.close(figure)
    manifest = {
        "schema_version": _SCHEMA_VERSION,
        "figure": f"S{number}",
        "backend": "python_matplotlib",
        "archetype": archetype,
        "core_conclusion": conclusion,
        "claim_boundaries": list(boundaries),
        "physical_size_inches": size,
        "minimum_configured_font_pt": _MIN_FONT_PT,
        "sources": list(source_records),
        "source_data": list(source_data),
        "outputs": outputs,
    }
    manifest_path = output_directory / f"supplementary_figure_{number}_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "figure": f"S{number}",
        "manifest": str(manifest_path),
        "outputs": [
            {**record, "path": str(output_directory / str(record["path"]))}
            for record in outputs
        ],
    }


def _box(
    axis: Axes,
    x: float,
    y: float,
    width: float,
    height: float,
    text: str,
    *,
    facecolor: str,
    edgecolor: str = _COLORS["navy"],
    fontsize: float = 6.7,
    weight: str = "normal",
    textcolor: str = _COLORS["ink"],
) -> None:
    axis.add_patch(
        FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.01,rounding_size=0.012",
            facecolor=facecolor,
            edgecolor=edgecolor,
            linewidth=0.8,
            transform=axis.transAxes,
        )
    )
    axis.text(
        x + width / 2,
        y + height / 2,
        text,
        transform=axis.transAxes,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight=weight,
        color=textcolor,
    )


def _arrow(axis: Axes, start: tuple[float, float], end: tuple[float, float]) -> None:
    axis.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=0.9,
            color=_COLORS["neutral"],
            transform=axis.transAxes,
        )
    )


def _plot_environment_flow(
    specification: dict[str, Any], output: Path, formats: Sequence[str]
) -> dict[str, object]:
    _supplementary_publication_style()
    flow = _mapping(specification["environment_flow"], "environment_flow")
    sources = [_source_record(flow[key]) for key in sorted(flow)]
    figure, (ax_a, ax_b) = plt.subplots(
        2,
        1,
        figsize=(_FIGURE_WIDTH_IN, 4.65),
        gridspec_kw={"height_ratios": (1.08, 0.92)},
    )
    for axis in (ax_a, ax_b):
        axis.set_axis_off()
        axis.set_xlim(0, 1)
        axis.set_ylim(0, 1)

    inputs = (
        (0.01, "Community\nload + PV", _COLORS["pale_blue"]),
        (0.205, "Alibaba 2026\njob sampler", _COLORS["pale_teal"]),
        (0.40, "Demand-response\nevent specification", _COLORS["pale_gold"]),
        (0.595, "Four-GPU power\ncalibration", _COLORS["pale_red"]),
    )
    for x, label, color in inputs:
        _box(ax_a, x, 0.72, 0.175, 0.18, label, facecolor=color, weight="bold")
        _arrow(ax_a, (x + 0.0875, 0.72), (0.49, 0.61))
    _box(
        ax_a,
        0.375,
        0.48,
        0.25,
        0.14,
        "Hash-bound frozen\nhourly scenario",
        facecolor="white",
        edgecolor=_COLORS["blue"],
        fontsize=7.2,
        weight="bold",
    )
    _arrow(ax_a, (0.50, 0.48), (0.50, 0.39))
    transition_boxes = (
        (0.02, "Release\narrivals"),
        (0.21, "Deadline\nqueues"),
        (0.40, "Aggregate\naction"),
        (0.59, "Class-aware\npower"),
        (0.78, "Community\nPCC metrics"),
    )
    for index, (x, label) in enumerate(transition_boxes):
        _box(ax_a, x, 0.17, 0.16, 0.15, label, facecolor=_COLORS["light"])
        if index < len(transition_boxes) - 1:
            _arrow(ax_a, (x + 0.16, 0.245), (transition_boxes[index + 1][0], 0.245))
    ax_a.text(
        0.5,
        0.06,
        "One-hour transition: arrivals → feasible execution → power → service and grid outcomes",
        transform=ax_a.transAxes,
        ha="center",
        fontsize=7.0,
        color=_COLORS["neutral"],
    )
    _panel_label(ax_a, "a", x=-0.01, y=1.0)

    layers = (
        (0.01, 0.19, "Nominal\nproxy", _COLORS["neutral"]),
        (0.205, 0.19, "Perfect-\ninformation", _COLORS["gold"]),
        (0.40, 0.19, "Restricted non-\nanticipative", _COLORS["purple"]),
        (0.595, 0.19, "Frozen causal\nrobust MPC", _COLORS["blue"]),
        (0.79, 0.19, "Locked-ID /\nlocked-OOD", _COLORS["red"]),
    )
    for index, (x, width, label, color) in enumerate(layers):
        textcolor = _COLORS["ink"] if color == _COLORS["gold"] else "white"
        _box(ax_b, x, 0.67, width - 0.02, 0.17, label, facecolor=color, edgecolor=color, fontsize=6.5, weight="bold", textcolor=textcolor)
        if index < len(layers) - 1:
            _arrow(ax_b, (x + width - 0.02, 0.755), (layers[index + 1][0], 0.755))
    outputs = (
        (0.04, "Firm capacity\nH × N × q", _COLORS["pale_blue"]),
        (0.285, "Repeated-event\ncompute debt", _COLORS["pale_red"]),
        (0.53, "PV hosting and\nPV utilisation", _COLORS["pale_teal"]),
        (0.775, "Transfer and\nfailure boundary", _COLORS["pale_gold"]),
    )
    for x, label, color in outputs:
        _box(ax_b, x, 0.25, 0.18, 0.17, label, facecolor=color, fontsize=6.6)
    ax_b.add_patch(
        Rectangle(
            (0.50, 0.17),
            0.22,
            0.34,
            facecolor="none",
            edgecolor=_COLORS["flex"],
            linewidth=1.0,
            linestyle="--",
            transform=ax_b.transAxes,
        )
    )
    ax_b.text(
        0.61,
        0.11,
        "BESS appears only in the renewable-planning branch",
        transform=ax_b.transAxes,
        ha="center",
        fontsize=6.4,
        color=_COLORS["flex"],
    )
    ax_b.text(
        0.5,
        0.00,
        "The environment is reusable; the manuscript distinguishes planning bounds from independently tested causal offers.",
        transform=ax_b.transAxes,
        ha="center",
        fontsize=7.0,
        color=_COLORS["ink"],
    )
    _panel_label(ax_b, "b", x=-0.01, y=1.0)
    figure.subplots_adjust(left=0.04, right=0.98, bottom=0.04, top=0.98, hspace=0.20)
    return _finalize(
        figure,
        number=1,
        output_directory=output,
        formats=formats,
        source_records=sources,
        source_data=(),
        conclusion="AIDRBench converts trace-informed jobs and measured power into distinct planning and causal demand-response evidence layers.",
        boundaries=(
            "The environment is a benchmark implementation, not the paper's sole scientific contribution.",
            "BESS is optimized only in the renewable-planning branch and is not an online environment action.",
        ),
        archetype="schematic-led composite",
    )


def _plot_calibration(
    specification: dict[str, Any], output: Path, formats: Sequence[str]
) -> dict[str, object]:
    _supplementary_publication_style()
    calibration = _mapping(specification["calibration"], "calibration")
    artifact_path = Path(str(calibration["artifact"]))
    means_path = Path(str(calibration["run_gpu_means"]))
    artifact = _mapping(yaml.safe_load(artifact_path.read_text(encoding="utf-8")), "artifact")
    means = pd.read_parquet(means_path)
    table_record = _write_csv(means, output / "supplementary_figure_2_calibration.csv")
    fit_repeats = {int(value) for value in calibration["fit_repeats"]}
    held_out_repeats = {int(value) for value in calibration["held_out_repeats"]}
    if fit_repeats & held_out_repeats:
        raise ValueError("calibration fit and held-out repeats overlap")

    figure, (ax_a, ax_b) = plt.subplots(
        1,
        2,
        figsize=(_FIGURE_WIDTH_IN, 3.45),
        gridspec_kw={"width_ratios": (1.45, 1.0)},
    )
    categories = (
        ("training", 1, "Training\n1 GPU", _COLORS["purple"]),
        ("training", 4, "Training\n4 GPUs", _COLORS["purple"]),
        ("offline_inference", 1, "Inference\n1 GPU", _COLORS["flex"]),
        ("offline_inference", 4, "Inference\n4 GPUs", _COLORS["flex"]),
    )
    for category, (mode, count, label, color) in enumerate(categories):
        subset = means[(means["mode"] == mode) & (means["gpu_count"] == count)]
        for repeat, group in subset.groupby("repeat", sort=True):
            repeat_value = int(float(str(repeat)))
            center = category + (repeat_value - 2) * 0.16
            values = group["mean_power_w"].to_numpy(dtype=float)
            offsets = np.linspace(-0.045, 0.045, len(values)) if len(values) > 1 else [0.0]
            held_out = repeat_value in held_out_repeats
            ax_a.scatter(
                center + np.asarray(offsets),
                values,
                s=22,
                facecolors="white" if held_out else color,
                edgecolors=color,
                linewidths=0.8,
                zorder=3,
            )
            ax_a.hlines(values.mean(), center - 0.07, center + 0.07, color=_COLORS["ink"], lw=1.0)
        ax_a.text(category, 211, label, ha="center", va="top", fontsize=6.6)
    ax_a.set_xlim(-0.55, 3.55)
    ax_a.set_ylim(205, 310)
    ax_a.set_xticks([])
    ax_a.set_ylabel("GPU-board power (W)")
    ax_a.grid(axis="y", color=_COLORS["grid"], linewidth=0.5)
    ax_a.set_title("Measured GPU observations and run means", loc="left", fontweight="bold")
    ax_a.scatter([], [], s=22, color=_COLORS["neutral"], label="Fit repeats 1–2")
    ax_a.scatter([], [], s=22, facecolors="white", edgecolors=_COLORS["neutral"], label="Held-out repeat 3")
    ax_a.legend(loc="upper left", ncol=2, handletextpad=0.4, columnspacing=1.0)
    _panel_label(ax_a, "a", x=-0.12, y=1.05)

    parameters = _mapping(artifact["parameters"], "artifact.parameters")
    active = _mapping(parameters["active_power_w_per_gpu_by_class"], "active power")
    rows: list[tuple[str, float, float, float, str]] = []
    for label, key, color in (
        ("Training", "training", _COLORS["purple"]),
        ("Offline inference", "offline_inference", _COLORS["flex"]),
    ):
        entry = _mapping(active[key], key)
        interval = [float(value) for value in entry["uncertainty_interval_w"]]
        rows.append((label, float(entry["estimate_w"]), interval[0], interval[1], color))
    for y, (label, estimate, lower, upper, color) in enumerate(rows[::-1]):
        ax_b.errorbar(
            estimate,
            y,
            xerr=np.array([[estimate - lower], [upper - estimate]]),
            fmt="o",
            color=color,
            ecolor=color,
            capsize=3,
            markersize=5,
        )
        ax_b.text(205, y, label, ha="left", va="center", fontsize=6.8)
    held_out_mae = float(
        _mapping(artifact["validation"], "validation")["held_out_power_mae_w"]
    )
    ax_b.axvline(300.0, color=_COLORS["grid"], linewidth=0.7)
    ax_b.set_yticks([])
    ax_b.set_xlim(200, 315)
    ax_b.set_ylim(-0.7, 1.7)
    ax_b.set_xlabel("Active power per GPU (W)")
    ax_b.set_title("Four-GPU fit and held-out check", loc="left", fontweight="bold")
    ax_b.text(
        0.02,
        0.13,
        f"Held-out MAE: {held_out_mae:.2f} W per GPU\n4 × PCIe GPUs; no NVLink\nNode overhead: engineering assumption",
        transform=ax_b.transAxes,
        fontsize=6.6,
        va="bottom",
        color=_COLORS["neutral"],
    )
    _panel_label(ax_b, "b", x=-0.12, y=1.05)
    figure.subplots_adjust(left=0.07, right=0.98, bottom=0.14, top=0.90, wspace=0.28)
    return _finalize(
        figure,
        number=2,
        output_directory=output,
        formats=formats,
        source_records=(_source_record(artifact_path), _source_record(means_path)),
        source_data=(table_record,),
        conclusion="Four-GPU measurements identify class-specific active board-power parameters and a held-out prediction error for the benchmark power model.",
        boundaries=(
            "GPU observations within a run are repeated measurements; independent run means are the uncertainty unit.",
            "The measurements anchor board power and do not measure whole-facility cooling or node overhead.",
        ),
        archetype="quantitative grid",
    )


def _selected_validation_artifact(trajectory: Mapping[str, Any]) -> Any:
    root = Path(str(trajectory["scenario_set"]))
    candidates: list[tuple[int, Path]] = []
    for child in root.iterdir():
        metadata_path = child / "metadata.json"
        if not metadata_path.is_file():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        candidates.append((int(metadata["episode_seed"]), child))
    if not candidates:
        raise ValueError("validation scenario set is empty")
    seed, path = min(candidates)
    if trajectory["representative_rule"] != "minimum_episode_seed":
        raise ValueError("unsupported representative trajectory rule")
    if seed != int(trajectory["expected_episode_seed"]):
        raise ValueError("representative trajectory seed mismatch")
    artifact = load_frozen_hourly_scenario(path)
    if artifact.scenario_hash != str(trajectory["expected_scenario_hash"]):
        raise ValueError("representative trajectory scenario hash mismatch")
    return artifact


def _selected_capacity(trajectory: Mapping[str, Any]) -> float:
    selection_path = Path(str(trajectory["selection"]))
    if sha256_file(selection_path) != str(trajectory["selection_sha256"]):
        raise ValueError("representative trajectory selection hash mismatch")
    selection = _mapping(json.loads(selection_path.read_text(encoding="utf-8")), "selection")
    matches = [
        row
        for row in selection["selected_capacities"]
        if int(row["duration_h"]) == int(trajectory["duration_h"])
        and int(row["notice_h"]) == int(trajectory["notice_h"])
        and np.isclose(float(row["reliability_target"]), float(trajectory["reliability_target"]))
    ]
    if len(matches) != 1:
        raise ValueError("representative trajectory capacity must match exactly one selection")
    return float(matches[0]["candidate_reduction_kw"])


def _build_observation_and_trajectory(
    specification: dict[str, Any], output: Path
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], list[dict[str, object]]]:
    trajectory = _mapping(
        specification["observation_and_trajectory"], "observation_and_trajectory"
    )
    artifact = _selected_validation_artifact(trajectory)
    capacity_kw = _selected_capacity(trajectory)
    controller_path = Path(str(trajectory["controller"]))
    if sha256_file(controller_path) != str(trajectory["controller_sha256"]):
        raise ValueError("representative trajectory controller hash mismatch")
    controller_specification = load_robust_mpc_specification(controller_path)
    document = _environment_document(
        artifact,
        duration_h=int(trajectory["duration_h"]),
        notice_h=int(trajectory["notice_h"]),
        requested_reduction_kw=capacity_kw,
        event_id=int(trajectory["event_id"]),
    )
    env = HourlyCommunityAIDemandResponseEnv(document)
    controller = make_hourly_controller(
        "robust_mpc", robust_mpc_specification=controller_specification
    )
    frame, summary = rollout_hourly_episode(env, controller, seed=artifact.episode_seed)
    names = env.observation_feature_names
    observation_space = cast(Any, env.observation_space)
    lows = np.asarray(observation_space.low, dtype=float)
    highs = np.asarray(observation_space.high, dtype=float)
    if len(names) != 63 or lows.shape != (63,) or highs.shape != (63,):
        raise RuntimeError("firm_v5 observation contract is not 63-dimensional")
    group_specs = (
        ("Time encoding", 4),
        ("Current power and request", 6),
        ("Backlog, arrivals and slack", 9),
        ("Controlled deadline feasibility", 8),
        ("Excess deadline feasibility", 8),
        ("Event and recovery history", 10),
        ("Running peaks and previous action", 6),
        ("Community forecast", 6),
        ("Available-flexibility forecast", 6),
    )
    groups = [group for group, count in group_specs for _ in range(count)]
    observation = pd.DataFrame(
        {
            "feature_index": np.arange(63),
            "feature_name": names,
            "observation_group": groups,
            "lower_bound": lows,
            "upper_bound": highs,
        }
    )
    desired_columns = (
        "hour",
        "arrival_gpu_h",
        "executed_gpu_h",
        "action_fraction",
        "community_power_kw",
        "dc_power_kw",
        "pcc_power_kw",
        "baseline_pcc_power_kw",
        "pcc_limit_kw",
        "backlog_gpu_h",
        "compute_debt_kwh",
        "missed_gpu_h",
        "event_active",
        "recovery_active",
        "is_clearance_tail",
    )
    missing = sorted(set(desired_columns).difference(frame.columns))
    if missing:
        raise RuntimeError(f"representative rollout is missing columns: {', '.join(missing)}")
    trajectory_frame = frame.loc[:, list(desired_columns)].copy()
    event_rows = trajectory_frame.index[trajectory_frame["event_active"].astype(bool)]
    if len(event_rows) != int(trajectory["duration_h"]):
        raise RuntimeError("representative event duration mismatch")
    event_start = int(trajectory_frame.loc[event_rows, "hour"].min())
    event_stop = int(trajectory_frame.loc[event_rows, "hour"].max()) + 1
    metadata = {
        "scenario_id": artifact.scenario_id,
        "scenario_hash": artifact.scenario_hash,
        "episode_seed": artifact.episode_seed,
        "representative_rule": trajectory["representative_rule"],
        "event_id": int(trajectory["event_id"]),
        "event_start_hour": event_start,
        "event_stop_hour": event_stop,
        "duration_h": int(trajectory["duration_h"]),
        "notice_h": int(trajectory["notice_h"]),
        "candidate_reduction_kw": capacity_kw,
        "controller": "robust_mpc",
        "deadline_miss_gpu_h": float(summary["deadline_miss_gpu_h"]),
        "terminal_backlog_gpu_h": float(summary["unfinished_terminal_backlog_gpu_h"]),
        "minimum_interval_delivery_ratio": float(summary["minimum_interval_delivery_ratio"]),
        "max_event_rebound_ratio": float(summary["max_event_rebound_ratio"]),
    }
    sources = [
        _source_record(trajectory["selection"]),
        _source_record(controller_path),
        _source_record(artifact.directory / "metadata.json"),
        _source_record(artifact.directory / "environment_config.yaml"),
        _source_record(artifact.directory / "community.parquet"),
        _source_record(artifact.directory / "arrivals.parquet"),
        _source_record(artifact.directory / "baseline.parquet"),
        _source_record(_REPOSITORY_ROOT / "src/aidrbench/envs/community_ai_dr_env.py"),
        _source_record(_REPOSITORY_ROOT / "src/aidrbench/evaluation/hourly_rollout.py"),
    ]
    return observation, trajectory_frame, metadata, sources


def _plot_observation(
    observation: pd.DataFrame,
    *,
    output: Path,
    formats: Sequence[str],
    sources: Sequence[dict[str, object]],
    table_record: dict[str, object],
) -> dict[str, object]:
    _supplementary_publication_style()
    figure, (ax_a, ax_b) = plt.subplots(
        1,
        2,
        figsize=(_FIGURE_WIDTH_IN, 4.15),
        gridspec_kw={"width_ratios": (1.0, 1.55)},
    )
    counts = observation.groupby("observation_group", sort=False).size()
    colors = [
        _COLORS["neutral"],
        _COLORS["blue"],
        _COLORS["purple"],
        _COLORS["gold"],
        _COLORS["red"],
        _COLORS["flex"],
        _COLORS["navy"],
        _COLORS["pale_gold"],
        _COLORS["pale_teal"],
    ]
    labels = counts.index.tolist()
    display_labels = {
        "Time encoding": "Time\nencoding",
        "Current power and request": "Power and\nvisible request",
        "Backlog, arrivals and slack": "Queue, arrivals\nand slack",
        "Controlled deadline feasibility": "Controlled-service\nfeasibility",
        "Excess deadline feasibility": "Excess-service\nfeasibility",
        "Event and recovery history": "Event and\nrecovery history",
        "Running peaks and previous action": "Peaks and\nprevious action",
        "Community forecast": "Community\nforecast",
        "Available-flexibility forecast": "Flexibility\nforecast",
    }
    values = counts.to_numpy(dtype=float)
    positions = np.arange(len(counts), dtype=float)
    ax_a.barh(positions, values, color=colors, height=0.66)
    for position, value in zip(positions, values, strict=True):
        ax_a.text(value + 0.25, position, f"{int(value)}", ha="left", va="center", fontsize=6.4)
    ax_a.set_xlim(0, 11.5)
    ax_a.set_yticks(positions, [display_labels[label] for label in labels], fontsize=6.1)
    ax_a.invert_yaxis()
    ax_a.set_xlabel("Dimensions")
    ax_a.set_title("Fixed 63-dimensional policy interface", loc="left", fontweight="bold")
    _panel_label(ax_a, "a", x=-0.18, y=1.05)

    ax_b.set_axis_off()
    ax_b.set_xlim(-6.8, 9.0)
    ax_b.set_ylim(-0.5, 3.25)
    ax_b.axvspan(-6, 0, color=_COLORS["pale_gold"], alpha=0.55)
    ax_b.axvspan(0, 4, color=_COLORS["pale_red"], alpha=0.70)
    ax_b.axvspan(4, 8, color=_COLORS["light"], alpha=0.80)
    ax_b.hlines((2.35, 1.25, 0.25), -6.2, 8.2, color=_COLORS["grid"], linewidth=1.0)
    for x, label in ((-6, "notice"), (0, "event start"), (4, "event stop"), (8, "recovery")):
        ax_b.vlines(x, -0.05, 2.75, color=_COLORS["neutral"], linewidth=0.7, linestyle="--")
        ax_b.text(x, -0.20, label, ha="center", fontsize=6.3, color=_COLORS["neutral"])
    ax_b.text(-6.5, 2.35, "Policy observation", va="center", ha="right", fontsize=6.6, fontweight="bold")
    ax_b.text(-6.5, 1.25, "Causal forecast", va="center", ha="right", fontsize=6.6, fontweight="bold")
    ax_b.text(-6.5, 0.25, "Audit-only state", va="center", ha="right", fontsize=6.6, fontweight="bold")
    ax_b.text(-3.0, 2.35, "request visible only\nafter declared notice", ha="center", va="center", fontsize=6.4)
    ax_b.text(2.0, 2.35, "current arrivals, queues,\npower and event state", ha="center", va="center", fontsize=6.4)
    ax_b.text(-2.0, 1.25, "6-h community and\navailable-flexibility forecast", ha="center", va="center", fontsize=6.4)
    ax_b.text(4.8, 1.25, "future arrivals remain hidden;\nrobust MPC uses history + envelope", ha="center", va="center", fontsize=6.4)
    ax_b.text(1.0, 0.25, "class queues, compute debt,\nfull outcomes and provenance", ha="center", va="center", fontsize=6.4)
    ax_b.set_title("Information timing and masking", loc="left", fontweight="bold")
    _panel_label(ax_b, "b", x=-0.09, y=1.05)
    figure.subplots_adjust(left=0.12, right=0.98, bottom=0.12, top=0.90, wspace=0.24)
    return _finalize(
        figure,
        number=3,
        output_directory=output,
        formats=formats,
        source_records=sources,
        source_data=(table_record,),
        conclusion="The 63-dimensional firm_v5 observation exposes bounded causal information while retaining compute debt and full class state only for audit.",
        boundaries=(
            "Compute debt is an audit diagnostic and is not a separately named policy-observation feature.",
            "Future workload arrivals are not revealed to the causal controller.",
        ),
        archetype="schematic-led composite",
    )


def _plot_trajectory(
    trajectory: pd.DataFrame,
    metadata: Mapping[str, Any],
    *,
    output: Path,
    formats: Sequence[str],
    sources: Sequence[dict[str, object]],
    table_record: dict[str, object],
) -> dict[str, object]:
    _supplementary_publication_style()
    start = int(metadata["event_start_hour"])
    stop = int(metadata["event_stop_hour"])
    pre = 12
    post = 24
    window = trajectory[(trajectory["hour"] >= start - pre) & (trajectory["hour"] < stop + post)]
    relative_hour = window["hour"].to_numpy(dtype=float) - start
    figure, axes = plt.subplots(
        4,
        1,
        figsize=(_FIGURE_WIDTH_IN, 5.7),
        sharex=True,
        gridspec_kw={"height_ratios": (1.0, 0.72, 1.05, 1.0)},
    )
    for axis in axes:
        axis.axvspan(0, stop - start, color=_COLORS["pale_red"], alpha=0.75, linewidth=0)
        axis.axvline(0, color=_COLORS["red"], linewidth=0.7)
        axis.axvline(stop - start, color=_COLORS["red"], linewidth=0.7)
        axis.grid(axis="y", color=_COLORS["grid"], linewidth=0.5)

    axes[0].plot(relative_hour, window["arrival_gpu_h"], color=_COLORS["gold"], linewidth=1.4, label="Arrivals")
    axes[0].plot(relative_hour, window["executed_gpu_h"], color=_COLORS["blue"], linewidth=1.6, label="Executed")
    axes[0].set_ylabel("GPU-h")
    axes[0].legend(loc="upper right", ncol=2)
    axes[0].set_title("Released and executed flexible work", loc="left", fontweight="bold")
    _panel_label(axes[0], "a", x=-0.07, y=1.05)

    axes[1].step(relative_hour, window["action_fraction"], where="post", color=_COLORS["purple"], linewidth=1.7)
    axes[1].set_ylim(-0.05, 1.05)
    axes[1].set_ylabel("Action")
    axes[1].set_title("Robust-MPC execution fraction", loc="left", fontweight="bold")
    _panel_label(axes[1], "b", x=-0.07, y=1.05)

    axes[2].plot(relative_hour, window["baseline_pcc_power_kw"], color=_COLORS["neutral"], linewidth=1.3, label="No-DR baseline")
    axes[2].plot(relative_hour, window["pcc_power_kw"], color=_COLORS["blue"], linewidth=1.7, label="Controlled PCC")
    axes[2].plot(relative_hour, window["pcc_limit_kw"], color=_COLORS["red"], linewidth=1.0, linestyle="--", label="Event/PCC limit")
    axes[2].set_ylabel("Power (kW)")
    axes[2].legend(loc="upper right", ncol=3, columnspacing=0.8)
    axes[2].set_title("Baseline-relative power delivery", loc="left", fontweight="bold")
    _panel_label(axes[2], "c", x=-0.07, y=1.05)

    axes[3].plot(relative_hour, window["backlog_gpu_h"], color=_COLORS["purple"], linewidth=1.5, label="Backlog")
    debt_axis = axes[3].twinx()
    debt_axis.plot(relative_hour, window["compute_debt_kwh"], color=_COLORS["red"], linewidth=1.5, label="Compute debt")
    axes[3].set_ylabel("Backlog (GPU-h)")
    debt_axis.set_ylabel("Compute debt (kWh)", color=_COLORS["red"])
    debt_axis.tick_params(axis="y", colors=_COLORS["red"])
    axes[3].set_xlabel("Hour relative to event start")
    axes[3].set_title("Deferred service state", loc="left", fontweight="bold")
    axes[3].text(
        0.99,
        0.05,
        f"scenario {str(metadata['scenario_hash'])[:10]}… | seed {metadata['episode_seed']}\n"
        f"R={float(metadata['candidate_reduction_kw']):.2f} kW; H={metadata['duration_h']} h; N={metadata['notice_h']} h",
        transform=axes[3].transAxes,
        ha="right",
        va="bottom",
        fontsize=6.3,
        color=_COLORS["neutral"],
    )
    _panel_label(axes[3], "d", x=-0.07, y=1.05)
    figure.subplots_adjust(left=0.08, right=0.91, bottom=0.08, top=0.96, hspace=0.42)
    return _finalize(
        figure,
        number=4,
        output_directory=output,
        formats=formats,
        source_records=sources,
        source_data=(table_record,),
        conclusion="A fixed non-locked validation trajectory makes the hourly coupling among arrivals, causal action, PCC delivery, backlog and compute debt auditable.",
        boundaries=(
            "The minimum validation seed was selected by a fixed rule rather than by visual appearance.",
            "One trajectory illustrates state transition and does not estimate population performance.",
        ),
        archetype="quantitative grid",
    )


def plot_nature_supplementary_figures(
    specification_path: str | Path,
    output_directory: str | Path,
    *,
    figures: Sequence[int] = (1, 2, 3, 4),
    formats: Sequence[str] | None = None,
) -> dict[str, object]:
    """Generate the declared four Supplementary Figures and provenance bundle."""

    specification = _load_specification(specification_path)
    requested = tuple(int(value) for value in figures)
    if not requested or set(requested).difference({1, 2, 3, 4}):
        raise ValueError("supplementary figure numbers must be drawn from 1, 2, 3, 4")
    export = _mapping(specification["export"], "export")
    selected_formats = tuple(str(value) for value in (formats or export["formats"]))
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    if 1 in requested:
        records.append(_plot_environment_flow(specification, output, selected_formats))
    if 2 in requested:
        records.append(_plot_calibration(specification, output, selected_formats))
    if 3 in requested or 4 in requested:
        observation, trajectory, metadata, sources = _build_observation_and_trajectory(
            specification, output
        )
        observation_record = _write_csv(
            observation, output / "supplementary_figure_3_observation.csv"
        )
        trajectory_record = _write_csv(
            trajectory, output / "supplementary_figure_4_trajectory.csv"
        )
        metadata_path = output / "representative_trajectory_metadata.json"
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        sources_with_metadata = [*sources, _source_record(metadata_path)]
        if 3 in requested:
            records.append(
                _plot_observation(
                    observation,
                    output=output,
                    formats=selected_formats,
                    sources=sources,
                    table_record=observation_record,
                )
            )
        if 4 in requested:
            records.append(
                _plot_trajectory(
                    trajectory,
                    metadata,
                    output=output,
                    formats=selected_formats,
                    sources=sources_with_metadata,
                    table_record=trajectory_record,
                )
            )
    records.sort(key=lambda record: int(str(record["figure"]).removeprefix("S")))
    portable = []
    for record in records:
        raw_outputs = record["outputs"]
        if not isinstance(raw_outputs, list) or not all(
            isinstance(item, dict) for item in raw_outputs
        ):
            raise ValueError("invalid supplementary figure output records")
        portable.append(
            {
                "figure": record["figure"],
                "manifest": Path(str(record["manifest"])).name,
                "outputs": [
                    {**item, "path": Path(str(item["path"])).name}
                    for item in raw_outputs
                ],
            }
        )
    index = {
        "schema_version": _SCHEMA_VERSION,
        "specification": _source_record(specification_path),
        "locked_sets_used": False,
        "figure_count": len(portable),
        "figures": portable,
    }
    index_path = output / "supplementary_figure_manifest.json"
    index_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {**index, "manifest": str(index_path), "output_directory": str(output)}
