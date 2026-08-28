from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pandas as pd
import pytest
import yaml

from aidrbench.controllers.robust_mpc_spec import (
    load_robust_mpc_specification,
    robust_mpc_specification_sha256,
)
from aidrbench.data.splits import sha256_file
from aidrbench.evaluation.community_profile_renewable import (
    compute_and_save_community_profile_renewable_sensitivity,
)
from aidrbench.evaluation.community_profile_sensitivity import (
    check_community_profile_no_dr_feasibility,
    compute_and_save_community_profile_sensitivity,
    freeze_community_profile_sensitivity_scenarios,
    load_community_profile_sensitivity_design,
)
from aidrbench.evaluation.firm_flexibility import FirmFlexibilityCriteria

ROOT = Path(__file__).resolve().parents[1]


def _write_test_community_profiles(tmp_path: Path) -> Path:
    """Create a small, deterministic profile bundle independent of local data."""

    timestamps = pd.date_range("2018-01-01", periods=24 * 14, freq="h")
    records: list[pd.DataFrame] = []
    for profile_id, phase_hours, pv_scale in (
        ("eulp_mixed_3a", 0, 1.00),
        ("eulp_mixed_3c", 5, 0.85),
        ("eulp_mixed_5a", 9, 0.70),
    ):
        clock_hours = [int(value) for value in timestamps.hour]
        load = [500.0 + 8.0 * ((hour + phase_hours) % 24) for hour in clock_hours]
        pv = [
            120.0 * pv_scale * max(0.0, 1.0 - abs(hour - 12.0) / 6.0)
            for hour in clock_hours
        ]
        records.append(
            pd.DataFrame(
                {
                    "timestamp": timestamps,
                    "community_load_kw": load,
                    "pv_generation_kw": pv,
                    "profile_id": profile_id,
                    "source": "self_contained_ci_fixture",
                }
            )
        )
    path = tmp_path / "community_profiles.parquet"
    pd.concat(records, ignore_index=True).to_parquet(path, index=False)
    return path


def _base_document(community_path: Path) -> dict[str, object]:
    document = yaml.safe_load(
        (ROOT / "configs/env/nature_mainline_development.yaml").read_text(
            encoding="utf-8"
        )
    )
    document["env"]["episode_days"] = 2
    document["env"]["clearance_tail_hours"] = 48
    document["virtual_datacenter"]["node_count"] = 4
    document["dr"]["event_start_hour_choices"] = [24]
    document["dr"]["event_duration_hours"] = 1
    document["community"]["path"] = str(community_path)
    document["community"]["window_start"] = "2018-01-01T00:00:00"
    document["community"]["window_end"] = "2018-01-15T00:00:00"
    document["workload"]["source"] = "synthetic"
    document["workload"].pop("summary_path", None)
    return cast(dict[str, object], document)


def _write_contracts(tmp_path: Path) -> tuple[Path, Path]:
    community_path = _write_test_community_profiles(tmp_path)
    base_path = tmp_path / "base.yaml"
    base_path.write_text(
        yaml.safe_dump(_base_document(community_path), sort_keys=False), encoding="utf-8"
    )
    design_path = tmp_path / "design.yaml"
    design_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "design": "paired_climate_zone_profiles",
                "base_config": str(base_path),
                "profile_split_manifest": str(
                    ROOT / "data/manifests/community_profile_split_v1.yaml"
                ),
                "require_no_dr_service_feasibility": True,
                "cases": [
                    {
                        "name": "reference_3a",
                        "profile_id": "eulp_mixed_3a",
                        "climate_zone": "3A",
                    },
                    {
                        "name": "climate_3c",
                        "profile_id": "eulp_mixed_3c",
                        "climate_zone": "3C",
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    gate = check_community_profile_no_dr_feasibility(
        design_path,
        seeds=[7],
        output_directory=tmp_path / "gate",
    )
    controller_path = ROOT / "configs/controller/nature_robust_mpc_v1.yaml"
    controller = load_robust_mpc_specification(controller_path)
    criteria = FirmFlexibilityCriteria(reliability_target=0.50, confidence_level=0.50)
    selection_path = tmp_path / "selection.json"
    selection_path.write_text(
        json.dumps(
            {
                "selection_dataset_role": "validation",
                "controller": "robust_mpc",
                "controller_provenance": {
                    "controller_config_sha256": sha256_file(controller_path),
                    "normalized_specification_sha256": (
                        robust_mpc_specification_sha256(controller)
                    ),
                },
                "criteria": criteria.as_dict(),
                "selected_capacities": [
                    {
                        "duration_h": 1,
                        "notice_h": 0,
                        "reliability_target": 0.50,
                        "candidate_reduction_kw": 1.0,
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    execution_path = tmp_path / "execution.yaml"
    execution_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "design": "paired_climate_zone_pi_and_fixed_causal",
                "case_specification": str(design_path),
                "service_gate_manifest": str(gate["manifest"]),
                "service_gate_seed_range": [7, 7],
                "development_seed_range": [7, 7],
                "durations_h": [1],
                "reliability_target": 0.50,
                "confidence_level": 0.50,
                "nominal_flexibility_fraction": 0.50,
                "controller_config": str(controller_path),
                "reference_selection": str(selection_path),
                "causal_notice_h": 0,
                "causal_durations_h": [1],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return design_path, execution_path


def test_community_profile_sensitivity_pairs_only_profile_and_solves(
    tmp_path: Path,
) -> None:
    _, execution_path = _write_contracts(tmp_path)

    frozen = freeze_community_profile_sensitivity_scenarios(
        execution_path, output_directory=tmp_path / "scenarios"
    )
    result = compute_and_save_community_profile_sensitivity(
        tmp_path / "scenarios",
        specification=execution_path,
        output_directory=tmp_path / "result",
        workers=1,
    )

    assert frozen["case_count"] == 2
    assert frozen["scenario_count"] == 2
    assert result["row_count"] == 2
    assert result["causal_summary_row_count"] == 2
    frontier = pd.read_parquet(str(result["pi_frontier"]))
    boundary = pd.read_parquet(str(result["pi_firm_boundary"]))
    transfer = pd.read_parquet(str(result["causal_transfer_summary"]))
    assert set(frontier["community_profile_case"]) == {
        "reference_3a",
        "climate_3c",
    }
    assert set(frontier["perfect_information_status"]) == {"optimal"}
    assert len(boundary) == 2
    assert set(transfer["transfer_interpretation"]) == {
        "fixed_validation_selected_candidate_development_diagnostic"
    }
    index = json.loads(
        (tmp_path / "scenarios/community_profile_sensitivity_scenarios.json").read_text(
            encoding="utf-8"
        )
    )
    arrivals = {
        case["scenarios"][0]["arrivals_sha256"] for case in index["cases"]
    }
    communities = {
        case["scenarios"][0]["community_sha256"] for case in index["cases"]
    }
    assert len(arrivals) == 1
    assert len(communities) == 2


def test_community_profile_sensitivity_fails_closed_if_design_changes(
    tmp_path: Path,
) -> None:
    design_path, execution_path = _write_contracts(tmp_path)
    document = yaml.safe_load(design_path.read_text(encoding="utf-8"))
    document["cases"][1]["profile_id"] = "eulp_mixed_5a"
    document["cases"][1]["climate_zone"] = "5A"
    design_path.write_text(
        yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="service-gate identity mismatch"):
        freeze_community_profile_sensitivity_scenarios(
            execution_path, output_directory=tmp_path / "scenarios"
        )


def test_community_profile_sensitivity_rejects_unregistered_profile() -> None:
    with pytest.raises(ValueError, match="absent from the split manifest"):
        load_community_profile_sensitivity_design(
            {
                "schema_version": 1,
                "design": "paired_climate_zone_profiles",
                "base_config": "configs/env/nature_mainline_development.yaml",
                "profile_split_manifest": (
                    "data/manifests/community_profile_split_v1.yaml"
                ),
                "require_no_dr_service_feasibility": True,
                "cases": [
                    {
                        "name": "reference_3a",
                        "profile_id": "eulp_mixed_3a",
                        "climate_zone": "3A",
                    },
                    {
                        "name": "climate_9z",
                        "profile_id": "eulp_mixed_9z",
                        "climate_zone": "9Z",
                    },
                ],
            }
        )


def test_community_profile_renewable_sensitivity_solves_sparse_paired_slice(
    tmp_path: Path,
) -> None:
    _, execution_path = _write_contracts(tmp_path)
    scenario_path = tmp_path / "scenarios"
    freeze_community_profile_sensitivity_scenarios(
        execution_path, output_directory=scenario_path
    )
    portfolio_path = ROOT / "configs/community/pv_bess.yaml"
    renewable_path = tmp_path / "renewable.yaml"
    renewable_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "design": "paired_climate_zone_pv_hosting",
                "community_profile_execution": str(execution_path),
                "portfolio": {
                    "path": str(portfolio_path),
                    "sha256": sha256_file(portfolio_path),
                },
                "solver": {
                    "name": "HIGHS",
                    "threads_per_process": 1,
                    "time_limit_seconds": 300,
                    "bess_dispatch_mode": "milp_exclusive",
                },
                "pv_hosting": {
                    "dc_scale_of_reference_mix": 1.0,
                    "maximum_pv_curtailment_fraction": 0.05,
                    "maximum_deadline_miss_rate": 0.01,
                    "near_pcc_limit_fraction": 0.95,
                },
                "paired_inference": {
                    "confidence_level": 0.95,
                    "familywise_method": "bonferroni",
                    "planned_contrast_count": 4,
                    "bootstrap_resamples": 1000,
                    "bootstrap_seed": 2026,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    result = compute_and_save_community_profile_renewable_sensitivity(
        scenario_path,
        specification=renewable_path,
        output_directory=tmp_path / "renewable_result",
        workers=1,
    )

    assert result["scenario_count"] == 2
    assert result["row_count"] == 8
    summary = pd.read_parquet(str(result["summary"]))
    contrasts = pd.read_parquet(str(result["contrasts"]))
    assert len(summary) == 8
    assert len(contrasts) == 4
    assert summary["all_scenarios_feasible"].all()

    completed = tmp_path / "renewable_result"
    incomplete = tmp_path / ".renewable_result.incomplete"
    completed.replace(incomplete)
    replay = compute_and_save_community_profile_renewable_sensitivity(
        scenario_path,
        specification=renewable_path,
        output_directory=completed,
        workers=1,
    )
    replay_manifest = json.loads(Path(str(replay["manifest"])).read_text(encoding="utf-8"))
    assert replay_manifest["resumed_partition_count"] == 2
