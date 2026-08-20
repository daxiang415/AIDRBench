from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from aidrbench.data.splits import sha256_file
from aidrbench.evaluation.sensitivity import (
    check_sparse_sensitivity_no_dr_feasibility,
)
from aidrbench.evaluation.workload_sensitivity import (
    compute_and_save_workload_sensitivity,
    freeze_workload_sensitivity_scenarios,
    load_workload_sensitivity_specification,
)

ROOT = Path(__file__).resolve().parents[1]


def _base_document() -> dict[str, object]:
    document = yaml.safe_load(
        (ROOT / "configs/env/hourly_continuous.yaml").read_text(encoding="utf-8")
    )
    document["env"]["episode_days"] = 2
    document["env"]["clearance_tail_hours"] = 48
    document["dr"]["event_start_hours"] = [24]
    document["dr"]["event_duration_hours"] = 1
    return document


def _write_contracts(tmp_path: Path) -> tuple[Path, Path, Path]:
    base_path = tmp_path / "base.yaml"
    base_path.write_text(
        yaml.safe_dump(_base_document(), sort_keys=False),
        encoding="utf-8",
    )
    sparse_path = tmp_path / "sparse.yaml"
    sparse_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "design": "sparse_factorial",
                "base_config": str(base_path),
                "require_no_dr_service_feasibility": True,
                "cases": [
                    {
                        "name": "reference",
                        "flexible_arrival_utilization": 0.50,
                        "rigid_gpu_utilization": 0.30,
                        "deadline_slack_scale": 1.0,
                    },
                    {
                        "name": "arrival_high",
                        "flexible_arrival_utilization": 0.60,
                        "rigid_gpu_utilization": 0.30,
                        "deadline_slack_scale": 1.0,
                    },
                    {
                        "name": "deadline_loose",
                        "flexible_arrival_utilization": 0.50,
                        "rigid_gpu_utilization": 0.30,
                        "deadline_slack_scale": 1.25,
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    gate = check_sparse_sensitivity_no_dr_feasibility(
        sparse_path,
        seeds=[7],
        output_directory=tmp_path / "gate",
    )
    execution_path = tmp_path / "execution.yaml"
    execution_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "design": "sparse_factorial_pi",
                "sparse_specification": str(sparse_path),
                "service_gate_manifest": str(gate["manifest"]),
                "development_seed_range": [7, 7],
                "durations_h": [1],
                "reliability_target": 0.50,
                "confidence_level": 0.50,
                "nominal_flexibility_fraction": 0.50,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return sparse_path, Path(str(gate["manifest"])), execution_path


def test_workload_sensitivity_freezes_paired_scenarios_and_solves_pi(
    tmp_path: Path,
) -> None:
    _, _, execution_path = _write_contracts(tmp_path)
    scenarios = freeze_workload_sensitivity_scenarios(
        execution_path,
        output_directory=tmp_path / "scenarios",
    )
    result = compute_and_save_workload_sensitivity(
        tmp_path / "scenarios",
        specification=execution_path,
        output_directory=tmp_path / "result",
        workers=1,
    )

    assert scenarios["case_count"] == 3
    assert scenarios["scenario_count"] == 3
    assert result["row_count"] == 3
    frontier = pd.read_parquet(str(result["frontier"]))
    boundary = pd.read_parquet(str(result["firm_boundary"]))
    assert set(frontier["workload_case"]) == {
        "reference",
        "arrival_high",
        "deadline_loose",
    }
    assert set(frontier["perfect_information_status"]) == {"optimal"}
    assert frontier.loc[
        frontier["workload_case"] == "reference",
        "paired_capacity_delta_kw",
    ].tolist() == pytest.approx([0.0])
    assert len(boundary) == 3
    assert boundary["estimable"].all()
    manifest = json.loads(Path(str(result["manifest"])).read_text(encoding="utf-8"))
    assert manifest["scenario_index_sha256"] == sha256_file(
        tmp_path / "scenarios" / "workload_sensitivity_scenarios.json"
    )
    assert manifest["evidence_scope"] == "development_only"


def test_workload_sensitivity_fails_closed_if_sparse_schema_changes(
    tmp_path: Path,
) -> None:
    sparse_path, _, execution_path = _write_contracts(tmp_path)
    document = yaml.safe_load(sparse_path.read_text(encoding="utf-8"))
    document["cases"][0]["deadline_slack_scale"] = 1.01
    sparse_path.write_text(
        yaml.safe_dump(document, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="specification hash mismatch"):
        freeze_workload_sensitivity_scenarios(
            execution_path,
            output_directory=tmp_path / "scenarios",
        )


def test_workload_sensitivity_schema_rejects_unknown_fields() -> None:
    with pytest.raises(ValueError, match="missing or unknown fields"):
        load_workload_sensitivity_specification(
            {
                "schema_version": 1,
                "design": "sparse_factorial_pi",
                "sparse_specification": "sparse.yaml",
                "service_gate_manifest": "gate.json",
                "development_seed_range": [1, 2],
                "durations_h": [4, 8],
                "reliability_target": 0.95,
                "confidence_level": 0.95,
                "nominal_flexibility_fraction": 0.50,
                "unexpected": True,
            }
        )
