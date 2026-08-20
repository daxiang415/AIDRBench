from __future__ import annotations

from pathlib import Path

import yaml

from aidrbench.data.splits import sha256_file
from aidrbench.envs.hourly_config import load_hourly_environment_config
from aidrbench.evaluation.sensitivity import (
    SensitivityCaseSpecification,
    apply_sensitivity_case,
    check_sparse_sensitivity_no_dr_feasibility,
    load_sparse_sensitivity_specification,
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


def test_split_utilization_and_deadline_scale_are_independently_parsed() -> None:
    case = SensitivityCaseSpecification(
        name="split_case",
        flexible_arrival_utilization=0.70,
        rigid_gpu_utilization=0.30,
        deadline_slack_scale=0.80,
    )
    document = apply_sensitivity_case(_base_document(), case)

    config = load_hourly_environment_config(document)

    assert config.flexible_arrival_utilization == 0.70
    assert config.rigid_gpu_utilization == 0.30
    assert config.deadline_slack_scale == 0.80
    assert config.make_power_model().rigid_gpu_utilization == 0.30
    assert "event_reduction_kw" not in document["dr"]


def test_sparse_sensitivity_requires_no_dr_service_gate(tmp_path: Path) -> None:
    base_path = tmp_path / "base.yaml"
    base_path.write_text(
        yaml.safe_dump(_base_document(), sort_keys=False),
        encoding="utf-8",
    )
    specification = {
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
            }
        ],
    }

    parsed = load_sparse_sensitivity_specification(specification)
    result = check_sparse_sensitivity_no_dr_feasibility(
        specification,
        seeds=[7],
        output_directory=tmp_path / "gate",
    )

    assert parsed.design == "sparse_factorial"
    assert parsed.require_no_dr_service_feasibility
    assert result["all_cases_service_feasible"] is True
    manifest = yaml.safe_load(Path(str(result["manifest"])).read_text(encoding="utf-8"))
    assert manifest["table_sha256"] == sha256_file(Path(str(result["table"])))
