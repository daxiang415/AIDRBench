from __future__ import annotations

from pathlib import Path

import yaml

from aidrbench.evaluation.protocol import (
    validate_hourly_experiment_protocol,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "data/manifests/hourly_experiment_protocol_v2.yaml"


def test_repository_protocol_has_loadable_formal_configs_and_frozen_structure() -> None:
    report = validate_hourly_experiment_protocol(PROTOCOL)

    # The overall result may additionally depend on large, intentionally
    # untracked local datasets. Structural and calibration checks must be
    # invariant between the GPU server and a clean CI checkout.
    assert report["checks"]["environment_configs"] is True
    assert report["checks"]["test_locked"] is True
    assert report["checks"]["environment_interface_frozen"] is True
    assert report["checks"]["episode_seeds_disjoint"] is True
    assert report["checks"]["reward_thresholds_match_frozen_criteria"] is True


def test_protocol_detects_seed_leakage(tmp_path: Path) -> None:
    document = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
    document["splits"]["validation"]["episode_seed_range"] = [19999, 20099]
    invalid = tmp_path / "protocol.yaml"
    invalid.write_text(yaml.safe_dump(document), encoding="utf-8")

    report = validate_hourly_experiment_protocol(invalid)

    assert report["valid"] is False
    assert report["checks"]["episode_seeds_disjoint"] is False
