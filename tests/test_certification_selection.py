from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from aidrbench.evaluation.certification import (
    evaluate_selected_capacity_on_locked_test,
    select_firm_capacity_on_validation,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/env/hourly_continuous.yaml"


def _write_temporary_protocol(tmp_path: Path) -> Path:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert isinstance(config, dict)
    environment = config["env"]
    dr = config["dr"]
    assert isinstance(environment, dict)
    assert isinstance(dr, dict)
    environment["episode_days"] = 1
    environment["clearance_tail_hours"] = 12
    environment["episode_seed_range"] = [20, 21]
    dr["event_start_hours"] = [8]
    dr["event_duration_hours"] = 2
    dr["recovery_window_hours"] = 8
    config_path = tmp_path / "validation.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    protocol = {
        "protocol_id": "temporary_certification_protocol",
        "frozen_criteria": {
            "reliability_target": 0.5,
            "confidence_level": 0.5,
            "min_delivery_ratio": 0.0,
            "min_interval_delivery_ratio": 0.0,
            "max_deadline_miss_rate": 1.0,
            "max_rebound_ratio": 100.0,
            "min_window_peak_relief_fraction": 0.0,
            "max_terminal_backlog_fraction": 1.0,
        },
        "splits": {
            "validation": {
                "role": "controller_and_hyperparameter_selection",
                "episode_seed_range": [20, 21],
                "configs": [str(config_path)],
            },
            "test": {
                "role": "locked_ood_evaluation",
                "episode_seed_range": [30, 31],
                "configs": [str(config_path)],
            },
        },
    }
    protocol_path = tmp_path / "protocol.yaml"
    protocol_path.write_text(yaml.safe_dump(protocol), encoding="utf-8")
    return protocol_path


def test_validation_selection_freezes_capacity_without_touching_test_split(tmp_path: Path) -> None:
    protocol_path = _write_temporary_protocol(tmp_path)

    result = select_firm_capacity_on_validation(
        protocol_manifest=protocol_path,
        controller="no_control",
        model_path=None,
        durations_h=[2],
        candidate_reduction_fractions=[0.0],
        output_directory=tmp_path / "selection",
        search_method="grid",
    )

    selection = json.loads(Path(result["selection"]).read_text(encoding="utf-8"))
    assert selection["selection_split"] == "validation"
    assert selection["validation_seed_count"] == 2
    assert selection["selected_capacities"][0]["certified_reduction_kw"] == 0.0
    assert "test_seed_count" not in selection


def test_locked_evaluation_refuses_non_validation_selection(tmp_path: Path) -> None:
    path = tmp_path / "bad_selection.json"
    path.write_text(
        json.dumps({"schema_version": 1, "selection_split": "test"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="frozen validation selection"):
        evaluate_selected_capacity_on_locked_test(
            selection_path=path,
            output_directory=tmp_path / "output",
        )


def test_locked_evaluation_requires_the_selected_protocol_manifest(tmp_path: Path) -> None:
    selection_path = tmp_path / "selection.json"
    selected_manifest = tmp_path / "selected_protocol.yaml"
    requested_manifest = tmp_path / "requested_protocol.yaml"
    selection_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "selection_split": "validation",
                "protocol_manifest": str(selected_manifest),
                "controller": "no_control",
                "selected_capacities": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="does not match"):
        evaluate_selected_capacity_on_locked_test(
            selection_path=selection_path,
            output_directory=tmp_path / "output",
            expected_protocol_manifest=requested_manifest,
        )
