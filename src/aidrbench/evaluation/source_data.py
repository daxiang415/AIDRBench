"""Deterministic, provenance-aware source-data exports for manuscript figures."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

Scalar = str | int | float | bool

_TABLE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_]*$")


@dataclass(frozen=True)
class SourceInputSpecification:
    """One immutable table input and any labels added during export."""

    path: str
    labels: dict[str, Scalar]


@dataclass(frozen=True)
class SourceTableSpecification:
    """Exact projection used to construct one manuscript source-data table."""

    table_id: str
    figures: tuple[int, ...]
    panels: tuple[str, ...]
    output: str
    inputs: tuple[SourceInputSpecification, ...]
    columns: tuple[str, ...]
    sort_by: tuple[str, ...]


@dataclass(frozen=True)
class SourceDataSpecification:
    """Validated source-data bundle specification."""

    schema_version: str
    bundle_id: str
    tables: tuple[SourceTableSpecification, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mapping(value: object, *, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a mapping")
    if not all(isinstance(key, str) for key in value):
        raise ValueError(f"{field} keys must be strings")
    return {str(key): item for key, item in value.items()}


def _string(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _string_sequence(
    value: object,
    *,
    field: str,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and bool(item.strip()) for item in value
    ):
        raise ValueError(f"{field} must be a list of strings")
    if not allow_empty and not value:
        raise ValueError(f"{field} must not be empty")
    return tuple(value)


def _integer_sequence(value: object, *, field: str) -> tuple[int, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field} must be a non-empty list of integers")
    if not all(isinstance(item, int) and not isinstance(item, bool) and item > 0 for item in value):
        raise ValueError(f"{field} must contain positive integers")
    return tuple(value)


def _labels(value: object, *, field: str) -> dict[str, Scalar]:
    if value is None:
        return {}
    document = _mapping(value, field=field)
    labels: dict[str, Scalar] = {}
    for key, item in document.items():
        if not isinstance(item, (str, int, float, bool)):
            raise ValueError(f"{field}.{key} must be a string, number, or boolean")
        labels[key] = item
    return labels


def _load_input(value: object, *, field: str) -> SourceInputSpecification:
    document = _mapping(value, field=field)
    return SourceInputSpecification(
        path=_string(document.get("path"), field=f"{field}.path"),
        labels=_labels(document.get("labels"), field=f"{field}.labels"),
    )


def _load_table(value: object, *, field: str) -> SourceTableSpecification:
    document = _mapping(value, field=field)
    table_id = _string(document.get("table_id"), field=f"{field}.table_id")
    if _TABLE_ID_PATTERN.fullmatch(table_id) is None:
        raise ValueError(f"{field}.table_id must contain only lowercase letters, digits, and '_'")

    output = _string(document.get("output"), field=f"{field}.output")
    output_path = Path(output)
    if output_path.name != output or output_path.suffix.lower() != ".csv":
        raise ValueError(f"{field}.output must be a plain .csv filename")

    raw_inputs = document.get("inputs")
    if not isinstance(raw_inputs, list) or not raw_inputs:
        raise ValueError(f"{field}.inputs must be a non-empty list")
    inputs = tuple(
        _load_input(item, field=f"{field}.inputs[{index}]") for index, item in enumerate(raw_inputs)
    )

    columns = _string_sequence(document.get("columns"), field=f"{field}.columns")
    if len(set(columns)) != len(columns):
        raise ValueError(f"{field}.columns contains duplicates")
    sort_by = _string_sequence(
        document.get("sort_by", []),
        field=f"{field}.sort_by",
        allow_empty=True,
    )
    if not set(sort_by).issubset(columns):
        raise ValueError(f"{field}.sort_by must be a subset of columns")

    return SourceTableSpecification(
        table_id=table_id,
        figures=_integer_sequence(document.get("figures"), field=f"{field}.figures"),
        panels=_string_sequence(document.get("panels"), field=f"{field}.panels"),
        output=output,
        inputs=inputs,
        columns=columns,
        sort_by=sort_by,
    )


def load_source_data_specification(path: str | Path) -> SourceDataSpecification:
    """Load and validate a manuscript source-data bundle specification."""

    specification_path = Path(path)
    document = _mapping(
        yaml.safe_load(specification_path.read_text(encoding="utf-8")),
        field="source-data specification",
    )
    raw_tables = document.get("tables")
    if not isinstance(raw_tables, list) or not raw_tables:
        raise ValueError("tables must be a non-empty list")
    tables = tuple(
        _load_table(item, field=f"tables[{index}]") for index, item in enumerate(raw_tables)
    )

    table_ids = [table.table_id for table in tables]
    outputs = [table.output for table in tables]
    if len(set(table_ids)) != len(table_ids):
        raise ValueError("table_id values must be unique")
    if len(set(outputs)) != len(outputs):
        raise ValueError("output filenames must be unique")

    return SourceDataSpecification(
        schema_version=_string(document.get("schema_version"), field="schema_version"),
        bundle_id=_string(document.get("bundle_id"), field="bundle_id"),
        tables=tables,
    )


def _read_table(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported source-data input format: {path}")


def _csv_safe(value: object) -> object:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return value


def _git_state(repository_root: Path) -> dict[str, object]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "working_tree_dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
    }


def export_manuscript_source_data(
    specification_path: str | Path,
    output_directory: str | Path,
    *,
    repository_root: str | Path = ".",
) -> dict[str, object]:
    """Export exactly declared figure data and write a hash-bound manifest."""

    source_path = Path(specification_path).resolve()
    root = Path(repository_root).resolve()
    destination = Path(output_directory).resolve()
    specification = load_source_data_specification(source_path)
    destination.mkdir(parents=True, exist_ok=True)

    try:
        specification_display_path = source_path.relative_to(root).as_posix()
    except ValueError as error:
        raise ValueError(
            f"source-data specification escapes repository root: {source_path}"
        ) from error

    table_records: list[dict[str, object]] = []
    total_rows = 0
    for table in specification.tables:
        frames: list[pd.DataFrame] = []
        input_records: list[dict[str, object]] = []
        for source in table.inputs:
            input_path = (root / source.path).resolve()
            try:
                display_path = input_path.relative_to(root).as_posix()
            except ValueError as error:
                raise ValueError(
                    f"source-data input escapes repository root: {source.path}"
                ) from error

            frame = _read_table(input_path)
            for column, value in source.labels.items():
                if column in frame.columns:
                    raise ValueError(
                        f"{table.table_id}: label column already exists in {display_path}: {column}"
                    )
                frame[column] = value

            missing = sorted(set(table.columns).difference(frame.columns))
            if missing:
                raise ValueError(
                    f"{table.table_id}: missing columns in {display_path}: {', '.join(missing)}"
                )
            frames.append(frame.loc[:, list(table.columns)].copy())
            input_records.append(
                {
                    "path": display_path,
                    "sha256": _sha256(input_path),
                    "rows_read": int(len(frame)),
                    "labels": source.labels,
                }
            )

        exported = pd.concat(frames, ignore_index=True)
        if exported.empty:
            raise ValueError(f"{table.table_id}: source-data table must not be empty")
        if table.sort_by:
            exported = exported.sort_values(
                list(table.sort_by),
                kind="stable",
                na_position="last",
            )
        exported = exported.reset_index(drop=True)
        for column in exported.select_dtypes(include="object").columns:
            exported[column] = exported[column].map(_csv_safe)

        output_path = destination / table.output
        exported.to_csv(
            output_path,
            index=False,
            encoding="utf-8",
            lineterminator="\n",
            float_format="%.12g",
        )
        table_records.append(
            {
                "table_id": table.table_id,
                "figures": list(table.figures),
                "panels": list(table.panels),
                "output": table.output,
                "output_sha256": _sha256(output_path),
                "row_count": int(len(exported)),
                "columns": list(table.columns),
                "inputs": input_records,
            }
        )
        total_rows += int(len(exported))

    manifest: dict[str, object] = {
        "schema_version": "aidrbench.manuscript_source_data_manifest.v1",
        "bundle_id": specification.bundle_id,
        "source_specification": {
            "path": specification_display_path,
            "schema_version": specification.schema_version,
            "sha256": _sha256(source_path),
        },
        "software": {"git": _git_state(root)},
        "tables": table_records,
    }
    manifest_path = destination / "source_data_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "bundle_id": specification.bundle_id,
        "table_count": len(table_records),
        "row_count": total_rows,
        "manifest": str(manifest_path),
        "output_directory": str(destination),
    }
