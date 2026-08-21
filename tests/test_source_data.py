from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from aidrbench.evaluation.source_data import (
    export_manuscript_source_data,
    load_source_data_specification,
)


def _write_specification(path: Path, tables: list[dict[str, object]]) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "aidrbench.manuscript_source_data_specification.v1",
                "bundle_id": "test_bundle",
                "tables": tables,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_default_nature_source_data_specification_is_valid() -> None:
    specification = load_source_data_specification("configs/paper/nature_source_data_v1.yaml")
    assert specification.bundle_id == "nature_communications_model_a_v1"
    assert len(specification.tables) == 16
    assert {table.table_id for table in specification.tables} >= {
        "fig1_fig2_pi_firm_boundaries",
        "fig3_exhaustion_event_summary",
        "fig4_hosting_paired_contrasts",
        "fig5_locked_ood_certificates",
    }


def test_export_source_data_combines_labels_sorts_and_hashes(tmp_path: Path) -> None:
    pd.DataFrame(
        {
            "duration_h": [8, 4],
            "capacity_kw": [38.0, 40.0],
        }
    ).to_parquet(tmp_path / "development.parquet", index=False)
    pd.DataFrame(
        {
            "duration_h": [8, 4],
            "capacity_kw": [37.0, 39.0],
        }
    ).to_parquet(tmp_path / "validation.parquet", index=False)

    specification = tmp_path / "source_data.yaml"
    _write_specification(
        specification,
        [
            {
                "table_id": "fig2_capacity",
                "figures": [2],
                "panels": ["a"],
                "output": "fig2_capacity.csv",
                "inputs": [
                    {
                        "path": "development.parquet",
                        "labels": {"evaluation_split": "development"},
                    },
                    {
                        "path": "validation.parquet",
                        "labels": {"evaluation_split": "validation"},
                    },
                ],
                "columns": ["evaluation_split", "duration_h", "capacity_kw"],
                "sort_by": ["evaluation_split", "duration_h"],
            }
        ],
    )

    summary = export_manuscript_source_data(
        specification,
        tmp_path / "bundle",
        repository_root=tmp_path,
    )
    assert summary["table_count"] == 1
    assert summary["row_count"] == 4

    exported_path = tmp_path / "bundle" / "fig2_capacity.csv"
    exported = pd.read_csv(exported_path)
    assert exported.to_dict(orient="records") == [
        {
            "evaluation_split": "development",
            "duration_h": 4,
            "capacity_kw": 40.0,
        },
        {
            "evaluation_split": "development",
            "duration_h": 8,
            "capacity_kw": 38.0,
        },
        {
            "evaluation_split": "validation",
            "duration_h": 4,
            "capacity_kw": 39.0,
        },
        {
            "evaluation_split": "validation",
            "duration_h": 8,
            "capacity_kw": 37.0,
        },
    ]

    manifest = json.loads((tmp_path / "bundle" / "source_data_manifest.json").read_text())
    assert manifest["tables"][0]["row_count"] == 4
    assert (
        manifest["tables"][0]["output_sha256"]
        == hashlib.sha256(exported_path.read_bytes()).hexdigest()
    )


def test_export_source_data_fails_closed_on_missing_columns(tmp_path: Path) -> None:
    pd.DataFrame({"duration_h": [4]}).to_parquet(tmp_path / "input.parquet", index=False)
    specification = tmp_path / "source_data.yaml"
    _write_specification(
        specification,
        [
            {
                "table_id": "fig2_capacity",
                "figures": [2],
                "panels": ["a"],
                "output": "fig2_capacity.csv",
                "inputs": [{"path": "input.parquet"}],
                "columns": ["duration_h", "capacity_kw"],
                "sort_by": ["duration_h"],
            }
        ],
    )

    with pytest.raises(ValueError, match="missing columns.*capacity_kw"):
        export_manuscript_source_data(
            specification,
            tmp_path / "bundle",
            repository_root=tmp_path,
        )


def test_source_data_specification_rejects_output_path_traversal(
    tmp_path: Path,
) -> None:
    specification = tmp_path / "source_data.yaml"
    _write_specification(
        specification,
        [
            {
                "table_id": "fig2_capacity",
                "figures": [2],
                "panels": ["a"],
                "output": "../fig2_capacity.csv",
                "inputs": [{"path": "input.parquet"}],
                "columns": ["duration_h"],
                "sort_by": [],
            }
        ],
    )

    with pytest.raises(ValueError, match="plain .csv filename"):
        load_source_data_specification(specification)
