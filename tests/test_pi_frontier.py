from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from aidrbench.data.frozen_scenarios import freeze_hourly_scenario, load_frozen_hourly_scenario
from aidrbench.evaluation.pi_frontier import solve_frozen_pi_frontier, validate_pi_frontier

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/env/hourly_continuous.yaml"


def test_frozen_pi_frontier_is_physical_and_duration_monotone(tmp_path: Path) -> None:
    frozen = freeze_hourly_scenario(CONFIG, seed=21, output_directory=tmp_path)
    artifact = load_frozen_hourly_scenario(str(frozen["output"]))

    frontier = solve_frozen_pi_frontier(artifact, durations_h=[1, 2, 3])

    assert list(frontier["capacity_layer"].unique()) == ["perfect_information"]
    assert list(frontier["duration_h"]) == [1, 2, 3]
    assert (frontier["perfect_information_capacity_kw"] >= 0.0).all()
    assert (
        frontier["perfect_information_capacity_kw"]
        <= frontier["physical_dynamic_upper_bound_kw"] + 1e-6
    ).all()
    assert (
        frontier["perfect_information_capacity_kw"].diff().dropna() <= 1e-6
    ).all()


def test_pi_frontier_validator_rejects_nonmonotone_capacity() -> None:
    frontier = pd.DataFrame(
        {
            "scenario_hash": ["a" * 64, "a" * 64],
            "event_id": [0, 0],
            "duration_h": [1, 2],
            "perfect_information_capacity_kw": [10.0, 11.0],
            "physical_dynamic_upper_bound_kw": [20.0, 20.0],
        }
    )

    with pytest.raises(ValueError, match="duration monotonicity"):
        validate_pi_frontier(frontier)
