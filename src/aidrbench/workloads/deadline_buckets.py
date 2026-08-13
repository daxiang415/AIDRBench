"""Fluid hourly deadline buckets for the V0 demand-response environment."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

import numpy as np

DEFAULT_BUCKET_LABELS_H: Final[tuple[int, ...]] = (0, 1, 2, 3, 6, 12, 24, 48)
_EPSILON: Final[float] = 1e-9


def _non_negative_finite(value: float, name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


def _positive_finite(value: float, name: str) -> float:
    result = _non_negative_finite(value, name)
    if result <= 0.0:
        raise ValueError(f"{name} must be positive")
    return result


@dataclass(frozen=True, slots=True)
class HourlyArrival:
    """One fluid quantity of flexible GPU-hours arriving in a controller hour."""

    gpu_hours: float
    slack_hours: float
    job_class: str = "training"

    def __post_init__(self) -> None:
        _positive_finite(self.gpu_hours, "gpu_hours")
        _positive_finite(self.slack_hours, "slack_hours")
        if not self.job_class.strip():
            raise ValueError("job_class must not be empty")


@dataclass(frozen=True, slots=True)
class DeadlineBucketStep:
    """Conservation-preserving result of one hourly queue transition."""

    arrived_gpu_h: float
    executed_gpu_h: float
    missed_gpu_h: float
    backlog_gpu_h: float
    bucket_gpu_h: tuple[float, ...]
    mean_slack_h: float
    p10_slack_h: float
    requested_gpu_h: float


class HourlyDeadlineBuckets:
    """Fluid EDF queue with integer-hour deadline resolution.

    The queue stores work by remaining whole-hour deadline. At each transition
    it adds arrivals, serves the requested amount under EDF, records work due
    at the end of the current hour as missed, and then advances every remaining
    bucket by one hour. This matches the V0 hourly approximation and makes
    workload conservation explicit.
    """

    def __init__(
        self,
        *,
        max_deadline_hours: int = 48,
        bucket_labels_h: tuple[int, ...] = DEFAULT_BUCKET_LABELS_H,
    ) -> None:
        if isinstance(max_deadline_hours, bool) or not isinstance(max_deadline_hours, int):
            raise TypeError("max_deadline_hours must be an integer")
        if max_deadline_hours <= 0:
            raise ValueError("max_deadline_hours must be positive")
        if not bucket_labels_h:
            raise ValueError("bucket_labels_h must not be empty")
        if tuple(sorted(bucket_labels_h)) != bucket_labels_h:
            raise ValueError("bucket_labels_h must be sorted")
        if bucket_labels_h[-1] != max_deadline_hours:
            raise ValueError("last bucket label must equal max_deadline_hours")
        if bucket_labels_h[0] != 0:
            raise ValueError("first bucket label must be zero")
        self.max_deadline_hours = max_deadline_hours
        self.bucket_labels_h = bucket_labels_h
        self._due_gpu_h = np.zeros(max_deadline_hours, dtype="float64")
        self.cumulative_arrived_gpu_h = 0.0
        self.cumulative_executed_gpu_h = 0.0
        self.cumulative_missed_gpu_h = 0.0

    def reset(self) -> None:
        """Clear all remaining and cumulative work."""

        self._due_gpu_h.fill(0.0)
        self.cumulative_arrived_gpu_h = 0.0
        self.cumulative_executed_gpu_h = 0.0
        self.cumulative_missed_gpu_h = 0.0

    @property
    def backlog_gpu_h(self) -> float:
        return float(self._due_gpu_h.sum())

    @property
    def bucket_gpu_h(self) -> tuple[float, ...]:
        """Aggregate remaining work into the configured deadline buckets."""

        return self._bucket_values()

    @property
    def remaining_by_deadline_gpu_h(self) -> tuple[float, ...]:
        """Remaining work for every whole-hour deadline, earliest first."""

        return tuple(float(value) for value in self._due_gpu_h)

    @property
    def mean_slack_h(self) -> float:
        """Work-weighted mean remaining slack in the current queue."""

        return self._mean_slack_hours()

    @property
    def p10_slack_h(self) -> float:
        """Work-weighted 10th-percentile remaining slack in the current queue."""

        return self._slack_quantile_hours(0.10)

    def _deadline_index(self, slack_hours: float) -> int:
        # A one-hour slack must finish in the current interval, so it occupies
        # index zero before the shift at the end of this transition.
        rounded_hours = math.ceil(_positive_finite(slack_hours, "slack_hours"))
        return min(max(rounded_hours - 1, 0), self.max_deadline_hours - 1)

    def add(self, arrivals: tuple[HourlyArrival, ...] | list[HourlyArrival]) -> float:
        """Add arrivals and return their total GPU-hours."""

        arrived = 0.0
        for arrival in arrivals:
            index = self._deadline_index(arrival.slack_hours)
            self._due_gpu_h[index] += arrival.gpu_hours
            arrived += arrival.gpu_hours
        self.cumulative_arrived_gpu_h += arrived
        return arrived

    def _serve_edf(self, requested_gpu_h: float) -> float:
        remaining_request = _non_negative_finite(requested_gpu_h, "requested_gpu_h")
        executed = 0.0
        for index in range(len(self._due_gpu_h)):
            if remaining_request <= _EPSILON:
                break
            work = min(float(self._due_gpu_h[index]), remaining_request)
            self._due_gpu_h[index] -= work
            remaining_request -= work
            executed += work
        return executed

    def _bucket_values(self) -> tuple[float, ...]:
        values: list[float] = []
        lower = -1
        for upper in self.bucket_labels_h:
            if upper == 0:
                values.append(float(self._due_gpu_h[0]))
            else:
                start = lower + 1
                stop = min(upper, self.max_deadline_hours - 1) + 1
                values.append(float(self._due_gpu_h[start:stop].sum()))
            lower = upper
        return tuple(values)

    def _mean_slack_hours(self) -> float:
        backlog = self.backlog_gpu_h
        if backlog <= _EPSILON:
            return 0.0
        indices = np.arange(1, self.max_deadline_hours + 1, dtype="float64")
        return float(np.dot(self._due_gpu_h, indices) / backlog)

    def _slack_quantile_hours(self, quantile: float) -> float:
        """Return a work-weighted remaining-slack quantile in whole hours."""

        if not 0.0 <= quantile <= 1.0:
            raise ValueError("quantile must be in [0, 1]")
        backlog = self.backlog_gpu_h
        if backlog <= _EPSILON:
            return 0.0
        threshold = backlog * quantile
        index = int(np.searchsorted(np.cumsum(self._due_gpu_h), threshold, side="left"))
        return float(min(index + 1, self.max_deadline_hours))

    def advance(
        self,
        arrivals: tuple[HourlyArrival, ...] | list[HourlyArrival],
        *,
        requested_gpu_h: float,
        capacity_gpu_h: float,
    ) -> DeadlineBucketStep:
        """Advance one hour with bounded requested execution under EDF."""

        capacity = _non_negative_finite(capacity_gpu_h, "capacity_gpu_h")
        requested = _non_negative_finite(requested_gpu_h, "requested_gpu_h")
        if requested > capacity + _EPSILON:
            raise ValueError("requested_gpu_h exceeds hourly capacity_gpu_h")
        arrived = self.add(arrivals)
        executed = self._serve_edf(min(requested, capacity))
        missed = float(self._due_gpu_h[0])
        self._due_gpu_h[0] = 0.0
        self.cumulative_executed_gpu_h += executed
        self.cumulative_missed_gpu_h += missed
        self._due_gpu_h[:-1] = self._due_gpu_h[1:]
        self._due_gpu_h[-1] = 0.0
        backlog = self.backlog_gpu_h
        return DeadlineBucketStep(
            arrived_gpu_h=arrived,
            executed_gpu_h=executed,
            missed_gpu_h=missed,
            backlog_gpu_h=backlog,
            bucket_gpu_h=self._bucket_values(),
            mean_slack_h=self._mean_slack_hours(),
            p10_slack_h=self._slack_quantile_hours(0.10),
            requested_gpu_h=requested,
        )

    def conservation_error_gpu_h(self) -> float:
        """Return accumulated arrivals minus accounted work, for test assertions."""

        return (
            self.cumulative_arrived_gpu_h
            - self.cumulative_executed_gpu_h
            - self.cumulative_missed_gpu_h
            - self.backlog_gpu_h
        )
