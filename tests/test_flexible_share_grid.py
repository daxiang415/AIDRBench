from pathlib import Path

import pandas as pd
import pytest

from aidrbench.evaluation.flexible_share_grid import design
from aidrbench.evaluation.flexible_share_grid_analysis import contrast_plan
from aidrbench.evaluation.flexible_share_sensitivity import load_spec

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def grid_spec(tmp_path: Path) -> dict:
    spec = load_spec(ROOT / "configs/sensitivity/nature_flexible_share_v3.yaml")
    pd.DataFrame(
        [
            {"case": "work_low_010", "workload_fraction": 0.1, "gpu_pool_fraction": 0.4},
            {"case": "reference", "workload_fraction": 0.75, "gpu_pool_fraction": 0.6},
        ]
    ).to_parquet(tmp_path / "service_gate.parquet", index=False)
    pd.DataFrame(
        [{"case": "work_010", "workload_fraction": 0.1, "gpu_pool_fraction": 0.6}]
    ).to_parquet(tmp_path / "structural_screen.parquet", index=False)
    return {**spec, "prior_results": str(tmp_path)}


def test_joint_grid_keeps_every_coordinate_and_accounts_for_both_pools(grid_spec: dict) -> None:
    grid = design(grid_spec)
    assert len(grid) == 54
    assert grid.structurally_feasible.sum() == 32
    assert (~grid.structurally_feasible).sum() == 22
    assert (grid.flexible_gpu_count + grid.rigid_gpu_count).eq(576).all()
    assert (grid.flexible_work_gpu_h_per_hour + grid.rigid_work_gpu_h_per_hour).tolist() == (
        pytest.approx([374.4] * 54)
    )
    assert set(grid.case) >= {"work_low_010", "work_010"}
    assert grid.reused_v2_case.sum() == 1


def test_flexible_mean_overload_is_not_a_rigid_construction_failure(grid_spec: dict) -> None:
    grid = design(grid_spec)
    row = grid.loc[(grid.workload_fraction == 0.6) & (grid.gpu_pool_fraction == 0.1)].iloc[0]
    assert row.structurally_feasible
    assert row.mean_arrivals_exceed_flexible_pool
    assert row.screening_status == "constructible"
    rigid_failure = grid.loc[
        (grid.workload_fraction == 0.1) & (grid.gpu_pool_fraction == 0.9)
    ].iloc[0]
    assert not rigid_failure.structurally_feasible
    assert rigid_failure.required_rigid_utilization > 1


def test_grid_does_not_silently_duplicate_coordinates(grid_spec: dict) -> None:
    repeated = {**grid_spec, "grid_workload_fractions": [0.1, 0.1]}
    with pytest.raises(ValueError, match="duplicate grid coordinates"):
        design(repeated)


def test_paired_interactions_keep_the_declared_four_corner_signs(grid_spec: dict) -> None:
    grid = design(grid_spec)
    feasible = set(grid.loc[grid.structurally_feasible, "case"]) | {"reference"}
    contrasts, skipped = contrast_plan(grid_spec, grid, feasible)
    corner = next(c for c in contrasts if c["label"] == "work 10-20%, GPU 20-30%")
    assert corner["terms"] == {
        "grid_f020_g030": 1,
        "grid_f010_g030": -1,
        "grid_f020_g020": -1,
        "grid_f010_g020": 1,
    }
    assert all(sum(c["terms"].values()) == 0 for c in contrasts)
    assert all(set(c["terms"]).issubset(feasible) for c in contrasts)
    assert len({tuple(sorted(c["terms"].items())) for c in contrasts}) == len(contrasts)
    assert skipped
