"""Compare paired tensor-parallel runs using AIPerf and GPU telemetry."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

_METRICS = (
    "request_count",
    "request_throughput",
    "effective_concurrency",
    "output_token_throughput",
    "output_token_throughput_per_user",
    "active_decode_throughput",
    "time_to_first_token",
    "inter_token_latency",
    "request_latency",
    "total_usage_completion_tokens",
)

_TELEMETRY_COLUMNS = {
    "sample_index",
    "device_timestamp",
    "gpu_index",
    "power_draw_w",
    "power_limit_w",
    "utilization_gpu_pct",
    "temperature_gpu_c",
}


def _load_json_mapping(path: str | Path) -> dict[str, Any]:
    input_path = Path(path)
    loaded: object = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"AIPerf summary must be a JSON object: {input_path}")
    return loaded


def _finite_number(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def _metric_average(summary: Mapping[str, Any], key: str) -> float:
    raw = summary.get(key)
    if not isinstance(raw, Mapping):
        raise ValueError(f"AIPerf metric {key!r} is missing or malformed")
    return _finite_number(raw.get("avg"), field=f"{key}.avg")


def _positive_ratio(numerator: float, denominator: float, *, field: str) -> float:
    if denominator <= 0:
        raise ValueError(f"{field} denominator must be positive")
    return numerator / denominator


def _validate_gpu_ids(gpu_ids: Sequence[int]) -> tuple[int, ...]:
    result: list[int] = []
    for gpu_id in gpu_ids:
        if isinstance(gpu_id, bool) or not isinstance(gpu_id, int) or gpu_id < 0:
            raise ValueError("GPU IDs must be non-negative integers")
        if gpu_id in result:
            raise ValueError(f"duplicate GPU ID: {gpu_id}")
        result.append(gpu_id)
    if not result:
        raise ValueError("at least one GPU ID is required")
    return tuple(result)


def _telemetry_window(
    path: str | Path,
    *,
    start_time: str,
    end_time: str,
    gpu_ids: Sequence[int],
    duration_seconds: float,
    completion_tokens: float,
) -> dict[str, object]:
    selected_ids = _validate_gpu_ids(gpu_ids)
    frame = pd.read_parquet(path)
    missing = sorted(_TELEMETRY_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"telemetry is missing columns: {missing}")

    timestamps = pd.to_datetime(frame["device_timestamp"], errors="coerce")
    if bool(timestamps.isna().any()):
        raise ValueError("telemetry contains invalid device_timestamp values")
    start = pd.Timestamp(start_time)
    end = pd.Timestamp(end_time)
    if start.tzinfo is not None or end.tzinfo is not None:
        raise ValueError("AIPerf timestamps must be local-naive to match nvidia-smi timestamps")
    if end <= start:
        raise ValueError("AIPerf end_time must be later than start_time")

    selected = frame.loc[
        timestamps.between(start, end, inclusive="both")
        & frame["gpu_index"].isin(selected_ids)
    ].copy()
    if selected.empty:
        raise ValueError("no telemetry samples overlap the AIPerf benchmark window")
    returned_ids = {int(value) for value in selected["gpu_index"].unique()}
    absent = sorted(set(selected_ids) - returned_ids)
    if absent:
        raise ValueError(f"telemetry has no benchmark-window samples for GPU IDs: {absent}")

    per_gpu: list[dict[str, object]] = []
    for gpu_id in selected_ids:
        rows = selected.loc[selected["gpu_index"] == gpu_id]
        per_gpu.append(
            {
                "gpu_index": gpu_id,
                "samples": int(len(rows)),
                "mean_power_w": float(rows["power_draw_w"].mean()),
                "peak_power_w": float(rows["power_draw_w"].max()),
                "power_limit_w": float(rows["power_limit_w"].median()),
                "mean_utilization_pct": float(rows["utilization_gpu_pct"].mean()),
                "peak_utilization_pct": float(rows["utilization_gpu_pct"].max()),
                "mean_temperature_c": float(rows["temperature_gpu_c"].mean()),
                "peak_temperature_c": float(rows["temperature_gpu_c"].max()),
            }
        )

    sample_power = selected.groupby("sample_index", sort=True)["power_draw_w"].sum()
    mean_total_power_w = float(sample_power.mean())
    estimated_energy_j = mean_total_power_w * duration_seconds
    return {
        "window_start": start_time,
        "window_end": end_time,
        "selected_gpu_ids": list(selected_ids),
        "samples": int(selected["sample_index"].nunique()),
        "mean_total_power_w": mean_total_power_w,
        "peak_total_power_w": float(sample_power.max()),
        "estimated_energy_j": estimated_energy_j,
        "estimated_energy_per_completion_token_j": (
            estimated_energy_j / completion_tokens if completion_tokens > 0 else None
        ),
        "per_gpu": per_gpu,
    }


def _run_summary(
    aiperf_path: str | Path,
    telemetry_path: str | Path,
    *,
    gpu_ids: Sequence[int],
) -> dict[str, object]:
    summary = _load_json_mapping(aiperf_path)
    start_time = summary.get("start_time")
    end_time = summary.get("end_time")
    if not isinstance(start_time, str) or not isinstance(end_time, str):
        raise ValueError("AIPerf summary must contain string start_time and end_time")
    metrics = {key: _metric_average(summary, key) for key in _METRICS}
    duration_seconds = _metric_average(summary, "benchmark_duration")
    telemetry = _telemetry_window(
        telemetry_path,
        start_time=start_time,
        end_time=end_time,
        gpu_ids=gpu_ids,
        duration_seconds=duration_seconds,
        completion_tokens=metrics["total_usage_completion_tokens"],
    )
    error_summary = summary.get("error_summary")
    error_count = len(error_summary) if isinstance(error_summary, list) else None
    return {
        "aiperf_path": str(aiperf_path),
        "telemetry_path": str(telemetry_path),
        "gpu_ids": list(_validate_gpu_ids(gpu_ids)),
        "gpu_count": len(gpu_ids),
        "benchmark_duration_seconds": duration_seconds,
        "error_count": error_count,
        "metrics": metrics,
        "telemetry": telemetry,
    }


def compare_topology_runs(
    baseline_aiperf: str | Path,
    baseline_telemetry: str | Path,
    candidate_aiperf: str | Path,
    candidate_telemetry: str | Path,
    *,
    baseline_gpu_ids: Sequence[int],
    candidate_gpu_ids: Sequence[int],
    topology_class: str = "unknown",
    transport: str = "unknown",
) -> dict[str, object]:
    """Compare a baseline run with a larger tensor-parallel candidate run."""

    baseline = _run_summary(
        baseline_aiperf,
        baseline_telemetry,
        gpu_ids=baseline_gpu_ids,
    )
    candidate = _run_summary(
        candidate_aiperf,
        candidate_telemetry,
        gpu_ids=candidate_gpu_ids,
    )
    baseline_metrics = baseline["metrics"]
    candidate_metrics = candidate["metrics"]
    baseline_power = baseline["telemetry"]
    candidate_power = candidate["telemetry"]
    if not isinstance(baseline_metrics, dict) or not isinstance(candidate_metrics, dict):
        raise TypeError("internal metric summaries must be mappings")
    if not isinstance(baseline_power, dict) or not isinstance(candidate_power, dict):
        raise TypeError("internal telemetry summaries must be mappings")

    candidate_gpu_count = _finite_number(candidate["gpu_count"], field="candidate gpu_count")
    baseline_gpu_count = _finite_number(baseline["gpu_count"], field="baseline gpu_count")
    gpu_count_ratio = _positive_ratio(
        candidate_gpu_count,
        baseline_gpu_count,
        field="GPU count ratio",
    )
    aggregate_speedup = _positive_ratio(
        float(candidate_metrics["output_token_throughput"]),
        float(baseline_metrics["output_token_throughput"]),
        field="aggregate output throughput ratio",
    )
    service_speedup = _positive_ratio(
        float(candidate_metrics["output_token_throughput_per_user"]),
        float(baseline_metrics["output_token_throughput_per_user"]),
        field="per-user output throughput ratio",
    )
    active_decode_speedup = _positive_ratio(
        float(candidate_metrics["active_decode_throughput"]),
        float(baseline_metrics["active_decode_throughput"]),
        field="active decode throughput ratio",
    )
    power_ratio = _positive_ratio(
        float(candidate_power["mean_total_power_w"]),
        float(baseline_power["mean_total_power_w"]),
        field="mean power ratio",
    )
    baseline_energy_per_token = float(
        baseline_power["estimated_energy_per_completion_token_j"]
    )
    candidate_energy_per_token = float(
        candidate_power["estimated_energy_per_completion_token_j"]
    )

    effective_concurrency = max(
        float(baseline_metrics["effective_concurrency"]),
        float(candidate_metrics["effective_concurrency"]),
    )
    arrival_limited = (
        0.95 <= aggregate_speedup <= 1.05
        and effective_concurrency < candidate_gpu_count
    )
    request_count = min(
        float(baseline_metrics["request_count"]),
        float(candidate_metrics["request_count"]),
    )
    warnings: list[str] = []
    if arrival_limited:
        warnings.append(
            "fixed arrival schedule did not saturate the baseline; aggregate throughput is "
            "demand-limited, so use service-speed and latency ratios for this comparison"
        )
    if request_count < 30:
        warnings.append("fewer than 30 paired requests; treat this as a smoke baseline")

    return {
        "schema_version": 1,
        "comparison": "paired_tensor_parallel_topology",
        "topology": {"class": topology_class, "transport": transport},
        "baseline": baseline,
        "candidate": candidate,
        "derived": {
            "gpu_count_ratio": gpu_count_ratio,
            "aggregate_output_throughput_speedup": aggregate_speedup,
            "service_speedup_per_user": service_speedup,
            "active_decode_speedup": active_decode_speedup,
            "per_gpu_service_scaling_efficiency": service_speedup / gpu_count_ratio,
            "observed_nonideal_scaling_fraction": 1.0 - service_speedup / gpu_count_ratio,
            "request_latency_improvement_pct": 100.0
            * (
                1.0
                - float(candidate_metrics["request_latency"])
                / float(baseline_metrics["request_latency"])
            ),
            "inter_token_latency_improvement_pct": 100.0
            * (
                1.0
                - float(candidate_metrics["inter_token_latency"])
                / float(baseline_metrics["inter_token_latency"])
            ),
            "ttft_improvement_pct": 100.0
            * (
                1.0
                - float(candidate_metrics["time_to_first_token"])
                / float(baseline_metrics["time_to_first_token"])
            ),
            "mean_power_ratio": power_ratio,
            "service_throughput_per_watt_ratio": service_speedup / power_ratio,
            "energy_efficiency_ratio": baseline_energy_per_token / candidate_energy_per_token,
            "arrival_limited": arrival_limited,
        },
        "warnings": warnings,
    }


def write_topology_comparison(comparison: Mapping[str, object], output: str | Path) -> None:
    """Write one topology comparison as deterministic, human-readable JSON."""

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
