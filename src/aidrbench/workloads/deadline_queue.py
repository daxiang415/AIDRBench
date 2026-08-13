"""Preemptible, deadline-aware batch-work queue for demand response."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DEFAULT_DEADLINE_BUCKET_EDGES_S = (900.0, 1_800.0, 3_600.0, 7_200.0, 14_400.0)
_EPSILON = 1e-9


def _finite_non_negative(value: float, name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


def _finite_positive(value: float, name: str) -> float:
    result = _finite_non_negative(value, name)
    if result <= 0.0:
        raise ValueError(f"{name} must be positive")
    return result


def _dataset_float(value: object, name: str) -> float:
    try:
        parsed = float(str(value))
    except ValueError as exc:
        raise ValueError(f"{name} must be numeric") from exc
    return parsed


def _dataset_bool(value: object, name: str) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise ValueError(f"{name} must be boolean")


@dataclass(frozen=True, slots=True)
class BatchJobSpec:
    """Hardware-normalized batch work with release and deadline timestamps."""

    job_id: str
    release_time_s: float
    work_gpu_seconds: float
    gpu_demand: float
    deadline_time_s: float
    preemptible: bool = True
    priority: str = "normal"

    def __post_init__(self) -> None:
        if not self.job_id.strip():
            raise ValueError("job_id must not be empty")
        release = _finite_non_negative(self.release_time_s, "release_time_s")
        deadline = _finite_positive(self.deadline_time_s, "deadline_time_s")
        _finite_positive(self.work_gpu_seconds, "work_gpu_seconds")
        _finite_positive(self.gpu_demand, "gpu_demand")
        if deadline <= release:
            raise ValueError("deadline_time_s must be later than release_time_s")
        if not self.priority.strip():
            raise ValueError("priority must not be empty")


@dataclass(slots=True)
class _BatchJobState:
    spec: BatchJobSpec
    remaining_work_gpu_seconds: float
    started_at_s: float | None = None
    locked_gpu_count: float = 0.0


@dataclass(frozen=True, slots=True)
class CompletedBatchJob:
    job_id: str
    release_time_s: float
    deadline_time_s: float
    started_at_s: float
    completed_at_s: float
    work_gpu_seconds: float
    waiting_time_s: float
    flow_time_s: float


@dataclass(frozen=True, slots=True)
class MissedBatchJob:
    job_id: str
    deadline_time_s: float
    missed_at_s: float
    missed_work_gpu_seconds: float


@dataclass(frozen=True, slots=True)
class DeadlineQueueStep:
    """Raw queue KPIs for one controller interval."""

    start_time_s: float
    end_time_s: float
    requested_gpu_count: int
    service_ratio: float
    arrived_jobs: int
    arrived_work_gpu_seconds: float
    served_work_gpu_seconds: float
    completed_jobs: int
    deadline_missed_jobs: int
    deadline_missed_work_gpu_seconds: float
    backlog_jobs: int
    backlog_work_gpu_seconds: float
    backlog_by_deadline_bucket: tuple[float, ...]
    average_allocated_gpus: float
    average_active_pool_gpus: float
    peak_committed_nonpreemptible_gpus: float
    cumulative_completed_jobs: int
    cumulative_deadline_missed_jobs: int
    cumulative_deadline_missed_work_gpu_seconds: float


class DeadlineBatchQueue:
    """Event-driven EDF queue whose main control is active batch GPU count.

    Work is measured in GPU-seconds. A preemptible job can be paused whenever
    the controller requests zero batch GPUs, then resumed later without losing
    completed work. Once a non-preemptible job starts, its GPU allocation is
    committed until completion; this makes infeasible shedding explicit rather
    than silently discarding work.
    """

    def __init__(
        self,
        jobs: tuple[BatchJobSpec, ...] | list[BatchJobSpec],
        *,
        max_batch_gpus: int = 2,
        bucket_edges_s: tuple[float, ...] = DEFAULT_DEADLINE_BUCKET_EDGES_S,
    ) -> None:
        if isinstance(max_batch_gpus, bool) or max_batch_gpus <= 0:
            raise ValueError("max_batch_gpus must be a positive integer")
        if not isinstance(max_batch_gpus, int):
            raise TypeError("max_batch_gpus must be an integer")
        validated_edges = tuple(
            _finite_positive(edge, "deadline bucket edge") for edge in bucket_edges_s
        )
        if tuple(sorted(validated_edges)) != validated_edges:
            raise ValueError("deadline bucket edges must be sorted")
        if len(set(validated_edges)) != len(validated_edges):
            raise ValueError("deadline bucket edges must be unique")
        job_ids = [job.job_id for job in jobs]
        if len(job_ids) != len(set(job_ids)):
            raise ValueError("job IDs must be unique")

        self.max_batch_gpus = max_batch_gpus
        self.bucket_edges_s = validated_edges
        self._specs = tuple(sorted(jobs, key=lambda job: (job.release_time_s, job.job_id)))
        self.reset()

    def reset(self, *, start_time_s: float = 0.0) -> None:
        """Reset all jobs and counters without changing the immutable workload."""

        self.current_time_s = _finite_non_negative(start_time_s, "start_time_s")
        self._next_job_index = 0
        while (
            self._next_job_index < len(self._specs)
            and self._specs[self._next_job_index].release_time_s < self.current_time_s
        ):
            self._next_job_index += 1
        self._active: dict[str, _BatchJobState] = {}
        self.completed: list[CompletedBatchJob] = []
        self.missed: list[MissedBatchJob] = []
        self.cumulative_served_work_gpu_seconds = 0.0
        self.cumulative_arrived_work_gpu_seconds = 0.0
        self.cumulative_missed_work_gpu_seconds = 0.0
        self._release_ready(None)

    def _release_ready(self, collector: list[_BatchJobState] | None) -> None:
        while self._next_job_index < len(self._specs):
            spec = self._specs[self._next_job_index]
            if spec.release_time_s > self.current_time_s + _EPSILON:
                break
            state = _BatchJobState(spec, spec.work_gpu_seconds)
            self._active[spec.job_id] = state
            self.cumulative_arrived_work_gpu_seconds += spec.work_gpu_seconds
            if collector is not None:
                collector.append(state)
            self._next_job_index += 1

    def _expire_due(self, collector: list[MissedBatchJob]) -> None:
        due = sorted(
            (
                state
                for state in self._active.values()
                if state.spec.deadline_time_s <= self.current_time_s + _EPSILON
            ),
            key=lambda state: (state.spec.deadline_time_s, state.spec.job_id),
        )
        for state in due:
            missed_work = max(state.remaining_work_gpu_seconds, 0.0)
            missed = MissedBatchJob(
                job_id=state.spec.job_id,
                deadline_time_s=state.spec.deadline_time_s,
                missed_at_s=self.current_time_s,
                missed_work_gpu_seconds=missed_work,
            )
            collector.append(missed)
            self.missed.append(missed)
            self.cumulative_missed_work_gpu_seconds += missed_work
            del self._active[state.spec.job_id]

    def _allocations(
        self, requested_gpu_count: int
    ) -> tuple[dict[str, float], float, float]:
        committed = sum(
            state.locked_gpu_count
            for state in self._active.values()
            if state.locked_gpu_count > 0.0
        )
        active_pool = max(float(requested_gpu_count), committed)
        available = active_pool
        allocations: dict[str, float] = {}

        for state in sorted(
            self._active.values(),
            key=lambda item: (item.spec.deadline_time_s, item.spec.job_id),
        ):
            if state.locked_gpu_count <= 0.0:
                continue
            allocation = min(state.locked_gpu_count, available)
            allocations[state.spec.job_id] = allocation
            available -= allocation

        for state in sorted(
            self._active.values(),
            key=lambda item: (item.spec.deadline_time_s, item.spec.job_id),
        ):
            if state.spec.job_id in allocations or available <= _EPSILON:
                continue
            demand = min(state.spec.gpu_demand, float(self.max_batch_gpus))
            if not state.spec.preemptible:
                if available + _EPSILON < demand:
                    continue
                state.locked_gpu_count = demand
                allocation = demand
            else:
                allocation = min(demand, available)
            allocations[state.spec.job_id] = allocation
            available -= allocation
            if state.started_at_s is None:
                state.started_at_s = self.current_time_s
        return allocations, active_pool, committed

    def _next_event_time(
        self,
        end_time_s: float,
        allocations: dict[str, float],
        service_ratio: float,
    ) -> float:
        candidates = [end_time_s]
        if self._next_job_index < len(self._specs):
            release = self._specs[self._next_job_index].release_time_s
            if release > self.current_time_s + _EPSILON:
                candidates.append(release)
        candidates.extend(
            state.spec.deadline_time_s
            for state in self._active.values()
            if state.spec.deadline_time_s > self.current_time_s + _EPSILON
        )
        for job_id, allocated_gpus in allocations.items():
            rate = allocated_gpus * service_ratio
            if rate > 0.0:
                state = self._active[job_id]
                candidates.append(
                    self.current_time_s + state.remaining_work_gpu_seconds / rate
                )
        return min(candidate for candidate in candidates if candidate > self.current_time_s)

    def _complete_finished(self, collector: list[CompletedBatchJob]) -> None:
        finished = sorted(
            (
                state
                for state in self._active.values()
                if state.remaining_work_gpu_seconds <= _EPSILON
            ),
            key=lambda state: (state.spec.deadline_time_s, state.spec.job_id),
        )
        for state in finished:
            started_at = state.started_at_s
            if started_at is None:
                raise RuntimeError("completed batch job has no start timestamp")
            completed = CompletedBatchJob(
                job_id=state.spec.job_id,
                release_time_s=state.spec.release_time_s,
                deadline_time_s=state.spec.deadline_time_s,
                started_at_s=started_at,
                completed_at_s=self.current_time_s,
                work_gpu_seconds=state.spec.work_gpu_seconds,
                waiting_time_s=started_at - state.spec.release_time_s,
                flow_time_s=self.current_time_s - state.spec.release_time_s,
            )
            collector.append(completed)
            self.completed.append(completed)
            del self._active[state.spec.job_id]

    def backlog_by_deadline_bucket(self) -> tuple[float, ...]:
        """Return remaining GPU-seconds in the README's deadline buckets."""

        buckets = [0.0] * (len(self.bucket_edges_s) + 1)
        for state in self._active.values():
            remaining_time = max(state.spec.deadline_time_s - self.current_time_s, 0.0)
            bucket_index = len(self.bucket_edges_s)
            for index, edge in enumerate(self.bucket_edges_s):
                if remaining_time <= edge:
                    bucket_index = index
                    break
            buckets[bucket_index] += state.remaining_work_gpu_seconds
        return tuple(buckets)

    @property
    def backlog_work_gpu_seconds(self) -> float:
        return sum(state.remaining_work_gpu_seconds for state in self._active.values())

    def advance(
        self,
        dt_seconds: float,
        *,
        requested_gpu_count: int,
        service_ratio: float = 1.0,
    ) -> DeadlineQueueStep:
        """Advance one control interval under a batch-GPU and power-cap action."""

        duration = _finite_positive(dt_seconds, "dt_seconds")
        if isinstance(requested_gpu_count, bool) or not isinstance(requested_gpu_count, int):
            raise TypeError("requested_gpu_count must be an integer")
        if not 0 <= requested_gpu_count <= self.max_batch_gpus:
            raise ValueError("requested_gpu_count is outside the batch pool")
        ratio = _finite_positive(service_ratio, "service_ratio")
        if ratio > 1.0:
            raise ValueError("service_ratio must not exceed 1.0")

        start_time = self.current_time_s
        end_time = start_time + duration
        arrived: list[_BatchJobState] = []
        completed: list[CompletedBatchJob] = []
        missed: list[MissedBatchJob] = []
        served_work = 0.0
        allocated_gpu_seconds = 0.0
        active_pool_gpu_seconds = 0.0
        peak_committed = 0.0

        self._release_ready(arrived)
        self._expire_due(missed)
        while self.current_time_s < end_time - _EPSILON:
            allocations, active_pool, committed = self._allocations(requested_gpu_count)
            peak_committed = max(peak_committed, committed)
            next_time = min(
                self._next_event_time(end_time, allocations, ratio),
                end_time,
            )
            event_duration = next_time - self.current_time_s
            allocated = sum(allocations.values())
            for job_id, allocated_gpus in allocations.items():
                state = self._active[job_id]
                work = min(
                    state.remaining_work_gpu_seconds,
                    allocated_gpus * ratio * event_duration,
                )
                state.remaining_work_gpu_seconds -= work
                served_work += work
            allocated_gpu_seconds += allocated * event_duration
            active_pool_gpu_seconds += active_pool * event_duration
            self.current_time_s = next_time
            self._complete_finished(completed)
            self._release_ready(arrived)
            self._expire_due(missed)

        self.current_time_s = end_time
        self.cumulative_served_work_gpu_seconds += served_work
        backlog = self.backlog_work_gpu_seconds
        return DeadlineQueueStep(
            start_time_s=start_time,
            end_time_s=end_time,
            requested_gpu_count=requested_gpu_count,
            service_ratio=ratio,
            arrived_jobs=len(arrived),
            arrived_work_gpu_seconds=sum(
                state.spec.work_gpu_seconds for state in arrived
            ),
            served_work_gpu_seconds=served_work,
            completed_jobs=len(completed),
            deadline_missed_jobs=len(missed),
            deadline_missed_work_gpu_seconds=sum(
                job.missed_work_gpu_seconds for job in missed
            ),
            backlog_jobs=len(self._active),
            backlog_work_gpu_seconds=backlog,
            backlog_by_deadline_bucket=self.backlog_by_deadline_bucket(),
            average_allocated_gpus=allocated_gpu_seconds / duration,
            average_active_pool_gpus=active_pool_gpu_seconds / duration,
            peak_committed_nonpreemptible_gpus=peak_committed,
            cumulative_completed_jobs=len(self.completed),
            cumulative_deadline_missed_jobs=len(self.missed),
            cumulative_deadline_missed_work_gpu_seconds=(
                self.cumulative_missed_work_gpu_seconds
            ),
        )


def load_batch_jobs(path: str | Path) -> tuple[BatchJobSpec, ...]:
    """Load P1 batch-job Parquet output into validated queue specifications."""

    frame = pd.read_parquet(path)
    required = {
        "job_id",
        "release_time_s",
        "work_gpu_seconds",
        "gpu_demand_local",
        "deadline_time_s",
        "preemptible",
        "priority",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"batch job dataset is missing columns: {missing}")
    return tuple(
        BatchJobSpec(
            job_id=str(row.job_id),
            release_time_s=_dataset_float(row.release_time_s, "release_time_s"),
            work_gpu_seconds=_dataset_float(row.work_gpu_seconds, "work_gpu_seconds"),
            gpu_demand=_dataset_float(row.gpu_demand_local, "gpu_demand_local"),
            deadline_time_s=_dataset_float(row.deadline_time_s, "deadline_time_s"),
            preemptible=_dataset_bool(row.preemptible, "preemptible"),
            priority=str(row.priority),
        )
        for row in frame.itertuples(index=False)
    )
