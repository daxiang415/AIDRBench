"""Stable-Baselines3 policy adapter for the hourly environment KPI rollout."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import numpy as np

from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv

SB3AlgorithmName = Literal["dqn", "ppo", "sac"]


class SB3HourlyPolicyController:
    """Use a saved SB3 policy while retaining the common rollout interface."""

    forecast_assumption = "policy_observation_only"
    information_structure = "causal_normalized_policy_observation"

    def __init__(self, algorithm: SB3AlgorithmName, model_path: str | Path) -> None:
        try:
            from stable_baselines3 import DQN, PPO, SAC
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "RL policy evaluation requires the project 'rl' optional dependencies"
            ) from exc
        self.algorithm = algorithm
        self.name: str = algorithm
        checkpoint = Path(model_path)
        self.expected_observation_version: str | None = None
        metadata_path = checkpoint.with_name("training.json")
        if metadata_path.is_file():
            try:
                metadata: object = json.loads(metadata_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid policy metadata: {metadata_path}") from exc
            if isinstance(metadata, dict):
                version = metadata.get("observation_version")
                if isinstance(version, str) and version:
                    self.expected_observation_version = version
        if algorithm == "dqn":
            self.model: Any = DQN.load(str(checkpoint), device="cpu")
        elif algorithm == "ppo":
            self.model = PPO.load(str(checkpoint), device="cpu")
        else:
            self.model = SAC.load(str(checkpoint), device="cpu")

    def act(
        self, env: HourlyCommunityAIDemandResponseEnv, info: dict[str, Any]
    ) -> np.ndarray | int:
        del info
        if (
            self.expected_observation_version is not None
            and self.expected_observation_version != env.observation_version
        ):
            raise ValueError(
                "saved policy observation version "
                f"{self.expected_observation_version} is incompatible with "
                f"AIDRBench {env.observation_version}"
            )
        model_shape = self.model.observation_space.shape
        if model_shape != env.observation_space.shape:
            raise ValueError(
                "saved policy observation shape "
                f"{model_shape} is incompatible with AIDRBench "
                f"{env.observation_version} shape {env.observation_space.shape}"
            )
        action, _ = self.model.predict(env.current_observation, deterministic=True)
        if env.config.action_mode == "discrete":
            return int(np.asarray(action).item())
        return np.asarray(action, dtype=np.float32).reshape(1)
