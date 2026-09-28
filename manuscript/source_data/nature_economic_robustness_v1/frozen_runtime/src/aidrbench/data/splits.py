"""Content hashing, chronological splits, and manifest validation."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

TIME_COLUMNS = {
    "inference": "timestamp_s",
    "burstgpt": "timestamp_s",
    "batch": "release_time_s",
    "alibaba": "release_time_s",
    "community": "timestamp",
    "dr": "start_time",
}
REQUIRED_COLUMNS = {
    "inference": {
        "timestamp_s",
        "session_id",
        "elapsed_time_s",
        "original_model_label",
        "request_tokens",
        "response_tokens",
        "total_tokens",
        "log_type",
        "source_file",
    },
    "batch": {
        "job_id",
        "release_time_s",
        "work_gpu_seconds",
        "gpu_demand_original",
        "gpu_demand_local",
        "duration_original_s",
        "deadline_time_s",
        "deadline_is_synthetic",
        "slack_factor",
        "priority",
        "preemptible",
        "source_file",
    },
    "community": {
        "timestamp",
        "community_load_kw",
        "pv_generation_kw",
        "net_community_load_kw",
        "profile_id",
        "season",
        "source",
    },
    "dr": {
        "event_id",
        "start_time",
        "end_time",
        "duration_minutes",
        "notice_minutes",
        "reduction_fraction",
        "pcc_limit_kw",
        "post_event_ramp_minutes",
    },
}


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _serialize_time(value: object) -> str | float:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return float(value)  # type: ignore[arg-type]


def _time_column(name: str, frame: pd.DataFrame) -> str:
    configured = TIME_COLUMNS.get(name.lower())
    if configured is not None and configured in frame.columns:
        return configured
    for candidate in ("timestamp_s", "release_time_s", "timestamp", "start_time"):
        if candidate in frame.columns:
            return candidate
    raise ValueError(f"cannot identify time column for dataset {name}")


def create_split_manifest(
    datasets: Mapping[str, str | Path],
    output: str | Path,
    *,
    seed: int = 42,
) -> dict[str, object]:
    """Record deterministic 60/20/20 chronological partitions and file hashes."""

    manifest_datasets: dict[str, object] = {}
    for name, raw_path in sorted(datasets.items()):
        path = Path(raw_path)
        frame = pd.read_parquet(path)
        time_column = _time_column(name, frame)
        ordered = frame.sort_values(time_column, kind="stable").reset_index(drop=True)
        if len(ordered) < 3:
            raise ValueError(f"dataset {name} needs at least three rows for time splits")
        unique_times = ordered[time_column].drop_duplicates().reset_index(drop=True)
        if len(unique_times) < 3:
            raise ValueError(f"dataset {name} needs at least three distinct timestamps")
        train_row = max(0, int(len(ordered) * 0.6) - 1)
        validation_row = min(len(ordered) - 2, int(len(ordered) * 0.8) - 1)
        train_boundary = ordered[time_column].iloc[train_row]
        validation_boundary = ordered[time_column].iloc[validation_row]
        if validation_boundary <= train_boundary:
            later_times = unique_times[unique_times > train_boundary]
            validation_boundary = later_times.iloc[0]
        ranges = {
            "train": ordered[ordered[time_column] <= train_boundary],
            "validation": ordered[
                (ordered[time_column] > train_boundary)
                & (ordered[time_column] <= validation_boundary)
            ],
            "test": ordered[ordered[time_column] > validation_boundary],
        }
        splits: dict[str, object] = {}
        for split_name, split_frame in ranges.items():
            splits[split_name] = {
                "rows": len(split_frame),
                "start": _serialize_time(split_frame[time_column].iloc[0]),
                "end": _serialize_time(split_frame[time_column].iloc[-1]),
            }
        manifest_datasets[name] = {
            "path": str(path),
            "sha256": sha256_file(path),
            "rows": len(frame),
            "time_column": time_column,
            "preserve_time_order": True,
            "splits": splits,
        }

    manifest: dict[str, object] = {
        "schema_version": 1,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "seed": seed,
        "split_policy": {"train": 0.6, "validation": 0.2, "test": 0.2},
        "datasets": manifest_datasets,
    }
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(manifest, handle, sort_keys=False, allow_unicode=True)
    return manifest


def validate_manifest(manifest_path: str | Path) -> dict[str, object]:
    """Re-hash every dataset referenced by a split manifest."""

    path = Path(manifest_path)
    with path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    if not isinstance(document, dict) or not isinstance(document.get("datasets"), dict):
        raise ValueError("manifest must contain a datasets mapping")
    datasets: dict[str, Any] = document["datasets"]
    results: dict[str, object] = {}
    valid = True
    for name, entry in datasets.items():
        if not isinstance(entry, dict) or "path" not in entry or "sha256" not in entry:
            raise ValueError(f"invalid manifest entry for {name}")
        dataset_path = Path(str(entry["path"]))
        exists = dataset_path.is_file()
        actual = sha256_file(dataset_path) if exists else None
        matches = exists and actual == entry["sha256"]
        schema_valid = False
        time_order_valid = False
        row_count_valid = False
        semantics_valid = False
        missing_columns: list[str] = []
        if exists:
            frame = pd.read_parquet(dataset_path)
            required = REQUIRED_COLUMNS.get(str(name), set())
            missing_columns = sorted(required - set(frame.columns))
            schema_valid = not missing_columns
            time_column = str(entry.get("time_column", ""))
            time_order_valid = time_column in frame.columns and bool(
                frame[time_column].is_monotonic_increasing
            )
            row_count_valid = len(frame) == int(entry.get("rows", -1))
            semantics_valid = _validate_semantics(str(name), frame)
        entry_valid = (
            matches and schema_valid and time_order_valid and row_count_valid and semantics_valid
        )
        valid = valid and entry_valid
        results[str(name)] = {
            "exists": exists,
            "hash_matches": matches,
            "sha256": actual,
            "schema_valid": schema_valid,
            "missing_columns": missing_columns,
            "time_order_valid": time_order_valid,
            "row_count_valid": row_count_valid,
            "semantics_valid": semantics_valid,
        }
    return {"valid": valid, "manifest": str(path), "datasets": results}


def _collect_source_files(node: object) -> list[tuple[str, str, int | None]]:
    files: list[tuple[str, str, int | None]] = []
    if isinstance(node, dict):
        location = node.get("local_path", node.get("path"))
        expected_hash = node.get("verified_sha256", node.get("sha256"))
        expected_bytes = node.get("bytes")
        if isinstance(location, str) and isinstance(expected_hash, str):
            files.append(
                (
                    location,
                    expected_hash,
                    int(expected_bytes) if isinstance(expected_bytes, int) else None,
                )
            )
        for value in node.values():
            files.extend(_collect_source_files(value))
    elif isinstance(node, list):
        for value in node:
            files.extend(_collect_source_files(value))
    return files


def validate_source_manifest(manifest_path: str | Path) -> dict[str, object]:
    """Verify source files and their binding to the formal protocol inputs."""

    path = Path(manifest_path)
    with path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    if not isinstance(document, dict):
        raise ValueError("source manifest must be a mapping")
    files = _collect_source_files(document)
    if not files:
        raise ValueError("source manifest contains no hashed local files")
    results: dict[str, object] = {}
    valid = True
    for location, expected_hash, expected_bytes in files:
        source_path = Path(location)
        exists = source_path.is_file()
        actual_hash = sha256_file(source_path) if exists else None
        actual_bytes = source_path.stat().st_size if exists else None
        hash_matches = actual_hash == expected_hash
        size_matches = expected_bytes is None or actual_bytes == expected_bytes
        file_valid = exists and hash_matches and size_matches
        valid = valid and file_valid
        results[location] = {
            "exists": exists,
            "hash_matches": hash_matches,
            "size_matches": size_matches,
            "sha256": actual_hash,
            "bytes": actual_bytes,
        }
    binding = document.get("formal_mainline_binding")
    binding_valid = isinstance(binding, dict)
    binding_rows: dict[str, object] = {}
    if isinstance(binding, dict):
        protocol_path = Path(str(binding.get("protocol_path", "")))
        inputs = binding.get("inputs")
        sources = document.get("sources")
        binding_valid = (
            protocol_path.is_file()
            and isinstance(inputs, dict)
            and isinstance(sources, dict)
        )
        protocol_data: object = None
        if protocol_path.is_file():
            protocol_document = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
            if isinstance(protocol_document, dict):
                protocol_data = protocol_document.get("data")
        for name in ("community", "workload_sampler", "hardware_calibration"):
            entry = inputs.get(name) if isinstance(inputs, dict) else None
            protocol_entry = protocol_data.get(name) if isinstance(protocol_data, dict) else None
            source_id = entry.get("source_id") if isinstance(entry, dict) else None
            source_entry = sources.get(source_id) if isinstance(sources, dict) else None
            matches = (
                isinstance(entry, dict)
                and isinstance(protocol_entry, dict)
                and isinstance(source_entry, dict)
                and source_entry.get("used_in_formal_mainline") is True
                and entry.get("path") == protocol_entry.get("path")
                and entry.get("sha256") == protocol_entry.get("sha256")
            )
            binding_valid = binding_valid and matches
            binding_rows[name] = {
                "source_id": source_id,
                "source_declared_for_formal_mainline": (
                    isinstance(source_entry, dict)
                    and source_entry.get("used_in_formal_mainline") is True
                ),
                "protocol_path_matches": (
                    isinstance(entry, dict)
                    and isinstance(protocol_entry, dict)
                    and entry.get("path") == protocol_entry.get("path")
                ),
                "protocol_hash_matches": (
                    isinstance(entry, dict)
                    and isinstance(protocol_entry, dict)
                    and entry.get("sha256") == protocol_entry.get("sha256")
                ),
            }
    valid = valid and binding_valid
    return {
        "valid": valid,
        "manifest": str(path),
        "files": results,
        "formal_mainline_binding": {
            "valid": binding_valid,
            "inputs": binding_rows,
        },
    }


def _validate_semantics(name: str, frame: pd.DataFrame) -> bool:
    if name == "inference":
        return bool(
            (frame["request_tokens"] > 0).all()
            and (frame["response_tokens"] > 0).all()
            and (frame["total_tokens"] >= frame["request_tokens"]).all()
        )
    if name == "batch":
        return bool(
            (frame["work_gpu_seconds"] > 0).all()
            and (frame["gpu_demand_local"] > 0).all()
            and (frame["deadline_time_s"] > frame["release_time_s"]).all()
            and frame["deadline_is_synthetic"].all()
        )
    if name == "community":
        return bool(
            (frame["community_load_kw"] > 0).all() and (frame["pv_generation_kw"] >= 0).all()
        )
    if name == "dr":
        return bool(
            (frame["end_time"] > frame["start_time"]).all()
            and (frame["duration_minutes"] > 0).all()
            and frame["reduction_fraction"].between(0, 1, inclusive="neither").all()
        )
    return True
