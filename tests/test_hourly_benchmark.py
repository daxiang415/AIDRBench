from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from aidrbench.evaluation.hourly_benchmark import (
    aggregate_hourly_benchmark,
    run_hourly_benchmark,
)


def test_aggregate_hourly_benchmark_reports_mean_and_ci() -> None:
    episodes = pd.DataFrame(
        {
            "controller": ["threshold", "threshold", "no_control"],
            "seed": [1, 2, 1],
            "energy_above_limit_kwh": [2.0, 4.0, 8.0],
        }
    )

    aggregate = aggregate_hourly_benchmark(episodes).set_index("controller")

    assert aggregate.loc["threshold", "episodes"] == 2
    assert aggregate.loc["threshold", "energy_above_limit_kwh_mean"] == pytest.approx(3.0)
    assert aggregate.loc["threshold", "energy_above_limit_kwh_ci95"] > 0.0
    assert pd.isna(aggregate.loc["no_control", "energy_above_limit_kwh_ci95"])


def test_hourly_benchmark_persists_matched_rule_episodes(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]

    summary = run_hourly_benchmark(
        config=root / "configs/env/hourly_continuous.yaml",
        controllers=("no_control", "threshold", "robust_mpc"),
        seeds=(5,),
        output_directory=tmp_path,
    )

    episodes = pd.read_parquet(summary["episode_metrics"])
    aggregate = pd.read_parquet(summary["aggregate_metrics"])
    assert summary["episodes"] == 3
    assert set(episodes["controller"]) == {"no_control", "threshold", "robust_mpc"}
    assert set(episodes["action_mode"]) == {"continuous"}
    assert set(aggregate["controller"]) == {"no_control", "threshold", "robust_mpc"}
    assert set(aggregate["action_mode"]) == {"continuous"}
    assert set(aggregate["information_structure"]) == {
        "causal_control_state",
        "causal_control_state_plus_6h_environment_forecast",
    }
    assert Path(str(summary["manifest"])).is_file()
