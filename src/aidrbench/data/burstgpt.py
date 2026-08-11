"""BurstGPT ingestion with deterministic filtering and schema normalization."""

from __future__ import annotations

import glob
from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = (
    "timestamp_s",
    "session_id",
    "elapsed_time_s",
    "original_model_label",
    "request_tokens",
    "response_tokens",
    "total_tokens",
    "log_type",
    "source_file",
)


def _column_lookup(frame: pd.DataFrame) -> dict[str, str]:
    return {str(column).strip().lower().replace("_", " "): str(column) for column in frame.columns}


def _column(frame: pd.DataFrame, *names: str) -> pd.Series[Any]:
    lookup = _column_lookup(frame)
    for name in names:
        normalized = name.strip().lower().replace("_", " ")
        if normalized in lookup:
            return frame[lookup[normalized]]
    raise ValueError(f"missing BurstGPT column; expected one of {names}")


def _optional_column(frame: pd.DataFrame, *names: str) -> pd.Series[Any] | None:
    try:
        return _column(frame, *names)
    except ValueError:
        return None


def resolve_inputs(input_pattern: str) -> list[Path]:
    """Resolve a file or glob in stable lexical order."""

    paths = [Path(path) for path in sorted(glob.glob(input_pattern))]
    if not paths and Path(input_pattern).is_file():
        paths = [Path(input_pattern)]
    if not paths:
        raise FileNotFoundError(f"no BurstGPT files matched: {input_pattern}")
    return paths


def preprocess_burstgpt(
    input_pattern: str,
    output: str | Path,
    *,
    time_scale: float = 1.0,
    exclude_failed_responses: bool = True,
) -> dict[str, object]:
    """Normalize one or more official BurstGPT CSV files into Parquet."""

    if time_scale <= 0:
        raise ValueError("time_scale must be greater than zero")

    paths = resolve_inputs(input_pattern)
    frames: list[pd.DataFrame] = []
    input_rows = 0
    for path in paths:
        raw = pd.read_csv(path)
        input_rows += len(raw)
        timestamp = pd.to_numeric(_column(raw, "timestamp"), errors="coerce")
        request_tokens = pd.to_numeric(_column(raw, "request tokens"), errors="coerce")
        response_tokens = pd.to_numeric(_column(raw, "response tokens"), errors="coerce")
        total_source = _optional_column(raw, "total tokens")
        total_tokens = (
            pd.to_numeric(total_source, errors="coerce")
            if total_source is not None
            else request_tokens + response_tokens
        )
        session_source = _optional_column(raw, "session id")
        elapsed_source = _optional_column(raw, "elapsed time", "elapsed time s")
        log_source = _optional_column(raw, "log type")

        row_number = pd.Series(raw.index, index=raw.index, dtype="int64")
        session_id = (
            session_source.astype("string")
            if session_source is not None
            else path.name + ":" + row_number.astype("string").str.zfill(9)
        )
        elapsed = (
            pd.to_numeric(elapsed_source, errors="coerce")
            if elapsed_source is not None
            else timestamp - timestamp.min()
        )
        frame = pd.DataFrame(
            {
                "timestamp_s": timestamp,
                "session_id": session_id,
                "elapsed_time_s": elapsed,
                "original_model_label": _column(raw, "model").astype("string"),
                "request_tokens": request_tokens,
                "response_tokens": response_tokens,
                "total_tokens": total_tokens,
                "log_type": (
                    log_source.astype("string")
                    if log_source is not None
                    else pd.Series("unknown", index=raw.index, dtype="string")
                ),
                "source_file": path.name,
            }
        )
        frames.append(frame)

    result = pd.concat(frames, ignore_index=True)
    result = result.dropna(
        subset=["timestamp_s", "request_tokens", "response_tokens", "total_tokens"]
    )
    result = result[result["request_tokens"] > 0]
    if exclude_failed_responses:
        result = result[result["response_tokens"] > 0]
    if result.empty:
        raise ValueError("BurstGPT preprocessing produced no valid requests")

    timestamp_origin = float(result["timestamp_s"].min())
    result["timestamp_s"] = (
        timestamp_origin + (result["timestamp_s"] - timestamp_origin) / time_scale
    )
    result["elapsed_time_s"] = result["elapsed_time_s"] / time_scale
    for column in ("request_tokens", "response_tokens", "total_tokens"):
        result[column] = result[column].astype("int64")
    result = result.sort_values(["timestamp_s", "source_file", "session_id"], kind="stable")
    result = result.loc[:, REQUIRED_COLUMNS].reset_index(drop=True)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(output_path, index=False)
    return {
        "dataset": "burstgpt",
        "inputs": [str(path) for path in paths],
        "input_rows": input_rows,
        "output_rows": len(result),
        "dropped_rows": input_rows - len(result),
        "time_scale": time_scale,
        "exclude_failed_responses": exclude_failed_responses,
        "output": str(output_path),
    }
