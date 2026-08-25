from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from aidrbench.data.splits import validate_source_manifest


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_bound_manifest(tmp_path: Path) -> Path:
    inputs: dict[str, dict[str, object]] = {}
    protocol_data: dict[str, dict[str, object]] = {}
    sources: dict[str, dict[str, object]] = {}
    for name in ("community", "workload_sampler", "hardware_calibration"):
        payload = name.encode()
        artifact = tmp_path / f"{name}.bin"
        artifact.write_bytes(payload)
        digest = _sha256(payload)
        source_id = f"source_{name}"
        sources[source_id] = {
            "used_in_formal_mainline": True,
            "artifact": {
                "path": str(artifact),
                "sha256": digest,
                "bytes": len(payload),
            },
        }
        inputs[name] = {
            "source_id": source_id,
            "path": str(artifact),
            "sha256": digest,
            "bytes": len(payload),
        }
        protocol_data[name] = {"path": str(artifact), "sha256": digest}
    protocol = tmp_path / "protocol.yaml"
    protocol.write_text(
        yaml.safe_dump({"data": protocol_data}, sort_keys=False), encoding="utf-8"
    )
    manifest = tmp_path / "sources.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "sources": sources,
                "formal_mainline_binding": {
                    "protocol_path": str(protocol),
                    "inputs": inputs,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return manifest


def test_source_manifest_validates_formal_protocol_binding(tmp_path: Path) -> None:
    report = validate_source_manifest(_write_bound_manifest(tmp_path))

    assert report["valid"] is True
    assert report["formal_mainline_binding"]["valid"] is True


def test_source_manifest_rejects_protocol_hash_mismatch(tmp_path: Path) -> None:
    manifest = _write_bound_manifest(tmp_path)
    document = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    document["formal_mainline_binding"]["inputs"]["workload_sampler"]["sha256"] = (
        "0" * 64
    )
    manifest.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    report = validate_source_manifest(manifest)

    assert report["valid"] is False
    assert report["formal_mainline_binding"]["valid"] is False
    assert report["formal_mainline_binding"]["inputs"]["workload_sampler"][
        "protocol_hash_matches"
    ] is False
