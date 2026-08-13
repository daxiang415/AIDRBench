from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from aidrbench.telemetry import nvidia_smi
from aidrbench.telemetry.nvidia_smi import NvidiaSmiError, parse_nvidia_smi_csv

SAMPLE_OUTPUT = (
    "2026/08/11 18:00:00.123, 0, GPU-aaaa, NVIDIA RTX PRO 6000, "
    "91.5, 600.0, 44, 12, 51, 1800, 2000, 1024, P2\n"
    "2026/08/11 18:00:00.124, 1, GPU-bbbb, NVIDIA RTX PRO 6000, "
    "N/A, 600.0, 0, 0, 39, [N/A], 2000, 512, P8\n"
)


def test_parser_preserves_raw_timestamps_and_missing_values() -> None:
    records = parse_nvidia_smi_csv(
        SAMPLE_OUTPUT,
        host_timestamp_utc="2026-08-11T09:00:00+00:00",
        host_monotonic_s=123.5,
    )

    assert [record["gpu_index"] for record in records] == [0, 1]
    assert records[0]["power_draw_w"] == 91.5
    assert records[0]["host_monotonic_s"] == 123.5
    assert records[1]["power_draw_w"] is None
    assert records[1]["clocks_sm_mhz"] is None
    assert records[1]["device_timestamp"] == "2026/08/11 18:00:00.124"


def test_parser_rejects_schema_drift_and_empty_output() -> None:
    with pytest.raises(NvidiaSmiError, match="expected 13"):
        parse_nvidia_smi_csv(
            "2026/08/11 18:00:00, 0, too-few-fields",
            host_timestamp_utc="now",
            host_monotonic_s=1.0,
        )
    with pytest.raises(NvidiaSmiError, match="no GPU rows"):
        parse_nvidia_smi_csv("", host_timestamp_utc="now", host_monotonic_s=1.0)


def test_collector_writes_stable_parquet_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parsed = parse_nvidia_smi_csv(
        SAMPLE_OUTPUT,
        host_timestamp_utc="2026-08-11T09:00:00+00:00",
        host_monotonic_s=123.5,
    )

    def fake_sample(**kwargs: object) -> list[dict[str, object]]:
        assert kwargs["gpu_ids"] == (0, 1)
        return [dict(record) for record in parsed]

    monkeypatch.setattr(nvidia_smi, "sample_nvidia_smi", fake_sample)
    output = tmp_path / "gpu_telemetry.parquet"
    summary = nvidia_smi.collect_nvidia_smi_telemetry(
        output,
        duration_seconds=0.001,
        gpu_ids=[0, 1],
    )
    frame = pd.read_parquet(output)

    assert tuple(frame.columns) == nvidia_smi.TELEMETRY_COLUMNS
    assert summary["samples"] == 1
    assert summary["rows"] == 2
    assert summary["gpu_indices"] == [0, 1]
    assert bool(summary["read_only"])


def test_collector_rejects_invalid_targets_before_sampling(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=".parquet"):
        nvidia_smi.collect_nvidia_smi_telemetry(
            tmp_path / "telemetry.csv", duration_seconds=1.0
        )
    with pytest.raises(ValueError, match="duplicate GPU ID"):
        nvidia_smi.collect_nvidia_smi_telemetry(
            tmp_path / "telemetry.parquet", duration_seconds=1.0, gpu_ids=[0, 0]
        )
