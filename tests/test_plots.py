from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from aidrbench.evaluation.plots import plot_hourly_results


def _write_episode(root: Path, controller: str, seed: int) -> Path:
    episode = root / "episodes" / controller / f"seed_{seed}"
    episode.mkdir(parents=True)
    frame = pd.DataFrame(
        {
            "hour": [0, 1, 2, 3, 4],
            "pcc_power_kw": [90.0, 80.0, 75.0, 85.0, 90.0],
            "baseline_pcc_power_kw": [90.0, 90.0, 90.0, 90.0, 90.0],
            "pcc_limit_kw": [100.0, 80.0, 80.0, 100.0, 100.0],
            "dc_power_kw": [20.0, 10.0, 5.0, 15.0, 20.0],
            "backlog_gpu_h": [0.0, 2.0, 4.0, 2.0, 0.0],
            "compute_debt_kwh": [0.0, 1.0, 2.0, 1.0, 0.0],
            "event_active": [False, True, True, False, False],
            "is_clearance_tail": [False, False, False, False, True],
            "controller": [controller] * 5,
            "episode_seed": [seed] * 5,
        }
    )
    timeseries = episode / "timeseries.parquet"
    frame.to_parquet(timeseries, index=False)
    return timeseries


def test_plot_hourly_results_writes_representative_main_week(tmp_path: Path) -> None:
    benchmark = tmp_path / "benchmark"
    first = _write_episode(benchmark, "threshold", 20001)
    second = _write_episode(benchmark, "threshold", 20000)
    pd.DataFrame.from_records(
        [
            {"controller": "threshold", "seed": 20001, "timeseries": str(first)},
            {"controller": "threshold", "seed": 20000, "timeseries": str(second)},
        ]
    ).to_parquet(benchmark / "episodes.parquet", index=False)

    summary = plot_hourly_results(benchmark, tmp_path / "figures")

    record = summary["figures"][0]
    assert record["seed"] == 20000
    assert record["hours"] == 4
    assert Path(record["figure"]).stat().st_size > 0
    manifest = json.loads(Path(summary["manifest"]).read_text(encoding="utf-8"))
    assert manifest["figures"] == summary["figures"]
    assert manifest["include_clearance_tail"] is False


def test_plot_hourly_results_rejects_unavailable_controller(tmp_path: Path) -> None:
    benchmark = tmp_path / "benchmark"
    timeseries = _write_episode(benchmark, "threshold", 20000)
    pd.DataFrame.from_records(
        [{"controller": "threshold", "seed": 20000, "timeseries": str(timeseries)}]
    ).to_parquet(benchmark / "episodes.parquet", index=False)

    with pytest.raises(ValueError, match="not present"):
        plot_hourly_results(benchmark, tmp_path / "figures", controllers=["mpc"])
