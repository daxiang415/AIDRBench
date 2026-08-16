"""Perfect-information power-duration frontiers on frozen scenarios."""

from __future__ import annotations

import copy
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from aidrbench.controllers.hourly_oracle import solve_full_horizon_oracle
from aidrbench.data.frozen_scenarios import FrozenHourlyScenario, load_frozen_hourly_scenario
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv


def _positive_durations(durations: Sequence[int]) -> tuple[int, ...]:
    if not durations:
        raise ValueError("PI frontier needs at least one duration")
    if any(isinstance(duration, bool) or not isinstance(duration, int) for duration in durations):
        raise ValueError("PI frontier durations must be positive integers")
    normalized = tuple(int(duration) for duration in durations)
    if any(duration <= 0 for duration in normalized):
        raise ValueError("PI frontier durations must be positive integers")
    if len(set(normalized)) != len(normalized):
        raise ValueError("PI frontier durations must be unique")
    return tuple(sorted(normalized))


def _environment_document(
    artifact: FrozenHourlyScenario,
    *,
    duration_h: int,
    event_id: int,
) -> dict[str, Any]:
    document = copy.deepcopy(artifact.config_document)
    raw_scenario = document.get("scenario")
    scenario = dict(raw_scenario) if isinstance(raw_scenario, dict) else {}
    scenario.update(
        {
            "frozen_path": str(artifact.directory),
            "frozen_event_ids": [event_id],
        }
    )
    document["scenario"] = scenario
    raw_dr = document.get("dr")
    if not isinstance(raw_dr, dict):
        raise ValueError("frozen scenario environment config is missing a dr mapping")
    dr = dict(raw_dr)
    # The artifact supplies starts, notices and request anchors.  The one
    # intentional variation in this frontier is the event duration.
    dr.update(
        {
            "source": "configured",
            "events_path": None,
            "event_duration_hours": duration_h,
            "event_duration_choices": None,
            "event_notice_choices": None,
            "event_reduction_fraction_range": None,
            "event_start_jitter_hours": 0,
        }
    )
    document["dr"] = dr
    return document


def solve_frozen_pi_frontier(
    artifact: FrozenHourlyScenario,
    *,
    durations_h: Sequence[int],
    event_id: int = 0,
) -> pd.DataFrame:
    """Solve a fresh, single-event perfect-information duration frontier.

    A frozen scenario carries all exogenous data.  Each row selects the same
    event anchor and changes only its duration.  The result is explicitly a
    perfect-information bound, not a causal or certified capacity.
    """

    durations = _positive_durations(durations_h)
    available_event_ids = {int(event["event_id"]) for event in artifact.events}
    if event_id not in available_event_ids:
        raise ValueError(f"frozen scenario does not contain event ID {event_id}")
    rows: list[dict[str, Any]] = []
    for duration_h in durations:
        document = _environment_document(
            artifact,
            duration_h=duration_h,
            event_id=event_id,
        )
        env = HourlyCommunityAIDemandResponseEnv(document)
        env.reset(seed=artifact.episode_seed)
        snapshot = env.full_horizon_planning_snapshot()
        reward = env.config.reward
        solution = solve_full_horizon_oracle(
            snapshot,
            min_delivery_ratio=reward.min_delivery_ratio,
            min_interval_delivery_ratio=reward.min_delivery_ratio,
            max_deadline_miss_rate=reward.max_deadline_miss_rate,
            max_rebound_ratio=reward.max_rebound_ratio,
            min_window_peak_relief_fraction=reward.min_window_peak_relief_fraction,
            max_terminal_backlog_fraction=reward.max_terminal_backlog_fraction,
        )
        physical_upper_bound_kw = snapshot.dynamic_kw_per_gpu_h * snapshot.capacity_gpu_h
        if solution.perfect_information_capacity_kw > physical_upper_bound_kw + 1e-6:
            raise RuntimeError("perfect-information solution exceeds the physical dynamic bound")
        rows.append(
            {
                "scenario_id": artifact.scenario_id,
                "scenario_hash": artifact.scenario_hash,
                "episode_seed": artifact.episode_seed,
                "event_id": event_id,
                "duration_h": duration_h,
                "capacity_layer": "perfect_information",
                "perfect_information_capacity_kw": solution.perfect_information_capacity_kw,
                "perfect_information_capacity_fraction_of_dynamic_range": (
                    solution.perfect_information_capacity_fraction_of_dynamic_range
                ),
                "physical_dynamic_upper_bound_kw": physical_upper_bound_kw,
                "minimum_mean_delivery_ratio": solution.minimum_mean_delivery_ratio_for_bound,
                "minimum_interval_delivery_ratio": (
                    solution.minimum_interval_delivery_ratio_for_bound
                ),
                "maximum_rebound_ratio": solution.maximum_rebound_ratio_for_bound,
                "minimum_window_relief_fraction": solution.minimum_window_relief_fraction_for_bound,
                "deadline_miss_gpu_h": solution.total_deadline_miss_gpu_h,
                "terminal_backlog_gpu_h": solution.terminal_backlog_gpu_h,
                "pcc_capacity_kw": snapshot.pcc_capacity_kw,
                "actual_dc_peak_kw": env._full_dc_power_kw,
                "perfect_information_status": solution.status,
                "objective_solve_seconds": solution.objective_solve_seconds,
                "refinement_solve_seconds": solution.refinement_solve_seconds,
            }
        )
    result = pd.DataFrame.from_records(rows)
    validate_pi_frontier(result)
    return result


def validate_pi_frontier(frontier: pd.DataFrame) -> None:
    """Enforce physical and duration-monotonicity invariants before reporting."""

    required = {
        "scenario_hash",
        "event_id",
        "duration_h",
        "perfect_information_capacity_kw",
        "physical_dynamic_upper_bound_kw",
    }
    missing = sorted(required - set(frontier.columns))
    if missing:
        raise ValueError(f"PI frontier is missing columns: {missing}")
    if frontier.empty:
        raise ValueError("PI frontier is empty")
    if (frontier["perfect_information_capacity_kw"] < -1e-9).any():
        raise ValueError("PI frontier contains a negative capacity")
    if (
        frontier["perfect_information_capacity_kw"]
        > frontier["physical_dynamic_upper_bound_kw"] + 1e-6
    ).any():
        raise ValueError("PI frontier exceeds the physical dynamic-power bound")
    for _, group in frontier.groupby(["scenario_hash", "event_id"], sort=False):
        ordered = group.sort_values("duration_h")
        capacity = ordered["perfect_information_capacity_kw"].to_numpy()
        if len(capacity) > 1 and (capacity[1:] > capacity[:-1] + 1e-6).any():
            raise ValueError("PI frontier violates duration monotonicity")


def _discover_artifacts(path: str | Path) -> list[FrozenHourlyScenario]:
    root = Path(path)
    if (root / "metadata.json").is_file():
        return [load_frozen_hourly_scenario(root)]
    if not root.is_dir():
        raise FileNotFoundError(f"frozen scenario path does not exist: {root}")
    artifacts = [
        load_frozen_hourly_scenario(child)
        for child in sorted(root.iterdir())
        if child.is_dir() and (child / "metadata.json").is_file()
    ]
    if not artifacts:
        raise ValueError(f"no frozen scenario artifacts found in: {root}")
    return artifacts


def compute_and_save_pi_frontier(
    scenario_path: str | Path,
    *,
    durations_h: Sequence[int],
    output_directory: str | Path,
    event_id: int = 0,
) -> dict[str, str | int]:
    """Compute and persist a hash-linked PI frontier for every supplied artifact."""

    artifacts = _discover_artifacts(scenario_path)
    frames = [
        solve_frozen_pi_frontier(
            artifact,
            durations_h=durations_h,
            event_id=event_id,
        )
        for artifact in artifacts
    ]
    frontier = pd.concat(frames, ignore_index=True)
    validate_pi_frontier(frontier)
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    frontier_path = output / "pi_frontier.parquet"
    manifest_path = output / "pi_frontier.json"
    frontier.to_parquet(frontier_path, index=False)
    manifest_path.write_text(
        json.dumps(
            {
                "capacity_layer": "perfect_information",
                "event_id": event_id,
                "durations_h": list(_positive_durations(durations_h)),
                "scenario_count": len(artifacts),
                "scenario_hashes": [artifact.scenario_hash for artifact in artifacts],
                "frontier": str(frontier_path),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "scenario_count": len(artifacts),
        "row_count": len(frontier),
        "frontier": str(frontier_path),
        "manifest": str(manifest_path),
    }
