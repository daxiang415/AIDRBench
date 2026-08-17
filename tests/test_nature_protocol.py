from __future__ import annotations

from pathlib import Path

import yaml

from aidrbench.evaluation.nature_protocol import validate_nature_mainline_protocol

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "data/manifests/nature_mainline_protocol_v1.yaml"


def test_nature_mainline_protocol_is_ready_without_opening_locked_scenarios() -> None:
    report = validate_nature_mainline_protocol(PROTOCOL)

    assert report["valid"] is True
    checks = report["checks"]
    assert isinstance(checks, dict)
    assert checks["single_event_primary_configs"] is True
    assert checks["all_workload_classes_calibrated"] is True
    rows = report["details"]["statistical_power"]
    assert any(
        row["scenario_set"] == "validation"
        and row["reliability_target"] == 0.99
        and row["sample_size_sufficient"] is False
        for row in rows
    )
    assert any(
        row["scenario_set"] == "locked_ood"
        and row["reliability_target"] == 0.99
        and row["sample_size_sufficient"] is True
        for row in rows
    )


def test_nature_protocol_rejects_randomized_multi_event_primary_config(
    tmp_path: Path,
) -> None:
    document = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
    config_path = ROOT / "configs/env/nature_mainline_development.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["dr"]["event_start_hours"] = [17, 65]
    bad_config = tmp_path / "bad.yaml"
    bad_config.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    document["scenario_sets"]["development"]["config"] = str(bad_config)
    candidate = tmp_path / "protocol.yaml"
    candidate.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    report = validate_nature_mainline_protocol(candidate)

    assert report["valid"] is False
    assert report["checks"]["single_event_primary_configs"] is False
