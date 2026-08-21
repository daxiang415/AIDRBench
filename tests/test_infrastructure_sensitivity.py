from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from aidrbench.data.splits import sha256_file
from aidrbench.evaluation.infrastructure_sensitivity import (
    check_infrastructure_no_dr_feasibility,
    compute_and_save_infrastructure_sensitivity,
    freeze_infrastructure_sensitivity_scenarios,
    load_infrastructure_sensitivity_design,
)

ROOT = Path(__file__).resolve().parents[1]


def _base_document() -> dict[str, object]:
    document = yaml.safe_load(
        (ROOT / "configs/env/hourly_continuous.yaml").read_text(encoding="utf-8")
    )
    document["env"]["episode_days"] = 2
    document["env"]["clearance_tail_hours"] = 48
    document["virtual_datacenter"]["node_count"] = 4
    document["workload"]["workload_mix"] = {
        "shares": {"training": 0.50, "offline_inference": 0.50},
        "flexible_fractions": {"training": 1.00, "offline_inference": 0.50},
    }
    document["hardware"] = {
        "calibration_artifact": str(
            ROOT / "data/calibration/rtx6000pro_4gpu_v1.yaml"
        ),
        "require_calibration_artifact": True,
        "require_all_workload_class_power": True,
        "calibration_power_case": "nominal",
    }
    document["dr"]["event_start_hours"] = [24]
    document["dr"]["event_duration_hours"] = 1
    return document


def _write_contracts(tmp_path: Path) -> tuple[Path, Path]:
    base_path = tmp_path / "base.yaml"
    base_path.write_text(
        yaml.safe_dump(_base_document(), sort_keys=False), encoding="utf-8"
    )
    design_path = tmp_path / "design.yaml"
    design_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "design": "sparse_oat",
                "base_config": str(base_path),
                "require_no_dr_service_feasibility": True,
                "cases": [
                    {
                        "name": "reference",
                        "pue": 1.2,
                        "node_fixed_overhead_power_case": "nominal",
                    },
                    {
                        "name": "pue_high",
                        "pue": 1.3,
                        "node_fixed_overhead_power_case": "nominal",
                    },
                    {
                        "name": "node_overhead_upper",
                        "pue": 1.2,
                        "node_fixed_overhead_power_case": "upper_bound",
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    gate = check_infrastructure_no_dr_feasibility(
        design_path,
        seeds=[7],
        output_directory=tmp_path / "gate",
    )
    execution_path = tmp_path / "execution.yaml"
    execution_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "design": "sparse_oat_pi",
                "case_specification": str(design_path),
                "service_gate_manifest": str(gate["manifest"]),
                "service_gate_seed_range": [7, 7],
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
    return design_path, execution_path


def test_infrastructure_sensitivity_freezes_paired_scenarios_and_solves_pi(
    tmp_path: Path,
) -> None:
    _, execution_path = _write_contracts(tmp_path)

    frozen = freeze_infrastructure_sensitivity_scenarios(
        execution_path, output_directory=tmp_path / "scenarios"
    )
    result = compute_and_save_infrastructure_sensitivity(
        tmp_path / "scenarios",
        specification=execution_path,
        output_directory=tmp_path / "result",
        workers=1,
    )

    assert frozen["case_count"] == 3
    assert frozen["scenario_count"] == 3
    assert result["row_count"] == 3
    frontier = pd.read_parquet(str(result["frontier"]))
    boundary = pd.read_parquet(str(result["firm_boundary"]))
    assert set(frontier["infrastructure_case"]) == {
        "reference",
        "pue_high",
        "node_overhead_upper",
    }
    assert set(frontier["perfect_information_status"]) == {"optimal"}
    assert frontier.loc[
        frontier["infrastructure_case"] == "reference", "paired_capacity_delta_kw"
    ].tolist() == pytest.approx([0.0])
    assert len(boundary) == 3
    manifest = json.loads(Path(str(result["manifest"])).read_text(encoding="utf-8"))
    assert manifest["scenario_index_sha256"] == sha256_file(
        tmp_path / "scenarios" / "infrastructure_sensitivity_scenarios.json"
    )
    assert manifest["evidence_scope"] == "development_only"


def test_infrastructure_sensitivity_fails_closed_if_design_changes(
    tmp_path: Path,
) -> None:
    design_path, execution_path = _write_contracts(tmp_path)
    document = yaml.safe_load(design_path.read_text(encoding="utf-8"))
    document["cases"][1]["pue"] = 1.31
    design_path.write_text(
        yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="service-gate identity mismatch"):
        freeze_infrastructure_sensitivity_scenarios(
            execution_path, output_directory=tmp_path / "scenarios"
        )


def test_infrastructure_sensitivity_rejects_cartesian_case() -> None:
    with pytest.raises(ValueError, match="exactly one factor"):
        load_infrastructure_sensitivity_design(
            {
                "schema_version": 1,
                "design": "sparse_oat",
                "base_config": "base.yaml",
                "require_no_dr_service_feasibility": True,
                "cases": [
                    {
                        "name": "reference",
                        "pue": 1.2,
                        "node_fixed_overhead_power_case": "nominal",
                    },
                    {
                        "name": "combined_corner",
                        "pue": 1.3,
                        "node_fixed_overhead_power_case": "upper_bound",
                    },
                ],
            }
        )
