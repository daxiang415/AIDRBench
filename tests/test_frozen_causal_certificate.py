from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from aidrbench.controllers.robust_mpc_spec import load_robust_mpc_specification
from aidrbench.data.frozen_scenarios import freeze_hourly_scenarios
from aidrbench.evaluation.firm_flexibility import FirmFlexibilityCriteria
from aidrbench.evaluation.frozen_causal_certificate import (
    certify_selected_frozen_causal_capacities,
    select_frozen_causal_capacities,
)

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER_CONFIG = ROOT / "configs/controller/nature_robust_mpc_v1.yaml"


def _small_config() -> dict[str, object]:
    document = yaml.safe_load(
        (ROOT / "configs/env/hourly_continuous.yaml").read_text(encoding="utf-8")
    )
    document["env"]["episode_days"] = 2
    document["env"]["clearance_tail_hours"] = 12
    document["dr"].pop("event_start_hours")
    document["dr"]["event_start_hour_choices"] = [20, 21]
    document["dr"]["event_duration_hours"] = 1
    document["dr"]["event_notice_hours"] = 0
    return document


def test_nature_robust_mpc_specification_is_complete_and_strict() -> None:
    specification = load_robust_mpc_specification(CONTROLLER_CONFIG)
    incomplete = yaml.safe_load(CONTROLLER_CONFIG.read_text(encoding="utf-8"))
    incomplete.pop("switching_penalty")

    assert specification.controller == "robust_mpc"
    assert specification.horizon_hours == 6
    with pytest.raises(ValueError, match="fields mismatch"):
        load_robust_mpc_specification(incomplete)


def test_frozen_causal_selection_is_separate_from_locked_certificate(tmp_path: Path) -> None:
    validation = tmp_path / "validation"
    locked_id = tmp_path / "locked-id"
    freeze_hourly_scenarios(_small_config(), seeds=[101, 102], output_directory=validation)
    freeze_hourly_scenarios(_small_config(), seeds=[201, 202], output_directory=locked_id)
    criteria = FirmFlexibilityCriteria(reliability_target=0.50, confidence_level=0.80)

    selected = select_frozen_causal_capacities(
        validation,
        controller_config=CONTROLLER_CONFIG,
        durations_h=[1],
        notices_h=[0],
        candidate_fractions=[0.0, 0.1],
        criteria=criteria,
        output_directory=tmp_path / "selection",
        workers=2,
    )
    certified = certify_selected_frozen_causal_capacities(
        locked_id,
        selection_path=selected["selection"],
        controller_config=CONTROLLER_CONFIG,
        output_directory=tmp_path / "certificate",
    )
    selection_document = json.loads(Path(selected["selection"]).read_text(encoding="utf-8"))
    certificate_document = json.loads(Path(certified["manifest"]).read_text(encoding="utf-8"))

    assert selection_document["selection_interpretation"].endswith("not_reliability_certificate")
    assert selection_document["selected_capacities"][0]["candidate_reduction_kw"] > 0.0
    assert not set(selection_document["validation_scenario_hashes"]) & set(
        certificate_document["locked_id_scenario_hashes"]
    )
    assert certificate_document["capacity_layer"] == "independent_causal_certificate"
    assert certificate_document["controller"] == "robust_mpc"
    assert selection_document["schema_version"] == 2
    assert selection_document["capacity_search"]["method"] == "binary"
    assert selection_document["capacity_search"]["scenario_workers"] == 2
    assert len(
        selection_document["controller_provenance"][
            "normalized_specification_sha256"
        ]
    ) == 64


def test_frozen_causal_certificate_rejects_controller_specification_mismatch(
    tmp_path: Path,
) -> None:
    validation = tmp_path / "validation"
    locked_id = tmp_path / "locked-id"
    freeze_hourly_scenarios(_small_config(), seeds=[111], output_directory=validation)
    freeze_hourly_scenarios(_small_config(), seeds=[211], output_directory=locked_id)
    controller_config = tmp_path / "robust-mpc.yaml"
    controller_config.write_text(CONTROLLER_CONFIG.read_text(encoding="utf-8"), encoding="utf-8")
    criteria = FirmFlexibilityCriteria(reliability_target=0.50, confidence_level=0.80)

    selected = select_frozen_causal_capacities(
        validation,
        controller_config=controller_config,
        durations_h=[1],
        notices_h=[0],
        candidate_fractions=[0.0, 0.1],
        criteria=criteria,
        output_directory=tmp_path / "selection",
    )
    changed = yaml.safe_load(controller_config.read_text(encoding="utf-8"))
    changed["arrival_safety_sigma"] = 2.0
    controller_config.write_text(yaml.safe_dump(changed, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="controller specification mismatch"):
        certify_selected_frozen_causal_capacities(
            locked_id,
            selection_path=selected["selection"],
            controller_config=controller_config,
            output_directory=tmp_path / "certificate",
        )

    controller_config.write_text(
        CONTROLLER_CONFIG.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    selection_path = Path(selected["selection"])
    selection_document = json.loads(selection_path.read_text(encoding="utf-8"))
    selection_document["controller_provenance"]["source_sha256"][
        "src/aidrbench/controllers/hourly.py"
    ] = "0" * 64
    tampered_selection = tmp_path / "tampered-selection.json"
    tampered_selection.write_text(
        json.dumps(selection_document),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="controller specification mismatch: source_sha256"):
        certify_selected_frozen_causal_capacities(
            locked_id,
            selection_path=tampered_selection,
            controller_config=controller_config,
            output_directory=tmp_path / "tampered-certificate",
        )
