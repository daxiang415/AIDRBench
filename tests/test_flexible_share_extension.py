from pathlib import Path

import pandas as pd
import pytest
import yaml

from aidrbench.evaluation.flexible_share_extension import new_cases, structural_screen
from aidrbench.evaluation.flexible_share_sensitivity import (
    case_document,
    load_spec,
    scaled_arrivals,
)

ROOT = Path(__file__).resolve().parents[1]


def test_low_workload_curve_keeps_both_pools_within_average_physical_capacity() -> None:
    spec = load_spec(ROOT / "configs/sensitivity/nature_flexible_share_v2.yaml")
    parent = yaml.safe_load((ROOT / "configs/env/nature_mainline_development.yaml").read_text())
    cases = new_cases(spec)
    assert [c.workload_fraction for c in cases] == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    for case in cases:
        _, facts = case_document(parent, case, total_work_gpu_h_per_hour=374.4)
        assert facts["flexible_gpu_count"] == 230
        assert facts["rigid_gpu_count"] == 346
        assert facts["rigid_gpu_utilization"] <= 1
        assert facts["actual_flexible_pool_utilization"] <= 1
        assert facts["flexible_work_gpu_h_per_hour"] + facts[
            "rigid_work_gpu_h_per_hour"
        ] == pytest.approx(374.4)


def test_infeasible_original_pool_screen_is_not_counted_as_simulation_failure() -> None:
    spec = load_spec(ROOT / "configs/sensitivity/nature_flexible_share_v2.yaml")
    screen = structural_screen(spec)
    assert screen["rigid_work_gpu_h_per_hour"].tolist() == pytest.approx([336.96, 299.52, 262.08])
    assert not screen["structurally_feasible"].any()
    assert screen["required_rigid_utilization"].gt(1).all()
    assert screen["scenario_count"].eq(0).all()


def test_low_fraction_arrivals_keep_times_without_inventing_flexible_inference() -> None:
    spec = load_spec(ROOT / "configs/sensitivity/nature_flexible_share_v2.yaml")
    source = pd.DataFrame(
        {
            "job_class": ["training", "training", "offline_inference"],
            "arrival_gpu_h": [70.0, 30.0, 50.0],
            "timestamp_index": [0, 3, 2],
            "slack_hours": [12, 24, 4],
        }
    )
    for case in new_cases(spec)[:3]:
        result = scaled_arrivals(source, case)
        assert result["job_class"].tolist() == ["training", "training"]
        assert result["arrival_gpu_h"].sum() == pytest.approx(200 * case.workload_fraction)
        assert result["timestamp_index"].tolist() == [0, 3]
        assert result["slack_hours"].tolist() == [12, 24]
