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
from aidrbench.evaluation.certification import (
    certify_firm_flexibility,
    make_certificate_scenario,
    summarize_candidate_outcomes,
)
from aidrbench.evaluation.firm_flexibility import (
    FirmFlexibilityCriteria,
    derive_event_outcomes,
    wilson_lower_bound,
)
from aidrbench.evaluation.hourly_rollout import rollout_hourly_episode

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/env/hourly_continuous.yaml"
TRAIN_CONFIG = ROOT / "configs/env/hourly_continuous_train.yaml"


def test_wilson_lower_bound_is_conservative_and_monotone() -> None:
    lower_all_success = wilson_lower_bound(10, 10, 0.95)
    lower_partial_success = wilson_lower_bound(8, 10, 0.95)

    assert 0.0 < lower_partial_success < lower_all_success < 1.0
    assert wilson_lower_bound(0, 10, 0.95) == 0.0


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


def test_certificate_uses_joint_success_and_one_sided_lower_bound() -> None:
    criteria = FirmFlexibilityCriteria(
        reliability_target=0.5,
        confidence_level=0.5,
        min_delivery_ratio=0.0,
        max_deadline_miss_rate=1.0,
        max_rebound_ratio=100.0,
        min_window_peak_relief_fraction=0.0,
        max_terminal_backlog_fraction=1.0,
    )

    certificate, candidates, outcomes = certify_firm_flexibility(
        config=CONFIG,
        controller="no_control",
        model_path=None,
        duration_h=2,
        candidate_reduction_fractions=(0.0,),
        seeds=(1, 2),
        criteria=criteria,
    )

    assert certificate.certified_reduction_kw == pytest.approx(0.0)
    assert certificate.success_rate_lower_ci >= criteria.reliability_target
    assert candidates.loc[0, "certified"]
    assert certificate.episode_count == 2
    assert certificate.event_count_per_episode == 3
    assert certificate.event_start_hours == (17, 65, 113)
    assert certificate.certificate_scope == "repeated_event_joint_episode"
    assert len(outcomes) == 6
    assert outcomes["success"].all()


def test_candidate_summary_counts_joint_episode_success_not_event_rows() -> None:
    criteria = FirmFlexibilityCriteria(reliability_target=0.5, confidence_level=0.5)
    outcomes = pd.DataFrame(
        {
            "seed": [1, 1, 2, 2],
            "candidate_reduction_kw": [10.0] * 4,
            "success": [True, False, True, True],
            "delivery_ratio": [1.0] * 4,
            "minimum_interval_delivery_ratio": [1.0] * 4,
            "deadline_miss_rate": [0.0] * 4,
            "rebound_ratio": [0.0] * 4,
            "window_peak_relief_kw": [10.0] * 4,
            "window_peak_relief_fraction": [1.0] * 4,
            "recovery_time_h": [0.0] * 4,
        }
    )

    summary = summarize_candidate_outcomes(outcomes, criteria=criteria, dc_peak_kw=100.0)

    assert summary["success_count"] == 1
    assert summary["episode_count"] == 2
    assert summary["event_count_per_episode"] == 2


def test_certificate_scenario_disables_training_randomization() -> None:
    scenario = make_certificate_scenario(
        TRAIN_CONFIG,
        duration_h=2,
        requested_reduction_kw=10.0,
    )
    dr = scenario["dr"]

    assert isinstance(dr, dict)
    assert dr["event_start_hours"] == [17, 65, 113]
    assert dr["event_start_jitter_hours"] == 4
    assert dr["event_duration_choices"] is None
    assert dr["event_notice_choices"] is None
    assert dr["event_notice_hours"] == 0
    assert dr["event_reduction_fraction_range"] is None
