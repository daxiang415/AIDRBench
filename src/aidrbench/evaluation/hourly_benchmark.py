"""Reproducible multi-controller benchmark for the V0 hourly environment."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal, cast

import pandas as pd

from aidrbench.controllers.hourly import make_hourly_controller
from aidrbench.controllers.hourly_sb3 import SB3AlgorithmName, SB3HourlyPolicyController
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv
from aidrbench.evaluation.hourly_rollout import (
    HourlyController,
    rollout_hourly_episode,
    save_hourly_rollout,
)

BenchmarkControllerName = Literal[
    "no_control", "threshold", "edf_valley", "mpc", "dqn", "ppo", "sac"
]
RL_CONTROLLER_NAMES = frozenset(("dqn", "ppo", "sac"))


def _controller_for(
    name: BenchmarkControllerName,
    model_paths: Mapping[str, str | Path],
) -> HourlyController:
    if name in RL_CONTROLLER_NAMES:
        model_path = model_paths.get(name)
        if model_path is None:
            raise ValueError(f"benchmark controller '{name}' needs --model {name}=PATH")
        return SB3HourlyPolicyController(cast(SB3AlgorithmName, name), model_path)
    return make_hourly_controller(name)


def aggregate_hourly_benchmark(episodes: pd.DataFrame) -> pd.DataFrame:
    """Return controller means and normal-approximation 95% confidence intervals."""

    if episodes.empty:
        raise ValueError("cannot aggregate an empty hourly benchmark")
    if "controller" not in episodes:
        raise ValueError("benchmark episodes must contain a controller column")
    numeric_columns = episodes.select_dtypes(include="number").columns.tolist()
    numeric_columns = [column for column in numeric_columns if column != "seed"]
    rows: list[dict[str, float | int | str]] = []
    for controller, group in episodes.groupby("controller", sort=False):
        row: dict[str, float | int | str] = {
            "controller": str(controller),
            "episodes": int(len(group)),
        }
        # Scenario labels are retained when they are invariant within a
        # controller's repeated seeds.  This makes the DQN discrete-action
        # variant explicit in the aggregate table rather than implicit in a
        # model filename.
        for column in (
            "action_mode",
            "workload_source",
            "forecast_assumption",
            "observation_version",
            "reward_version",
        ):
            if column in group and group[column].nunique(dropna=False) == 1:
                row[column] = str(group[column].iloc[0])
        for column in numeric_columns:
            values = group[column].dropna()
            mean = float(values.mean()) if not values.empty else math.nan
            if len(values) > 1:
                ci95 = float(1.96 * values.std(ddof=1) / math.sqrt(len(values)))
            else:
                ci95 = math.nan
            row[f"{column}_mean"] = mean
            row[f"{column}_ci95"] = ci95
        rows.append(row)
    return pd.DataFrame.from_records(rows)


def run_hourly_benchmark(
    *,
    config: str | Path,
    controllers: Sequence[BenchmarkControllerName],
    seeds: Sequence[int],
    output_directory: str | Path,
    model_paths: Mapping[str, str | Path] | None = None,
) -> dict[str, str | int]:
    """Evaluate controllers and persist every episode plus common aggregate KPIs.

    Every controller/seed gets a fresh environment.  Thus arrivals, community
    load, DR events and the clearance tail are identical for controllers with
    the same seed and configuration.
    """

    if not controllers:
        raise ValueError("benchmark needs at least one controller")
    if not seeds:
        raise ValueError("benchmark needs at least one seed")
    if len(set(controllers)) != len(controllers):
        raise ValueError("benchmark controller names must be unique")
    if len(set(seeds)) != len(seeds):
        raise ValueError("benchmark seeds must be unique")
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    supplied_models = model_paths or {}
    episode_rows: list[dict[str, object]] = []
    for name in controllers:
        for seed in seeds:
            # DQN is purposefully evaluated on the matching five-level action
            # variant; all physical inputs remain fixed by ``config``.
            if name == "dqn":
                env = HourlyCommunityAIDemandResponseEnv(config, action_mode="discrete")
            else:
                env = HourlyCommunityAIDemandResponseEnv(config)
            controller = _controller_for(name, supplied_models)
            frame, summary = rollout_hourly_episode(env, controller, seed=seed)
            summary["action_mode"] = env.config.action_mode
            episode_directory = output / "episodes" / name / f"seed_{seed}"
            paths = save_hourly_rollout(frame, summary, episode_directory)
            episode_rows.append({**summary, **paths})
    episodes = pd.DataFrame.from_records(episode_rows)
    aggregate = aggregate_hourly_benchmark(episodes)
    episodes_path = output / "episodes.parquet"
    aggregate_path = output / "aggregate.parquet"
    manifest_path = output / "benchmark.json"
    episodes.to_parquet(episodes_path, index=False)
    aggregate.to_parquet(aggregate_path, index=False)
    manifest_path.write_text(
        json.dumps(
            {
                "config": str(config),
                "controllers": list(controllers),
                "seeds": list(seeds),
                "model_paths": {name: str(path) for name, path in supplied_models.items()},
                "episodes": str(episodes_path),
                "aggregate": str(aggregate_path),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "episodes": len(episodes),
        "episode_metrics": str(episodes_path),
        "aggregate_metrics": str(aggregate_path),
        "manifest": str(manifest_path),
    }
