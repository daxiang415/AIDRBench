"""AIPerf smoke-trace preparation without changing the source dataset."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

BURSTGPT_REQUIRED_COLUMNS = ("Timestamp", "Request tokens", "Response tokens")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_burstgpt_smoke_trace(
    source: str | Path,
    output: str | Path,
    *,
    requests: int = 10,
    time_scale: float = 20.0,
) -> dict[str, object]:
    """Copy the first valid requests and compress only their replay timestamps."""

    if isinstance(requests, bool) or not isinstance(requests, int) or requests <= 0:
        raise ValueError("requests must be a positive integer")
    if time_scale <= 0:
        raise ValueError("time_scale must be positive")
    source_path = Path(source)
    output_path = Path(output)
    if source_path.resolve() == output_path.resolve():
        raise ValueError("smoke trace output must differ from the source")

    selected: list[dict[str, str]] = []
    with source_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        if fieldnames is None:
            raise ValueError("BurstGPT source is missing a CSV header")
        missing = sorted(set(BURSTGPT_REQUIRED_COLUMNS) - set(fieldnames))
        if missing:
            raise ValueError(f"BurstGPT source is missing columns: {missing}")
        first_timestamp: float | None = None
        for raw_row in reader:
            try:
                timestamp = float(raw_row["Timestamp"])
                request_tokens = int(raw_row["Request tokens"])
                response_tokens = int(raw_row["Response tokens"])
            except (KeyError, TypeError, ValueError):
                continue
            if request_tokens <= 0 or response_tokens <= 0:
                continue
            if first_timestamp is None:
                first_timestamp = timestamp
            row = dict(raw_row)
            scaled_timestamp = (timestamp - first_timestamp) / time_scale
            row["Timestamp"] = f"{scaled_timestamp:.6f}".rstrip("0").rstrip(".")
            selected.append(row)
            if len(selected) == requests:
                break

    if len(selected) != requests:
        raise ValueError(
            f"BurstGPT source contains only {len(selected)} valid rows; requested {requests}"
        )
    replay_span_seconds = float(selected[-1]["Timestamp"])
    original_span_seconds = replay_span_seconds * time_scale

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected)
    return {
        "source": str(source_path),
        "output": str(output_path),
        "requests": len(selected),
        "time_scale": time_scale,
        "original_span_seconds": original_span_seconds,
        "replay_span_seconds": replay_span_seconds,
        "source_sha256": _sha256(source_path),
        "output_sha256": _sha256(output_path),
        "smoke_only": True,
    }
