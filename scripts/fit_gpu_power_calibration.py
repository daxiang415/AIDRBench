#!/usr/bin/env python3
"""Fit the hourly power artifact from bounded GPU calibration runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from scipy import stats

from aidrbench.calibration.artifact import (
    HARDWARE_CALIBRATION_SCHEMA_VERSION,
    calibration_artifact_sha256,
)

_RUN_PATTERN = re.compile(
    r"^(training|offline_inference)_(1|4)gpu_repeat([1-9][0-9]*)_workload\.json$"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _positive(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0.0:
        raise argparse.ArgumentTypeError("value must be finite and positive")
    return parsed


def _confidence_interval(values: np.ndarray, confidence: float = 0.95) -> tuple[float, float]:
    """Student-t confidence interval over independent run means."""

    cleaned = values[np.isfinite(values)]
    if len(cleaned) < 2:
        raise ValueError("at least two finite observations are required for an interval")
    mean = float(cleaned.mean())
    standard_deviation = float(cleaned.std(ddof=1))
    multiplier = float(stats.t.ppf((1.0 + confidence) / 2.0, len(cleaned) - 1))
    radius = multiplier * standard_deviation / math.sqrt(len(cleaned))
    return max(mean - radius, 1e-3), mean + radius


def _measurement_rows(raw_directory: Path) -> tuple[pd.DataFrame, dict[str, str]]:
    rows: list[dict[str, object]] = []
    hashes: dict[str, str] = {}
    for workload_path in sorted(raw_directory.glob("*_workload.json")):
        match = _RUN_PATTERN.match(workload_path.name)
        if match is None:
            continue
        mode, gpu_count_text, repeat_text = match.groups()
        telemetry_path = workload_path.with_name(
            workload_path.name.replace("_workload.json", "_telemetry.parquet")
        )
        if not telemetry_path.is_file():
            raise FileNotFoundError(f"missing paired telemetry: {telemetry_path}")
        workload = json.loads(workload_path.read_text(encoding="utf-8"))
        ranks = workload.get("ranks")
        if not isinstance(ranks, list) or not ranks:
            raise ValueError(f"workload metadata has no ranks: {workload_path}")
        start = pd.to_datetime(
            min(str(rank["started_at_utc"]) for rank in ranks), utc=True
        ) + pd.Timedelta(1, unit="s")
        stop = pd.to_datetime(
            max(str(rank["ended_at_utc"]) for rank in ranks), utc=True
        ) - pd.Timedelta(1, unit="s")
        telemetry = pd.read_parquet(telemetry_path)
        timestamps = pd.to_datetime(telemetry["host_timestamp_utc"], utc=True)
        window = telemetry.loc[(timestamps >= start) & (timestamps <= stop)].copy()
        physical_gpu_ids = {int(value) for value in workload["physical_gpu_ids"]}
        active = window.loc[window["gpu_index"].isin(physical_gpu_ids)]
        if active.empty or set(int(value) for value in active["gpu_index"].unique()) != (
            physical_gpu_ids
        ):
            raise ValueError(f"incomplete active-GPU telemetry: {telemetry_path}")
        for gpu_index, group in active.groupby("gpu_index", sort=True):
            rows.append(
                {
                    "mode": mode,
                    "gpu_count": int(gpu_count_text),
                    "repeat": int(repeat_text),
                    "gpu_index": int(gpu_index),
                    "sample_count": len(group),
                    "mean_power_w": float(group["power_draw_w"].mean()),
                    "std_power_w": float(group["power_draw_w"].std()),
                    "mean_utilization_pct": float(group["utilization_gpu_pct"].mean()),
                    "mean_temperature_c": float(group["temperature_gpu_c"].mean()),
                    "mean_sm_clock_mhz": float(group["clocks_sm_mhz"].mean()),
                }
            )
        hashes[str(workload_path)] = _sha256(workload_path)
        hashes[str(telemetry_path)] = _sha256(telemetry_path)
    frame = pd.DataFrame.from_records(rows)
    expected = {
        (mode, gpu_count, repeat)
        for mode in ("training", "offline_inference")
        for gpu_count in (1, 4)
        for repeat in (1, 2, 3)
    }
    observed = set(zip(frame["mode"], frame["gpu_count"], frame["repeat"], strict=False))
    if observed != expected:
        raise ValueError(f"calibration matrix mismatch; missing={sorted(expected - observed)}")
    return frame, hashes


def _idle_parameter(raw_directory: Path) -> tuple[float, tuple[float, float], float, str]:
    idle_path = raw_directory / "idle_baseline.parquet"
    idle = pd.read_parquet(idle_path)
    calibration = idle.loc[idle["sample_index"] < 20]
    held_out = idle.loc[idle["sample_index"] >= 20]
    gpu_means = calibration.groupby("gpu_index")["power_draw_w"].mean().to_numpy()
    estimate = float(gpu_means.mean())
    # This file contains one node-level idle run. GPUs characterize device
    # heterogeneity within that run; they are not independent experimental
    # repeats and therefore do not support a confidence interval.
    interval = (float(gpu_means.min()), float(gpu_means.max()))
    held_out_means = held_out.groupby("gpu_index")["power_draw_w"].mean().to_numpy()
    held_out_mae = float(np.abs(held_out_means - estimate).mean())
    return estimate, interval, held_out_mae, _sha256(idle_path)


def fit(args: argparse.Namespace) -> None:
    raw_directory = Path(args.raw_directory)
    output_path = Path(args.output)
    summary_directory = output_path.parent / "rtx6000pro_4gpu_v1_fit"
    summary_directory.mkdir(parents=True, exist_ok=True)
    rows, raw_hashes = _measurement_rows(raw_directory)
    rows.to_parquet(summary_directory / "run_gpu_means.parquet", index=False)

    idle_estimate, idle_interval, idle_mae, idle_hash = _idle_parameter(raw_directory)
    raw_hashes[str(raw_directory / "idle_baseline.parquet")] = idle_hash
    active_parameters: dict[str, dict[str, object]] = {}
    held_out_errors: list[float] = []
    class_diagnostics: dict[str, object] = {}
    for job_class in ("training", "offline_inference"):
        class_rows = rows.loc[(rows["mode"] == job_class) & (rows["gpu_count"] == 4)]
        run_means = class_rows.groupby("repeat", sort=True)["mean_power_w"].mean()
        calibration_values = run_means.loc[[1, 2]].to_numpy(dtype="float64")
        held_out_values = run_means.loc[[3]].to_numpy(dtype="float64")
        estimate = float(calibration_values.mean())
        interval = _confidence_interval(calibration_values)
        errors = np.abs(held_out_values - estimate)
        held_out_errors.extend(float(value) for value in errors)
        active_parameters[job_class] = {
            "estimate_w": estimate,
            "uncertainty_interval_w": [float(interval[0]), float(interval[1])],
            "uncertainty_method": "student_t_95_confidence_interval_over_run_means",
            "statistical_unit": "independent_four_gpu_workload_run_mean",
            "independent_unit_count": len(calibration_values),
            "confidence_level": 0.95,
        }
        class_diagnostics[job_class] = {
            "calibration_independent_runs": len(calibration_values),
            "held_out_independent_runs": len(held_out_values),
            "gpus_observed_per_run": 4,
            "held_out_mae_w": float(errors.mean()),
            "single_gpu_mean_w": float(
                rows.loc[
                    (rows["mode"] == job_class) & (rows["gpu_count"] == 1),
                    "mean_power_w",
                ].mean()
            ),
            "four_gpu_calibration_mean_w": estimate,
        }

    held_out_mae = float(np.mean(held_out_errors))
    artifact: dict[str, Any] = {
        "schema_version": HARDWARE_CALIBRATION_SCHEMA_VERSION,
        "artifact_id": "rtx6000pro_4gpu_v1",
        "hardware": {
            "identifier": "NVIDIA RTX PRO 6000 Blackwell Max-Q Workstation Edition",
            "topology_identifier": "4x_gpu_pcie_node_no_nvlink",
        },
        "measurement": {
            "method": (
                "1 s nvidia-smi GPU board-power telemetry; BF16 8192x8192 training "
                "with NCCL all-reduce and batched offline inference; repeats 1-2 fit, "
                "repeat 3 held out; published host/GPU identifiers are redacted; node "
                "overhead is an explicit non-measured assumption"
            ),
            "raw_input_sha256": dict(sorted(raw_hashes.items())),
            "fit_summary": str(summary_directory / "fit_summary.json"),
        },
        "parameters": {
            "idle_power_w_per_gpu": {
                "estimate_w": idle_estimate,
                "uncertainty_interval_w": [idle_interval[0], idle_interval[1]],
                "uncertainty_method": "between_gpu_range_within_single_idle_run",
                "statistical_unit": "single_node_idle_run",
                "independent_unit_count": 1,
            },
            "node_fixed_overhead_w": {
                "estimate_w": args.node_fixed_overhead_w,
                "uncertainty_interval_w": [
                    args.node_fixed_overhead_lower_w,
                    args.node_fixed_overhead_upper_w,
                ],
                "uncertainty_method": "engineering_assumption_range_no_node_meter",
                "statistical_unit": "engineering_assumption",
                "independent_unit_count": 0,
            },
            "active_power_w_per_gpu_by_class": active_parameters,
        },
        "validation": {"held_out_power_mae_w": held_out_mae},
        "evidence_class": "benchmark_anchored_synthetic",
    }
    artifact["artifact_sha256"] = calibration_artifact_sha256(artifact)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(artifact, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    fit_summary = {
        "artifact": str(output_path),
        "artifact_sha256": artifact["artifact_sha256"],
        "evidence_class": artifact["evidence_class"],
        "idle_held_out_mae_w": idle_mae,
        "active_held_out_mae_w": held_out_mae,
        "node_fixed_overhead_source": "explicit assumption; no BMC/PDU/RAPL access",
        "class_diagnostics": class_diagnostics,
    }
    (summary_directory / "fit_summary.json").write_text(
        json.dumps(fit_summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(fit_summary, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-directory", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--node-fixed-overhead-w", type=_positive, required=True)
    parser.add_argument("--node-fixed-overhead-lower-w", type=_positive, required=True)
    parser.add_argument("--node-fixed-overhead-upper-w", type=_positive, required=True)
    return parser


if __name__ == "__main__":
    fit(build_parser().parse_args())
