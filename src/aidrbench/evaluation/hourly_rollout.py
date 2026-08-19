"""Shared rollout and KPI reporting for V0 hourly controllers."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import pandas as pd

from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv
from aidrbench.evaluation.firm_flexibility import (
    FirmFlexibilityCriteria,
    derive_event_outcomes,
)

HourlyAction = np.ndarray | int


class HourlyController(Protocol):
    """Minimal common interface for rules, MPC and trained RL policies."""

    name: str

    def act(
        self, env: HourlyCommunityAIDemandResponseEnv, info: dict[str, Any]
    ) -> HourlyAction: ...
KPI_TOLERANCE_KW = 1e-4
_CLASS_METRIC_PREFIXES = {
    "arrival_gpu_h_by_class": "arrived",
    "executed_gpu_h_by_class": "executed",
    "missed_gpu_h_by_class": "missed",
    "backlog_gpu_h_by_class": "backlog",
}


def _class_metric_columns(info: Mapping[str, Any]) -> dict[str, float]:
    """Flatten per-class queue accounting into stable Parquet column names."""

    columns: dict[str, float] = {}
    for info_key, prefix in _CLASS_METRIC_PREFIXES.items():
        values = info.get(info_key)
        if not isinstance(values, tuple):
            continue
        for job_class, value in values:
            normalized_class = re.sub(r"[^a-z0-9]+", "_", str(job_class).lower()).strip("_")
            if not normalized_class:
                raise ValueError("job class cannot normalize to an empty metric name")
            columns[f"{prefix}_{normalized_class}_gpu_h"] = float(value)
    return columns


def rollout_hourly_episode(
    env: HourlyCommunityAIDemandResponseEnv,
    controller: HourlyController,
    *,
    seed: int,
) -> tuple[pd.DataFrame, dict[str, float | int | str]]:
    """Run one reproducible episode and derive README section 22 KPIs."""

    reset = getattr(controller, "reset", None)
    if callable(reset):
        reset()
    _, info = env.reset(seed=seed)
    rows: list[dict[str, Any]] = []
    terminated = False
    truncated = False
    hour = 0
    while not (terminated or truncated):
        control_state = info.get("control_state")
        if not isinstance(control_state, Mapping):
            raise RuntimeError("hourly rollout is missing the causal control state")
        decision_metrics = {
            "decision_backlog_gpu_h": float(control_state["backlog_gpu_h"]),
            "decision_compute_debt_kwh": float(control_state["compute_debt_kwh"]),
            "decision_remaining_by_deadline_gpu_h": tuple(
                float(value)
                for value in control_state["remaining_by_deadline_gpu_h"]
            ),
            "decision_event_request_reference_kw": float(
                control_state["event_request_reference_kw"]
            ),
            "decision_event_notice_remaining_hours": float(
                control_state["event_notice_remaining_hours"]
            ),
        }
        action_start = time.perf_counter()
        action = controller.act(env, info)
        action_time_ms = (time.perf_counter() - action_start) * 1_000.0
        _, reward, terminated, truncated, info = env.step(action)
        rows.append(
            {
                "hour": hour,
                "reward": reward,
                "controller": controller.name,
                "controller_action_time_ms": action_time_ms,
                **decision_metrics,
                **{
                    key: value
                    for key, value in info.items()
                    if isinstance(value, bool | int | float | str)
                },
                **_class_metric_columns(info),
            }
        )
        hour += 1
    frame = pd.DataFrame.from_records(rows)
    if frame.empty:
        raise RuntimeError("hourly rollout unexpectedly produced no steps")
    main = frame.loc[~frame["is_clearance_tail"]]
    violations = main["limit_violation_kw"]
    reportable_violations = violations.where(violations > KPI_TOLERANCE_KW, 0.0)
    delivered_reduction_kw = (main["baseline_pcc_power_kw"] - main["pcc_power_kw"]).clip(lower=0.0)
    event_delivered_reduction_kw = delivered_reduction_kw.loc[main["event_active"]]
    requested_reduction_kw = (main["baseline_pcc_power_kw"] - main["pcc_limit_kw"]).clip(lower=0.0)
    terminal_backlog = float(frame["backlog_gpu_h"].iloc[-1])
    completed_gpu_h = float(frame["executed_gpu_h"].sum())
    total_arrival_gpu_h = float(frame["arrival_gpu_h"].sum())
    rebound_peak_kw = float(main["rebound_excess_kw"].max())
    peak_delivered_reduction_kw = (
        float(event_delivered_reduction_kw.max())
        if not event_delivered_reduction_kw.empty
        else 0.0
    )
    event_outcomes = derive_event_outcomes(
        frame,
        env.event_manifest,
        recovery_tolerance_gpu_h=(
            env.config.recovery_backlog_tolerance_fraction * env.power_model.flexible_capacity_gpu_h
        ),
    )
    delivery_ratios = np.asarray([outcome.delivery_ratio for outcome in event_outcomes])
    minimum_interval_delivery_ratios = np.asarray(
        [outcome.minimum_interval_delivery_ratio for outcome in event_outcomes]
    )
    window_reliefs = np.asarray([outcome.window_peak_relief_kw for outcome in event_outcomes])
    window_relief_fractions = np.asarray(
        [outcome.window_peak_relief_fraction for outcome in event_outcomes]
    )
    recovery_times = np.asarray(
        [
            outcome.recovery_time_h
            for outcome in event_outcomes
            if outcome.recovery_time_h is not None
        ]
    )
    rebound_ratios = np.asarray([outcome.rebound_ratio for outcome in event_outcomes])
    criteria = FirmFlexibilityCriteria()
    event_decisions = [outcome.success(criteria) for outcome in event_outcomes]
    firm_event_successes = sum(success for success, _ in event_decisions)
    failure_counts = {
        reason: sum(reason in failures for _, failures in event_decisions)
        for reason in (
            "delivery",
            "interval_delivery",
            "deadline",
            "rebound",
            "window_relief",
            "terminal_backlog",
        )
    }
    pcc_limit_compliance_rate = (
        float((reportable_violations.loc[main["event_active"]] <= 0.0).mean())
        if bool(main["event_active"].any())
        else 1.0
    )
    summary: dict[str, float | int | str] = {
        "controller": controller.name,
        "seed": seed,
        "episode_seed": int(frame["episode_seed"].iloc[0]),
        "hours": len(frame),
        "main_hours": len(main),
        "pcc_peak_kw": float(main["pcc_power_kw"].max()),
        "background_community_peak_kw": float(frame["background_community_peak_kw"].iloc[0]),
        "pcc_capacity_kw": float(frame["pcc_capacity_kw"].iloc[0]),
        "target_dc_peak_kw": float(frame["target_dc_peak_kw"].iloc[0]),
        "actual_dc_peak_kw": float(frame["actual_dc_peak_kw"].iloc[0]),
        "actual_dc_peak_fraction_of_pcc": float(
            frame["actual_dc_peak_fraction_of_pcc"].iloc[0]
        ),
        "dc_peak_sizing_error_kw": float(frame["dc_peak_sizing_error_kw"].iloc[0]),
        "scenario_provenance": str(frame["scenario_provenance"].iloc[0]),
        "frozen_scenario_id": str(frame["frozen_scenario_id"].iloc[0]),
        "frozen_scenario_hash": str(frame["frozen_scenario_hash"].iloc[0]),
        "gross_community_peak_kw": float(main["community_gross_power_kw"].max()),
        "net_community_peak_kw": float(main["community_power_kw"].max()),
        "peak_reduction_kw": peak_delivered_reduction_kw,
        "requested_peak_reduction_kw": float(requested_reduction_kw.max()),
        "capacity_violation_hours": int((reportable_violations > 0.0).sum()),
        "maximum_violation_kw": float(reportable_violations.max()),
        "energy_above_limit_kwh": float(reportable_violations.sum()),
        # Kept for compatibility; this is hourly PCC-limit compliance, not
        # the joint firm-flexibility success definition.
        "dr_success_rate": pcc_limit_compliance_rate,
        "pcc_limit_compliance_rate": pcc_limit_compliance_rate,
        "event_count": len(event_outcomes),
        "firm_event_successes": firm_event_successes,
        "firm_event_success_rate": (
            firm_event_successes / len(event_outcomes) if event_outcomes else 1.0
        ),
        **{f"{reason}_failure_count": count for reason, count in failure_counts.items()},
        "mean_event_delivery_ratio": float(delivery_ratios.mean()) if len(delivery_ratios) else 1.0,
        "min_event_delivery_ratio": float(delivery_ratios.min()) if len(delivery_ratios) else 1.0,
        "mean_event_minimum_interval_delivery_ratio": (
            float(minimum_interval_delivery_ratios.mean())
            if len(minimum_interval_delivery_ratios)
            else 1.0
        ),
        "minimum_interval_delivery_ratio": (
            float(minimum_interval_delivery_ratios.min())
            if len(minimum_interval_delivery_ratios)
            else 1.0
        ),
        "mean_window_peak_relief_kw": float(window_reliefs.mean()) if len(window_reliefs) else 0.0,
        "min_window_peak_relief_kw": float(window_reliefs.min()) if len(window_reliefs) else 0.0,
        "mean_window_peak_relief_fraction": (
            float(window_relief_fractions.mean()) if len(window_relief_fractions) else 1.0
        ),
        "min_window_peak_relief_fraction": (
            float(window_relief_fractions.min()) if len(window_relief_fractions) else 1.0
        ),
        "p95_recovery_time_h": (
            float(np.quantile(recovery_times, 0.95)) if len(recovery_times) else float("nan")
        ),
        "post_event_rebound_peak_kw": rebound_peak_kw,
        "rebound_ratio": float(rebound_ratios.max()) if len(rebound_ratios) else 0.0,
        "mean_event_rebound_ratio": (
            float(rebound_ratios.mean()) if len(rebound_ratios) else 0.0
        ),
        "max_event_rebound_ratio": float(rebound_ratios.max()) if len(rebound_ratios) else 0.0,
        "completed_flexible_gpu_h": completed_gpu_h,
        "deadline_miss_gpu_h": float(frame["missed_gpu_h"].sum()),
        "deadline_miss_rate": (
            float(frame["missed_gpu_h"].sum()) / total_arrival_gpu_h
            if total_arrival_gpu_h > 0.0
            else 0.0
        ),
        "mean_backlog_gpu_h": float(frame["backlog_gpu_h"].mean()),
        "max_backlog_gpu_h": float(frame["backlog_gpu_h"].max()),
        "mean_compute_debt_kwh": float(frame["compute_debt_kwh"].mean()),
        "max_compute_debt_kwh": float(frame["compute_debt_kwh"].max()),
        "unfinished_terminal_backlog_gpu_h": terminal_backlog,
        "terminal_backlog_excess_gpu_h": float(frame["terminal_backlog_excess_gpu_h"].iloc[-1]),
        "terminal_backlog_excess_fraction": (
            float(frame["terminal_backlog_excess_gpu_h"].iloc[-1]) / total_arrival_gpu_h
            if total_arrival_gpu_h > 0.0
            else 0.0
        ),
        "action_switching_l1": float(frame["action_fraction"].diff().abs().fillna(0.0).sum()),
        "total_dc_energy_kwh": float(frame["dc_energy_kwh"].sum()),
        "flexible_work_energy_kwh": float(frame["flexible_energy_kwh"].sum()),
        "gross_community_energy_kwh": float(
            frame["community_gross_power_kw"].sum() * env.config.timestep_hours
        ),
        "pv_generation_energy_kwh": float(
            frame["pv_generation_kw"].sum() * env.config.timestep_hours
        ),
        "net_community_energy_kwh": float(
            frame["community_power_kw"].sum() * env.config.timestep_hours
        ),
        "total_pcc_energy_kwh": float(
            frame["pcc_power_kw"].sum() * env.config.timestep_hours
        ),
        "energy_per_completed_gpu_h": (
            float(frame["flexible_energy_kwh"].sum()) / completed_gpu_h
            if completed_gpu_h > 0.0
            else 0.0
        ),
        "training_share": float(frame["training_share"].iloc[0]),
        "flexible_workload_share": float(frame["flexible_workload_share"].iloc[0]),
        "workload_source": env.config.workload_source,
        "community_source": str(frame["community_source"].iloc[0]),
        "community_profile_id": str(frame["community_profile_id"].iloc[0]),
        "community_episode_start": str(frame["community_episode_start"].iloc[0]),
        "dr_source": str(frame["dr_source"].iloc[0]),
        "dr_events_path": str(frame["dr_events_path"].iloc[0]),
        "arrivals_path": (
            str(env.config.alibaba_arrivals_path)
            if env.config.alibaba_arrivals_path is not None
            else "generated_in_memory"
        ),
        "forecast_assumption": getattr(controller, "forecast_assumption", "current_state_only"),
        "information_structure": getattr(controller, "information_structure", "undeclared"),
        "mean_controller_action_time_ms": float(frame["controller_action_time_ms"].mean()),
        "max_controller_action_time_ms": float(frame["controller_action_time_ms"].max()),
        "observation_version": env.observation_version,
        "reward_version": env.config.reward.version,
    }
    for column in sorted(str(column) for column in frame.columns):
        if not (column.startswith("executed_") and column.endswith("_gpu_h")):
            continue
        if column == "executed_gpu_h":
            continue
        job_class = column.removeprefix("executed_").removesuffix("_gpu_h")
        summary[f"completed_{job_class}_gpu_h"] = float(frame[column].sum())
    summary_metadata = getattr(controller, "summary_metadata", None)
    if callable(summary_metadata):
        extra_metadata = summary_metadata()
        overlap = sorted(set(summary).intersection(extra_metadata))
        if overlap:
            raise ValueError(f"controller summary metadata overlaps shared KPIs: {overlap}")
        summary.update(extra_metadata)
    return frame, summary


def save_hourly_rollout(
    frame: pd.DataFrame,
    summary: Mapping[str, float | int | str],
    output_directory: str | Path,
) -> dict[str, str]:
    """Persist the shared time series and scalar report for plotting later."""

    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    time_series_path = output / "timeseries.parquet"
    summary_path = output / "metrics.json"
    frame.to_parquet(time_series_path, index=False)
    summary_path.write_text(
        json.dumps(dict(summary), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"timeseries": str(time_series_path), "metrics": str(summary_path)}
