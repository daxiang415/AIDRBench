from __future__ import annotations

from pathlib import Path

import cvxpy as cp
import pandas as pd
import pytest


def test_highs_and_parquet_stack_is_available_in_a_clean_install(tmp_path: Path) -> None:
    """Exercise the external pieces required by every formal optimization path."""

    assert "HIGHS" in cp.installed_solvers()
    dispatch = cp.Variable(2, nonneg=True)
    problem = cp.Problem(
        cp.Maximize(dispatch[0] + 2.0 * dispatch[1]),
        [dispatch <= 1.0, cp.sum(dispatch) <= 1.5],
    )

    objective = problem.solve(solver="HIGHS")

    assert problem.status == "optimal"
    assert objective == pytest.approx(2.5)
    artifact = tmp_path / "optimization-smoke.parquet"
    pd.DataFrame({"dispatch": dispatch.value}).to_parquet(artifact, index=False)
    restored = pd.read_parquet(artifact)
    assert restored["dispatch"].sum() == pytest.approx(1.5)
