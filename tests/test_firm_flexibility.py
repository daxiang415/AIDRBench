from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from aidrbench.controllers.hourly import make_hourly_controller
from aidrbench.envs.community_ai_dr_env import (
    ContinuousCommunityAIDemandResponseEnv,
    HourlyDREvent,
)
from aidrbench.evaluation.firm_flexibility import (
    FirmFlexibilityCriteria,
    derive_event_outcomes,
    lower_tolerance_order_statistic_rank,
    minimum_successes_for_wilson,
    wilson_lower_bound,
)
from aidrbench.evaluation.hourly_rollout import rollout_hourly_episode

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/env/hourly_continuous.yaml"


def test_wilson_lower_bound_is_conservative_and_monotone() -> None:
    lower_all_success = wilson_lower_bound(10, 10, 0.95)
    lower_partial_success = wilson_lower_bound(8, 10, 0.95)

    assert 0.0 < lower_partial_success < lower_all_success < 1.0
    assert wilson_lower_bound(0, 10, 0.95) == 0.0


def test_wilson_sample_size_gate_rejects_underpowered_q99_design() -> None:
    assert minimum_successes_for_wilson(100, 0.95, 0.95) == 99
    assert minimum_successes_for_wilson(100, 0.99, 0.95) is None
    assert minimum_successes_for_wilson(500, 0.99, 0.95) == 499


def test_exact_lower_tolerance_rank_accounts_for_selected_capacity() -> None:
    rank_95 = lower_tolerance_order_statistic_rank(100, 0.95, 0.95)
    rank_99_small = lower_tolerance_order_statistic_rank(100, 0.99, 0.95)
    rank_99_large = lower_tolerance_order_statistic_rank(500, 0.99, 0.95)

    assert rank_95 is not None and rank_95[0] == 2
    assert rank_95[1] >= 0.95
    assert rank_99_small is None
    assert rank_99_large is not None and rank_99_large[0] == 2


def test_rollout_exposes_compute_debt_and_rebound_aware_event_metrics() -> None:
    env = ContinuousCommunityAIDemandResponseEnv(CONFIG)

    frame, summary = rollout_hourly_episode(env, make_hourly_controller("threshold"), seed=3)
    outcomes = derive_event_outcomes(
        frame,
        env.event_manifest,
        recovery_tolerance_gpu_h=(
            env.config.recovery_backlog_tolerance_fraction
            * env.power_model.flexible_capacity_gpu_h
        ),
    )

    assert {"compute_debt_kwh", "delivery_ratio", "event_id", "p10_slack_h"} <= set(frame)
    assert len(outcomes) == len(env.event_manifest) == 3
    assert np.isfinite(frame["compute_debt_kwh"]).all()
    assert summary["event_count"] == 3
    assert "mean_window_peak_relief_kw" in summary
    assert "firm_event_success_rate" in summary
    assert "max_event_rebound_ratio" in summary
    assert summary["rebound_ratio"] == summary["max_event_rebound_ratio"]


def test_interval_delivery_prevents_average_only_success() -> None:
    frame = pd.DataFrame(
        {
            "hour": [0, 1, 2, 3, 4],
            "event_active": [True, True, True, True, False],
            "pcc_power_kw": [90.0, 90.0, 90.0, 92.0, 100.0],
            "baseline_pcc_power_kw": [100.0] * 5,
            "delivered_reduction_kw": [10.0, 10.0, 10.0, 8.0, 0.0],
            "requested_reduction_kw": [10.0, 10.0, 10.0, 10.0, 0.0],
            "backlog_gpu_h": [0.0] * 5,
            "baseline_backlog_gpu_h": [0.0] * 5,
            "missed_gpu_h": [0.0] * 5,
            "arrival_gpu_h": [1.0, 0.0, 0.0, 0.0, 0.0],
            "terminal_backlog_excess_gpu_h": [0.0] * 5,
        }
    )
    event = HourlyDREvent(
        event_id=0,
        source_event_id="test-event",
        start_hour=0,
        stop_hour=4,
        recovery_stop_hour=5,
        requested_reduction_kw=10.0,
        notice_hours=0.0,
    )

    outcome = derive_event_outcomes(
        frame,
        (event,),
        recovery_tolerance_gpu_h=0.0,
    )[0]
    success, failures = outcome.success(
        FirmFlexibilityCriteria(
            reliability_target=0.5,
            confidence_level=0.5,
            min_delivery_ratio=0.95,
            min_interval_delivery_ratio=0.95,
            max_deadline_miss_rate=1.0,
            max_rebound_ratio=1.0,
            min_window_peak_relief_fraction=0.0,
            max_terminal_backlog_fraction=1.0,
        )
    )

    assert outcome.delivery_ratio == pytest.approx(0.95)
    assert outcome.minimum_interval_delivery_ratio == pytest.approx(0.80)
    assert not success
    assert "interval_delivery" in failures
    assert "mean_delivery" not in failures


def test_zero_capacity_candidate_has_no_rebound_settlement_ratio() -> None:
    frame = pd.DataFrame(
        {
            "hour": [0, 1],
            "event_active": [True, False],
            "pcc_power_kw": [99.0, 110.0],
            "baseline_pcc_power_kw": [100.0, 100.0],
            "delivered_reduction_kw": [1.0, 0.0],
            "requested_reduction_kw": [0.0, 0.0],
            "backlog_gpu_h": [0.0, 0.0],
            "baseline_backlog_gpu_h": [0.0, 0.0],
            "missed_gpu_h": [0.0, 0.0],
            "arrival_gpu_h": [1.0, 0.0],
            "terminal_backlog_excess_gpu_h": [0.0, 0.0],
        }
    )
    event = HourlyDREvent(
        event_id=0,
        source_event_id="zero-capacity",
        start_hour=0,
        stop_hour=1,
        recovery_stop_hour=2,
        requested_reduction_kw=0.0,
        notice_hours=0.0,
    )

    outcome = derive_event_outcomes(frame, (event,), recovery_tolerance_gpu_h=0.0)[0]

    assert outcome.rebound_peak_kw == pytest.approx(10.0)
    assert outcome.rebound_ratio == pytest.approx(0.0)
