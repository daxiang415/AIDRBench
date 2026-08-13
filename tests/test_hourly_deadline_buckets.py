from __future__ import annotations

import pytest

from aidrbench.workloads.deadline_buckets import HourlyArrival, HourlyDeadlineBuckets


def test_hourly_deadline_buckets_record_miss_and_preserve_gpu_hours() -> None:
    queue = HourlyDeadlineBuckets()

    step = queue.advance(
        [HourlyArrival(gpu_hours=3.0, slack_hours=1.0)],
        requested_gpu_h=0.0,
        capacity_gpu_h=4.0,
    )

    assert step.arrived_gpu_h == pytest.approx(3.0)
    assert step.executed_gpu_h == pytest.approx(0.0)
    assert step.missed_gpu_h == pytest.approx(3.0)
    assert step.backlog_gpu_h == pytest.approx(0.0)
    assert queue.conservation_error_gpu_h() == pytest.approx(0.0)


def test_hourly_deadline_buckets_shift_then_miss_unserved_work() -> None:
    queue = HourlyDeadlineBuckets()

    first = queue.advance(
        [HourlyArrival(gpu_hours=2.0, slack_hours=2.0)],
        requested_gpu_h=0.0,
        capacity_gpu_h=4.0,
    )
    second = queue.advance([], requested_gpu_h=0.0, capacity_gpu_h=4.0)

    assert first.backlog_gpu_h == pytest.approx(2.0)
    assert second.missed_gpu_h == pytest.approx(2.0)
    assert queue.conservation_error_gpu_h() == pytest.approx(0.0)


def test_hourly_deadline_buckets_execute_by_earliest_deadline_first() -> None:
    queue = HourlyDeadlineBuckets()

    step = queue.advance(
        [
            HourlyArrival(gpu_hours=2.0, slack_hours=12.0, job_class="training"),
            HourlyArrival(gpu_hours=1.0, slack_hours=1.0, job_class="offline_inference"),
        ],
        requested_gpu_h=1.5,
        capacity_gpu_h=4.0,
    )

    assert step.executed_gpu_h == pytest.approx(1.5)
    assert step.missed_gpu_h == pytest.approx(0.0)
    assert step.backlog_gpu_h == pytest.approx(1.5)
    assert queue.bucket_gpu_h[0] == pytest.approx(0.0)
    assert queue.conservation_error_gpu_h() == pytest.approx(0.0)


def test_hourly_deadline_buckets_expose_work_weighted_p10_slack() -> None:
    queue = HourlyDeadlineBuckets()

    step = queue.advance(
        [
            HourlyArrival(gpu_hours=9.0, slack_hours=2.0),
            HourlyArrival(gpu_hours=1.0, slack_hours=24.0),
        ],
        requested_gpu_h=0.0,
        capacity_gpu_h=12.0,
    )

    # After one bucket advance the short work has one hour remaining; at
    # least 10% of queued GPU-hours are therefore in the one-hour slack tail.
    assert step.p10_slack_h == pytest.approx(1.0)
    assert step.mean_slack_h > step.p10_slack_h
