from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from aidrbench.data.frozen_scenarios import freeze_hourly_scenarios
from aidrbench.data.splits import sha256_file
from aidrbench.evaluation.renewable_ensemble import (
    compute_renewable_integration_ensemble,
    load_renewable_integration_specification,
)

ROOT = Path(__file__).resolve().parents[1]


def _short_pv_scenario_config() -> dict[str, object]:
    document = yaml.safe_load(
        (ROOT / "configs/env/hourly_continuous.yaml").read_text(encoding="utf-8")
    )
    assert isinstance(document, dict)
    assert isinstance(document["env"], dict)
    assert isinstance(document["community"], dict)
    assert isinstance(document["dr"], dict)
    document["env"]["episode_days"] = 1
    document["env"]["clearance_tail_hours"] = 12
    document["env"]["episode_seed_range"] = [91, 92]
    document["community"]["pv_enabled"] = True
    document["dr"]["event_start_hours"] = [8]
    document["dr"]["event_duration_hours"] = 2
    document["dr"]["recovery_window_hours"] = 8
    return document


def _write_specification(
    tmp_path: Path,
    *,
    dataset_role: str = "development_renewable_integration",
) -> Path:
    portfolio_path = ROOT / "configs/community/pv_bess.yaml"
    document = {
        "schema_version": 1,
        "model_a_git_commit": "a" * 40,
        "dataset_role": dataset_role,
        "independent_unit": "frozen_scenario",
        "expected_scenario_count": 2,
        "expected_episode_seed_range": [91, 92],
        "portfolio": {
            "path": str(portfolio_path),
            "sha256": sha256_file(portfolio_path),
        },
        "solver": {
            "name": "HIGHS",
            "threads_per_process": 1,
            "bess_dispatch_mode": "milp_exclusive",
        },
        "pv_hosting": {
            "envelope_dc_scales": [0.5, 1.0],
            "headline_max_curtailment_fraction": 0.05,
            "sensitivity_max_curtailment_fractions": [0.0, 0.2],
            "fixed_comparison_dc_scale": 0.5,
        },
        "fixed_capacity_operation": {
            "dc_scale_of_reference_mix": 0.5,
            "pv_rated_kw": 300.0,
            "near_pcc_limit_fraction": 0.95,
            "lexicographic_tolerance_kwh": 1e-5,
        },
        "paired_inference": {
            "confidence_level": 0.95,
            "familywise_method": "bonferroni",
            "hosting_planned_contrast_count": 2,
            "operation_planned_contrast_count": 10,
            "bootstrap_resamples": 1000,
            "bootstrap_seed": 123,
        },
        "capacity_aggregation": {
            "headline": "simultaneous_scenario_feasible_minimum",
            "descriptive_quantiles": [0.05, 0.5, 0.95],
        },
    }
    path = tmp_path / "renewable_specification.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path


def test_renewable_specification_rejects_implicit_fields(tmp_path: Path) -> None:
    path = _write_specification(tmp_path)
    specification = load_renewable_integration_specification(path)
    assert specification.fixed_operation_dc_scale == 0.5

    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["solver"]["implicit_default"] = True
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="fields mismatch"):
        load_renewable_integration_specification(path)


def test_validation_renewable_requires_validation_scenario_path(tmp_path: Path) -> None:
    scenarios = tmp_path / "development_scenarios"
    freeze_hourly_scenarios(
        _short_pv_scenario_config(),
        seeds=[91, 92],
        output_directory=scenarios,
    )
    specification = _write_specification(
        tmp_path,
        dataset_role="validation_renewable_replication",
    )

    with pytest.raises(ValueError, match="requires a validation path"):
        compute_renewable_integration_ensemble(
            scenarios,
            specification_path=specification,
            output_directory=tmp_path / "renewable",
            workers=1,
        )


def test_renewable_ensemble_is_paired_checkpointed_and_resumable(
    tmp_path: Path,
) -> None:
    scenarios = tmp_path / "development_scenarios"
    freeze_hourly_scenarios(
        _short_pv_scenario_config(),
        seeds=[91, 92],
        output_directory=scenarios,
    )
    specification = _write_specification(tmp_path)
    output = tmp_path / "renewable"

    first = compute_renewable_integration_ensemble(
        scenarios,
        specification_path=specification,
        output_directory=output,
        workers=1,
    )
    second = compute_renewable_integration_ensemble(
        scenarios,
        specification_path=specification,
        output_directory=output,
        workers=1,
    )

    scenario_results = pd.read_parquet(first["scenario_results"])
    hosting_contrasts = pd.read_parquet(first["pv_hosting_contrasts"])
    operation_contrasts = pd.read_parquet(first["pv_operation_contrasts"])
    assert first["row_count"] == 48
    assert len(scenario_results) == 48
    assert len(hosting_contrasts) == 2
    assert len(operation_contrasts) == 10
    assert set(scenario_results["capacity_layer"]) == {
        "perfect_information_renewable_planning_bound"
    }
    bess_operation = scenario_results.loc[
        (scenario_results["analysis_variant"] == "fixed_capacity_pv_operation")
        & scenario_results["bess_enabled"]
    ]
    assert (
        bess_operation["maximum_simultaneous_bess_charge_discharge_kw"] <= 1e-6
    ).all()
    assert first["solved_scenario_count"] == 2
    assert second["solved_scenario_count"] == 0
    assert second["resumed_scenario_count"] == 2
    run_state = json.loads((output / "renewable_integration_run.json").read_text())
    assert set(run_state["source_sha256"]) == {
        "src/aidrbench/data/frozen_scenarios.py",
        "src/aidrbench/envs/community_ai_dr_env.py",
        "src/aidrbench/evaluation/hosting_capacity.py",
        "src/aidrbench/evaluation/non_anticipative.py",
        "src/aidrbench/evaluation/renewable_integration.py",
        "src/aidrbench/evaluation/renewable_ensemble.py",
    }


def test_fixed_operation_scale_must_match_hosting_comparison(tmp_path: Path) -> None:
    path = _write_specification(tmp_path)
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["fixed_capacity_operation"]["dc_scale_of_reference_mix"] = 1.0
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="same data-centre scale"):
        load_renewable_integration_specification(path)
