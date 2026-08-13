from __future__ import annotations

from pathlib import Path

import gymnasium as gym
import numpy as np
import pandas as pd
import pytest
import yaml
from gymnasium.utils.env_checker import check_env

from aidrbench.envs.community_ai_dr_env import (
    ContinuousCommunityAIDemandResponseEnv,
)
from aidrbench.envs.registration import (
    CONTINUOUS_ENV_ID,
    DISCRETE_ENV_ID,
    register_environments,
)
from aidrbench.workloads.deadline_buckets import HourlyArrival

ROOT = Path(__file__).resolve().parents[1]
CONTINUOUS_CONFIG = ROOT / "configs/env/hourly_continuous.yaml"
DISCRETE_CONFIG = ROOT / "configs/env/hourly_discrete.yaml"
TRAIN_CONFIG = ROOT / "configs/env/hourly_continuous_train.yaml"


@pytest.mark.parametrize(
    ("environment_id", "config_path"),
    (
        (CONTINUOUS_ENV_ID, CONTINUOUS_CONFIG),
        (DISCRETE_ENV_ID, DISCRETE_CONFIG),
    ),
)
def test_hourly_environment_passes_gymnasium_checker(
    environment_id: str,
    config_path: Path,
) -> None:
    register_environments()
    env = gym.make(environment_id, config=config_path)

    check_env(env.unwrapped)


def test_registered_hourly_environments_construct_through_gymnasium() -> None:
    register_environments()

    continuous = gym.make(CONTINUOUS_ENV_ID, config=CONTINUOUS_CONFIG)
    discrete = gym.make(DISCRETE_ENV_ID, config=DISCRETE_CONFIG)

    assert continuous.action_space.shape == (1,)
    assert discrete.action_space.n == 5


def test_zero_action_defers_and_full_action_executes_flexible_work() -> None:
    zero_env = ContinuousCommunityAIDemandResponseEnv(CONTINUOUS_CONFIG)
    full_env = ContinuousCommunityAIDemandResponseEnv(CONTINUOUS_CONFIG)
    zero_env.reset(seed=11)
    full_env.reset(seed=11)

    _, _, _, _, zero_info = zero_env.step(np.asarray((0.0,), dtype=np.float32))
    _, _, _, _, full_info = full_env.step(np.asarray((1.0,), dtype=np.float32))

    assert zero_info["arrival_gpu_h"] > 0.0
    assert zero_info["executed_gpu_h"] == pytest.approx(0.0)
    assert full_info["executed_gpu_h"] > 0.0
    assert full_info["backlog_gpu_h"] < zero_info["backlog_gpu_h"]


def test_tail_has_no_new_arrivals_and_conservation_holds() -> None:
    env = ContinuousCommunityAIDemandResponseEnv(CONTINUOUS_CONFIG)
    _, _ = env.reset(seed=4)
    final_info: dict[str, object] = {}
    for index in range(env.config.total_hours):
        _, _, _, truncated, final_info = env.step(np.asarray((1.0,), dtype=np.float32))
        if index >= env.config.main_hours:
            assert final_info["arrival_gpu_h"] == pytest.approx(0.0)
    assert truncated
    assert final_info["conservation_error_gpu_h"] == pytest.approx(0.0, abs=1e-8)
    assert final_info["training_share"] == pytest.approx(0.50)
    assert final_info["flexible_workload_share"] == pytest.approx(0.74)


def test_control_state_exposes_urgency_and_hourly_load_forecast() -> None:
    env = ContinuousCommunityAIDemandResponseEnv(CONTINUOUS_CONFIG)
    _, reset_info = env.reset(seed=12)

    state = reset_info["control_state"]

    assert len(state["deadline_bucket_gpu_h"]) == 8
    assert state["urgent_gpu_h"] == pytest.approx(0.0)
    assert len(state["remaining_by_deadline_gpu_h"]) == env.config.max_deadline_hours
    assert len(state["deadline_feasibility_ratio"]) == 8
    assert len(state["community_forecast_kw"]) == env.config.forecast_horizon_hours + 1
    assert len(state["pcc_limit_forecast_kw"]) == env.config.forecast_horizon_hours + 1


def test_hourly_arrivals_are_observable_before_the_action() -> None:
    env = ContinuousCommunityAIDemandResponseEnv(CONTINUOUS_CONFIG)
    _, reset_info = env.reset(seed=12)
    initial_backlog = float(reset_info["control_state"]["backlog_gpu_h"])

    _, _, _, _, info = env.step(np.asarray((0.0,), dtype=np.float32))

    assert initial_backlog > 0.0
    assert info["arrival_gpu_h"] == pytest.approx(initial_backlog)


def test_deadline_feasibility_normalization_has_unit_capacity_boundary() -> None:
    env = ContinuousCommunityAIDemandResponseEnv(CONTINUOUS_CONFIG)
    env.reset(seed=12)
    env._queue.reset()
    env._baseline_queue.reset()
    env._queue.add(
        [
            HourlyArrival(env._capacity_gpu_h, 1.0),
            HourlyArrival(env._capacity_gpu_h, 2.0),
        ]
    )

    observation = dict(zip(env.observation_feature_names, env.current_observation, strict=True))

    assert observation["deadline_feasibility_0h"] == pytest.approx(1.0)
    assert observation["deadline_feasibility_1h"] == pytest.approx(1.0)
    assert observation["excess_deadline_feasibility_0h"] == pytest.approx(1.0)
    assert observation["excess_deadline_feasibility_1h"] == pytest.approx(1.0)


def test_observation_is_scale_invariant_for_proportional_virtual_fleets() -> None:
    small_config = yaml.safe_load(CONTINUOUS_CONFIG.read_text(encoding="utf-8"))
    large_config = yaml.safe_load(CONTINUOUS_CONFIG.read_text(encoding="utf-8"))
    small_config["virtual_datacenter"]["node_count"] = 2
    large_config["virtual_datacenter"]["node_count"] = 4
    small_config["community"]["target_peak_kw"] = 1_000.0
    large_config["community"]["target_peak_kw"] = 2_000.0
    small = ContinuousCommunityAIDemandResponseEnv(small_config)
    large = ContinuousCommunityAIDemandResponseEnv(large_config)

    small_observation, _ = small.reset(seed=3)
    large_observation, _ = large.reset(seed=3)

    assert small.observation_version == large.observation_version == "firm_v4"
    assert small.observation_space.shape == large.observation_space.shape == (63,)
    assert np.allclose(small_observation, large_observation, atol=1e-7)
    for _ in range(24):
        action = np.asarray((0.75,), dtype=np.float32)
        small_observation, small_reward, _, _, _ = small.step(action)
        large_observation, large_reward, _, _, _ = large.step(action)
        assert np.allclose(small_observation, large_observation, atol=1e-6)
        assert small_reward == pytest.approx(large_reward, abs=1e-8)


def test_recovery_and_running_window_state_are_observable() -> None:
    env = ContinuousCommunityAIDemandResponseEnv(CONTINUOUS_CONFIG)
    env.reset(seed=12)
    first_event = env.event_manifest[0]
    observation = env.current_observation
    for hour in range(first_event.stop_hour):
        action = 0.0 if hour >= first_event.start_hour else 1.0
        observation, _, _, _, _ = env.step(np.asarray((action,), dtype=np.float32))
    state = dict(zip(env.observation_feature_names, observation, strict=True))

    assert state["event_active"] == pytest.approx(0.0)
    assert state["recovery_active"] == pytest.approx(1.0)
    assert state["event_window_active"] == pytest.approx(1.0)
    assert state["recovery_remaining_fraction"] > 0.0
    assert state["event_request_fraction"] > 0.0
    assert state["running_window_baseline_peak_fraction"] > 0.0
    assert state["running_window_pcc_peak_fraction"] > 0.0


def test_event_state_exposes_compute_debt_and_explicit_delivery_request() -> None:
    env = ContinuousCommunityAIDemandResponseEnv(CONTINUOUS_CONFIG)
    env.reset(seed=12)
    info: dict[str, object] = {}
    for _ in range(18):
        _, _, _, _, info = env.step(np.asarray((0.0,), dtype=np.float32))

    assert info["event_active"]
    assert info["event_id"] == 0
    assert float(info["requested_reduction_kw"]) > 0.0
    assert float(info["compute_debt_kwh"]) > 0.0
    assert "p10_slack_h" in info


def test_reward_prefers_delivering_an_active_dr_request() -> None:
    responding_env = ContinuousCommunityAIDemandResponseEnv(CONTINUOUS_CONFIG)
    ignoring_env = ContinuousCommunityAIDemandResponseEnv(CONTINUOUS_CONFIG)
    responding_env.reset(seed=12)
    ignoring_env.reset(seed=12)
    event_start = responding_env.event_manifest[0].start_hour
    for _ in range(event_start):
        responding_env.step(np.asarray((1.0,), dtype=np.float32))
        ignoring_env.step(np.asarray((1.0,), dtype=np.float32))

    _, responding_reward, _, _, responding_info = responding_env.step(
        np.asarray((0.0,), dtype=np.float32)
    )
    _, ignoring_reward, _, _, ignoring_info = ignoring_env.step(
        np.asarray((1.0,), dtype=np.float32)
    )

    assert (
        responding_info["dr_tracking_error_fraction"] < ignoring_info["dr_tracking_error_fraction"]
    )
    assert responding_reward > ignoring_reward
    assert responding_info["backlog_excess_gpu_h"] >= 0.0
    assert responding_info["delivery_violation_cost"] == pytest.approx(0.0)
    assert ignoring_info["delivery_violation_cost"] > 1.0
    assert responding_reward == pytest.approx(-responding_info["reward_penalty"])


def test_reward_reports_independent_threshold_normalized_costs() -> None:
    env = ContinuousCommunityAIDemandResponseEnv(CONTINUOUS_CONFIG)
    env.reset(seed=12)
    _, reward, _, _, info = env.step(np.asarray((0.0,), dtype=np.float32))

    cost_names = {
        "delivery_violation_cost",
        "deadline_feasibility_violation_cost",
        "deadline_violation_cost",
        "rebound_violation_cost",
        "window_relief_violation_cost",
        "terminal_backlog_violation_cost",
        "excess_backlog_shaping_cost",
        "switching_cost",
    }
    assert info["reward_version"] == "firm_threshold_v2"
    assert all(float(info[name]) >= 0.0 for name in cost_names)
    assert reward == pytest.approx(-float(info["reward_penalty"]))


def test_explicit_seed_is_reproducible_but_auto_reset_samples_new_training_episode() -> None:
    env = ContinuousCommunityAIDemandResponseEnv(CONTINUOUS_CONFIG)

    seeded_a, _ = env.reset(seed=21)
    seeded_b, _ = env.reset(seed=21)
    automatic_a, _ = env.reset()
    automatic_b, _ = env.reset()

    assert np.array_equal(seeded_a, seeded_b)
    assert not np.array_equal(automatic_a, automatic_b)


def test_training_distribution_samples_dr_duration_and_request_by_seed() -> None:
    env = ContinuousCommunityAIDemandResponseEnv(TRAIN_CONFIG)

    env.reset(seed=1)
    events_a = env.event_manifest
    env.reset(seed=2)
    events_b = env.event_manifest

    assert all(1 <= event.stop_hour - event.start_hour <= 4 for event in events_a)
    assert all(1 <= event.stop_hour - event.start_hour <= 4 for event in events_b)
    assert all(event.notice_hours in {0.0, 2.0, 4.0, 6.0} for event in events_a + events_b)
    assert events_a != events_b


def test_training_notice_is_observable_before_configured_event() -> None:
    env = ContinuousCommunityAIDemandResponseEnv(TRAIN_CONFIG)
    env.reset(seed=1)
    noticed_event = next(event for event in env.event_manifest if event.notice_hours > 0.0)
    info: dict[str, object] = {}
    for _ in range(noticed_event.start_hour - int(noticed_event.notice_hours) + 1):
        _, _, _, _, info = env.step(np.asarray((1.0,), dtype=np.float32))

    assert not info["event_active"]
    assert info["event_notice_remaining_hours"] == pytest.approx(noticed_event.notice_hours)


def test_configured_episode_seed_range_is_enforced() -> None:
    config = yaml.safe_load(CONTINUOUS_CONFIG.read_text(encoding="utf-8"))
    config["env"]["episode_seed_range"] = [100, 199]
    env = ContinuousCommunityAIDemandResponseEnv(config)

    _, mapped = env.reset(seed=7)
    _, direct = env.reset(seed=150)
    _, automatic = env.reset()

    assert mapped["episode_seed"] == 107
    assert direct["episode_seed"] == 150
    assert 100 <= automatic["episode_seed"] <= 199


def test_environment_uses_selected_real_community_profile(tmp_path: Path) -> None:
    timestamps = pd.date_range("2018-01-01 00:15:00", periods=30 * 4, freq="15min")
    gross_kw = np.linspace(400.0, 800.0, len(timestamps))
    community_path = tmp_path / "community.parquet"
    pd.DataFrame(
        {
            "timestamp": timestamps,
            "community_load_kw": gross_kw,
            "pv_generation_kw": gross_kw * 0.20,
            "net_community_load_kw": gross_kw * 0.80,
            "profile_id": "selected_profile",
            "source": "test_real_profile",
        }
    ).to_parquet(community_path, index=False)
    config = yaml.safe_load(CONTINUOUS_CONFIG.read_text(encoding="utf-8"))
    config["env"].update(
        {"episode_days": 1, "clearance_tail_hours": 1, "forecast_horizon_hours": 2}
    )
    config["community"] = {
        "source": "nrel_eulp",
        "path": str(community_path),
        "profile_id": "selected_profile",
        "episode_start": "2018-01-01 01:00:00",
        "target_peak_kw": 1_000.0,
        "pv_enabled": True,
    }

    env = ContinuousCommunityAIDemandResponseEnv(config)
    _, reset_info = env.reset(seed=7)
    _, _, _, _, info = env.step(np.asarray((1.0,), dtype=np.float32))

    assert reset_info["community_source"] == "test_real_profile"
    assert reset_info["community_profile_id"] == "selected_profile"
    assert reset_info["community_episode_start"] == "2018-01-01 01:00:00"
    assert info["pv_generation_kw"] > 0.0
    assert info["community_power_kw"] == pytest.approx(
        info["community_gross_power_kw"] - info["pv_generation_kw"]
    )
    assert info["pcc_power_kw"] == pytest.approx(info["community_power_kw"] + info["dc_power_kw"])


def test_environment_uses_absolute_time_dr_manifest_and_notice(tmp_path: Path) -> None:
    timestamps = pd.date_range("2018-01-01 00:15:00", periods=4 * 72, freq="15min")
    gross_kw = 600.0 + 100.0 * np.sin(np.arange(len(timestamps)) * 2.0 * np.pi / 96.0)
    community_path = tmp_path / "community.parquet"
    pd.DataFrame(
        {
            "timestamp": timestamps,
            "community_load_kw": gross_kw,
            "pv_generation_kw": np.maximum(gross_kw - 650.0, 0.0),
            "net_community_load_kw": np.minimum(gross_kw, 650.0),
            "profile_id": "selected_profile",
            "source": "test_real_profile",
        }
    ).to_parquet(community_path, index=False)
    events_path = tmp_path / "dr.parquet"
    pd.DataFrame(
        {
            "event_id": ["manifest_event_1"],
            "start_time": [pd.Timestamp("2018-01-02 12:00:00")],
            "end_time": [pd.Timestamp("2018-01-02 14:00:00")],
            "duration_minutes": [120],
            "notice_minutes": [120],
            "reduction_fraction": [0.2],
            "community_profile_id": ["selected_profile"],
        }
    ).to_parquet(events_path, index=False)
    config = yaml.safe_load(CONTINUOUS_CONFIG.read_text(encoding="utf-8"))
    config["env"].update(
        {"episode_days": 1, "clearance_tail_hours": 1, "forecast_horizon_hours": 2}
    )
    config["community"] = {
        "source": "nrel_eulp",
        "path": str(community_path),
        "profile_id": "selected_profile",
        "episode_start": "2018-01-02 00:00:00",
        "target_peak_kw": 1_000.0,
        "pv_enabled": True,
    }
    config["dr"].update({"source": "manifest", "events_path": str(events_path)})

    env = ContinuousCommunityAIDemandResponseEnv(config)
    observation, reset_info = env.reset(seed=7)

    assert env.observation_space.contains(observation)
    assert reset_info["dr_source"] == "manifest"
    assert len(env.event_manifest) == 1
    assert env.event_manifest[0].source_event_id == "manifest_event_1"
    assert env.event_manifest[0].start_hour == 12
    info: dict[str, object] = {}
    for _ in range(11):
        _, _, _, _, info = env.step(np.asarray((1.0,), dtype=np.float32))
    assert info["event_notice_remaining_hours"] == pytest.approx(2.0)
    for _ in range(2):
        _, _, _, _, info = env.step(np.asarray((1.0,), dtype=np.float32))
    assert info["event_active"]
    assert info["event_source_id"] == "manifest_event_1"
    assert float(info["requested_reduction_kw"]) > 0.0
