from __future__ import annotations

import json
import warnings
from pathlib import Path

import pandas as pd
import pytest
import yaml

from aidrbench.data.frozen_scenarios import freeze_hourly_scenario, load_frozen_hourly_scenario
from aidrbench.evaluation.non_anticipative import (
    ObservationPartitionSpecification,
    attach_matched_pi_ensemble_comparison,
    build_observation_information_nodes,
    compute_and_save_non_anticipative_frontier,
    merge_non_anticipative_frontier_partitions,
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

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "error",
            message="invalid value encountered in reduce",
            category=RuntimeWarning,
        )
        solution = solve_frozen_non_anticipative_capacity(
            artifacts,
            duration_h=2,
            reliability_target=1.0,
        )

    assert solution.status == "optimal"
    assert solution.scenario_count == 2
    assert solution.notice_h == 0
    assert solution.required_success_count == 2
    assert solution.selected_success_count >= solution.required_success_count
    assert len(solution.common_execution_gpu_h) == 36
    assert 0.0 <= solution.non_anticipative_capacity_kw <= (
        solution.physical_dynamic_upper_bound_kw + 1e-6
    )
    summary = solution.summary()
    assert summary["capacity_layer"] == "restricted_scenario_based_causal_bound"
    assert summary["statistical_interpretation"] == "restricted_scenario_ensemble_bound"
    assert summary["empirical_success_fraction"] == pytest.approx(1.0)
    assert summary["non_anticipative_policy_class"] == "common_open_loop_schedule"


def test_direct_sparse_fixed_capacity_matches_joint_cvxpy_boundary(tmp_path: Path) -> None:
    config = _short_scenario_config()
    artifacts = [
        load_frozen_hourly_scenario(
            str(freeze_hourly_scenario(config, seed=seed, output_directory=tmp_path)["output"])
        )
        for seed in (53, 54)
    ]
    joint = solve_frozen_non_anticipative_capacity(
        artifacts,
        duration_h=2,
        reliability_target=1.0,
    )
    feasible_capacity = max(0.0, joint.non_anticipative_capacity_kw - 1e-5)
    fixed = solve_frozen_non_anticipative_capacity(
        artifacts,
        duration_h=2,
        reliability_target=1.0,
        fixed_capacity_kw=feasible_capacity,
        fixed_failed_scenario_hashes=frozenset(),
    )

    assert fixed.status == "optimal"
    assert fixed.capacity_selection_method == (
        "matched_pi_upper_bound_direct_sparse_feasibility_"
        "conservative_minimum_guaranteed_peak"
    )
    assert fixed.non_anticipative_capacity_kw == pytest.approx(feasible_capacity)
    assert fixed.selected_success_count == 2
    with pytest.raises(RuntimeError, match="infeasible"):
        solve_frozen_non_anticipative_capacity(
            artifacts,
            duration_h=2,
            reliability_target=1.0,
            fixed_capacity_kw=joint.non_anticipative_capacity_kw + 1.0,
            fixed_failed_scenario_hashes=frozenset(),
        )


def test_non_anticipative_validator_rejects_insufficient_successes() -> None:
    frontier = pd.DataFrame(
        {
            "duration_h": [2],
            "notice_h": [0],
            "ensemble_success_fraction_target": [1.0],
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
            for job_class in dict(solution.scenario_execution_gpu_h_by_class[node[0]]):
                class_reference = dict(
                    solution.scenario_execution_gpu_h_by_class[node[0]]
                )[job_class][hour]
                for scenario_index in node[1:]:
                    assert dict(
                        solution.scenario_execution_gpu_h_by_class[scenario_index]
                    )[job_class][hour] == pytest.approx(class_reference, abs=1e-6)


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
    assert len(policies) == 2 * 36 * 2
    assert set(policies.columns) == {
        "duration_h",
        "notice_h",
        "event_id",
        "policy_class",
        "scenario_hash",
        "hour",
        "information_node_id",
        "job_class",
        "execution_gpu_h",
    }
    assert set(policies["job_class"]) == {"offline_inference", "training"}
    grouped = policies.groupby(
        ["duration_h", "hour", "information_node_id", "job_class"]
    )
    action_ranges = grouped["execution_gpu_h"].agg(lambda values: values.max() - values.min())
    assert (action_ranges <= 1e-6).all()
    manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
    assert manifest["policies"] == result["policies"]
    assert manifest["policy_row_count"] == len(policies)
    assert manifest["independent_statistical_unit"] == "frozen_episode"
    assert manifest["confidence_bound"] is None
    assert manifest["solver"] == {"name": "HIGHS", "threads_per_solve": 1}


def test_notice_override_is_recorded_in_causal_solution(tmp_path: Path) -> None:
    config = _short_scenario_config()
    artifacts = [
        load_frozen_hourly_scenario(
            str(freeze_hourly_scenario(config, seed=seed, output_directory=tmp_path)["output"])
        )
        for seed in (81, 82)
    ]

    solution = solve_frozen_non_anticipative_capacity(
        artifacts,
        duration_h=2,
        notice_h=6,
        reliability_target=1.0,
    )

    assert solution.notice_h == 6


def test_observation_partition_rejects_forecast_information_leakage(
    tmp_path: Path,
) -> None:
    config = _short_scenario_config()
    artifacts = [
        load_frozen_hourly_scenario(
            str(freeze_hourly_scenario(config, seed=seed, output_directory=tmp_path)["output"])
        )
        for seed in (91, 92)
    ]

    with pytest.raises(ValueError, match="longer forecast"):
        build_observation_information_nodes(
            artifacts,
            duration_h=2,
            specification=ObservationPartitionSpecification(forecast_horizon_hours=7),
        )


def test_matched_pi_comparison_uses_same_empirical_failure_count() -> None:
    hashes = [f"{index:064x}" for index in range(4)]
    na = pd.DataFrame(
        {
            "duration_h": [2],
            "notice_h": [0],
            "ensemble_success_fraction_target": [0.75],
            "scenario_count": [4],
            "required_success_count": [3],
            "selected_success_count": [3],
            "non_anticipative_capacity_kw": [7.0],
            "physical_dynamic_upper_bound_kw": [20.0],
        }
    )
    pi = pd.DataFrame(
        {
            "scenario_hash": hashes,
            "event_id": [0] * 4,
            "duration_h": [2] * 4,
            "perfect_information_capacity_kw": [5.0, 8.0, 9.0, 10.0],
        }
    )

    compared = attach_matched_pi_ensemble_comparison(
        na,
        pi,
        scenario_hashes=hashes,
        event_id=0,
    )

    assert compared.loc[0, "matched_pi_allowed_failure_count"] == 1
    assert compared.loc[0, "matched_pi_ensemble_capacity_kw"] == pytest.approx(8.0)
    assert compared.loc[0, "information_restriction_gap_kw"] == pytest.approx(1.0)
    assert compared.loc[
        0, "information_restriction_gap_fraction_of_matched_pi"
    ] == pytest.approx(0.125)


def test_matched_pi_upper_bound_uses_fixed_feasibility_fast_path(tmp_path: Path) -> None:
    config = _short_scenario_config()
    scenario_directory = tmp_path / "scenarios"
    artifacts = [
        load_frozen_hourly_scenario(
            str(
                freeze_hourly_scenario(
                    config,
                    seed=seed,
                    output_directory=scenario_directory,
                )["output"]
            )
        )
        for seed in (101, 102)
    ]
    pi_path = tmp_path / "pi_frontier.parquet"
    pd.DataFrame(
        {
            "scenario_hash": [artifact.scenario_hash for artifact in artifacts],
            "event_id": [0, 0],
            "duration_h": [2, 2],
            "perfect_information_capacity_kw": [0.0, 0.0],
        }
    ).to_parquet(pi_path, index=False)

    result = compute_and_save_non_anticipative_frontier(
        scenario_directory,
        durations_h=[2],
        output_directory=tmp_path / "result",
        reliability_target=0.5,
        matched_pi_frontier_path=pi_path,
    )

    frontier = pd.read_parquet(result["frontier"])
    assert frontier.loc[0, "capacity_selection_method"] == (
        "matched_pi_upper_bound_direct_sparse_feasibility_"
        "conservative_minimum_guaranteed_peak"
    )
    assert frontier.loc[0, "non_anticipative_capacity_kw"] == pytest.approx(0.0)
    assert frontier.loc[0, "information_restriction_gap_kw"] == pytest.approx(0.0)
    manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
    assert manifest["capacity_selection_methods"] == [
        "matched_pi_upper_bound_direct_sparse_feasibility_"
        "conservative_minimum_guaranteed_peak"
    ]


def test_merge_non_anticipative_partitions_preserves_provenance(tmp_path: Path) -> None:
    inputs = []
    for notice_h in (0, 2):
        root = tmp_path / f"n{notice_h}"
        root.mkdir()
        frontier = pd.DataFrame(
            {
                "duration_h": [1],
                "notice_h": [notice_h],
                "event_id": [0],
                "ensemble_success_fraction_target": [1.0],
                "non_anticipative_capacity_kw": [5.0],
                "physical_dynamic_upper_bound_kw": [10.0],
                "required_success_count": [1],
                "selected_success_count": [1],
                "capacity_selection_method": ["test_method"],
            }
        )
        frontier.to_parquet(root / "non_anticipative_frontier.parquet", index=False)
        policy = pd.DataFrame(
            {
                "duration_h": [1],
                "notice_h": [notice_h],
                "event_id": [0],
                "policy_class": ["test_policy"],
                "scenario_hash": ["a" * 64],
                "hour": [0],
                "information_node_id": [0],
                "job_class": ["training"],
                "execution_gpu_h": [1.0],
            }
        )
        policy.to_parquet(root / "non_anticipative_policies.parquet", index=False)
        manifest = {
            "capacity_layer": "restricted_scenario_based_causal_bound",
            "statistical_interpretation": "finite_scenario_ensemble_not_independent_certificate",
            "deployable_on_unseen_scenarios": False,
            "independent_statistical_unit": "frozen_episode",
            "capacity_and_failures_selected_on": "same_finite_scenario_ensemble",
            "confidence_bound": None,
            "multiplicity_interpretation": "descriptive",
            "policy_export_scope": "audit",
            "solver": {"name": "HIGHS", "threads_per_solve": 1},
            "information_structure": "coarse_observation_partition_tree",
            "observation_partition": {"test": True},
            "event_id": 0,
            "ensemble_success_fraction_target": 1.0,
            "scenario_count": 1,
            "scenario_hashes": ["a" * 64],
            "matched_pi_reference": {"sha256": "b" * 64},
            "provenance": {"test": True},
            "policy_row_count": 1,
        }
        (root / "non_anticipative_frontier.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
        inputs.append(root)

    result = merge_non_anticipative_frontier_partitions(
        inputs,
        output_directory=tmp_path / "merged",
    )

    assert result["row_count"] == 2
    assert result["partition_count"] == 2
    merged = pd.read_parquet(result["frontier"])
    assert sorted(merged["notice_h"].astype(int)) == [0, 2]
    merged_manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
    assert len(merged_manifest["merged_from_partitions"]) == 2
    assert all(
        len(partition["frontier_sha256"]) == 64
        for partition in merged_manifest["merged_from_partitions"]
    )
