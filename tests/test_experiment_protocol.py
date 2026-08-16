from __future__ import annotations

from pathlib import Path

import yaml

from aidrbench.evaluation.protocol import (
    validate_hourly_experiment_protocol,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "data/manifests/hourly_experiment_protocol_v2.yaml"


def test_repository_hourly_experiment_protocol_is_valid() -> None:
    report = validate_hourly_experiment_protocol(PROTOCOL)

    assert report["valid"] is True
    assert all(report["checks"].values())


def test_protocol_detects_seed_leakage(tmp_path: Path) -> None:
    document = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
    document["splits"]["validation"]["episode_seed_range"] = [19999, 20099]
    invalid = tmp_path / "protocol.yaml"
    invalid.write_text(yaml.safe_dump(document), encoding="utf-8")

    report = validate_hourly_experiment_protocol(invalid)

    assert report["valid"] is False
    assert report["checks"]["episode_seeds_disjoint"] is False
