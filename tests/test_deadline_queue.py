from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from aidrbench.workloads.deadline_queue import (
    BatchJobSpec,
    DeadlineBatchQueue,
    load_batch_jobs,
)


def _job(
    job_id: str,
    *,
    release: float = 0.0,
    work: float = 120.0,
    gpus: float = 2.0,
    deadline: float = 600.0,
    preemptible: bool = True,
) -> BatchJobSpec:
    return BatchJobSpec(job_id, release, work, gpus, deadline, preemptible)


def test_batch_work_can_be_deferred_then_recovered() -> None:
    queue = DeadlineBatchQueue([_job("train")])

    shed = queue.advance(60.0, requested_gpu_count=0)
    assert shed.served_work_gpu_seconds == 0.0
    assert shed.backlog_work_gpu_seconds == 120.0
    assert shed.average_active_pool_gpus == 0.0

    recover = queue.advance(60.0, requested_gpu_count=2)
    assert recover.served_work_gpu_seconds == pytest.approx(120.0)
    assert recover.completed_jobs == 1
    assert recover.backlog_work_gpu_seconds == 0.0
    assert queue.completed[0].waiting_time_s == pytest.approx(60.0)


def test_service_ratio_maps_power_cap_to_slower_progress() -> None:
    queue = DeadlineBatchQueue([_job("train", work=120.0)])

    step = queue.advance(60.0, requested_gpu_count=2, service_ratio=0.8)

    assert step.served_work_gpu_seconds == pytest.approx(96.0)
    assert step.backlog_work_gpu_seconds == pytest.approx(24.0)


def test_earliest_deadline_first_and_no_silent_work_loss() -> None:
    queue = DeadlineBatchQueue(
        [
            _job("later", work=20.0, gpus=1.0, deadline=100.0),
            _job("urgent", work=10.0, gpus=1.0, deadline=20.0),
        ],
        max_batch_gpus=1,
    )

    step = queue.advance(10.0, requested_gpu_count=1)

    assert step.completed_jobs == 1
    assert queue.completed[0].job_id == "urgent"
    assert step.backlog_work_gpu_seconds == pytest.approx(20.0)
    assert (
        step.served_work_gpu_seconds
        + step.backlog_work_gpu_seconds
        + step.deadline_missed_work_gpu_seconds
        == pytest.approx(30.0)
    )


def test_unserved_work_becomes_an_explicit_deadline_miss() -> None:
    queue = DeadlineBatchQueue([_job("train", work=90.0, deadline=30.0)])

    step = queue.advance(60.0, requested_gpu_count=0)

    assert step.deadline_missed_jobs == 1
    assert step.deadline_missed_work_gpu_seconds == pytest.approx(90.0)
    assert step.backlog_work_gpu_seconds == 0.0
    assert queue.missed[0].missed_at_s == pytest.approx(30.0)


def test_nonpreemptible_job_forces_committed_gpus_after_shedding() -> None:
    queue = DeadlineBatchQueue(
        [_job("nonpreemptible", work=20.0, deadline=100.0, preemptible=False)]
    )
    first = queue.advance(5.0, requested_gpu_count=2)
    assert first.backlog_work_gpu_seconds == pytest.approx(10.0)

    second = queue.advance(5.0, requested_gpu_count=0)

    assert second.completed_jobs == 1
    assert second.average_active_pool_gpus == pytest.approx(2.0)
    assert second.peak_committed_nonpreemptible_gpus == pytest.approx(2.0)


def test_release_inside_step_is_served_and_bucketed() -> None:
    queue = DeadlineBatchQueue(
        [_job("later", release=30.0, work=60.0, gpus=1.0, deadline=1_000.0)]
    )

    step = queue.advance(60.0, requested_gpu_count=1)

    assert step.arrived_jobs == 1
    assert step.served_work_gpu_seconds == pytest.approx(30.0)
    assert step.backlog_by_deadline_bucket[1] == pytest.approx(30.0)


def test_load_batch_jobs_from_p1_schema(tmp_path: Path) -> None:
    path = tmp_path / "batch.parquet"
    pd.DataFrame(
        [
            {
                "job_id": "j1",
                "release_time_s": 0.0,
                "work_gpu_seconds": 120.0,
                "gpu_demand_local": 2.0,
                "deadline_time_s": 600.0,
                "preemptible": True,
                "priority": "normal",
            }
        ]
    ).to_parquet(path, index=False)

    jobs = load_batch_jobs(path)

    assert jobs == (_job("j1"),)
