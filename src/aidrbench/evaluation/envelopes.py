"""Comparison of static planning envelopes and certified job-derived flexibility."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

_REQUIRED_CERTIFICATE_COLUMNS = frozenset(
    {
        "controller",
        "duration_h",
        "certified_reduction_kw",
        "dc_peak_kw",
    }
)


def load_certificate_table(path: str | Path) -> pd.DataFrame:
    """Load an aggregate certificate table or a directory created by ``certify``."""

    location = Path(path)
    table_path = location / "certificates.parquet" if location.is_dir() else location
    if not table_path.is_file():
        raise FileNotFoundError(f"certificate table does not exist: {table_path}")
    table = pd.read_parquet(table_path)
    missing = _REQUIRED_CERTIFICATE_COLUMNS.difference(table.columns)
    if missing:
        raise ValueError(f"certificate table is missing columns: {sorted(missing)}")
    return table


def compare_static_envelopes(
    certificates: pd.DataFrame,
    *,
    static_fractions: Sequence[float],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare each fixed envelope against a duration-specific certificate."""

    if certificates.empty:
        raise ValueError("cannot compare envelopes for an empty certificate table")
    missing = _REQUIRED_CERTIFICATE_COLUMNS.difference(certificates.columns)
    if missing:
        raise ValueError(f"certificate table is missing columns: {sorted(missing)}")
    fractions = sorted({float(value) for value in static_fractions})
    if not fractions or fractions[0] < 0.0 or fractions[-1] > 1.0:
        raise ValueError("static_fractions must be non-empty values in [0, 1]")
    rows: list[dict[str, object]] = []
    for certificate in certificates.to_dict(orient="records"):
        certified_kw = float(certificate["certified_reduction_kw"])
        dc_peak_kw = float(certificate["dc_peak_kw"])
        for fraction in fractions:
            static_kw = fraction * dc_peak_kw
            bias_kw = static_kw - certified_kw
            row: dict[str, object] = {str(key): value for key, value in certificate.items()}
            row.update(
                {
                    "static_fraction": fraction,
                    "static_reduction_kw": static_kw,
                    "bias_kw": bias_kw,
                    "relative_bias": bias_kw / max(certified_kw, 1e-6),
                    "static_overcommits": static_kw > certified_kw + 1e-9,
                }
            )
            rows.append(row)
    comparison = pd.DataFrame.from_records(rows)
    summary = (
        comparison.groupby(["controller", "duration_h", "static_fraction"], as_index=False)
        .agg(
            static_reduction_kw=("static_reduction_kw", "mean"),
            certified_reduction_kw=("certified_reduction_kw", "mean"),
            mean_bias_kw=("bias_kw", "mean"),
            mean_relative_bias=("relative_bias", "mean"),
            false_commitment_probability=("static_overcommits", "mean"),
            comparisons=("static_overcommits", "size"),
        )
        .sort_values(["controller", "duration_h", "static_fraction"], ignore_index=True)
    )
    return comparison, summary


def save_envelope_comparison(
    comparison: pd.DataFrame,
    summary: pd.DataFrame,
    *,
    certificate_paths: Sequence[str | Path],
    output_directory: str | Path,
) -> dict[str, str]:
    """Persist comparison tables and an input manifest for reproducibility."""

    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    comparison_path = output / "envelope_bias.parquet"
    summary_path = output / "envelope_bias_summary.parquet"
    manifest_path = output / "envelope_bias.json"
    comparison.to_parquet(comparison_path, index=False)
    summary.to_parquet(summary_path, index=False)
    manifest_path.write_text(
        json.dumps(
            {
                "certificate_paths": [str(path) for path in certificate_paths],
                "comparison": str(comparison_path),
                "summary": str(summary_path),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "comparison": str(comparison_path),
        "summary": str(summary_path),
        "manifest": str(manifest_path),
    }
