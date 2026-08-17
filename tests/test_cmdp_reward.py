from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from aidrbench.envs.community_ai_dr_env import ContinuousCommunityAIDemandResponseEnv
from aidrbench.rewards.cmdp import (
    CMDP_CONSTRAINT_NAMES,
    CMDPDualState,
    FirmCMDPRewardConfig,
    FirmCMDPRewardWrapper,
)
from aidrbench.training import load_rl_training_config

ROOT = Path(__file__).resolve().parents[1]
ENV_CONFIG = ROOT / "configs/env/hourly_continuous.yaml"


def _wrapped_environment(version: str = "firm_cmdp_v1") -> FirmCMDPRewardWrapper:
    config = FirmCMDPRewardConfig(version=version)
    dual = CMDPDualState.initialize(config)
    return FirmCMDPRewardWrapper(
        ContinuousCommunityAIDemandResponseEnv(ENV_CONFIG),
        config,
        dual,
        gamma=0.995,
    )


def test_cmdp_config_is_loaded_separately_from_environment_reward() -> None:
    config = load_rl_training_config(ROOT / "configs/algorithms/ppo_cmdp.yaml")

    assert config.reward_adapter is not None
    assert config.reward_adapter.version == "firm_cmdp_v4"
    assert config.environment_config == Path("configs/env/hourly_formal_train_continuous.yaml")


def test_useful_compute_reward_makes_full_service_better_than_stopping() -> None:
    stopped = _wrapped_environment()
    serving = _wrapped_environment()
    stopped.reset(seed=4)
    serving.reset(seed=4)

    _, stopped_reward, _, _, stopped_info = stopped.step(
        np.asarray((0.0,), dtype=np.float32)
    )
    _, serving_reward, _, _, serving_info = serving.step(
        np.asarray((1.0,), dtype=np.float32)
    )

    assert serving_info["training_useful_compute_reward"] > 0.0
    assert stopped_info["training_useful_compute_reward"] == pytest.approx(0.0)
    assert serving_reward > stopped_reward
    assert stopped_info["training_reward_version"] == "firm_cmdp_v1"
    assert stopped_info["environment_reward"] != pytest.approx(stopped_reward)


def test_v2_shapes_running_recovery_violation_before_physical_settlement() -> None:
    old = _wrapped_environment("firm_cmdp_v1")
    corrected = _wrapped_environment("firm_cmdp_v2")
    old.reset(seed=12)
    corrected.reset(seed=12)
    first_event = old.unwrapped.event_manifest[0]

    found_running_violation = False
    for hour in range(first_event.recovery_stop_hour):
        action = 0.0 if first_event.start_hour <= hour < first_event.stop_hour else 1.0
        old_step = old.step(np.asarray((action,), dtype=np.float32))
        corrected_step = corrected.step(np.asarray((action,), dtype=np.float32))
        old_info = old_step[4]
        corrected_info = corrected_step[4]
        running_cost = float(corrected_info["running_rebound_violation_cost"]) + float(
            corrected_info["running_window_relief_violation_cost"]
        )
        if running_cost <= 0.0:
            continue
        assert corrected_info["completed_recovery_event_count"] == 0
        assert corrected_info["rebound_violation_cost"] == pytest.approx(0.0)
        assert corrected_info["window_relief_violation_cost"] == pytest.approx(0.0)
        assert corrected_info["training_recovery_potential_cost"] == pytest.approx(
            running_cost
        )
        assert corrected_info["training_potential_shaping_reward"] < old_info[
            "training_potential_shaping_reward"
        ]
        found_running_violation = True
        break

    assert found_running_violation


def test_v3_cancels_sb3_discount_for_physical_stage_objective() -> None:
    gamma = 0.995
    corrected = _wrapped_environment("firm_cmdp_v3")
    corrected.reset(seed=4)

    first = corrected.step(np.asarray((1.0,), dtype=np.float32))[4]
    second = corrected.step(np.asarray((1.0,), dtype=np.float32))[4]

    assert first["training_discount_correction"] == pytest.approx(1.0)
    assert second["training_discount_correction"] == pytest.approx(gamma**-1)
    assert gamma * float(second["training_discount_correction"]) == pytest.approx(1.0)


def test_v4_recovery_increments_sum_to_settled_physical_cost() -> None:
    corrected = _wrapped_environment("firm_cmdp_v4")
    corrected.reset(seed=12)
    first_event = corrected.unwrapped.event_manifest[0]
    increment_sums = {"rebound": 0.0, "window_relief": 0.0}
    final_info: dict[str, object] = {}

    for hour in range(first_event.recovery_stop_hour):
        action = 0.0 if first_event.start_hour <= hour < first_event.stop_hour else 1.0
        final_info = corrected.step(np.asarray((action,), dtype=np.float32))[4]
        increment_sums["rebound"] += float(final_info["cmdp_rebound_cost"])
        increment_sums["window_relief"] += float(final_info["cmdp_window_relief_cost"])

    assert final_info["completed_recovery_event_count"] == 1
    assert increment_sums["rebound"] == pytest.approx(
        float(final_info["rebound_violation_cost"])
    )
    assert increment_sums["window_relief"] == pytest.approx(
        float(final_info["window_relief_violation_cost"])
    )


def test_v5_repeats_running_recovery_violation_while_window_is_active() -> None:
    corrected = _wrapped_environment("firm_cmdp_v5")
    corrected.reset(seed=12)
    first_event = corrected.unwrapped.event_manifest[0]
    observed_costs: list[float] = []

    for hour in range(first_event.recovery_stop_hour):
        action = 0.0 if first_event.start_hour <= hour < first_event.stop_hour else 1.0
        info = corrected.step(np.asarray((action,), dtype=np.float32))[4]
        running_cost = float(info["running_rebound_violation_cost"]) + float(
            info["running_window_relief_violation_cost"]
        )
        training_cost = float(info["cmdp_rebound_cost"]) + float(
            info["cmdp_window_relief_cost"]
        )
        if bool(info["event_window_active"]) and running_cost > 0.0:
            assert training_cost == pytest.approx(running_cost)
            observed_costs.append(training_cost)

    assert len(observed_costs) >= 2

    _, _, _, _, after_window = corrected.step(np.asarray((1.0,), dtype=np.float32))
    assert not after_window["event_window_active"]
    assert after_window["cmdp_rebound_cost"] == pytest.approx(0.0)
    assert after_window["cmdp_window_relief_cost"] == pytest.approx(0.0)


def test_dual_state_updates_only_observed_constraints_and_is_bounded() -> None:
    config = FirmCMDPRewardConfig(
        dual_learning_rate=0.5,
        dual_tolerance=0.1,
        maximum_multiplier=2.0,
    )
    dual = CMDPDualState.initialize(config)
    peak_costs = {name: 0.0 for name in CMDP_CONSTRAINT_NAMES}
    observed = {name: False for name in CMDP_CONSTRAINT_NAMES}
    peak_costs["deadline"] = 10.0
    observed["deadline"] = True

    dual.update(peak_costs, observed, config)

    assert dual.multipliers["deadline"] == pytest.approx(2.0)
    assert dual.multipliers["delivery"] == pytest.approx(1.0)
    assert dual.updates == 1


def test_cmdp_config_rejects_unknown_version() -> None:
    with pytest.raises(
        ValueError,
        match="firm_cmdp_v1.*firm_cmdp_v2.*firm_cmdp_v3.*firm_cmdp_v4.*firm_cmdp_v5",
    ):
        FirmCMDPRewardConfig.from_mapping({"version": "unknown"})
