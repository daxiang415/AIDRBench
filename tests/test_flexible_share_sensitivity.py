from pathlib import Path

import pandas as pd
import pytest
import yaml

from aidrbench.envs.hourly_config import load_hourly_environment_config
from aidrbench.evaluation.flexible_share_sensitivity import (
    ShareCase,
    case_document,
    cases_for,
    load_spec,
    scaled_arrivals,
)

ROOT = Path(__file__).resolve().parents[1]


def test_share_grid_conserves_total_work_and_counts_integer_gpu_pools() -> None:
    spec = load_spec(ROOT / "configs/sensitivity/nature_flexible_share_v1.yaml")
    parent = yaml.safe_load((ROOT / "configs/env/nature_mainline_development.yaml").read_text())
    cases = cases_for(spec)
    assert len(cases) == 13
    for case in cases:
        document, facts = case_document(parent, case, total_work_gpu_h_per_hour=374.4)
        config = load_hourly_environment_config(document)
        flexible = 576 * config.flexible_arrival_utilization * config.workload_mix.flexible_share
        rigid = facts["rigid_gpu_count"] * config.rigid_gpu_utilization
        assert flexible + rigid == pytest.approx(374.4, abs=1e-10)
        assert flexible / (flexible + rigid) == pytest.approx(case.workload_fraction)
        assert facts["flexible_gpu_count"] + facts["rigid_gpu_count"] == 576
        assert "target_total_utilization" in parent["workload"]
    # These points intentionally test overload, rather than lowering total work
    # until a small flexible pool becomes feasible.
    small_pool = next(case for case in cases if case.name == "pool_040")
    _, facts = case_document(parent, small_pool, total_work_gpu_h_per_hour=374.4)
    assert facts["actual_flexible_pool_utilization"] > 1


def test_scaling_preserves_parent_record_times_and_class_work_targets() -> None:
    arrivals = pd.DataFrame(
        {
            "job_class": ["training", "training", "offline_inference"],
            "timestamp_index": [0, 1, 0],
            "slack_hours": [6, 24, 4],
            "arrival_gpu_h": [80.0, 20.0, 50.0],
        }
    )
    for fraction in (0.4, 0.5, 0.6, 0.75, 0.9, 0.95):
        result = scaled_arrivals(arrivals, ShareCase("test", "workload", fraction, 0.6))
        assert result["arrival_gpu_h"].sum() == pytest.approx(200 * fraction)
        assert result.loc[result["job_class"] == "training", "slack_hours"].tolist() == [6, 24]
        assert result.loc[result["job_class"] == "training", "timestamp_index"].tolist() == [0, 1]
    assert arrivals["arrival_gpu_h"].tolist() == [80, 20, 50]


def test_gpu_pool_only_case_preserves_every_arrival() -> None:
    arrivals = pd.DataFrame(
        {"job_class": ["training", "offline_inference"], "arrival_gpu_h": [100.0, 50.0]}
    )
    pd.testing.assert_frame_equal(
        scaled_arrivals(arrivals, ShareCase("pool", "gpu_pool", 0.75, 0.5)), arrivals
    )


def test_share_case_rejects_rigid_pool_overload_instead_of_clipping() -> None:
    parent = yaml.safe_load((ROOT / "configs/env/nature_mainline_development.yaml").read_text())
    with pytest.raises(ValueError, match="rigid demand exceeds"):
        case_document(
            parent, ShareCase("bad", "workload", 0.1, 0.6), total_work_gpu_h_per_hour=374.4
        )


def test_reference_changes_only_rounding_correction_in_rigid_power() -> None:
    parent = yaml.safe_load((ROOT / "configs/env/nature_mainline_development.yaml").read_text())
    reference, facts = case_document(
        parent, ShareCase("reference", "reference", 0.75, 0.6), total_work_gpu_h_per_hour=374.4
    )
    assert reference["workload"]["workload_mix"] == parent["workload"]["workload_mix"]
    assert reference["workload"]["flexible_arrival_utilization"] == pytest.approx(0.65)
    assert facts["rigid_gpu_utilization"] == pytest.approx(93.6 / 230)
    assert facts["flexible_work_gpu_h_per_hour"] == pytest.approx(280.8)
