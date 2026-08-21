"""Alibaba GPU v2026 Lite summary preprocessing and arrival synthesis.

Lite data has no day/hour arrival order.  This module therefore produces
Alibaba-2026-calibrated *synthetic* hourly arrivals; it must never be presented
as a chronological replay of the production trace.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

_EPSILON = 1e-12
_CANONICAL_ALIASES: Mapping[str, tuple[str, ...]] = {
    "pod_id": ("pod_id",),
    "workload_id": ("workload_id",),
    "gpu_spec_public": ("gpu_spec_public", "gpu_type_public"),
    "priority_class": ("priority_class",),
    "job_type_public": ("job_type_public",),
    "model_type_public": ("model_type_public",),
    "gpu_request": ("gpu_request",),
    "duration_hours": ("duration_hours",),
}
SUMMARY_OUTPUT_COLUMNS = (
    "pod_id",
    "workload_id",
    "gpu_spec_public",
    "priority_class",
    "job_type_public",
    "model_type_public",
    "gpu_request",
    "duration_hours",
    "duration_hours_raw",
    "requested_work_gpu_h",
    "requested_work_gpu_h_raw",
    "duration_winsorized",
    "source_mode",
)
ARRIVAL_OUTPUT_COLUMNS = (
    "episode_id",
    "timestamp_index",
    "job_class",
    "priority_class",
    "model_type",
    "arrival_gpu_h",
    "slack_hours",
    "source_mode",
)


def _positive_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be positive")
    return result


def _fraction(
    value: object, name: str, *, allow_zero: bool = False, allow_one: bool = True
) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    upper_ok = result <= 1.0 if allow_one else result < 1.0
    lower_ok = result >= 0.0 if allow_zero else result > 0.0
    if not math.isfinite(result) or not lower_ok or not upper_ok:
        if allow_zero:
            interval = "[0, 1]" if allow_one else "[0, 1)"
        else:
            interval = "(0, 1]" if allow_one else "(0, 1)"
        raise ValueError(f"{name} must be in {interval}")
    return result


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _string_set(values: Sequence[str], name: str) -> frozenset[str]:
    normalized = frozenset(str(value).strip().lower() for value in values if str(value).strip())
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    return normalized


@dataclass(frozen=True, slots=True)
class DeadlineClassPolicy:
    """Scenario deadline policy for one class, not an Alibaba trace field."""

    minimum_slack_h: int
    maximum_slack_h: int
    multiplier_low: float
    multiplier_high: float

    def __post_init__(self) -> None:
        _positive_int(self.minimum_slack_h, "minimum_slack_h")
        _positive_int(self.maximum_slack_h, "maximum_slack_h")
        if self.maximum_slack_h < self.minimum_slack_h:
            raise ValueError("maximum_slack_h must be at least minimum_slack_h")
        _positive_float(self.multiplier_low, "multiplier_low")
        _positive_float(self.multiplier_high, "multiplier_high")
        if self.multiplier_high < self.multiplier_low:
            raise ValueError("multiplier_high must be at least multiplier_low")

    def sample_slack_hours(
        self,
        duration_hours: float,
        rng: np.random.Generator,
        *,
        slack_scale: float = 1.0,
        max_deadline_hours: int | None = None,
    ) -> int:
        duration = _positive_float(duration_hours, "duration_hours")
        scale = _positive_float(slack_scale, "slack_scale")
        multiplier = float(rng.uniform(self.multiplier_low, self.multiplier_high))
        base_slack = float(
            np.clip(
                multiplier * duration,
                self.minimum_slack_h,
                self.maximum_slack_h,
            )
        )
        upper = max_deadline_hours if max_deadline_hours is not None else self.maximum_slack_h
        _positive_int(upper, "max_deadline_hours")
        return max(1, min(int(upper), math.ceil(base_slack * scale)))


@dataclass(frozen=True, slots=True)
class AlibabaDeadlinePolicy:
    """README section 13 scenario policy for flexible Alibaba job classes."""

    training: DeadlineClassPolicy = DeadlineClassPolicy(6, 48, 2.0, 6.0)
    offline_inference: DeadlineClassPolicy = DeadlineClassPolicy(2, 24, 1.5, 4.0)

    def for_class(self, job_class: str) -> DeadlineClassPolicy:
        if job_class == "training":
            return self.training
        if job_class == "offline_inference":
            return self.offline_inference
        raise ValueError(f"no Alibaba deadline policy for job class: {job_class}")

    @classmethod
    def from_mapping(cls, value: object | None) -> AlibabaDeadlinePolicy:
        if value is None:
            return cls()
        if not isinstance(value, Mapping):
            raise ValueError("workload.deadline_policy must be a mapping")

        def parse(job_class: str, default: DeadlineClassPolicy) -> DeadlineClassPolicy:
            raw = value.get(job_class, {})
            if not isinstance(raw, Mapping):
                raise ValueError(f"deadline_policy.{job_class} must be a mapping")
            multipliers = raw.get(
                "slack_multiplier_range", [default.multiplier_low, default.multiplier_high]
            )
            if (
                not isinstance(multipliers, list)
                or len(multipliers) != 2
                or any(
                    isinstance(item, bool) or not isinstance(item, int | float)
                    for item in multipliers
                )
            ):
                raise ValueError(
                    f"deadline_policy.{job_class}.slack_multiplier_range must contain two numbers"
                )
            return DeadlineClassPolicy(
                minimum_slack_h=_positive_int(
                    raw.get("minimum_slack_h", default.minimum_slack_h),
                    f"deadline_policy.{job_class}.minimum_slack_h",
                ),
                maximum_slack_h=_positive_int(
                    raw.get("maximum_slack_h", default.maximum_slack_h),
                    f"deadline_policy.{job_class}.maximum_slack_h",
                ),
                multiplier_low=_positive_float(
                    multipliers[0], f"deadline_policy.{job_class}.slack_multiplier_range[0]"
                ),
                multiplier_high=_positive_float(
                    multipliers[1], f"deadline_policy.{job_class}.slack_multiplier_range[1]"
                ),
            )

        defaults = cls()
        return cls(
            training=parse("training", defaults.training),
            offline_inference=parse("offline_inference", defaults.offline_inference),
        )


def _resolve_summary_sources(columns: Iterable[str]) -> dict[str, str]:
    available = set(columns)
    sources: dict[str, str] = {}
    missing: list[str] = []
    for canonical, aliases in _CANONICAL_ALIASES.items():
        source = next((candidate for candidate in aliases if candidate in available), None)
        if source is None:
            missing.append(canonical)
        else:
            sources[canonical] = source
    if missing:
        raise ValueError(f"Alibaba v2026 summary is missing required columns: {missing}")
    return sources


def _canonicalize_summary_columns(frame: pd.DataFrame, sources: Mapping[str, str]) -> pd.DataFrame:
    renamed = {source: canonical for canonical, source in sources.items()}
    return frame.rename(columns=renamed).loc[:, list(_CANONICAL_ALIASES)].copy()


def _valid_summary_rows(frame: pd.DataFrame, sources: Mapping[str, str]) -> pd.DataFrame:
    canonical = _canonicalize_summary_columns(frame, sources)
    canonical["gpu_request"] = pd.to_numeric(canonical["gpu_request"], errors="coerce")
    canonical["duration_hours_raw"] = pd.to_numeric(canonical["duration_hours"], errors="coerce")
    numeric_mask = np.isfinite(canonical["gpu_request"].to_numpy(dtype="float64", na_value=np.nan))
    numeric_mask &= np.isfinite(
        canonical["duration_hours_raw"].to_numpy(dtype="float64", na_value=np.nan)
    )
    valid = canonical.loc[numeric_mask].copy()
    return valid.loc[(valid["gpu_request"] > 0.0) & (valid["duration_hours_raw"] > 0.0)].copy()


def _normalize_summary_rows(valid: pd.DataFrame, duration_cap: float | None) -> pd.DataFrame:
    normalized = valid.copy()
    normalized["duration_hours"] = normalized["duration_hours_raw"].astype("float64")
    if duration_cap is not None:
        normalized["duration_hours"] = normalized["duration_hours_raw"].clip(upper=duration_cap)
    normalized["duration_winsorized"] = (
        normalized["duration_hours"] < normalized["duration_hours_raw"]
    )
    normalized["requested_work_gpu_h"] = normalized["gpu_request"] * normalized["duration_hours"]
    normalized["requested_work_gpu_h_raw"] = (
        normalized["gpu_request"] * normalized["duration_hours_raw"]
    )
    for column in (
        "pod_id",
        "workload_id",
        "gpu_spec_public",
        "priority_class",
        "job_type_public",
        "model_type_public",
    ):
        normalized[column] = (
            normalized[column].astype("string").fillna("unknown").str.strip().str.lower()
        )
    for column in (
        "gpu_request",
        "duration_hours",
        "duration_hours_raw",
        "requested_work_gpu_h",
        "requested_work_gpu_h_raw",
    ):
        normalized[column] = normalized[column].astype("float64")
    normalized["source_mode"] = "alibaba2026_summary"
    return normalized.loc[:, SUMMARY_OUTPUT_COLUMNS].reset_index(drop=True)


def preprocess_alibaba_summary(
    input_path: str | Path,
    output_path: str | Path,
    *,
    winsorize_quantile: float | None = 0.995,
) -> dict[str, object]:
    """Normalize a v2026 summary while retaining its raw duration tail.

    The output's ``duration_hours`` may be winsorized for the main scenario;
    ``duration_hours_raw`` and ``requested_work_gpu_h_raw`` remain available
    for a long-tail sensitivity analysis.
    """

    if winsorize_quantile is not None:
        _fraction(winsorize_quantile, "winsorize_quantile")
    source = Path(input_path)
    parquet_file = pq.ParquetFile(source)
    sources = _resolve_summary_sources(parquet_file.schema.names)
    source_columns = list(dict.fromkeys(sources.values()))
    metadata = parquet_file.metadata
    input_rows = metadata.num_rows if metadata is not None else 0
    duration_cap: float | None = None
    if winsorize_quantile is not None and winsorize_quantile < 1.0:
        durations: list[np.ndarray] = []
        for batch in parquet_file.iter_batches(
            columns=[sources["gpu_request"], sources["duration_hours"]], batch_size=250_000
        ):
            values = batch.to_pandas()
            gpu_request = pd.to_numeric(values[sources["gpu_request"]], errors="coerce")
            duration = pd.to_numeric(values[sources["duration_hours"]], errors="coerce")
            valid_mask = np.isfinite(gpu_request.to_numpy(dtype="float64", na_value=np.nan))
            valid_mask &= np.isfinite(duration.to_numpy(dtype="float64", na_value=np.nan))
            valid_mask &= gpu_request.to_numpy(dtype="float64", na_value=np.nan) > 0.0
            valid_mask &= duration.to_numpy(dtype="float64", na_value=np.nan) > 0.0
            if valid_mask.any():
                durations.append(duration.to_numpy(dtype="float64", na_value=np.nan)[valid_mask])
        if not durations:
            raise ValueError("Alibaba v2026 summary has no finite positive GPU jobs")
        duration_cap = float(np.quantile(np.concatenate(durations), winsorize_quantile))
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    writer: pq.ParquetWriter | None = None
    output_rows = 0
    winsorized_rows = 0
    try:
        for batch in parquet_file.iter_batches(columns=source_columns, batch_size=250_000):
            valid = _valid_summary_rows(batch.to_pandas(), sources)
            normalized = _normalize_summary_rows(valid, duration_cap)
            if normalized.empty:
                continue
            table = pa.Table.from_pandas(normalized, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(destination, table.schema, compression="snappy")
            writer.write_table(table)
            output_rows += len(normalized)
            winsorized_rows += int(normalized["duration_winsorized"].sum())
    finally:
        if writer is not None:
            writer.close()
    if writer is None:
        raise ValueError("Alibaba v2026 summary has no finite positive GPU jobs")
    return {
        "dataset": "alibaba_gpu_v2026_summary",
        "input_rows": input_rows,
        "output_rows": output_rows,
        "dropped_rows": input_rows - output_rows,
        "winsorize_quantile": winsorize_quantile,
        "duration_cap_hours": duration_cap,
        "winsorized_rows": winsorized_rows,
        "deadline_is_synthetic": True,
        "source_mode": "alibaba2026_calibrated_synthetic",
        "output": str(destination),
    }


def _hourly_intensity(hours: int, rng: np.random.Generator, arrival_process: str) -> np.ndarray:
    hour_of_day = np.arange(hours, dtype="float64") % 24.0
    base = 0.78 + 0.22 * np.sin(2.0 * np.pi * (hour_of_day - 4.0) / 24.0)
    if arrival_process == "nhpp":
        variation = rng.lognormal(mean=0.0, sigma=0.20, size=hours)
    elif arrival_process == "block":
        block_count = math.ceil(hours / 4)
        blocks = rng.lognormal(mean=0.0, sigma=0.45, size=block_count)
        variation = np.repeat(blocks, 4)[:hours]
    else:
        raise ValueError("arrival_process must be 'nhpp' or 'block'")
    intensity = base * variation
    return intensity / float(intensity.mean())


def make_alibaba_lite_sampler_pool(
    summary_path: str | Path,
    output_path: str | Path,
    *,
    job_classes: Sequence[str] = ("training", "offline_inference"),
    priorities: Sequence[str] = ("lp",),
    rows_per_stratum: int = 50_000,
    seed: int = 2026,
    batch_size: int = 262_144,
) -> dict[str, object]:
    """Build a bounded uniform empirical sampler without loading the full summary.

    Random keys are assigned while Parquet batches are streamed. Keeping the
    smallest keys per class/priority stratum gives a fixed-size uniform sample
    while preserving within-row duration, GPU demand, and work relationships.
    """

    quota = _positive_int(rows_per_stratum, "rows_per_stratum")
    chunk_size = _positive_int(batch_size, "batch_size")
    selected_classes = _string_set(job_classes, "job_classes")
    selected_priorities = _string_set(priorities, "priorities")
    source = Path(summary_path)
    if not source.is_file():
        raise FileNotFoundError(f"Alibaba Lite summary does not exist: {source}")
    parquet = pq.ParquetFile(source)
    missing = sorted(set(SUMMARY_OUTPUT_COLUMNS) - set(parquet.schema.names))
    if missing:
        raise ValueError(f"Alibaba Lite summary is missing sampler columns: {missing}")

    rng = np.random.default_rng(seed)
    reservoirs: dict[tuple[str, str], pd.DataFrame] = {}
    eligible_counts: dict[tuple[str, str], int] = {}
    for batch in parquet.iter_batches(batch_size=chunk_size, columns=list(SUMMARY_OUTPUT_COLUMNS)):
        frame = pa.Table.from_batches([batch]).to_pandas()
        job_type = frame["job_type_public"].astype("string").str.lower()
        priority = frame["priority_class"].astype("string").str.lower()
        eligible = frame.loc[job_type.isin(selected_classes) & priority.isin(selected_priorities)]
        if eligible.empty:
            continue
        eligible = eligible.copy()
        eligible["_sample_key"] = rng.random(len(eligible))
        for raw_key, group in eligible.groupby(
            ["job_type_public", "priority_class"], sort=False, observed=True
        ):
            key = (str(raw_key[0]).lower(), str(raw_key[1]).lower())
            eligible_counts[key] = eligible_counts.get(key, 0) + len(group)
            previous = reservoirs.get(key)
            combined = (
                group if previous is None else pd.concat((previous, group), ignore_index=True)
            )
            reservoirs[key] = combined.nsmallest(quota, "_sample_key").reset_index(drop=True)

    expected = {
        (job_class, priority)
        for job_class in selected_classes
        for priority in selected_priorities
    }
    missing_strata = sorted(expected - set(reservoirs))
    if missing_strata:
        raise ValueError(f"Alibaba Lite summary has no rows for sampler strata: {missing_strata}")
    sampled = pd.concat(
        [reservoirs[key].drop(columns="_sample_key") for key in sorted(reservoirs)],
        ignore_index=True,
    ).loc[:, SUMMARY_OUTPUT_COLUMNS]
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sampled.to_parquet(destination, index=False)
    return {
        "dataset": "alibaba_gpu_v2026_summary_sampler_pool",
        "source": str(source),
        "output": str(destination),
        "rows": len(sampled),
        "rows_per_stratum": quota,
        "seed": seed,
        "job_classes": sorted(selected_classes),
        "priorities": sorted(selected_priorities),
        "eligible_rows_by_stratum": {
            f"{job_class}/{priority}": count
            for (job_class, priority), count in sorted(eligible_counts.items())
        },
        "sampled_rows_by_stratum": {
            f"{job_class}/{priority}": len(frame)
            for (job_class, priority), frame in sorted(reservoirs.items())
        },
        "sampling_method": "streaming_uniform_random_key_top_k_per_stratum",
    }


@lru_cache(maxsize=2)
def _read_normalized_summary(resolved_path: str) -> pd.DataFrame:
    """Read one preprocessed Lite summary once per process and source file."""

    frame = pd.read_parquet(resolved_path)
    missing = sorted(set(SUMMARY_OUTPUT_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(
            "Alibaba Lite arrival generation requires preprocess-alibaba-summary output; "
            f"missing columns: {missing}"
        )
    return frame.loc[:, SUMMARY_OUTPUT_COLUMNS].copy()


def _load_normalized_summary(path: str | Path) -> pd.DataFrame:
    # Callers only filter/reset-index the frame; keeping the cached object
    # read-only avoids reloading a 40-million-row summary for every Gym reset.
    return _read_normalized_summary(str(Path(path).resolve()))


def make_alibaba_lite_hourly_arrivals(
    summary_path: str | Path,
    *,
    hours: int,
    total_gpu_count: int,
    flexible_arrival_utilization: float,
    workload_shares: Mapping[str, float],
    flexible_fractions: Mapping[str, float],
    flexible_priorities: Sequence[str] = ("lp",),
    deadline_policy: AlibabaDeadlinePolicy | None = None,
    deadline_slack_scale: float = 1.0,
    max_deadline_hours: int = 48,
    arrival_process: str = "nhpp",
    seed: int,
) -> pd.DataFrame:
    """Sample trace-calibrated synthetic flexible arrivals at hourly resolution.

    Each hour/class total is scaled to the target virtual data-center GPU-hour
    demand. The sampled records retain the empirical ``gpu_request`` and
    ``duration_hours`` relationship only as a workload-shape distribution;
    their absolute Alibaba-cluster volume is never replayed.
    """

    _positive_int(hours, "hours")
    _positive_int(total_gpu_count, "total_gpu_count")
    utilization = _fraction(
        flexible_arrival_utilization,
        "flexible_arrival_utilization",
    )
    slack_scale = _positive_float(deadline_slack_scale, "deadline_slack_scale")
    _positive_int(max_deadline_hours, "max_deadline_hours")
    if set(workload_shares) != set(flexible_fractions):
        raise ValueError("workload_shares and flexible_fractions must have the same classes")
    shares = {
        name: _fraction(value, f"workload share for {name}", allow_zero=True)
        for name, value in workload_shares.items()
    }
    flexible = {
        name: _fraction(value, f"flexible fraction for {name}", allow_zero=True)
        for name, value in flexible_fractions.items()
    }
    if not math.isclose(sum(shares.values()), 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("workload_shares must sum to 1.0")
    priorities = _string_set(flexible_priorities, "flexible_priorities")
    policy = deadline_policy or AlibabaDeadlinePolicy()
    summary = _load_normalized_summary(summary_path)
    rng = np.random.default_rng(seed)
    intensity = _hourly_intensity(hours, rng, arrival_process)
    total_hourly_gpu_h = total_gpu_count * utilization * intensity
    records: list[dict[str, object]] = []
    for job_class, share in shares.items():
        flexible_share = share * flexible[job_class]
        if flexible_share <= _EPSILON:
            continue
        class_policy = policy.for_class(job_class)
        candidates = summary.loc[
            (summary["job_type_public"] == job_class) & (summary["priority_class"].isin(priorities))
        ].reset_index(drop=True)
        if candidates.empty:
            raise ValueError(
                "Alibaba Lite summary has no rows for configured flexible class/priority: "
                f"{job_class}/{sorted(priorities)}"
            )
        representative_work = float(candidates["requested_work_gpu_h"].median())
        if representative_work <= _EPSILON:
            raise ValueError(f"Alibaba Lite summary has invalid requested work for {job_class}")
        for timestamp_index, total_work in enumerate(total_hourly_gpu_h):
            target_work = float(total_work * flexible_share)
            if target_work <= _EPSILON:
                continue
            job_count = max(1, int(rng.poisson(target_work / representative_work)))
            selected_indices = rng.integers(0, len(candidates), size=job_count)
            selected = candidates.iloc[selected_indices]
            raw_work = selected["requested_work_gpu_h"].to_numpy(dtype="float64")
            scale = target_work / float(raw_work.sum())
            for row, arrival_gpu_h in zip(
                selected.to_dict(orient="records"), raw_work * scale, strict=True
            ):
                records.append(
                    {
                        "episode_id": timestamp_index // (24 * 7),
                        "timestamp_index": timestamp_index,
                        "job_class": job_class,
                        "priority_class": str(row["priority_class"]),
                        "model_type": str(row["model_type_public"]),
                        "arrival_gpu_h": float(arrival_gpu_h),
                        "slack_hours": class_policy.sample_slack_hours(
                            float(row["duration_hours"]),
                            rng,
                            slack_scale=slack_scale,
                            max_deadline_hours=max_deadline_hours,
                        ),
                        "source_mode": "alibaba2026_lite_calibrated_synthetic",
                    }
                )
    result = pd.DataFrame.from_records(records, columns=ARRIVAL_OUTPUT_COLUMNS)
    if result.empty:
        raise ValueError("Alibaba Lite arrival generation produced no flexible arrivals")
    return result.astype(
        {
            "episode_id": "int64",
            "timestamp_index": "int64",
            "arrival_gpu_h": "float64",
            "slack_hours": "int64",
        }
    )


def write_alibaba_lite_hourly_arrivals(
    summary_path: str | Path,
    output_path: str | Path,
    **kwargs: Any,
) -> dict[str, object]:
    """Generate and persist one Lite arrival frame with source-safe metadata."""

    arrivals = make_alibaba_lite_hourly_arrivals(summary_path, **kwargs)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    arrivals.to_parquet(destination, index=False)
    return {
        "source_mode": "alibaba2026_lite_calibrated_synthetic",
        "rows": len(arrivals),
        "hours": int(arrivals["timestamp_index"].max()) + 1,
        "arrival_gpu_h": float(arrivals["arrival_gpu_h"].sum()),
        "output": str(destination),
    }
