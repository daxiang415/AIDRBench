"""Cross-process heartbeat file used by an independent restore watchdog."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


class WatchdogError(RuntimeError):
    """Raised when a heartbeat cannot be validated safely."""


@dataclass(frozen=True, slots=True)
class Heartbeat:
    monotonic_seconds: float
    timestamp_utc: str
    status: str
    sequence: int


@dataclass(frozen=True, slots=True)
class WatchdogResult:
    reason: str
    restoration_called: bool
    last_sequence: int | None


def write_heartbeat(
    path: str | Path,
    *,
    sequence: int,
    status: str = "running",
    monotonic_seconds: float | None = None,
) -> Heartbeat:
    """Atomically publish a controller heartbeat for another process."""

    if sequence < 0:
        raise ValueError("heartbeat sequence must be non-negative")
    if status not in {"running", "stopped"}:
        raise ValueError("heartbeat status must be running or stopped")
    heartbeat = Heartbeat(
        monotonic_seconds=(time.monotonic() if monotonic_seconds is None else monotonic_seconds),
        timestamp_utc=datetime.now(UTC).isoformat(timespec="microseconds"),
        status=status,
        sequence=sequence,
    )
    heartbeat_path = Path(path)
    heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = heartbeat_path.with_suffix(heartbeat_path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(
            {
                "monotonic_seconds": heartbeat.monotonic_seconds,
                "timestamp_utc": heartbeat.timestamp_utc,
                "status": heartbeat.status,
                "sequence": heartbeat.sequence,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(heartbeat_path)
    return heartbeat


def read_heartbeat(path: str | Path) -> Heartbeat:
    """Read and validate a heartbeat written by :func:`write_heartbeat`."""

    heartbeat_path = Path(path)
    try:
        document = json.loads(heartbeat_path.read_text(encoding="utf-8"))
        monotonic_seconds = float(document["monotonic_seconds"])
        timestamp_utc = str(document["timestamp_utc"])
        status = str(document["status"])
        sequence = int(document["sequence"])
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise WatchdogError(f"invalid or missing heartbeat: {heartbeat_path}") from exc
    if monotonic_seconds < 0.0 or sequence < 0 or status not in {"running", "stopped"}:
        raise WatchdogError(f"invalid heartbeat values: {heartbeat_path}")
    return Heartbeat(monotonic_seconds, timestamp_utc, status, sequence)


def monitor_heartbeat(
    path: str | Path,
    *,
    timeout_seconds: float,
    poll_seconds: float,
    on_timeout: Callable[[], None],
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> WatchdogResult:
    """Block until clean stop or stale/missing heartbeat, then restore once."""

    if timeout_seconds <= 0.0 or poll_seconds <= 0.0:
        raise ValueError("watchdog timeout and poll intervals must be positive")
    started = clock()
    last_sequence: int | None = None
    while True:
        try:
            heartbeat = read_heartbeat(path)
        except WatchdogError:
            if clock() - started > timeout_seconds:
                on_timeout()
                return WatchdogResult("missing_heartbeat", True, last_sequence)
        else:
            last_sequence = heartbeat.sequence
            if heartbeat.status == "stopped":
                return WatchdogResult("clean_stop", False, last_sequence)
            if clock() - heartbeat.monotonic_seconds > timeout_seconds:
                on_timeout()
                return WatchdogResult("stale_heartbeat", True, last_sequence)
        sleeper(poll_seconds)
