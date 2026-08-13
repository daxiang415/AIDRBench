#!/usr/bin/env python3
"""Dependency-free emergency restoration from an AIDRBench manifest."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

QUERY_FIELDS = ("index", "uuid", "power.limit")


def _run(command: list[str]) -> str:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=10.0,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"executable not found: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("nvidia-smi command timed out") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "no diagnostic output"
        raise RuntimeError(
            f"command failed with exit code {completed.returncode}: {detail}"
        )
    return completed.stdout


def _manifest_defaults(path: Path) -> dict[int, tuple[str, float]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1:
        raise RuntimeError("unsupported restore manifest schema_version")
    raw_gpus = document.get("gpus")
    if not isinstance(raw_gpus, list) or not raw_gpus:
        raise RuntimeError("restore manifest contains no GPU defaults")
    defaults: dict[int, tuple[str, float]] = {}
    for index, raw_gpu in enumerate(raw_gpus):
        if not isinstance(raw_gpu, dict):
            raise RuntimeError(f"restore manifest GPU entry {index} is invalid")
        try:
            gpu_id = int(raw_gpu["gpu_id"])
            gpu_uuid = str(raw_gpu["gpu_uuid"])
            default_limit = float(raw_gpu["default_limit_w"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"restore manifest GPU entry {index} is invalid") from exc
        if gpu_id < 0 or not gpu_uuid or default_limit <= 0.0 or gpu_id in defaults:
            raise RuntimeError(f"restore manifest GPU entry {index} is unsafe")
        defaults[gpu_id] = (gpu_uuid, default_limit)
    return defaults


def _query(executable: str) -> dict[int, tuple[str, float]]:
    output = _run(
        [
            executable,
            f"--query-gpu={','.join(QUERY_FIELDS)}",
            "--format=csv,noheader,nounits",
        ]
    )
    states: dict[int, tuple[str, float]] = {}
    for row_number, row in enumerate(csv.reader(output.splitlines()), start=1):
        if not row or all(not value.strip() for value in row):
            continue
        if len(row) != len(QUERY_FIELDS):
            raise RuntimeError(f"GPU query row {row_number} has an unexpected schema")
        try:
            gpu_id = int(row[0].strip())
            gpu_uuid = row[1].strip()
            current_limit = float(row[2].strip())
        except ValueError as exc:
            raise RuntimeError(f"GPU query row {row_number} is invalid") from exc
        if gpu_id in states or not gpu_uuid:
            raise RuntimeError(f"GPU query row {row_number} is unsafe")
        states[gpu_id] = (gpu_uuid, current_limit)
    if not states:
        raise RuntimeError("GPU query returned no devices")
    return states


def restore(
    manifest: Path,
    *,
    executable: str,
    execute: bool,
) -> dict[str, object]:
    defaults = _manifest_defaults(manifest)
    before = _query(executable)
    if set(before) != set(defaults):
        raise RuntimeError(
            f"GPU ID mismatch; manifest={sorted(defaults)}, current={sorted(before)}"
        )
    for gpu_id, (expected_uuid, _) in defaults.items():
        if before[gpu_id][0] != expected_uuid:
            raise RuntimeError(f"GPU {gpu_id} UUID does not match restore manifest")
    if execute:
        failures: list[str] = []
        for gpu_id, (_, default_limit) in defaults.items():
            try:
                _run(
                    [
                        executable,
                        "--id",
                        str(gpu_id),
                        "--power-limit",
                        f"{default_limit:.2f}",
                    ]
                )
            except RuntimeError as exc:
                failures.append(f"GPU {gpu_id}: {exc}")
        if failures:
            raise RuntimeError("; ".join(failures))
        after = _query(executable)
        mismatched = [
            gpu_id
            for gpu_id, (_, default_limit) in defaults.items()
            if abs(after[gpu_id][1] - default_limit) > 0.51
        ]
        if mismatched:
            raise RuntimeError(f"restored limit verification failed for GPUs {mismatched}")
    return {
        "manifest": str(manifest),
        "dry_run": not execute,
        "verified_gpu_uuids": True,
        "gpu_ids": sorted(defaults),
        "default_limits_w": [defaults[gpu_id][1] for gpu_id in sorted(defaults)],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--acknowledge-hardware-mutation", action="store_true")
    parser.add_argument("--nvidia-smi", default="nvidia-smi")
    args = parser.parse_args()
    if args.execute and not args.acknowledge_hardware_mutation:
        parser.error("--execute requires --acknowledge-hardware-mutation")
    try:
        summary = restore(
            args.manifest,
            executable=args.nvidia_smi,
            execute=args.execute,
        )
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"restore failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
