from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from aidrbench.controllers.hourly_sb3 import SB3HourlyPolicyController
from aidrbench.envs.community_ai_dr_env import DiscreteCommunityAIDemandResponseEnv
from aidrbench.training import load_rl_training_config, train_hourly_rl


def test_training_config_rejects_invalid_algorithm_environment_pair(tmp_path: Path) -> None:
    config = tmp_path / "dqn.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "algorithm": "dqn",
                "environment_config": "configs/env/hourly_continuous.yaml",
                "total_timesteps": 8,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="DQN requires the discrete"):
        train_hourly_rl(
            config,
            seed=1,
            output_directory=tmp_path / "output",
        )


def test_dqn_smoke_training_saves_cpu_model(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    template = yaml.safe_load((root / "configs/algorithms/dqn.yaml").read_text())
    assert isinstance(template, dict)
    template["total_timesteps"] = 16
    template["checkpoint_interval"] = 8
    hyperparameters = template["hyperparameters"]
    assert isinstance(hyperparameters, dict)
    hyperparameters["learning_starts"] = 1
    hyperparameters["buffer_size"] = 100
    hyperparameters["batch_size"] = 8
    config = tmp_path / "dqn-smoke.yaml"
    config.write_text(yaml.safe_dump(template), encoding="utf-8")

    summary = train_hourly_rl(
        config,
        seed=4,
        output_directory=tmp_path / "output",
    )

    assert summary["algorithm"] == "dqn"
    assert summary["environment"] == "discrete"
    assert summary["device"] == "cpu"
    assert summary["observation_version"] == "firm_v4"
    assert summary["observation_size"] == 63
    assert Path(str(summary["model"])).is_file()
    assert Path(str(summary["replay_buffer"])).is_file()
    assert Path(str(summary["metadata"])).is_file()
    checkpoint = tmp_path / "output/checkpoints/step_000000008"
    assert (checkpoint / "model.zip").is_file()
    assert (checkpoint / "replay_buffer.pkl").is_file()
    checkpoint_metadata = yaml.safe_load((checkpoint / "training.json").read_text())
    assert checkpoint_metadata["observation_version"] == "firm_v4"
    assert summary["checkpoint_interval"] == 8

    policy = SB3HourlyPolicyController("dqn", summary["model"])
    env = DiscreteCommunityAIDemandResponseEnv(root / "configs/env/hourly_discrete.yaml")
    _, info = env.reset(seed=4)
    assert isinstance(policy.act(env, info), int)

    metadata_path = Path(str(summary["metadata"]))
    incompatible = json.loads(metadata_path.read_text(encoding="utf-8"))
    incompatible["observation_version"] = "obsolete"
    metadata_path.write_text(json.dumps(incompatible), encoding="utf-8")
    incompatible_policy = SB3HourlyPolicyController("dqn", summary["model"])
    with pytest.raises(ValueError, match="observation version"):
        incompatible_policy.act(env, info)


def test_training_config_reads_algorithm_defaults() -> None:
    root = Path(__file__).resolve().parents[1]

    config = load_rl_training_config(root / "configs/algorithms/ppo.yaml")

    assert config.algorithm == "ppo"
    assert config.n_envs == 4
    assert config.experiment_protocol is None
    assert config.checkpoint_interval is None


def test_sac_config_uses_a_small_cpu_policy() -> None:
    root = Path(__file__).resolve().parents[1]

    config = load_rl_training_config(root / "configs/algorithms/sac.yaml")

    assert config.hyperparameters["policy_kwargs"] == {"net_arch": [64, 64]}


def test_dqn_training_can_resume_a_saved_checkpoint(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    template = yaml.safe_load((root / "configs/algorithms/dqn.yaml").read_text())
    assert isinstance(template, dict)
    template["total_timesteps"] = 8
    hyperparameters = template["hyperparameters"]
    assert isinstance(hyperparameters, dict)
    hyperparameters.update({"learning_starts": 1, "buffer_size": 100, "batch_size": 8})
    config = tmp_path / "dqn-resume.yaml"
    config.write_text(yaml.safe_dump(template), encoding="utf-8")
    output = tmp_path / "output"

    first = train_hourly_rl(config, seed=4, output_directory=output)
    second = train_hourly_rl(
        config,
        seed=4,
        output_directory=output,
        resume_model=first["model"],
    )

    assert second["total_timesteps"] == 8
    assert second["actual_segment_timesteps"] == 8
    assert second["cumulative_timesteps"] == 16
    assert second["resumed_from"] == first["model"]
    assert second["replay_buffer"] == first["replay_buffer"]


def test_off_policy_resume_requires_replay_buffer(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    template = yaml.safe_load((root / "configs/algorithms/dqn.yaml").read_text())
    assert isinstance(template, dict)
    template["total_timesteps"] = 8
    hyperparameters = template["hyperparameters"]
    assert isinstance(hyperparameters, dict)
    hyperparameters.update({"learning_starts": 1, "buffer_size": 100, "batch_size": 8})
    config = tmp_path / "dqn-missing-buffer.yaml"
    config.write_text(yaml.safe_dump(template), encoding="utf-8")
    output = tmp_path / "output"
    first = train_hourly_rl(config, seed=4, output_directory=output)
    Path(str(first["replay_buffer"])).unlink()

    with pytest.raises(FileNotFoundError, match="requires replay buffer"):
        train_hourly_rl(
            config,
            seed=4,
            output_directory=output,
            resume_model=first["model"],
        )
