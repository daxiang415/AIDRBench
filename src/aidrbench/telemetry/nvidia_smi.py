"""Read-only, one-second-capable ``nvidia-smi`` telemetry collection."""

from __future__ import annotations

import csv
import math
import subprocess
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

QUERY_FIELDS = (
    "timestamp",
    "index",
    "uuid",
    "name",
    "power.draw",
    "power.limit",
    "utilization.gpu",
    "utilization.memory",
    "temperature.gpu",
    "clocks.sm",
    "clocks.mem",
    "memory.used",
    "pstate",
)

TELEMETRY_COLUMNS = (
    "sample_index",
    "host_timestamp_utc",
    "host_monotonic_s",
    "device_timestamp",
    "gpu_index",
    "gpu_uuid",
    "gpu_name",
    "power_draw_w",
    "power_limit_w",
    "utilization_gpu_pct",
    "utilization_memory_pct",
    "temperature_gpu_c",
    "clocks_sm_mhz",
    "clocks_memory_mhz",
    "memory_used_mib",
    "pstate",
)

_MISSING_VALUES = {"", "n/a", "[n/a]", "not supported", "[not supported]"}


class NvidiaSmiError(RuntimeError):
    """Raised when read-only GPU telemetry cannot be collected reliably."""


def _optional_float(value: str, field: str) -> float | None:
    normalized = value.strip()
    if normalized.lower() in _MISSING_VALUES:
        return None
    try:
        return float(normalized)
    except ValueError as exc:
        raise NvidiaSmiError(f"invalid numeric value for {field}: {value!r}") from exc


def _required_int(value: str, field: str) -> int:
    parsed = _optional_float(value, field)
    if parsed is None or not parsed.is_integer():
        raise NvidiaSmiError(f"{field} must be an integer, got: {value!r}")
    return int(parsed)


def parse_nvidia_smi_csv(
    output: str,
    *,
    host_timestamp_utc: str,
    host_monotonic_s: float,
) -> list[dict[str, object]]:
    """Parse headerless, nounits output produced by :func:`sample_nvidia_smi`."""

    records: list[dict[str, object]] = []
    for row_number, row in enumerate(csv.reader(output.splitlines()), start=1):
        if not row or all(not value.strip() for value in row):
            continue
        if len(row) != len(QUERY_FIELDS):
            raise NvidiaSmiError(
                f"nvidia-smi row {row_number} has {len(row)} fields; "
                f"expected {len(QUERY_FIELDS)}"
            )
        values = dict(zip(QUERY_FIELDS, (value.strip() for value in row), strict=True))
        records.append(
            {
                "sample_index": 0,
                "host_timestamp_utc": host_timestamp_utc,
                "host_monotonic_s": host_monotonic_s,
                "device_timestamp": values["timestamp"],
                "gpu_index": _required_int(values["index"], "index"),
                "gpu_uuid": values["uuid"],
                "gpu_name": values["name"],
                "power_draw_w": _optional_float(values["power.draw"], "power.draw"),
                "power_limit_w": _optional_float(values["power.limit"], "power.limit"),
                "utilization_gpu_pct": _optional_float(
                    values["utilization.gpu"], "utilization.gpu"
                ),
                "utilization_memory_pct": _optional_float(
                    values["utilization.memory"], "utilization.memory"
                ),
                "temperature_gpu_c": _optional_float(
                    values["temperature.gpu"], "temperature.gpu"
                ),
                "clocks_sm_mhz": _optional_float(values["clocks.sm"], "clocks.sm"),
                "clocks_memory_mhz": _optional_float(values["clocks.mem"], "clocks.mem"),
                "memory_used_mib": _optional_float(values["memory.used"], "memory.used"),
                "pstate": values["pstate"],
            }
        )
    if not records:
        raise NvidiaSmiError("nvidia-smi returned no GPU rows")
    return records


def _validate_gpu_ids(gpu_ids: Sequence[int] | None) -> tuple[int, ...] | None:
    if gpu_ids is None:
        return None
    validated: list[int] = []
    for gpu_id in gpu_ids:
        if isinstance(gpu_id, bool) or not isinstance(gpu_id, int) or gpu_id < 0:
            raise ValueError("GPU IDs must be non-negative integers")
        if gpu_id in validated:
            raise ValueError(f"duplicate GPU ID: {gpu_id}")
        validated.append(gpu_id)
    if not validated:
        raise ValueError("GPU ID selection must not be empty")
    return tuple(validated)


def sample_nvidia_smi(
    *,
    gpu_ids: Sequence[int] | None = None,
    executable: str = "nvidia-smi",
    timeout_seconds: float = 5.0,
) -> list[dict[str, object]]:
    """Take one read-only sample without invoking a shell or changing GPU state."""

    selected_ids = _validate_gpu_ids(gpu_ids)
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    command = [
        executable,
        f"--query-gpu={','.join(QUERY_FIELDS)}",
        "--format=csv,noheader,nounits",
    ]
    if selected_ids is not None:
        command.append(f"--id={','.join(str(gpu_id) for gpu_id in selected_ids)}")

    host_timestamp = datetime.now(UTC).isoformat(timespec="microseconds")
    host_monotonic = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise NvidiaSmiError(f"nvidia-smi executable not found: {executable}") from exc
    except subprocess.TimeoutExpired as exc:
        raise NvidiaSmiError(f"nvidia-smi timed out after {timeout_seconds:g} seconds") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "no diagnostic output"
        raise NvidiaSmiError(f"nvidia-smi failed with exit code {completed.returncode}: {detail}")

    records = parse_nvidia_smi_csv(
        completed.stdout,
        host_timestamp_utc=host_timestamp,
        host_monotonic_s=host_monotonic,
    )
    if selected_ids is not None:
        returned_ids: set[int] = set()
        for record in records:
            gpu_index = record["gpu_index"]
            if not isinstance(gpu_index, int):
                raise NvidiaSmiError("parsed GPU index is not an integer")
            returned_ids.add(gpu_index)
        missing = sorted(set(selected_ids) - returned_ids)
        unexpected = sorted(returned_ids - set(selected_ids))
        if missing or unexpected:
            raise NvidiaSmiError(
                f"GPU selection mismatch; missing={missing}, unexpected={unexpected}"
            )
    return records


def collect_nvidia_smi_telemetry(
    output: str | Path,
    *,
    duration_seconds: float,
    interval_seconds: float = 1.0,
    gpu_ids: Sequence[int] | None = None,
    executable: str = "nvidia-smi",
) -> dict[str, object]:
    """Collect fixed-cadence samples and write the raw records to Parquet."""

    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive")
    selected_ids = _validate_gpu_ids(gpu_ids)
    output_path = Path(output)
    if output_path.suffix.lower() != ".parquet":
        raise ValueError("telemetry output must use the .parquet extension")

    sample_count = max(1, math.ceil(duration_seconds / interval_seconds))
    started = time.monotonic()
    records: list[dict[str, object]] = []
    for sample_index in range(sample_count):
        target_time = started + sample_index * interval_seconds
        delay = target_time - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        sample = sample_nvidia_smi(gpu_ids=selected_ids, executable=executable)
        for record in sample:
            record["sample_index"] = sample_index
            records.append(record)

    frame = pd.DataFrame.from_records(records, columns=TELEMETRY_COLUMNS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output_path, index=False)
    return {
        "output": str(output_path),
        "rows": len(frame),
        "samples": sample_count,
        "gpu_indices": sorted(int(value) for value in frame["gpu_index"].unique()),
        "duration_seconds": duration_seconds,
        "interval_seconds": interval_seconds,
        "backend": "nvidia-smi",
        "read_only": True,
    }
