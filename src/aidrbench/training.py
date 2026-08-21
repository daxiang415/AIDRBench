"""CPU-only Stable-Baselines3 training entry points for the hourly V0 env."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import yaml

from aidrbench.rewards.cmdp import CMDPDualState, FirmCMDPRewardConfig

AlgorithmName = Literal["dqn", "ppo", "sac"]
EnvironmentKind = Literal["continuous", "discrete"]


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class RLTrainingConfig:
    """Algorithm settings kept separate from environment/scenario settings."""

    algorithm: AlgorithmName
    environment_config: Path
    total_timesteps: int
    n_envs: int
    policy: str
    hyperparameters: dict[str, Any]
    experiment_protocol: Path | None
    checkpoint_interval: int | None
    reward_adapter: FirmCMDPRewardConfig | None


def load_rl_training_config(path: str | Path) -> RLTrainingConfig:
    """Read one P3 training YAML while rejecting unsupported algorithm names."""

    with Path(path).open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    root = _mapping(document, "RL training config")
    raw_algorithm = str(root.get("algorithm", root.get("controller", ""))).lower()
    if raw_algorithm not in {"dqn", "ppo", "sac"}:
        raise ValueError("algorithm must be one of: dqn, ppo, sac")
    raw_environment = root.get("environment_config")
    if not isinstance(raw_environment, str) or not raw_environment.strip():
        raise ValueError("environment_config must be a non-empty path")
    raw_policy = root.get("policy", "MlpPolicy")
    if not isinstance(raw_policy, str) or not raw_policy.strip():
        raise ValueError("policy must be a non-empty string")
    raw_protocol = root.get("experiment_protocol")
    if raw_protocol is not None and (not isinstance(raw_protocol, str) or not raw_protocol.strip()):
        raise ValueError("experiment_protocol must be a non-empty path when supplied")
    raw_checkpoint_interval = root.get("checkpoint_interval")
    raw_reward_adapter = root.get("reward_adapter")
    return RLTrainingConfig(
        algorithm=cast(AlgorithmName, raw_algorithm),
        environment_config=Path(raw_environment),
        total_timesteps=_positive_int(root.get("total_timesteps", 50_000), "total_timesteps"),
        n_envs=_positive_int(root.get("n_envs", 1), "n_envs"),
        policy=raw_policy,
        hyperparameters=dict(_mapping(root.get("hyperparameters", {}), "hyperparameters")),
        experiment_protocol=(Path(raw_protocol) if isinstance(raw_protocol, str) else None),
        checkpoint_interval=(
            _positive_int(raw_checkpoint_interval, "checkpoint_interval")
            if raw_checkpoint_interval is not None
            else None
        ),
        reward_adapter=(
            FirmCMDPRewardConfig.from_mapping(raw_reward_adapter)
            if raw_reward_adapter is not None
            else None
        ),
    )


def _make_periodic_checkpoint_callback(
    *,
    algorithm: AlgorithmName,
    interval: int | None,
    initial_timesteps: int,
    output_directory: Path,
    seed: int,
    observation_version: str,
    observation_size: int,
    reward_version: str,
    reward_adapter: FirmCMDPRewardConfig | None,
    dual_state: CMDPDualState | None,
) -> Any | None:
    """Create an SB3 callback with resume-compatible checkpoint directories."""

    if interval is None:
        return None
    from stable_baselines3.common.callbacks import BaseCallback

    checkpoint_interval = interval

    class AIDRBenchCheckpointCallback(BaseCallback):
        def __init__(self) -> None:
            super().__init__(verbose=0)
            self.next_checkpoint = (
                initial_timesteps // checkpoint_interval + 1
            ) * checkpoint_interval

        def _on_step(self) -> bool:
            current = int(self.num_timesteps)
            if current < self.next_checkpoint:
                return True
            checkpoint = output_directory / f"step_{current:09d}"
            checkpoint.mkdir(parents=True, exist_ok=True)
            model_path = checkpoint / "model"
            self.model.save(str(model_path))
            replay_buffer_path: Path | None = None
            if algorithm in {"dqn", "sac"}:
                replay_buffer_path = checkpoint / "replay_buffer.pkl"
                cast(Any, self.model).save_replay_buffer(str(replay_buffer_path))
            (checkpoint / "training.json").write_text(
                json.dumps(
                    {
                        "algorithm": algorithm,
                        "seed": seed,
                        "observation_version": observation_version,
                        "observation_size": observation_size,
                        "reward_version": reward_version,
                        "training_reward_version": (
                            reward_adapter.version
                            if reward_adapter is not None
                            else reward_version
                        ),
                        "reward_adapter": (
                            reward_adapter.as_dict() if reward_adapter is not None else None
                        ),
                        "cmdp_dual_state": (
                            dual_state.as_dict() if dual_state is not None else None
                        ),
                        "cumulative_timesteps": current,
                        "model": str(model_path.with_suffix(".zip")),
                        "replay_buffer": (
                            str(replay_buffer_path) if replay_buffer_path is not None else None
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            self.next_checkpoint = (current // checkpoint_interval + 1) * checkpoint_interval
            return True

    return AIDRBenchCheckpointCallback()


def _restore_cmdp_dual_state(
    resume_model: str | Path | None,
    reward_adapter: FirmCMDPRewardConfig | None,
) -> CMDPDualState | None:
    """Initialize or restore training-only dual variables without silent mixing."""

    if resume_model is None:
        return CMDPDualState.initialize(reward_adapter) if reward_adapter is not None else None
    metadata_path = Path(resume_model).with_name("training.json")
    if not metadata_path.is_file():
        if reward_adapter is not None:
            raise FileNotFoundError(
                "CMDP resume requires training.json beside the saved model: "
                f"{metadata_path}"
            )
        return None
    try:
        metadata: object = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid training metadata: {metadata_path}") from exc
    if not isinstance(metadata, Mapping):
        raise ValueError(f"training metadata must be a mapping: {metadata_path}")
    saved_version = metadata.get("training_reward_version")
    if reward_adapter is None:
        if isinstance(saved_version, str) and saved_version.startswith("firm_cmdp_v"):
            raise ValueError(
                f"cannot resume a {saved_version} model without reward_adapter"
            )
        return None
    if saved_version != reward_adapter.version:
        raise ValueError(
            "resume training reward is incompatible: "
            f"saved={saved_version!r}, configured={reward_adapter.version!r}"
        )
    saved_adapter = metadata.get("reward_adapter")
    if saved_adapter != reward_adapter.as_dict():
        raise ValueError(
            "resume reward_adapter parameters do not match the saved training run"
        )
    return CMDPDualState.from_dict(metadata.get("cmdp_dual_state"), reward_adapter)


def _environment_kind(config_path: Path) -> EnvironmentKind:
    from aidrbench.envs.hourly_config import load_hourly_environment_config

    mode = load_hourly_environment_config(config_path).action_mode
    return mode


def _validate_combination(algorithm: AlgorithmName, environment: EnvironmentKind) -> None:
    if algorithm == "dqn" and environment != "discrete":
        raise ValueError("DQN requires the discrete hourly environment")
    if algorithm == "sac" and environment != "continuous":
        raise ValueError("SAC requires the continuous hourly environment")


def train_hourly_rl(
    training_config_path: str | Path,
    *,
    algorithm_override: AlgorithmName | None = None,
    environment_override: EnvironmentKind | None = None,
    seed: int,
    output_directory: str | Path,
    total_timesteps_override: int | None = None,
    resume_model: str | Path | None = None,
) -> dict[str, object]:
    """Train or resume DQN/PPO/SAC and persist reproducibility metadata.

    ``resume_model`` permits bounded training segments on a shared server.  A
    segment continues the model state and, for off-policy algorithms, the
    replay buffer stored beside the checkpoint.
    """

    config = load_rl_training_config(training_config_path)
    protocol_hash: str | None = None
    if config.experiment_protocol is not None:
        from aidrbench.data.splits import sha256_file
        from aidrbench.evaluation.protocol import validate_hourly_experiment_protocol

        protocol_report = validate_hourly_experiment_protocol(config.experiment_protocol)
        if not bool(protocol_report["valid"]):
            raise ValueError("formal RL training requires a valid locked experiment protocol")
        protocol_hash = sha256_file(config.experiment_protocol)
    algorithm = algorithm_override or config.algorithm
    environment = environment_override or _environment_kind(config.environment_config)
    _validate_combination(algorithm, environment)
    total_timesteps = total_timesteps_override or config.total_timesteps
    _positive_int(total_timesteps, "total_timesteps")
    dual_state = _restore_cmdp_dual_state(resume_model, config.reward_adapter)
    try:
        from stable_baselines3 import DQN, PPO, SAC
        from stable_baselines3.common.vec_env import DummyVecEnv
    except ModuleNotFoundError as exc:
        raise RuntimeError("RL training requires the project 'rl' optional dependencies") from exc

    from aidrbench.envs.community_ai_dr_env import (
        ContinuousCommunityAIDemandResponseEnv,
        DiscreteCommunityAIDemandResponseEnv,
    )
    from aidrbench.rewards.cmdp import FirmCMDPRewardWrapper

    environment_type = (
        ContinuousCommunityAIDemandResponseEnv
        if environment == "continuous"
        else DiscreteCommunityAIDemandResponseEnv
    )
    gamma = float(config.hyperparameters.get("gamma", 0.99))

    def make_training_environment() -> Any:
        hourly_env = environment_type(config.environment_config)
        if config.reward_adapter is None:
            return hourly_env
        if dual_state is None:
            raise RuntimeError("CMDP reward adapter has no dual state")
        return FirmCMDPRewardWrapper(
            hourly_env,
            config.reward_adapter,
            dual_state,
            gamma=gamma,
        )

    vector_env = DummyVecEnv(
        [make_training_environment for _ in range(config.n_envs)]
    )
    vector_env.seed(seed)
    first_env = cast(Any, vector_env.envs[0].unwrapped)
    observation_version = str(first_env.observation_version)
    observation_size = int(first_env.observation_space.shape[0])
    observation_features = list(first_env.observation_feature_names)
    algorithm_type = {"dqn": DQN, "ppo": PPO, "sac": SAC}[algorithm]
    from aidrbench.envs.hourly_config import load_hourly_environment_config

    environment_config = load_hourly_environment_config(config.environment_config)
    seed_range = environment_config.episode_seed_range
    first_episode_seed = (
        seed_range[0] + seed % (seed_range[1] - seed_range[0] + 1)
        if seed_range is not None and not seed_range[0] <= seed <= seed_range[1]
        else seed
    )
    try:
        if resume_model is None:
            model: Any = algorithm_type(
                config.policy,
                vector_env,
                seed=seed,
                device="cpu",
                verbose=0,
                **config.hyperparameters,
            )
        else:
            checkpoint = Path(resume_model)
            if not checkpoint.is_file():
                raise FileNotFoundError(f"resume model does not exist: {checkpoint}")
            if algorithm == "dqn":
                model = DQN.load(str(checkpoint), env=vector_env, device="cpu")
            elif algorithm == "ppo":
                model = PPO.load(str(checkpoint), env=vector_env, device="cpu")
            else:
                model = SAC.load(str(checkpoint), env=vector_env, device="cpu")
            if algorithm in {"dqn", "sac"}:
                resume_replay_buffer = checkpoint.with_name("replay_buffer.pkl")
                if not resume_replay_buffer.is_file():
                    raise FileNotFoundError(
                        "off-policy resume requires replay buffer beside checkpoint: "
                        f"{resume_replay_buffer}"
                    )
                model.load_replay_buffer(str(resume_replay_buffer))
        previous_timesteps = int(model.num_timesteps)
        output = Path(output_directory)
        output.mkdir(parents=True, exist_ok=True)
        checkpoint_callback = _make_periodic_checkpoint_callback(
            algorithm=algorithm,
            interval=config.checkpoint_interval,
            initial_timesteps=previous_timesteps,
            output_directory=output / "checkpoints",
            seed=seed,
            observation_version=observation_version,
            observation_size=observation_size,
            reward_version=environment_config.reward.version,
            reward_adapter=config.reward_adapter,
            dual_state=dual_state,
        )
        model.learn(
            total_timesteps=total_timesteps,
            progress_bar=False,
            reset_num_timesteps=resume_model is None,
            callback=checkpoint_callback,
        )
        cumulative_timesteps = int(model.num_timesteps)
        actual_segment_timesteps = cumulative_timesteps - previous_timesteps
        model_path = output / "model"
        model.save(str(model_path))
        replay_buffer_path: Path | None = None
        if algorithm in {"dqn", "sac"}:
            replay_buffer_path = output / "replay_buffer.pkl"
            model.save_replay_buffer(str(replay_buffer_path))
        metadata: dict[str, object] = {
            "algorithm": algorithm,
            "environment": environment,
            "environment_config": str(config.environment_config),
            "total_timesteps": total_timesteps,
            "requested_timesteps": total_timesteps,
            "actual_segment_timesteps": actual_segment_timesteps,
            "cumulative_timesteps": cumulative_timesteps,
            "n_envs": config.n_envs,
            "checkpoint_interval": config.checkpoint_interval,
            "seed": seed,
            "first_episode_seed": first_episode_seed,
            "episode_seed_range": seed_range,
            "observation_version": observation_version,
            "observation_size": observation_size,
            "observation_features": observation_features,
            "reward_version": environment_config.reward.version,
            "training_reward_version": (
                config.reward_adapter.version
                if config.reward_adapter is not None
                else environment_config.reward.version
            ),
            "reward_adapter": (
                config.reward_adapter.as_dict() if config.reward_adapter is not None else None
            ),
            "cmdp_dual_state": dual_state.as_dict() if dual_state is not None else None,
            "device": "cpu",
            "model": str(model_path.with_suffix(".zip")),
            "replay_buffer": str(replay_buffer_path) if replay_buffer_path else None,
            "hyperparameters": config.hyperparameters,
            "resumed_from": str(resume_model) if resume_model is not None else None,
            "experiment_protocol": (
                str(config.experiment_protocol) if config.experiment_protocol is not None else None
            ),
            "experiment_protocol_sha256": protocol_hash,
        }
        metadata_path = output / "training.json"
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return {**metadata, "metadata": str(metadata_path)}
    finally:
        vector_env.close()
