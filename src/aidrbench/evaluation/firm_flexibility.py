"""Rebound-aware event metrics and statistical firm-flexibility primitives."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from statistics import NormalDist

import pandas as pd

from aidrbench.envs.community_ai_dr_env import HourlyDREvent

_EPSILON = 1e-9
_EVENT_COLUMNS = frozenset(
    {
        "hour",
        "event_active",
        "pcc_power_kw",
        "baseline_pcc_power_kw",
        "delivered_reduction_kw",
        "requested_reduction_kw",
        "backlog_gpu_h",
        "baseline_backlog_gpu_h",
        "missed_gpu_h",
        "arrival_gpu_h",
        "terminal_backlog_excess_gpu_h",
    }
)


def wilson_lower_bound(successes: int, trials: int, confidence_level: float) -> float:
    """One-sided Wilson lower confidence bound for a Bernoulli success rate."""

    if isinstance(successes, bool) or isinstance(trials, bool):
        raise ValueError("successes and trials must be integers")
    if not 0 <= successes <= trials or trials <= 0:
        raise ValueError("successes must be in [0, trials] and trials must be positive")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be in (0, 1)")
    z = NormalDist().inv_cdf(confidence_level)
    observed = successes / trials
    z_squared = z * z
    denominator = 1.0 + z_squared / trials
    centre = observed + z_squared / (2.0 * trials)
    radius = z * math.sqrt(
        observed * (1.0 - observed) / trials + z_squared / (4.0 * trials * trials)
    )
    return max(0.0, (centre - radius) / denominator)


def minimum_successes_for_wilson(
    trials: int,
    reliability_target: float,
    confidence_level: float,
) -> int | None:
    """Return the fewest successes whose one-sided Wilson bound reaches ``q``.

    ``None`` means that even an all-success sample is too small to establish
    the requested reliability at the declared confidence level.
    """

    if isinstance(trials, bool) or not isinstance(trials, int) or trials <= 0:
        raise ValueError("trials must be a positive integer")
    if not 0.0 < reliability_target < 1.0:
        raise ValueError("reliability_target must be in (0, 1)")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be in (0, 1)")
    for successes in range(trials + 1):
        if (
            wilson_lower_bound(successes, trials, confidence_level)
            + _EPSILON
            >= reliability_target
        ):
            return successes
    return None


@dataclass(frozen=True, slots=True)
class FirmFlexibilityCriteria:
    """Frozen joint success definition for one reliable-flexibility certificate."""

    reliability_target: float = 0.95
    confidence_level: float = 0.95
    min_delivery_ratio: float = 0.95
    min_interval_delivery_ratio: float = 0.95
    max_deadline_miss_rate: float = 0.01
    max_rebound_ratio: float = 0.25
    min_window_peak_relief_fraction: float = 0.50
    max_terminal_backlog_fraction: float = 0.02

    def __post_init__(self) -> None:
        for name, value in (
            ("reliability_target", self.reliability_target),
            ("confidence_level", self.confidence_level),
        ):
            if not 0.0 < value < 1.0:
                raise ValueError(f"{name} must be in (0, 1)")
        for name, value in (
            ("min_delivery_ratio", self.min_delivery_ratio),
            ("min_interval_delivery_ratio", self.min_interval_delivery_ratio),
            ("min_window_peak_relief_fraction", self.min_window_peak_relief_fraction),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        for name, value in (
            ("max_deadline_miss_rate", self.max_deadline_miss_rate),
            ("max_rebound_ratio", self.max_rebound_ratio),
            ("max_terminal_backlog_fraction", self.max_terminal_backlog_fraction),
        ):
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and non-negative")

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EventOutcome:
    """All independent success inputs for one event in one episode."""

    event_id: int
    start_hour: int
    duration_h: int
    requested_reduction_kw: float
    delivery_ratio: float
    minimum_interval_delivery_ratio: float
    deadline_miss_rate: float
    rebound_peak_kw: float
    rebound_ratio: float
    window_peak_relief_kw: float
    window_peak_relief_fraction: float
    terminal_backlog_fraction: float
    recovery_time_h: float | None

    def success(self, criteria: FirmFlexibilityCriteria) -> tuple[bool, tuple[str, ...]]:
        """Return the joint certificate decision and auditable failure labels."""

        failures: list[str] = []
        mean_delivery_failed = self.delivery_ratio + _EPSILON < criteria.min_delivery_ratio
        interval_delivery_failed = (
            self.minimum_interval_delivery_ratio + _EPSILON
            < criteria.min_interval_delivery_ratio
        )
        if mean_delivery_failed or interval_delivery_failed:
            failures.append("delivery")
        if interval_delivery_failed:
            failures.append("interval_delivery")
        if self.deadline_miss_rate - _EPSILON > criteria.max_deadline_miss_rate:
            failures.append("deadline")
        if self.rebound_ratio - _EPSILON > criteria.max_rebound_ratio:
            failures.append("rebound")
        if self.window_peak_relief_fraction + _EPSILON < criteria.min_window_peak_relief_fraction:
            failures.append("window_relief")
        if self.terminal_backlog_fraction - _EPSILON > criteria.max_terminal_backlog_fraction:
            failures.append("terminal_backlog")
        return not failures, tuple(failures)


def derive_event_outcomes(
    frame: pd.DataFrame,
    events: Sequence[HourlyDREvent],
    *,
    recovery_tolerance_gpu_h: float,
) -> list[EventOutcome]:
    """Derive rebound-aware, episode-level outcomes from one rollout frame.

    The environment supplies an immutable event manifest, so this calculation
    remains correct even when recovery windows from repeated events overlap.
    """

    if frame.empty:
        raise ValueError("cannot derive firm-flexibility metrics from an empty frame")
    missing = _EVENT_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"rollout frame is missing firm-flexibility columns: {sorted(missing)}")
    if not math.isfinite(recovery_tolerance_gpu_h) or recovery_tolerance_gpu_h < 0.0:
        raise ValueError("recovery_tolerance_gpu_h must be finite and non-negative")
    total_arrivals = float(frame["arrival_gpu_h"].sum())
    deadline_miss_rate = (
        float(frame["missed_gpu_h"].sum()) / total_arrivals if total_arrivals > _EPSILON else 0.0
    )
    terminal_backlog_fraction = (
        float(frame["terminal_backlog_excess_gpu_h"].iloc[-1]) / total_arrivals
        if total_arrivals > _EPSILON
        else 0.0
    )
    outcomes: list[EventOutcome] = []
    for event in events:
        event_rows = frame.loc[
            (frame["hour"] >= event.start_hour) & (frame["hour"] < event.stop_hour)
        ]
        window_rows = frame.loc[
            (frame["hour"] >= event.start_hour)
            & (frame["hour"] < event.recovery_stop_hour)
        ]
        post_rows = frame.loc[
            (frame["hour"] >= event.stop_hour)
            & (frame["hour"] < event.recovery_stop_hour)
        ]
        if event_rows.empty or window_rows.empty:
            raise ValueError(f"event {event.event_id} has no complete rollout rows")
        requested_total = float(event_rows["requested_reduction_kw"].sum())
        delivered = event_rows[["delivered_reduction_kw", "requested_reduction_kw"]].min(axis=1)
        delivery_ratio = (
            float(delivered.sum() / requested_total) if requested_total > _EPSILON else 1.0
        )
        interval_requested = event_rows["requested_reduction_kw"]
        interval_delivery_ratios = delivered.divide(
            interval_requested.where(interval_requested > 0)
        )
        minimum_interval_delivery_ratio = (
            float(interval_delivery_ratios.min())
            if requested_total > _EPSILON
            else 1.0
        )
        rebound_peak_kw = (
            float(
                (post_rows["pcc_power_kw"] - post_rows["baseline_pcc_power_kw"])
                .clip(lower=0.0)
                .max()
            )
            if not post_rows.empty
            else 0.0
        )
        peak_delivered_kw = float(event_rows["delivered_reduction_kw"].clip(lower=0.0).max())
        rebound_ratio = rebound_peak_kw / peak_delivered_kw if peak_delivered_kw > _EPSILON else 0.0
        window_peak_relief_kw = float(
            window_rows["baseline_pcc_power_kw"].max() - window_rows["pcc_power_kw"].max()
        )
        window_relief_fraction = (
            window_peak_relief_kw / event.requested_reduction_kw
            if event.requested_reduction_kw > _EPSILON
            else 1.0
        )
        recovery_rows = frame.loc[
            (frame["hour"] >= event.stop_hour - 1)
            & (frame["hour"] < event.recovery_stop_hour)
        ]
        backlog_excess = recovery_rows["backlog_gpu_h"] - recovery_rows["baseline_backlog_gpu_h"]
        recovered = recovery_rows.loc[backlog_excess <= recovery_tolerance_gpu_h + _EPSILON]
        recovery_time_h = (
            float(recovered["hour"].iloc[0] - (event.stop_hour - 1))
            if not recovered.empty
            else None
        )
        outcomes.append(
            EventOutcome(
                event_id=event.event_id,
                start_hour=event.start_hour,
                duration_h=event.stop_hour - event.start_hour,
                requested_reduction_kw=event.requested_reduction_kw,
                delivery_ratio=delivery_ratio,
                minimum_interval_delivery_ratio=minimum_interval_delivery_ratio,
                deadline_miss_rate=deadline_miss_rate,
                rebound_peak_kw=rebound_peak_kw,
                rebound_ratio=rebound_ratio,
                window_peak_relief_kw=window_peak_relief_kw,
                window_peak_relief_fraction=window_relief_fraction,
                terminal_backlog_fraction=terminal_backlog_fraction,
                recovery_time_h=recovery_time_h,
            )
        )
    return outcomes


def event_outcomes_frame(
    outcomes: Sequence[EventOutcome], criteria: FirmFlexibilityCriteria | None = None
) -> pd.DataFrame:
    """Tabular event outcomes, optionally with the frozen success decision."""

    rows: list[dict[str, float | int | str | bool | None]] = []
    for outcome in outcomes:
        row: dict[str, float | int | str | bool | None] = asdict(outcome)
        if row["recovery_time_h"] is None:
            # Keep the column numeric across candidate tables; an unresolved
            # recovery is represented as NaN rather than an object column.
            row["recovery_time_h"] = math.nan
        if criteria is not None:
            success, failures = outcome.success(criteria)
            row["success"] = success
            row["failure_reasons"] = ",".join(failures)
        rows.append(row)
    return pd.DataFrame.from_records(rows)
