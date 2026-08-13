from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from aidrbench.calibration.topology_compare import (
    compare_topology_runs,
    write_topology_comparison,
)


def _write_aiperf(path: Path, *, speed: float, latency_ms: float) -> None:
    metric_values = {
        "benchmark_duration": 2.0,
        "request_count": 10.0,
        "request_throughput": 5.0,
        "effective_concurrency": 0.5,
        "output_token_throughput": 100.0,
        "output_token_throughput_per_user": speed,
        "active_decode_throughput": speed,
        "time_to_first_token": 20.0,
        "inter_token_latency": latency_ms,
        "request_latency": latency_ms * 100.0,
        "total_usage_completion_tokens": 200.0,
    }
    payload: dict[str, object] = {
        "start_time": "2026-01-01T12:00:00",
        "end_time": "2026-01-01T12:00:02",
        "error_summary": [],
    }
    payload.update({key: {"avg": value, "unit": "test"} for key, value in metric_values.items()})
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_telemetry(path: Path, gpu_ids: list[int], power_w: float) -> None:
    rows: list[dict[str, object]] = []
    for sample_index, timestamp in enumerate(
        ["2026/01/01 12:00:00.000", "2026/01/01 12:00:01.000", "2026/01/01 12:00:02.000"]
    ):
        for gpu_id in gpu_ids:
            rows.append(
                {
                    "sample_index": sample_index,
                    "device_timestamp": timestamp,
                    "gpu_index": gpu_id,
                    "power_draw_w": power_w,
                    "power_limit_w": 300.0,
                    "utilization_gpu_pct": 50.0,
                    "temperature_gpu_c": 55.0,
                }
            )
    pd.DataFrame(rows).to_parquet(path, index=False)


def test_compare_topology_runs_marks_arrival_limited_smoke(tmp_path: Path) -> None:
    baseline_json = tmp_path / "baseline.json"
    candidate_json = tmp_path / "candidate.json"
    baseline_telemetry = tmp_path / "baseline.parquet"
    candidate_telemetry = tmp_path / "candidate.parquet"
    _write_aiperf(baseline_json, speed=500.0, latency_ms=2.0)
    _write_aiperf(candidate_json, speed=600.0, latency_ms=1.5)
    _write_telemetry(baseline_telemetry, [0], 100.0)
    _write_telemetry(candidate_telemetry, [0, 1], 80.0)

    result = compare_topology_runs(
        baseline_json,
        baseline_telemetry,
        candidate_json,
        candidate_telemetry,
        baseline_gpu_ids=[0],
        candidate_gpu_ids=[0, 1],
        topology_class="NODE",
        transport="NCCL",
    )

    derived = result["derived"]
    assert isinstance(derived, dict)
    assert derived["arrival_limited"] is True
    assert derived["service_speedup_per_user"] == pytest.approx(1.2)
    assert derived["per_gpu_service_scaling_efficiency"] == pytest.approx(0.6)
    assert derived["inter_token_latency_improvement_pct"] == pytest.approx(25.0)
    assert derived["mean_power_ratio"] == pytest.approx(1.6)
    assert result["warnings"]

    output = tmp_path / "comparison.json"
    write_topology_comparison(result, output)
    assert json.loads(output.read_text(encoding="utf-8"))["topology"]["class"] == "NODE"


def test_compare_topology_runs_rejects_missing_gpu_samples(tmp_path: Path) -> None:
    baseline_json = tmp_path / "baseline.json"
    candidate_json = tmp_path / "candidate.json"
    baseline_telemetry = tmp_path / "baseline.parquet"
    candidate_telemetry = tmp_path / "candidate.parquet"
    _write_aiperf(baseline_json, speed=500.0, latency_ms=2.0)
    _write_aiperf(candidate_json, speed=600.0, latency_ms=1.5)
    _write_telemetry(baseline_telemetry, [0], 100.0)
    _write_telemetry(candidate_telemetry, [0], 80.0)

    with pytest.raises(ValueError, match="GPU IDs"):
        compare_topology_runs(
            baseline_json,
            baseline_telemetry,
            candidate_json,
            candidate_telemetry,
            baseline_gpu_ids=[0],
            candidate_gpu_ids=[0, 1],
        )
