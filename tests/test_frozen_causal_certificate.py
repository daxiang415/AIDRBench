from __future__ import annotations

import json
from pathlib import Path

import yaml

from aidrbench.data.frozen_scenarios import freeze_hourly_scenarios
from aidrbench.evaluation.firm_flexibility import FirmFlexibilityCriteria
from aidrbench.evaluation.frozen_causal_certificate import (
    certify_selected_frozen_causal_capacities,
    select_frozen_causal_capacities,
)

ROOT = Path(__file__).resolve().parents[1]


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


def test_frozen_causal_selection_is_separate_from_locked_certificate(tmp_path: Path) -> None:
    validation = tmp_path / "validation"
    locked_id = tmp_path / "locked-id"
    freeze_hourly_scenarios(_small_config(), seeds=[101, 102], output_directory=validation)
    freeze_hourly_scenarios(_small_config(), seeds=[201, 202], output_directory=locked_id)
    criteria = FirmFlexibilityCriteria(reliability_target=0.50, confidence_level=0.80)

    selected = select_frozen_causal_capacities(
        validation,
        durations_h=[1],
        notices_h=[0],
        candidate_fractions=[0.0, 0.1],
        criteria=criteria,
        output_directory=tmp_path / "selection",
    )
    certified = certify_selected_frozen_causal_capacities(
        locked_id,
        selection_path=selected["selection"],
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
