from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from aidrbench.controllers.hourly_oracle import HourlyFullHorizonOracleController
from aidrbench.envs.community_ai_dr_env import ContinuousCommunityAIDemandResponseEnv
from aidrbench.evaluation.hourly_rollout import rollout_hourly_episode

ROOT = Path(__file__).resolve().parents[1]
VALIDATION_CONFIG = ROOT / "configs/env/hourly_continuous.yaml"


def test_planning_snapshot_baseline_matches_environment_no_control() -> None:
    env = ContinuousCommunityAIDemandResponseEnv(VALIDATION_CONFIG)
    env.reset(seed=20)
    snapshot = env.full_horizon_planning_snapshot()
    observed: list[float] = []

    for _ in range(env.config.total_hours):
        _, _, _, _, info = env.step(np.asarray((1.0,), dtype=np.float32))
        observed.append(float(info["pcc_power_kw"]))

    assert observed == pytest.approx(snapshot.baseline_pcc_power_kw, abs=1e-8)
    execution_by_class = dict(snapshot.baseline_execution_gpu_h_by_class)
    class_power = dict(snapshot.dynamic_kw_per_gpu_h_by_class)
    reconstructed = np.asarray(snapshot.community_power_kw) + snapshot.fixed_dc_power_kw
    reconstructed = reconstructed + sum(
        class_power[job_class] * np.asarray(execution_by_class[job_class])
        for job_class in snapshot.workload_classes
    )
    assert reconstructed == pytest.approx(snapshot.baseline_pcc_power_kw, abs=1e-8)
    assert snapshot.baseline_deadline_miss_gpu_h == pytest.approx(0.0)
    assert snapshot.baseline_terminal_backlog_gpu_h == pytest.approx(0.0)


def test_full_horizon_oracle_replays_with_all_bound_constraints() -> None:
    env = ContinuousCommunityAIDemandResponseEnv(VALIDATION_CONFIG)
    controller = HourlyFullHorizonOracleController()

    _, summary = rollout_hourly_episode(env, controller, seed=20)

    assert summary["event_count"] == 3
    assert summary["deadline_miss_rate"] <= env.config.reward.max_deadline_miss_rate
    assert summary["terminal_backlog_excess_fraction"] <= (
        env.config.reward.max_terminal_backlog_fraction
    )
    assert summary["perfect_information_status"] == "optimal"
    assert float(summary["perfect_information_capacity_kw"]) > float(
        summary["requested_peak_reduction_kw"]
    )
    assert 0.0 < float(
        summary["perfect_information_capacity_fraction_of_dynamic_range"]
    ) <= 1.0 + 1e-8
    assert float(summary["perfect_information_minimum_mean_delivery_ratio"]) >= (
        env.config.reward.min_delivery_ratio
    )
    assert float(summary["perfect_information_minimum_interval_delivery_ratio"]) >= (
        env.config.reward.min_delivery_ratio
    )
    assert float(summary["perfect_information_maximum_rebound_ratio"]) <= (
        env.config.reward.max_rebound_ratio
    )
    assert float(summary["perfect_information_minimum_window_relief_fraction"]) >= (
        env.config.reward.min_window_peak_relief_fraction
    )
    assert controller.solution is not None
    class_execution = dict(controller.solution.execution_gpu_h_by_class)
    assert np.asarray(controller.solution.execution_gpu_h) == pytest.approx(
        sum(np.asarray(values) for values in class_execution.values()),
        abs=1e-7,
    )
