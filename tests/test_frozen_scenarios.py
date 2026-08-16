from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import yaml

from aidrbench.data.frozen_scenarios import (
    freeze_hourly_scenario,
    load_frozen_hourly_scenario,
)
from aidrbench.envs.community_ai_dr_env import ContinuousCommunityAIDemandResponseEnv

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/env/hourly_continuous.yaml"


def test_frozen_scenario_replays_identical_exogenous_inputs_and_baseline(tmp_path: Path) -> None:
    frozen_summary = freeze_hourly_scenario(CONFIG, seed=11, output_directory=tmp_path)
    artifact = load_frozen_hourly_scenario(str(frozen_summary["output"]))
    document = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    document["scenario"] = {"frozen_path": str(frozen_summary["output"])}

    generated = ContinuousCommunityAIDemandResponseEnv(CONFIG)
    replay = ContinuousCommunityAIDemandResponseEnv(document)
    generated_observation, generated_info = generated.reset(seed=11)
    replay_observation, replay_info = replay.reset(seed=11)

    assert replay_info["scenario_provenance"] == "frozen_artifact"
    assert replay_info["frozen_scenario_id"] == artifact.scenario_id
    assert replay_info["frozen_scenario_hash"] == artifact.scenario_hash
    assert generated_info["episode_seed"] == replay_info["episode_seed"] == artifact.episode_seed
    assert generated.event_manifest == replay.event_manifest
    assert np.allclose(generated_observation, replay_observation)
    assert np.allclose(
        artifact.baseline["baseline_pcc_power_kw"].to_numpy(),
        replay.full_horizon_planning_snapshot().baseline_pcc_power_kw,
    )

    for _ in range(12):
        action = np.asarray((0.5,), dtype=np.float32)
        generated_observation, generated_reward, _, _, generated_step = generated.step(action)
        replay_observation, replay_reward, _, _, replay_step = replay.step(action)
        assert np.allclose(generated_observation, replay_observation)
        assert generated_reward == pytest.approx(replay_reward)
        assert replay_step["pcc_power_kw"] == pytest.approx(generated_step["pcc_power_kw"])
        assert replay_step["arrival_gpu_h"] == pytest.approx(generated_step["arrival_gpu_h"])


def test_frozen_scenario_changes_only_duration_when_requested(tmp_path: Path) -> None:
    frozen_summary = freeze_hourly_scenario(CONFIG, seed=12, output_directory=tmp_path)
    artifact = load_frozen_hourly_scenario(str(frozen_summary["output"]))
    document = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    document["scenario"] = {"frozen_path": str(frozen_summary["output"])}
    document["dr"]["event_duration_hours"] = 4

    replay = ContinuousCommunityAIDemandResponseEnv(document)
    replay.reset(seed=12)

    assert len(replay.event_manifest) == len(artifact.events)
    for anchored, varied in zip(artifact.events, replay.event_manifest, strict=True):
        assert varied.source_event_id == anchored["source_event_id"]
        assert varied.start_hour == anchored["start_hour"]
        assert varied.stop_hour == anchored["start_hour"] + 4
        assert varied.notice_hours == pytest.approx(anchored["notice_hours"])
        assert varied.requested_reduction_kw == pytest.approx(anchored["requested_reduction_kw"])
    assert replay._community.equals(artifact.community)
    assert replay._arrivals.equals(artifact.arrivals)


def test_frozen_scenario_refuses_overwrite_and_physical_mismatch(tmp_path: Path) -> None:
    frozen_summary = freeze_hourly_scenario(CONFIG, seed=13, output_directory=tmp_path)
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        freeze_hourly_scenario(CONFIG, seed=13, output_directory=tmp_path)

    document = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    document["scenario"] = {"frozen_path": str(frozen_summary["output"])}
    document["community"]["pcc_capacity_kw"] = 900.0
    with pytest.raises(ValueError, match="PCC capacity"):
        ContinuousCommunityAIDemandResponseEnv(document)
