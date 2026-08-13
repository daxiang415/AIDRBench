from __future__ import annotations

from pathlib import Path

import pytest

from aidrbench.evaluation.firm_flexibility import FirmFlexibilityCriteria
from aidrbench.evaluation.stress_test import (
    make_repeated_event_start_hours,
    run_repeated_event_stress_test,
)

ROOT = Path(__file__).resolve().parents[1]


def test_repeated_event_schedule_rejects_an_impossible_grid() -> None:
    with pytest.raises(ValueError, match="does not fit"):
        make_repeated_event_start_hours(
            episode_days=1,
            events_per_day=3,
            duration_h=4,
            inter_event_gap_h=12,
        )


def test_repeated_event_stress_certifies_each_event_ordinal() -> None:
    criteria = FirmFlexibilityCriteria(
        reliability_target=0.5,
        confidence_level=0.5,
        min_delivery_ratio=0.0,
        max_deadline_miss_rate=1.0,
        max_rebound_ratio=100.0,
        min_window_peak_relief_fraction=0.0,
        max_terminal_backlog_fraction=1.0,
    )

    certificates, outcomes = run_repeated_event_stress_test(
        config=ROOT / "configs/env/hourly_continuous.yaml",
        controllers=("threshold",),
        model_paths={},
        events_per_day=1,
        inter_event_gap_h=2,
        duration_h=2,
        candidate_reduction_fractions=(0.05,),
        seeds=(1, 2),
        criteria=criteria,
    )

    assert len(certificates) == 7
    assert set(certificates["event_ordinal"]) == set(range(1, 8))
    assert len(outcomes) == 14
    assert certificates["residual_flexibility_ratio"].iloc[0] == pytest.approx(1.0)
