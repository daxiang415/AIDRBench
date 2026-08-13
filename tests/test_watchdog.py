from __future__ import annotations

from pathlib import Path

from aidrbench.hil.watchdog import monitor_heartbeat, read_heartbeat, write_heartbeat


def test_heartbeat_round_trip_and_clean_stop(tmp_path: Path) -> None:
    path = tmp_path / "heartbeat.json"
    write_heartbeat(path, sequence=7, status="stopped", monotonic_seconds=10.0)
    assert read_heartbeat(path).sequence == 7
    restored: list[bool] = []
    result = monitor_heartbeat(
        path,
        timeout_seconds=5.0,
        poll_seconds=1.0,
        on_timeout=lambda: restored.append(True),
        clock=lambda: 11.0,
        sleeper=lambda _: None,
    )
    assert result.reason == "clean_stop"
    assert not result.restoration_called
    assert not restored


def test_stale_heartbeat_calls_restore_once(tmp_path: Path) -> None:
    path = tmp_path / "heartbeat.json"
    write_heartbeat(path, sequence=3, monotonic_seconds=1.0)
    restored: list[bool] = []
    result = monitor_heartbeat(
        path,
        timeout_seconds=5.0,
        poll_seconds=1.0,
        on_timeout=lambda: restored.append(True),
        clock=lambda: 10.0,
        sleeper=lambda _: None,
    )
    assert result.reason == "stale_heartbeat"
    assert result.restoration_called
    assert restored == [True]


def test_missing_heartbeat_observes_startup_grace(tmp_path: Path) -> None:
    clock_values = iter((0.0, 2.0, 6.0))
    restored: list[bool] = []
    result = monitor_heartbeat(
        tmp_path / "missing.json",
        timeout_seconds=5.0,
        poll_seconds=1.0,
        on_timeout=lambda: restored.append(True),
        clock=lambda: next(clock_values),
        sleeper=lambda _: None,
    )
    assert result.reason == "missing_heartbeat"
    assert restored == [True]
