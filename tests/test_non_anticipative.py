from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from aidrbench.data.frozen_scenarios import freeze_hourly_scenario, load_frozen_hourly_scenario
from aidrbench.evaluation.non_anticipative import (
    build_observation_information_nodes,
    compute_and_save_non_anticipative_frontier,
    solve_frozen_non_anticipative_capacity,
    solve_frozen_observation_partition_capacity,
    validate_non_anticipative_frontier,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/env/hourly_continuous.yaml"


def _short_scenario_config() -> dict[str, object]:
    document = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    environment = document["env"]
    dr = document["dr"]
    assert isinstance(environment, dict)
    assert isinstance(dr, dict)
    environment["episode_days"] = 1
    environment["clearance_tail_hours"] = 12
    dr["event_start_hours"] = [8]
    dr["event_duration_hours"] = 2
    dr["recovery_window_hours"] = 8
    return document


def test_common_schedule_non_anticipative_capacity_respects_chance_constraint(
    tmp_path: Path,
) -> None:
    config = _short_scenario_config()
    first = freeze_hourly_scenario(config, seed=51, output_directory=tmp_path)
    second = freeze_hourly_scenario(config, seed=52, output_directory=tmp_path)
    artifacts = [
        load_frozen_hourly_scenario(str(first["output"])),
        load_frozen_hourly_scenario(str(second["output"])),
    ]

    solution = solve_frozen_non_anticipative_capacity(
        artifacts,
        duration_h=2,
        reliability_target=1.0,
    )

    assert solution.status == "optimal"
    assert solution.scenario_count == 2
    assert solution.required_success_count == 2
    assert solution.selected_success_count >= solution.required_success_count
    assert len(solution.common_execution_gpu_h) == 36
    assert 0.0 <= solution.non_anticipative_capacity_kw <= (
        solution.physical_dynamic_upper_bound_kw + 1e-6
    )
    summary = solution.summary()
    assert summary["capacity_layer"] == "non_anticipative_lower_bound"
    assert summary["non_anticipative_policy_class"] == "common_open_loop_schedule"


def test_non_anticipative_validator_rejects_insufficient_successes() -> None:
    frontier = pd.DataFrame(
        {
            "duration_h": [2],
            "non_anticipative_capacity_kw": [10.0],
            "physical_dynamic_upper_bound_kw": [20.0],
            "required_success_count": [2],
            "selected_success_count": [1],
        }
    )

    with pytest.raises(ValueError, match="chance constraint"):
        validate_non_anticipative_frontier(frontier)


def test_observation_partition_tree_ties_actions_only_at_shared_information_nodes(
    tmp_path: Path,
) -> None:
    config = _short_scenario_config()
    dr = config["dr"]
    assert isinstance(dr, dict)
    dr["event_start_jitter_hours"] = 2
    artifacts = [
        load_frozen_hourly_scenario(
            str(freeze_hourly_scenario(config, seed=seed, output_directory=tmp_path)["output"])
        )
        for seed in (61, 62, 63, 64)
    ]
    nodes = build_observation_information_nodes(artifacts, duration_h=2)
    solution = solve_frozen_observation_partition_capacity(
        artifacts,
        duration_h=2,
        reliability_target=0.5,
    )

    assert solution.non_anticipative_policy_class == "coarse_observation_partition_tree"
    assert solution.information_node_count > len(nodes)
    assert solution.required_success_count == 2
    assert solution.selected_success_count == 2
    assert not solution.common_execution_gpu_h
    for hour, hourly_nodes in nodes.items():
        for node in hourly_nodes:
            reference = solution.scenario_execution_gpu_h[node[0]][hour]
            for scenario_index in node[1:]:
                assert solution.scenario_execution_gpu_h[scenario_index][hour] == pytest.approx(
                    reference,
                    abs=1e-6,
                )


def test_observation_partition_export_records_auditable_node_actions(tmp_path: Path) -> None:
    config = _short_scenario_config()
    scenario_directory = tmp_path / "scenarios"
    for seed in (71, 72):
        freeze_hourly_scenario(config, seed=seed, output_directory=scenario_directory)

    result = compute_and_save_non_anticipative_frontier(
        scenario_directory,
        durations_h=[2],
        output_directory=tmp_path / "result",
        reliability_target=1.0,
    )

    policies = pd.read_parquet(result["policies"])
    assert len(policies) == 2 * 36
    assert set(policies.columns) == {
        "duration_h",
        "event_id",
        "policy_class",
        "scenario_hash",
        "hour",
        "information_node_id",
        "execution_gpu_h",
    }
    grouped = policies.groupby(["duration_h", "hour", "information_node_id"])
    action_ranges = grouped["execution_gpu_h"].agg(lambda values: values.max() - values.min())
    assert (action_ranges <= 1e-6).all()
    manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
    assert manifest["policies"] == result["policies"]
    assert manifest["policy_row_count"] == len(policies)
