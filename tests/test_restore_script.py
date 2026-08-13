from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_manifest(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "gpus": [
                    {
                        "gpu_id": 0,
                        "gpu_uuid": "GPU-zero",
                        "default_limit_w": 300.0,
                    },
                    {
                        "gpu_id": 1,
                        "gpu_uuid": "GPU-one",
                        "default_limit_w": 300.0,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _write_fake_nvidia_smi(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env python3
import sys
if any(arg.startswith("--query-gpu=") for arg in sys.argv):
    print("0, GPU-zero, 300.00")
    print("1, GPU-one, 300.00")
    raise SystemExit(0)
raise SystemExit("unexpected mutation command in dry-run test")
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def test_dependency_free_restore_script_dry_run(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts/restore_gpu_power.py"
    manifest = tmp_path / "restore.json"
    fake_nvidia_smi = tmp_path / "nvidia-smi"
    _write_manifest(manifest)
    _write_fake_nvidia_smi(fake_nvidia_smi)

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--manifest",
            str(manifest),
            "--nvidia-smi",
            str(fake_nvidia_smi),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["dry_run"] is True
    assert summary["verified_gpu_uuids"] is True
    assert summary["gpu_ids"] == [0, 1]


def test_restore_script_requires_second_execute_acknowledgement(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts/restore_gpu_power.py"
    manifest = tmp_path / "restore.json"
    _write_manifest(manifest)
    completed = subprocess.run(
        [sys.executable, str(script), "--manifest", str(manifest), "--execute"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    assert "requires --acknowledge-hardware-mutation" in completed.stderr
