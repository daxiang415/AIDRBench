from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd
import pytest

from aidrbench.data.frozen_scenarios import freeze_hourly_scenario, load_frozen_hourly_scenario
from aidrbench.evaluation.pi_frontier import (
    compute_and_save_pi_frontier,
    solve_frozen_pi_frontier,
    summarize_pi_firm_boundary,
    validate_pi_frontier,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/env/hourly_continuous.yaml"


def test_pi_frontier_rejects_nonpositive_worker_count(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="workers must be a positive integer"):
        compute_and_save_pi_frontier(
            tmp_path / "missing",
            durations_h=[1],
            output_directory=tmp_path / "output",
            workers=0,
        )


def test_frozen_pi_frontier_is_physical_and_duration_monotone(tmp_path: Path) -> None:
    frozen = freeze_hourly_scenario(CONFIG, seed=21, output_directory=tmp_path)
    artifact = load_frozen_hourly_scenario(str(frozen["output"]))

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "error",
            message="invalid value encountered in reduce",
            category=RuntimeWarning,
        )
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


def test_pi_scenario_optima_aggregate_to_confidence_bounded_firm_capacity() -> None:
    frontier = pd.DataFrame(
        {
            "scenario_hash": [f"{index:064x}" for index in range(100)],
            "event_id": [0] * 100,
            "duration_h": [2] * 100,
            "perfect_information_capacity_kw": [10.0] * 98 + [5.0] * 2,
            "physical_dynamic_upper_bound_kw": [20.0] * 100,
            "reference_mix_operating_peak_kw": [40.0] * 100,
            "worst_class_peak_kw": [45.0] * 100,
        }
    )

    boundary = summarize_pi_firm_boundary(
        frontier,
        reliability_targets=[0.95, 0.99],
        confidence_level=0.95,
        nominal_flexibility_fraction=0.50,
    ).set_index("reliability_target")

    assert boundary.loc[0.95, "perfect_information_firm_capacity_kw"] == pytest.approx(5.0)
    assert boundary.loc[0.95, "tolerance_order_statistic_rank"] == 2
    assert boundary.loc[0.95, "statistical_method"] == (
        "exact_binomial_nonparametric_lower_tolerance_bound"
    )
    assert boundary.loc[0.95, "sample_size_sufficient"]
    assert boundary.loc[0.95, "physical_gap_kw"] == pytest.approx(15.0)
    assert not boundary.loc[0.99, "sample_size_sufficient"]
    assert not boundary.loc[0.99, "estimable"]
    assert pd.isna(boundary.loc[0.99, "perfect_information_firm_capacity_kw"])
