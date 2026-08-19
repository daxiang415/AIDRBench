from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from aidrbench.data.splits import sha256_file
from aidrbench.evaluation.exhaustion import (
    compute_repeated_event_exhaustion_diagnostics,
    freeze_repeated_event_scenarios,
    load_repeated_event_exhaustion_specification,
    repeated_event_start_hours,
)

ROOT = Path(__file__).resolve().parents[1]


def _write_specification(tmp_path: Path) -> Path:
    base = yaml.safe_load(
        (ROOT / "configs/env/hourly_continuous.yaml").read_text(encoding="utf-8")
    )
    assert isinstance(base, dict)
    assert isinstance(base["env"], dict)
    base["env"]["episode_days"] = 1
    base["env"]["clearance_tail_hours"] = 12
    base_path = tmp_path / "base.yaml"
    base_path.write_text(yaml.safe_dump(base, sort_keys=False), encoding="utf-8")
    capacity_path = tmp_path / "capacity.parquet"
    pd.DataFrame.from_records(
        [{"duration_h": 2, "notice_h": 0, "na_capacity_kw": 5.0}]
    ).to_parquet(capacity_path, index=False)
    specification = {
        "schema_version": 1,
        "model_a_git_commit": "a" * 40,
        "dataset_role": "development_repeated_event_exhaustion",
        "base_environment_config": str(base_path),
        "controller_config": str(
            ROOT / "configs/controller/nature_robust_mpc_v1.yaml"
        ),
        "first_event_start_hour": 8,
        "max_event_count": 2,
        "duration_hours": [2],
        "recovery_gaps_hours": [2],
        "notice_hours": 0,
        "reliability_target": 0.95,
        "confidence_level": 0.95,
        "capacity_source": {
            "path": str(capacity_path),
            "sha256": sha256_file(capacity_path),
            "column": "na_capacity_kw",
            "notice_hours": 0,
        },
        "criteria": {
            "min_delivery_ratio": 0.95,
            "min_interval_delivery_ratio": 0.95,
            "max_deadline_miss_rate": 0.01,
            "max_rebound_ratio": 0.25,
            "min_window_peak_relief_fraction": 0.50,
            "max_terminal_backlog_fraction": 0.02,
        },
    }
    path = tmp_path / "exhaustion.yaml"
    path.write_text(yaml.safe_dump(specification, sort_keys=False), encoding="utf-8")
    return path


def test_exhaustion_specification_is_strict_and_checks_horizon(tmp_path: Path) -> None:
    path = _write_specification(tmp_path)
    specification = load_repeated_event_exhaustion_specification(path)

    assert repeated_event_start_hours(
        specification,
        duration_h=2,
        recovery_gap_h=2,
        main_hours=24,
    ) == (8, 12)
    with pytest.raises(ValueError, match="exceeds horizon"):
        repeated_event_start_hours(
            specification,
            duration_h=8,
            recovery_gap_h=8,
            main_hours=24,
        )

    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["implicit_default"] = True
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="fields mismatch"):
        load_repeated_event_exhaustion_specification(path)


def test_repeated_event_development_pipeline(tmp_path: Path) -> None:
    specification_path = _write_specification(tmp_path)
    scenario_root = tmp_path / "scenarios"
    frozen = freeze_repeated_event_scenarios(
        specification_path,
        seeds=[101],
        output_directory=scenario_root,
    )

    assert frozen["program_count"] == 1
    assert frozen["scenario_count"] == 1
    result = compute_repeated_event_exhaustion_diagnostics(
        scenario_root,
        specification_path=specification_path,
        output_directory=tmp_path / "result",
    )

    events = pd.read_parquet(result["event_outcomes"])
    summary = pd.read_parquet(result["exhaustion_summary"])
    joint = pd.read_parquet(result["joint_episode_summary"])
    assert list(events["event_ordinal"]) == [1, 2]
    assert list(summary["event_ordinal"]) == [1, 2]
    assert len(joint) == 1
    assert summary["fixed_commitment_residual_flexibility_ratio"].notna().all()
