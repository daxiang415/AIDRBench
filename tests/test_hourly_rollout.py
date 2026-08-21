from __future__ import annotations

from pathlib import Path

from aidrbench.controllers.hourly import HourlyMPCController, make_hourly_controller
from aidrbench.envs.community_ai_dr_env import ContinuousCommunityAIDemandResponseEnv
from aidrbench.evaluation.hourly_rollout import rollout_hourly_episode, save_hourly_rollout


def test_hourly_threshold_rollout_writes_shared_kpis(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    env = ContinuousCommunityAIDemandResponseEnv(root / "configs/env/hourly_continuous.yaml")

    frame, summary = rollout_hourly_episode(env, make_hourly_controller("threshold"), seed=3)
    saved = save_hourly_rollout(frame, summary, tmp_path)

    assert len(frame) == env.config.total_hours
    assert summary["controller"] == "threshold"
    assert summary["training_share"] == 0.5
    assert summary["workload_source"] == "synthetic"
    assert summary["community_source"] == "synthetic_hourly"
    assert float(summary["gross_community_energy_kwh"]) > 0.0
    assert float(summary["total_pcc_energy_kwh"]) > float(summary["net_community_energy_kwh"])
    assert "minimum_interval_delivery_ratio" in summary
    assert {"arrived_training_gpu_h", "executed_training_gpu_h", "backlog_training_gpu_h"} <= set(
        frame
    )
    assert "completed_training_gpu_h" in summary
    assert Path(saved["timeseries"]).is_file()
    assert Path(saved["metrics"]).is_file()


def test_hourly_edf_valley_rollout_uses_shared_kpis() -> None:
    root = Path(__file__).resolve().parents[1]
    env = ContinuousCommunityAIDemandResponseEnv(root / "configs/env/hourly_continuous.yaml")

    frame, summary = rollout_hourly_episode(env, make_hourly_controller("edf_valley"), seed=3)

    assert len(frame) == env.config.total_hours
    assert summary["controller"] == "edf_valley"
    assert summary["deadline_miss_gpu_h"] >= 0.0


def test_hourly_mpc_rollout_uses_online_forecast_metadata() -> None:
    root = Path(__file__).resolve().parents[1]
    env = ContinuousCommunityAIDemandResponseEnv(root / "configs/env/hourly_continuous.yaml")

    frame, summary = rollout_hourly_episode(env, make_hourly_controller("mpc"), seed=3)

    assert len(frame) == env.config.total_hours
    assert summary["controller"] == "mpc"
    assert "historical_mean_arrivals" in str(summary["forecast_assumption"])
    assert summary["information_structure"] == "causal_control_state_plus_6h_environment_forecast"
    assert float(summary["mean_controller_action_time_ms"]) >= 0.0


def test_causal_mpc_never_executes_an_estimated_future_release_immediately() -> None:
    root = Path(__file__).resolve().parents[1]
    env = ContinuousCommunityAIDemandResponseEnv(root / "configs/env/hourly_continuous.yaml")
    controller = HourlyMPCController()
    controller._arrival_history_gpu_h.extend((8.0, 12.0, 16.0))

    arrivals = controller._forecast_arrivals(env, horizon=4)

    assert arrivals[0] == 0.0
    assert arrivals[1] == 12.0
    controller.reset()
    assert controller._previous_fraction == 1.0


def test_hourly_robust_mpc_rollout_declares_its_arrival_envelope() -> None:
    root = Path(__file__).resolve().parents[1]
    env = ContinuousCommunityAIDemandResponseEnv(root / "configs/env/hourly_continuous.yaml")

    _, summary = rollout_hourly_episode(env, make_hourly_controller("robust_mpc"), seed=3)

    assert summary["controller"] == "robust_mpc"
    assert "uncertainty_envelope" in str(summary["forecast_assumption"])


def test_event_level_reward_costs_settle_once_at_recovery_end() -> None:
    root = Path(__file__).resolve().parents[1]
    env = ContinuousCommunityAIDemandResponseEnv(root / "configs/env/hourly_continuous.yaml")

    frame, _ = rollout_hourly_episode(env, make_hourly_controller("no_control"), seed=3)

    assert int(frame["completed_recovery_event_count"].sum()) == len(env.event_manifest)
    event_cost_rows = frame.loc[
        (frame["rebound_violation_cost"] > 0.0) | (frame["window_relief_violation_cost"] > 0.0)
    ]
    assert not event_cost_rows.empty
    assert (event_cost_rows["completed_recovery_event_count"] > 0).all()
    non_completion = frame["completed_recovery_event_count"] == 0
    event_costs = frame.loc[
        non_completion,
        ["rebound_violation_cost", "window_relief_violation_cost"],
    ]
    assert (event_costs == 0.0).all().all()
