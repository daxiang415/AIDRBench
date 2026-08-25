from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_clean_main_figure_source_data_bundle_is_complete_and_hash_bound() -> None:
    root = ROOT / "manuscript/source_data/nature_mainline_v1"
    manifest_path = root / "source_data_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["software"]["git"]["working_tree_dirty"] is False
    assert len(manifest["software"]["git"]["commit"]) == 40
    assert len(manifest["tables"]) == 21
    assert sum(int(table["row_count"]) for table in manifest["tables"]) == 17_386
    assert {figure for table in manifest["tables"] for figure in table["figures"]} == {
        1,
        2,
        3,
        4,
        5,
    }
    outputs = [str(table["output"]) for table in manifest["tables"]]
    assert len(outputs) == len(set(outputs))
    for table in manifest["tables"]:
        output = root / str(table["output"])
        assert output.is_file()
        assert _sha256(output) == table["output_sha256"]


def test_supplementary_source_data_copies_match_figure_manifests() -> None:
    source_root = ROOT / "manuscript/source_data/nature_supplementary_v1"
    manifest_root = ROOT / "docs/figures/nature_supplementary_v1"
    for number in (2, 3, 4):
        manifest = json.loads(
            (manifest_root / f"supplementary_figure_{number}_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        for record in manifest["source_data"]:
            source = source_root / record["path"]
            assert source.is_file()
            assert _sha256(source) == record["sha256"]

    metadata = json.loads(
        (source_root / "representative_trajectory_metadata.json").read_text(encoding="utf-8")
    )
    assert metadata["episode_seed"] == 20_000
    assert metadata["scenario_hash"].startswith("c53ae573b0")
    assert metadata["deadline_miss_gpu_h"] == 0.0
