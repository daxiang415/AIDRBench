"""Synthetic hourly workload inputs for the V0 demand-response environment."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from aidrbench.workloads.deadline_buckets import HourlyArrival

HOURLY_ARRIVAL_COLUMNS = (
    "episode_id",
    "timestamp_index",
    "job_class",
    "priority_class",
    "model_type",
    "arrival_gpu_h",
    "slack_hours",
    "source_mode",
)
HOURLY_COMMUNITY_COLUMNS = (
    "timestamp",
    "community_load_kw",
    "pv_generation_kw",
    "net_community_load_kw",
    "profile_id",
    "source",
)
HOURLY_DR_REQUIRED_COLUMNS = (
    "event_id",
    "start_time",
    "end_time",
    "duration_minutes",
    "notice_minutes",
    "reduction_fraction",
)
NANOSECONDS_PER_HOUR = 3_600_000_000_000

DEFAULT_WORKLOAD_SHARES = {
    "training": 0.50,
    "offline_inference": 0.30,
    "online_inference": 0.20,
}
DEFAULT_FLEXIBLE_FRACTIONS = {
    "training": 1.00,
    "offline_inference": 0.80,
    "online_inference": 0.00,
}
DEFAULT_DEADLINE_RANGES_H = {
    "training": (6, 48),
    "offline_inference": (2, 24),
}


def _fraction(value: object, name: str, *, allow_zero: bool = True) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    lower = 0.0 if allow_zero else 0.0
    if not math.isfinite(result) or result < lower or result > 1.0:
        interval = "[0, 1]" if allow_zero else "(0, 1]"
        raise ValueError(f"{name} must be in {interval}")
    if not allow_zero and result == 0.0:
        raise ValueError(f"{name} must be in (0, 1]")
    return result


def _positive_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be positive")
    return result


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return {str(key): item for key, item in value.items()}


@dataclass(frozen=True, slots=True)
class WorkloadMix:
    """GPU-hour workload composition and the fraction that is schedulable."""

    shares: dict[str, float]
    flexible_fractions: dict[str, float]

    def __post_init__(self) -> None:
        if set(self.shares) != set(self.flexible_fractions):
            raise ValueError("workload shares and flexible fractions must use identical classes")
        if not self.shares:
            raise ValueError("workload mix must contain at least one class")
        share_sum = sum(self.shares.values())
        if not math.isclose(share_sum, 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("workload shares must sum to 1.0")
        for name, share in self.shares.items():
            _fraction(share, f"share for {name}")
            _fraction(self.flexible_fractions[name], f"flexible fraction for {name}")

    @property
    def training_share(self) -> float:
        """Training share of total GPU-hour arrivals, requested by the user."""

        return self.shares.get("training", 0.0)

    @property
    def flexible_share(self) -> float:
        """Share of all arriving GPU-hours that can be shifted by the agent."""

        return sum(self.shares[name] * self.flexible_fractions[name] for name in self.shares)

    @property
    def rigid_share(self) -> float:
        return 1.0 - self.flexible_share

    def flexible_class_share(self, job_class: str) -> float:
        return self.shares.get(job_class, 0.0) * self.flexible_fractions.get(job_class, 0.0)

    @classmethod
    def from_mapping(cls, value: object) -> WorkloadMix:
        root = _mapping(value, "workload_mix")
        shares_raw = _mapping(root.get("shares", DEFAULT_WORKLOAD_SHARES), "workload_mix.shares")
        fractions_raw = _mapping(
            root.get("flexible_fractions", DEFAULT_FLEXIBLE_FRACTIONS),
            "workload_mix.flexible_fractions",
        )
        shares = {
            name: _fraction(item, f"workload_mix.shares.{name}")
            for name, item in shares_raw.items()
        }
        fractions = {
            name: _fraction(item, f"workload_mix.flexible_fractions.{name}")
            for name, item in fractions_raw.items()
        }
        return cls(shares=shares, flexible_fractions=fractions)


def make_synthetic_hourly_community(
    *,
    hours: int,
    peak_kw: float,
    seed: int,
    pv_enabled: bool = False,
) -> pd.DataFrame:
    """Create a deterministic hourly community with morning/evening peaks."""

    if isinstance(hours, bool) or not isinstance(hours, int) or hours <= 0:
        raise ValueError("hours must be a positive integer")
    peak = _positive_float(peak_kw, "peak_kw")
    rng = np.random.default_rng(seed)
    timestamps = pd.date_range("2026-01-05T00:00:00Z", periods=hours, freq="1h", tz=UTC)
    hour = timestamps.hour.to_numpy(dtype="float64")
    weekday = timestamps.dayofweek.to_numpy()
    morning = 0.18 * np.exp(-0.5 * ((hour - 8.0) / 1.7) ** 2)
    evening = 0.42 * np.exp(-0.5 * ((hour - 19.0) / 2.2) ** 2)
    weekend = np.where(weekday >= 5, -0.06, 0.0)
    innovations = rng.normal(0.0, 0.018, size=hours)
    noise = np.empty(hours, dtype="float64")
    noise[0] = innovations[0]
    for index in range(1, hours):
        noise[index] = 0.75 * noise[index - 1] + innovations[index]
    raw = np.clip(0.52 + morning + evening + weekend + noise, 0.12, None)
    community_kw = peak * raw / float(raw.max())
    daylight = np.maximum(0.0, np.sin(np.pi * (hour - 6.0) / 12.0))
    pv_kw = 0.16 * peak * daylight**1.8 if pv_enabled else np.zeros(hours)
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "community_load_kw": community_kw,
            "pv_generation_kw": pv_kw,
            "net_community_load_kw": community_kw - pv_kw,
            "profile_id": f"synthetic_seed_{seed}",
            "source": "synthetic_hourly",
        }
    )


def load_hourly_community_profile(
    path: str | Path,
    *,
    profile_id: str | None,
    target_peak_kw: float,
    pv_enabled: bool,
) -> pd.DataFrame:
    """Load, scale, and convert one community power profile to hourly means.

    Sub-hourly EULP records are interval-ending power values.  Right-closed
    hourly bins therefore preserve the energy represented by timestamps such
    as 00:15, 00:30, 00:45, and 01:00.  Incomplete boundary hours are removed.
    """

    input_path = Path(path)
    if not input_path.is_file():
        raise FileNotFoundError(f"community profile does not exist: {input_path}")
    frame = pd.read_parquet(input_path)
    required = {"timestamp", "community_load_kw", "pv_generation_kw"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"community profile is missing required columns: {missing}")

    selected_profile = profile_id
    if "profile_id" in frame.columns:
        available = sorted(frame["profile_id"].dropna().astype(str).unique().tolist())
        if selected_profile is None:
            if len(available) != 1:
                raise ValueError(
                    "community profile file contains multiple profiles; configure "
                    f"community.profile_id from {available}"
                )
            selected_profile = available[0]
        if selected_profile not in available:
            raise ValueError(
                f"unknown community profile_id {selected_profile!r}; available profiles: "
                f"{available}"
            )
        frame = frame.loc[frame["profile_id"].astype(str) == selected_profile]
    elif selected_profile is not None:
        raise ValueError("community.profile_id was configured but the file has no profile_id")
    else:
        selected_profile = input_path.stem

    normalized = frame.loc[:, ["timestamp", "community_load_kw", "pv_generation_kw"]].copy()
    normalized["timestamp"] = pd.to_datetime(normalized["timestamp"], errors="coerce")
    normalized["community_load_kw"] = pd.to_numeric(
        normalized["community_load_kw"], errors="coerce"
    )
    normalized["pv_generation_kw"] = pd.to_numeric(normalized["pv_generation_kw"], errors="coerce")
    if normalized.isna().any().any():
        raise ValueError("community profile contains invalid timestamps or power values")
    if (normalized["community_load_kw"] <= 0.0).any():
        raise ValueError("community_load_kw must be positive")
    if (normalized["pv_generation_kw"] < 0.0).any():
        raise ValueError("pv_generation_kw must be non-negative")
    normalized = normalized.sort_values("timestamp", kind="stable")
    if normalized["timestamp"].duplicated().any():
        raise ValueError("community profile contains duplicate timestamps")

    differences = normalized["timestamp"].diff().dropna()
    if differences.empty or (differences <= pd.Timedelta(0)).any():
        raise ValueError("community profile needs at least two ordered timestamps")
    resolution_ns = int(pd.Timedelta(differences.median()).value)
    hour_ns = NANOSECONDS_PER_HOUR
    if resolution_ns > hour_ns:
        raise ValueError("community profile resolution must be hourly or finer")
    if hour_ns % resolution_ns != 0:
        raise ValueError("community profile resolution must divide one hour exactly")

    if resolution_ns < hour_ns:
        samples_per_hour = hour_ns // resolution_ns
        indexed = normalized.set_index("timestamp")
        hourly_power = indexed.resample("1h", closed="right", label="right").mean()
        hourly_counts = (
            indexed["community_load_kw"].resample("1h", closed="right", label="right").count()
        )
        hourly_power = hourly_power.loc[hourly_counts == samples_per_hour]
        # EULP timestamps are interval-ending.  Expose conventional hourly
        # interval starts to the environment and DR event manifests.
        hourly_power.index = pd.DatetimeIndex(hourly_power.index) - timedelta(hours=1)
        normalized = hourly_power.reset_index()

    configured_peak = _positive_float(target_peak_kw, "target_peak_kw")
    observed_peak = float(normalized["community_load_kw"].max())
    scale = configured_peak / observed_peak
    gross_kw = normalized["community_load_kw"].astype("float64") * scale
    if pv_enabled:
        pv_kw = normalized["pv_generation_kw"].astype("float64") * scale
    else:
        pv_kw = pd.Series(0.0, index=normalized.index, dtype="float64")
    source = (
        str(frame["source"].iloc[0])
        if "source" in frame.columns and not frame["source"].empty
        else "community_parquet"
    )
    return pd.DataFrame(
        {
            "timestamp": normalized["timestamp"].to_numpy(),
            "community_load_kw": gross_kw.to_numpy(),
            "pv_generation_kw": pv_kw.to_numpy(),
            "net_community_load_kw": (gross_kw - pv_kw).to_numpy(),
            "profile_id": str(selected_profile),
            "source": source,
        },
        columns=HOURLY_COMMUNITY_COLUMNS,
    )


def select_hourly_community_window(
    profile: pd.DataFrame,
    *,
    hours: int,
    seed: int,
    episode_start: str | None = None,
    window_start: str | None = None,
    window_end: str | None = None,
) -> pd.DataFrame:
    """Select one contiguous, reproducible episode from an hourly profile."""

    if isinstance(hours, bool) or not isinstance(hours, int) or hours <= 0:
        raise ValueError("hours must be a positive integer")
    missing = sorted(set(HOURLY_COMMUNITY_COLUMNS) - set(profile.columns))
    if missing:
        raise ValueError(f"hourly community profile is missing columns: {missing}")
    ordered = profile.sort_values("timestamp", kind="stable").reset_index(drop=True)
    timestamps = pd.to_datetime(ordered["timestamp"])

    segment_starts = [0]
    segment_stops: list[int] = []
    hour_ns = NANOSECONDS_PER_HOUR
    for index, difference in enumerate(timestamps.diff().iloc[1:], start=1):
        if int(pd.Timedelta(difference).value) != hour_ns:
            segment_stops.append(index)
            segment_starts.append(index)
    segment_stops.append(len(ordered))
    all_candidate_starts = [
        start
        for segment_start, segment_stop in zip(segment_starts, segment_stops, strict=True)
        for start in range(segment_start, segment_stop - hours + 1)
    ]
    # Calendar-aligned weeks keep relative DR hour 17 at local 17:00 rather
    # than silently shifting event clock time with an arbitrary window offset.
    eligible_starts = all_candidate_starts
    if (window_start is None) != (window_end is None):
        raise ValueError("window_start and window_end must be supplied together")
    if window_start is not None and window_end is not None:
        lower = pd.to_datetime(window_start, utc=True).tz_localize(None)
        upper = pd.to_datetime(window_end, utc=True).tz_localize(None)
        if lower >= upper:
            raise ValueError("community window_start must be earlier than window_end")
        eligible_starts = [
            start
            for start in eligible_starts
            if pd.Timestamp(timestamps.iloc[start]) >= lower
            and pd.Timestamp(timestamps.iloc[start + hours - 1]) + timedelta(hours=1) <= upper
        ]
    candidate_starts = [
        start for start in eligible_starts if pd.Timestamp(timestamps.iloc[start]).hour == 0
    ]
    if not candidate_starts:
        raise ValueError(
            f"community profile has no eligible midnight-aligned contiguous {hours}-hour episode"
        )

    if episode_start is None:
        rng = np.random.default_rng(seed)
        start_index = int(rng.choice(candidate_starts))
    else:
        requested_start = pd.to_datetime(episode_start, utc=True).tz_localize(None)
        matches = ordered.index[timestamps == requested_start].tolist()
        if not matches:
            raise ValueError(f"community.episode_start is not in the profile: {episode_start}")
        start_index = int(matches[0])
        if start_index not in eligible_starts:
            raise ValueError("community.episode_start is outside the eligible contiguous window")
    return ordered.iloc[start_index : start_index + hours].reset_index(drop=True).copy()


def load_hourly_dr_manifest(
    path: str | Path,
    *,
    profile_id: str | None,
) -> pd.DataFrame:
    """Load an absolute-time DR manifest compatible with the hourly environment."""

    input_path = Path(path)
    if not input_path.is_file():
        raise FileNotFoundError(f"DR event manifest does not exist: {input_path}")
    frame = pd.read_parquet(input_path)
    missing = sorted(set(HOURLY_DR_REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"DR event manifest is missing required columns: {missing}")
    if "community_profile_id" in frame.columns and profile_id is not None:
        available = sorted(frame["community_profile_id"].dropna().astype(str).unique().tolist())
        if profile_id not in available:
            raise ValueError(
                f"DR manifest has no events for community profile {profile_id!r}; "
                f"available profiles: {available}"
            )
        frame = frame.loc[frame["community_profile_id"].astype(str) == profile_id]
    normalized = frame.copy()
    for column in ("start_time", "end_time"):
        normalized[column] = pd.to_datetime(
            normalized[column], errors="coerce", utc=True
        ).dt.tz_localize(None)
    for column in ("duration_minutes", "notice_minutes", "reduction_fraction"):
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
    if normalized.loc[:, HOURLY_DR_REQUIRED_COLUMNS].isna().any().any():
        raise ValueError("DR event manifest contains missing or invalid values")
    if normalized.empty:
        raise ValueError("DR event manifest contains no events for the selected profile")
    actual_duration_minutes = (
        normalized["end_time"] - normalized["start_time"]
    ).dt.total_seconds() / 60.0
    if not np.allclose(actual_duration_minutes, normalized["duration_minutes"]):
        raise ValueError("DR event duration_minutes disagrees with start_time/end_time")
    aligned_start = (
        normalized["start_time"].dt.minute.eq(0)
        & normalized["start_time"].dt.second.eq(0)
        & normalized["start_time"].dt.microsecond.eq(0)
    )
    whole_hour_duration = np.isclose(normalized["duration_minutes"] % 60.0, 0.0)
    if not bool(aligned_start.all()) or not bool(whole_hour_duration.all()):
        raise ValueError(
            "hourly environment requires DR events to start on the hour and have "
            "whole-hour durations; use an hourly manifest"
        )
    if (normalized["duration_minutes"] <= 0.0).any():
        raise ValueError("DR event durations must be positive")
    if (normalized["notice_minutes"] < 0.0).any():
        raise ValueError("DR event notices must be non-negative")
    if not normalized["reduction_fraction"].between(0.0, 1.0, inclusive="right").all():
        raise ValueError("DR event reduction_fraction must be in (0, 1]")
    if "requested_reduction_kw" in normalized.columns:
        normalized["requested_reduction_kw"] = pd.to_numeric(
            normalized["requested_reduction_kw"], errors="coerce"
        )
        if (
            normalized["requested_reduction_kw"].isna().any()
            or not np.isfinite(normalized["requested_reduction_kw"]).all()
            or (normalized["requested_reduction_kw"] < 0.0).any()
        ):
            raise ValueError("requested_reduction_kw must be finite and non-negative")
    normalized = normalized.sort_values("start_time", kind="stable").reset_index(drop=True)
    previous_end = normalized["end_time"].shift(1)
    if (normalized["start_time"] < previous_end).fillna(False).any():
        raise ValueError("hourly DR events must not overlap")
    return normalized


def select_dr_aligned_episode_start(
    community: pd.DataFrame,
    events: pd.DataFrame,
    *,
    total_hours: int,
    main_hours: int,
    seed: int,
    episode_start: str | None,
) -> str:
    """Choose a complete community window containing at least one manifest event."""

    timestamps = pd.to_datetime(community["timestamp"], utc=True).dt.tz_localize(None)
    event_starts = pd.to_datetime(events["start_time"])
    event_ends = pd.to_datetime(events["end_time"])
    timestamp_to_index = {timestamp: index for index, timestamp in enumerate(timestamps)}

    def is_valid_start(start: pd.Timestamp) -> bool:
        if start not in timestamp_to_index:
            return False
        start_index = timestamp_to_index[start]
        if start_index + total_hours > len(timestamps):
            return False
        expected_end = start + timedelta(hours=total_hours - 1)
        if timestamps.iloc[start_index + total_hours - 1] != expected_end:
            return False
        main_end = start + timedelta(hours=main_hours)
        return bool(((event_starts >= start) & (event_ends <= main_end)).any())

    if episode_start is not None:
        requested = pd.to_datetime(episode_start, utc=True).tz_localize(None)
        if not is_valid_start(requested):
            raise ValueError(
                "community.episode_start must begin a complete window containing at least "
                "one DR manifest event"
            )
        return requested.isoformat()
    starts = [timestamp for timestamp in timestamps if timestamp.hour == 0]
    candidates = [start for start in starts if is_valid_start(start)]
    if not candidates:
        raise ValueError("community profile and DR manifest have no compatible episode window")
    rng = np.random.default_rng(seed)
    return candidates[int(rng.integers(0, len(candidates)))].isoformat()


def make_synthetic_hourly_arrivals(
    *,
    hours: int,
    total_gpu_count: int,
    flexible_arrival_utilization: float,
    workload_mix: WorkloadMix,
    seed: int,
    deadline_ranges_h: Mapping[str, tuple[int, int]] = DEFAULT_DEADLINE_RANGES_H,
    deadline_slack_scale: float = 1.0,
    max_deadline_hours: int = 48,
) -> pd.DataFrame:
    """Generate reproducible flexible GPU-hour arrivals at hourly resolution.

    ``flexible_arrival_utilization`` scales the total potential AI arrival
    volume, after which the workload mix determines the schedulable share.
    Unlike the legacy total-utilization field, it does not also set rigid GPU
    power; rigid utilization is configured independently in the power model.
    """

    if isinstance(hours, bool) or not isinstance(hours, int) or hours <= 0:
        raise ValueError("hours must be a positive integer")
    if isinstance(total_gpu_count, bool) or not isinstance(total_gpu_count, int):
        raise TypeError("total_gpu_count must be an integer")
    if total_gpu_count <= 0:
        raise ValueError("total_gpu_count must be positive")
    utilization = _fraction(
        flexible_arrival_utilization,
        "flexible_arrival_utilization",
        allow_zero=False,
    )
    slack_scale = _positive_float(deadline_slack_scale, "deadline_slack_scale")
    if isinstance(max_deadline_hours, bool) or not isinstance(max_deadline_hours, int):
        raise TypeError("max_deadline_hours must be an integer")
    if max_deadline_hours <= 0:
        raise ValueError("max_deadline_hours must be positive")
    rng = np.random.default_rng(seed)
    hour_of_day = np.arange(hours, dtype="float64") % 24.0
    daily_shape = 0.82 + 0.18 * np.sin(2.0 * np.pi * (hour_of_day - 4.0) / 24.0)
    stochastic_shape = np.clip(rng.lognormal(mean=0.0, sigma=0.18, size=hours), 0.45, 2.2)
    shape = daily_shape * stochastic_shape
    shape /= float(shape.mean())
    total_gpu_h = total_gpu_count * utilization * shape
    records: list[dict[str, object]] = []
    for timestamp_index, total in enumerate(total_gpu_h):
        for job_class in workload_mix.shares:
            flexible_weight = workload_mix.flexible_class_share(job_class)
            if flexible_weight <= 0.0:
                continue
            bounds = deadline_ranges_h.get(job_class)
            if bounds is None:
                raise ValueError(f"deadline range missing for flexible class: {job_class}")
            minimum, maximum = bounds
            if minimum <= 0 or maximum < minimum:
                raise ValueError(f"invalid deadline range for {job_class}")
            records.append(
                {
                    "episode_id": timestamp_index // (24 * 7),
                    "timestamp_index": timestamp_index,
                    "job_class": job_class,
                    "priority_class": "LP",
                    "model_type": "synthetic",
                    "arrival_gpu_h": float(total * flexible_weight),
                    "slack_hours": max(
                        1,
                        min(
                            max_deadline_hours,
                            math.ceil(
                                int(rng.integers(minimum, maximum + 1)) * slack_scale
                            ),
                        ),
                    ),
                    "source_mode": "synthetic",
                }
            )
    return pd.DataFrame.from_records(
        records,
        columns=(
            "episode_id",
            "timestamp_index",
            "job_class",
            "priority_class",
            "model_type",
            "arrival_gpu_h",
            "slack_hours",
            "source_mode",
        ),
    )


def arrivals_for_hour(frame: pd.DataFrame, timestamp_index: int) -> list[HourlyArrival]:
    """Convert one scenario hour into queue arrivals without losing work."""

    rows = frame.loc[frame["timestamp_index"] == timestamp_index]
    records = rows.to_dict(orient="records")
    return [
        HourlyArrival(
            gpu_hours=float(record["arrival_gpu_h"]),
            slack_hours=float(record["slack_hours"]),
            job_class=str(record["job_class"]),
        )
        for record in records
        if float(record["arrival_gpu_h"]) > 0.0
    ]


def load_hourly_arrivals(path: str | Path) -> pd.DataFrame:
    """Load one pre-built hourly scenario and validate its V0 queue inputs."""

    frame = pd.read_parquet(path)
    missing = sorted(set(HOURLY_ARRIVAL_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"hourly arrivals are missing required columns: {missing}")
    normalized = frame.loc[:, HOURLY_ARRIVAL_COLUMNS].copy()
    normalized["timestamp_index"] = pd.to_numeric(normalized["timestamp_index"], errors="coerce")
    normalized["arrival_gpu_h"] = pd.to_numeric(normalized["arrival_gpu_h"], errors="coerce")
    normalized["slack_hours"] = pd.to_numeric(normalized["slack_hours"], errors="coerce")
    numeric = normalized[["timestamp_index", "arrival_gpu_h", "slack_hours"]]
    if numeric.isna().any().any():
        raise ValueError("hourly arrivals contain non-numeric queue values")
    if (normalized["timestamp_index"] < 0).any():
        raise ValueError("hourly arrival timestamp_index must be non-negative")
    if (normalized["arrival_gpu_h"] <= 0.0).any():
        raise ValueError("hourly arrival_gpu_h must be positive")
    if (normalized["slack_hours"] <= 0.0).any():
        raise ValueError("hourly arrival slack_hours must be positive")
    return normalized.astype(
        {
            "episode_id": "int64",
            "timestamp_index": "int64",
            "arrival_gpu_h": "float64",
            "slack_hours": "int64",
        }
    )
