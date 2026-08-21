from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from aidrbench.data.frozen_scenarios import freeze_hourly_scenario
from aidrbench.data.splits import sha256_file
from aidrbench.evaluation.criteria_sensitivity import (
    compute_and_save_criteria_sensitivity,
    load_criteria_sensitivity_specification,
    validate_criteria_sensitivity_frontier,
)

ROOT = Path(__file__).resolve().parents[1]


def _case(
    name: str,
    factor: str,
    *,
    delivery: float = 0.95,
) -> dict[str, object]:
    return {
        "name": name,
        "factor": factor,
        "min_delivery_ratio": delivery,
        "min_interval_delivery_ratio": delivery,
        "max_deadline_miss_rate": 0.01,
        "max_rebound_ratio": 0.25,
        "min_window_peak_relief_fraction": 0.50,
        "max_terminal_backlog_fraction": 0.02,
    }


def _specification(gate: Path) -> dict[str, object]:
    return {
        "schema_version": 1,
        "design": "one_factor_at_a_time",
        "service_gate_manifest": str(gate),
        "durations_h": [1],
        "reliability_target": 0.50,
        "confidence_level": 0.50,
        "nominal_flexibility_fraction": 0.50,
        "cases": [
            _case("reference", "reference"),
            _case("delivery_090", "delivery", delivery=0.90),
        ],
    }


def test_repository_criteria_sensitivity_is_sparse_complete_and_linked() -> None:
    specification = load_criteria_sensitivity_specification(
        ROOT / "configs/sensitivity/nature_success_criteria_oat_v1.yaml"
    )

    assert specification.design == "one_factor_at_a_time"
    assert specification.durations_h == (4, 8)
    assert len(specification.cases) == 9
    assert {
        case.factor for case in specification.cases
    } == {"reference", "delivery", "deadline", "rebound", "window_relief"}
    assert all(
        case.min_delivery_ratio == case.min_interval_delivery_ratio
        for case in specification.cases
    )


def test_criteria_sensitivity_rejects_a_mislabeled_multi_factor_case(tmp_path: Path) -> None:
    specification = _specification(tmp_path / "gate.json")
    cases = specification["cases"]
    assert isinstance(cases, list)
    cases[1]["max_rebound_ratio"] = 0.50

    with pytest.raises(ValueError, match="changes"):
        load_criteria_sensitivity_specification(specification)


def test_criteria_sensitivity_runs_only_after_hashed_service_gate(tmp_path: Path) -> None:
    base_document = yaml.safe_load(
        (ROOT / "configs/env/hourly_continuous.yaml").read_text(encoding="utf-8")
    )
    base_document["env"]["episode_days"] = 2
    base_document["env"]["clearance_tail_hours"] = 48
    base_document["dr"]["event_start_hours"] = [24]
    frozen = freeze_hourly_scenario(
        base_document,
        seed=31,
        output_directory=tmp_path / "scenarios",
    )

    gate_table = tmp_path / "gate.parquet"
    pd.DataFrame.from_records([{"service_feasible": True}]).to_parquet(
        gate_table,
        index=False,
    )
    gate_manifest = tmp_path / "gate.json"
    gate_manifest.write_text(
        json.dumps(
            {
                "all_cases_service_feasible": True,
                "downstream_sensitivity_execution_allowed": True,
                "table": str(gate_table),
                "table_sha256": sha256_file(gate_table),
            }
        ),
        encoding="utf-8",
    )
    specification = _specification(gate_manifest)
    output = tmp_path / "criteria"

    result = compute_and_save_criteria_sensitivity(
        str(frozen["output"]),
        specification=specification,
        output_directory=output,
    )

    frontier = pd.read_parquet(result["frontier"])
    parsed = load_criteria_sensitivity_specification(specification)
    validate_criteria_sensitivity_frontier(frontier, parsed)
    capacities = frontier.set_index("criteria_case")["perfect_information_capacity_kw"]
    assert result["row_count"] == 2
    assert capacities["delivery_090"] >= capacities["reference"] - 1e-6
    assert Path(result["manifest"]).is_file()
