from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "data/manifests/renewable_zero_miss_results_v1.yaml"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_zero_miss_result_receipt_is_hash_bound_and_non_locked() -> None:
    document = yaml.safe_load(RECEIPT.read_text(encoding="utf-8"))

    assert document["locked_sets_used"] is False
    assert document["reinforcement_learning_used"] is False
    assert document["integrity"]["all_solver_statuses_optimal"] is True
    assert document["integrity"]["maximum_deadline_miss_gpu_h"] == 0.0
    assert document["integrity"]["scenario_count"] == 200

    records = [
        document["configuration"],
        *document["implementation"].values(),
        *document["inputs"].values(),
        *document["outputs"].values(),
    ]
    for record in records:
        path = ROOT / record["path"]
        assert path.is_file(), path
        assert _sha256(path) == record["sha256"], path
