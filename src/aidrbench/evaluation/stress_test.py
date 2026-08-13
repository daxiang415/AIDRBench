"""Repeated-event exhaustion tests based on per-event flexibility certificates."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path

import pandas as pd

from aidrbench.evaluation.certification import (
    ControllerName,
    _environment_for,
    _read_mapping,
    evaluate_flexibility_candidate,
    summarize_candidate_outcomes,
)
from aidrbench.evaluation.firm_flexibility import FirmFlexibilityCriteria


def make_repeated_event_start_hours(
    *,
    episode_days: int,
    events_per_day: int,
    duration_h: int,
    inter_event_gap_h: int,
    first_event_hour: int = 12,
) -> tuple[int, ...]:
    """Create one exact-gap event chain, rejecting physically impossible grids."""

    if min(episode_days, events_per_day, duration_h) <= 0 or inter_event_gap_h < 0:
        raise ValueError(
            "episode days, event count and duration must be positive; gap non-negative"
        )
    if first_event_hour < 0:
        raise ValueError("first_event_hour must be non-negative")
    event_count = episode_days * events_per_day
    starts = tuple(
        first_event_hour + index * (duration_h + inter_event_gap_h)
        for index in range(event_count)
    )
    if starts[-1] + duration_h > episode_days * 24:
        raise ValueError(
            "repeated-event grid does not fit the episode; "
            "reduce events-per-day/gap or increase episode days"
        )
    return starts


def run_repeated_event_stress_test(
    *,
    config: str | Path | Mapping[str, object],
    controllers: Sequence[ControllerName],
    model_paths: Mapping[str, str | Path],
    events_per_day: int,
    inter_event_gap_h: int,
    duration_h: int,
    candidate_reduction_fractions: Sequence[float],
    seeds: Sequence[int],
    criteria: FirmFlexibilityCriteria,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Certify flexibility at each ordinal event and quantify exhaustion.

    The same seed sees the same arrival/community/event sequence for every
    candidate and controller.  Thus the ratio of certified capacities is a
    state-history effect rather than a different-scenario comparison.
    """

    if not controllers:
        raise ValueError("stress test needs at least one controller")
    if not candidate_reduction_fractions:
        raise ValueError("stress test needs candidate reduction fractions")
    raw_config = _read_mapping(config)
    raw_env = raw_config.get("env")
    if not isinstance(raw_env, Mapping):
        raise ValueError("stress test config requires an env mapping")
    raw_episode_days = raw_env.get("episode_days")
    if isinstance(raw_episode_days, bool) or not isinstance(raw_episode_days, int):
        raise ValueError("env.episode_days must be an integer")
    starts = make_repeated_event_start_hours(
        episode_days=raw_episode_days,
        events_per_day=events_per_day,
        duration_h=duration_h,
        inter_event_gap_h=inter_event_gap_h,
    )
    fractions = sorted({float(value) for value in candidate_reduction_fractions})
    if not all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in fractions):
        raise ValueError("candidate reduction fractions must be in [0, 1]")
    all_outcomes: list[pd.DataFrame] = []
    certificate_rows: list[dict[str, object]] = []
    for controller in controllers:
        reference_env = _environment_for(raw_config, controller)
        dc_peak_kw = reference_env.power_model.predict(
            reference_env.power_model.flexible_capacity_gpu_h
        ).dc_power_kw
        controller_model = model_paths.get(controller)
        controller_outcomes: list[pd.DataFrame] = []
        for fraction in fractions:
            outcomes, _ = evaluate_flexibility_candidate(
                config=raw_config,
                controller=controller,
                model_path=controller_model,
                duration_h=duration_h,
                requested_reduction_kw=fraction * dc_peak_kw,
                seeds=seeds,
                criteria=criteria,
                event_start_hours=starts,
            )
            outcomes["event_ordinal"] = outcomes["event_id"].astype(int) + 1
            outcomes["candidate_reduction_fraction_of_dc_peak"] = fraction
            outcomes["events_per_day"] = events_per_day
            outcomes["inter_event_gap_h"] = inter_event_gap_h
            controller_outcomes.append(outcomes)
            all_outcomes.append(outcomes)
        all_controller = pd.concat(controller_outcomes, ignore_index=True)
        per_event: list[dict[str, float | int | str | bool]] = []
        for event_ordinal, event_rows in all_controller.groupby("event_ordinal", sort=True):
            candidate_rows: list[dict[str, float | int | bool]] = []
            for _, candidate_rows_frame in event_rows.groupby("candidate_reduction_kw", sort=True):
                candidate_rows.append(
                    summarize_candidate_outcomes(
                        candidate_rows_frame,
                        criteria=criteria,
                        dc_peak_kw=dc_peak_kw,
                    )
                )
            candidate_table = pd.DataFrame.from_records(candidate_rows).sort_values(
                "candidate_reduction_kw", ignore_index=True
            )
            certified = candidate_table.loc[candidate_table["certified"]]
            selected = certified.iloc[-1] if not certified.empty else candidate_table.iloc[0]
            per_event.append(
                {
                    "controller": controller,
                    "event_ordinal": int(str(event_ordinal)),
                    "duration_h": duration_h,
                    "events_per_day": events_per_day,
                    "inter_event_gap_h": inter_event_gap_h,
                    "dc_peak_kw": dc_peak_kw,
                    "certified_reduction_kw": (
                        float(selected["candidate_reduction_kw"]) if not certified.empty else 0.0
                    ),
                    "certified": not certified.empty,
                    "success_rate": float(selected["success_rate"]),
                    "success_rate_lower_ci": float(selected["success_rate_lower_ci"]),
                    "event_failure_probability": 1.0 - float(selected["success_rate"]),
                    "p95_recovery_time_h": float(selected["p95_recovery_time_h"]),
                }
            )
        per_event_table = pd.DataFrame.from_records(per_event)
        fresh = float(per_event_table["certified_reduction_kw"].iloc[0])
        per_event_table["residual_flexibility_ratio"] = (
            per_event_table["certified_reduction_kw"] / fresh if fresh > 1e-9 else math.nan
        )
        per_event_table["exhaustion"] = 1.0 - per_event_table["residual_flexibility_ratio"]
        certificate_rows.extend(
            {str(key): value for key, value in record.items()}
            for record in per_event_table.to_dict(orient="records")
        )
    return pd.DataFrame.from_records(certificate_rows), pd.concat(all_outcomes, ignore_index=True)


def save_repeated_event_stress_test(
    certificates: pd.DataFrame,
    outcomes: pd.DataFrame,
    *,
    output_directory: str | Path,
) -> dict[str, str]:
    """Persist event-ordinal certificates and raw success decisions."""

    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    certificates_path = output / "event_certificates.parquet"
    outcomes_path = output / "event_outcomes.parquet"
    manifest_path = output / "stress_test.json"
    certificates.to_parquet(certificates_path, index=False)
    outcomes.to_parquet(outcomes_path, index=False)
    manifest_path.write_text(
        json.dumps(
            {
                "event_certificates": str(certificates_path),
                "event_outcomes": str(outcomes_path),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "event_certificates": str(certificates_path),
        "event_outcomes": str(outcomes_path),
        "manifest": str(manifest_path),
    }
