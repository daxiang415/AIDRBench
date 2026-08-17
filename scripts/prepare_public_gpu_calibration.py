#!/usr/bin/env python3
"""Publish calibration inputs after removing host and GPU identifiers."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

_WORKLOAD_PATTERN = re.compile(
    r"^(training|offline_inference)_(1|4)gpu_repeat([1-9][0-9]*)_workload\.json$"
)
_TELEMETRY_PATTERN = re.compile(
    r"^(training|offline_inference)_(1|4)gpu_repeat([1-9][0-9]*)_telemetry\.parquet$"
)


def prepare(source: Path, output: Path) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    telemetry_names = ["idle_baseline.parquet"] + [
        path.name
        for path in sorted(source.glob("*_telemetry.parquet"))
        if _TELEMETRY_PATTERN.match(path.name)
    ]
    for name in telemetry_names:
        source_path = source / name
        if not source_path.is_file():
            raise FileNotFoundError(f"missing calibration telemetry: {source_path}")
        frame = pd.read_parquet(source_path)
        frame["gpu_uuid"] = frame["gpu_index"].map(lambda value: f"redacted-gpu-{int(value)}")
        frame.to_parquet(output / name, index=False)
        copied.append(name)
    for source_path in sorted(source.glob("*_workload.json")):
        if _WORKLOAD_PATTERN.match(source_path.name) is None:
            continue
        document = json.loads(source_path.read_text(encoding="utf-8"))
        document["hostname"] = "redacted"
        (output / source_path.name).write_text(
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        copied.append(source_path.name)
    if len(copied) != 25:
        raise ValueError(f"expected 25 public calibration inputs, generated {len(copied)}")
    return {
        "source": str(source),
        "output": str(output),
        "published_files": len(copied),
        "redacted_fields": ["gpu_uuid", "hostname"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


if __name__ == "__main__":
    arguments = build_parser().parse_args()
    print(
        json.dumps(
            prepare(arguments.source, arguments.output),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
