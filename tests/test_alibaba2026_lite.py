from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from aidrbench.data.alibaba2026 import (
    ARRIVAL_OUTPUT_COLUMNS,
    SUMMARY_OUTPUT_COLUMNS,
    AlibabaDeadlinePolicy,
    make_alibaba_lite_hourly_arrivals,
    make_alibaba_lite_sampler_pool,
    preprocess_alibaba_summary,
)
from aidrbench.data.hourly import load_hourly_arrivals
from aidrbench.envs.community_ai_dr_env import ContinuousCommunityAIDemandResponseEnv


def _write_summary(path: Path) -> None:
    pd.DataFrame(
        [
            {
                "pod_id": "training-a",
                "workload_id": "workload-a",
                "gpu_spec_public": "h100",
                "priority_class": "LP",
                "job_type_public": "training",
                "model_type_public": "llm",
                "gpu_request": 4.0,
                "duration_hours": 2.0,
            },
            {
                "pod_id": "training-b",
                "workload_id": "workload-b",
                "gpu_spec_public": "h100",
                "priority_class": "LP",
                "job_type_public": "training",
                "model_type_public": "vision",
                "gpu_request": 2.0,
                "duration_hours": 8.0,
            },
            {
                "pod_id": "offline-a",
                "workload_id": "workload-c",
                "gpu_spec_public": "a100",
                "priority_class": "LP",
                "job_type_public": "offline_inference",
                "model_type_public": "llm",
                "gpu_request": 1.0,
                "duration_hours": 4.0,
            },
            {
                "pod_id": "online-a",
                "workload_id": "workload-d",
                "gpu_spec_public": "a100",
                "priority_class": "HP",
                "job_type_public": "online_inference",
                "model_type_public": "llm",
                "gpu_request": 1.0,
                "duration_hours": 1.0,
            },
            {
                "pod_id": "bad-gpu",
                "workload_id": "workload-e",
                "gpu_spec_public": "a100",
                "priority_class": "LP",
                "job_type_public": "training",
                "model_type_public": "llm",
                "gpu_request": 0.0,
                "duration_hours": 2.0,
            },
            {
                "pod_id": "bad-duration",
                "workload_id": "workload-f",
                "gpu_spec_public": "a100",
                "priority_class": "LP",
                "job_type_public": "training",
                "model_type_public": "llm",
                "gpu_request": 1.0,
                "duration_hours": 0.0,
            },
        ]
    ).to_parquet(path, index=False)


def test_preprocess_alibaba2026_summary_preserves_raw_long_tail(tmp_path: Path) -> None:
    source = tmp_path / "summary.parquet"
    output = tmp_path / "jobs_summary.parquet"
    _write_summary(source)

    summary = preprocess_alibaba_summary(source, output, winsorize_quantile=0.5)
    result = pd.read_parquet(output)

    assert summary["dataset"] == "alibaba_gpu_v2026_summary"
    assert summary["output_rows"] == 4
    assert tuple(result.columns) == SUMMARY_OUTPUT_COLUMNS
    assert result["duration_hours_raw"].max() == pytest.approx(8.0)
    assert result["duration_hours"].max() < result["duration_hours_raw"].max()
    assert result["requested_work_gpu_h"].equals(result["gpu_request"] * result["duration_hours"])
    assert result["source_mode"].unique().tolist() == ["alibaba2026_summary"]
    assert bool(result["duration_winsorized"].any())


def test_alibaba2026_lite_arrivals_are_reproducible_and_target_scaled(tmp_path: Path) -> None:
    source = tmp_path / "summary.parquet"
    normalized = tmp_path / "jobs_summary.parquet"
    _write_summary(source)
    preprocess_alibaba_summary(source, normalized, winsorize_quantile=None)
    kwargs = {
        "hours": 48,
        "total_gpu_count": 8,
        "flexible_arrival_utilization": 0.5,
        "workload_shares": {
            "training": 0.5,
            "offline_inference": 0.5,
            "online_inference": 0.0,
        },
        "flexible_fractions": {
            "training": 1.0,
            "offline_inference": 1.0,
            "online_inference": 0.0,
        },
        "flexible_priorities": ("LP",),
        "deadline_policy": AlibabaDeadlinePolicy(),
        "arrival_process": "nhpp",
        "seed": 23,
    }

    first = make_alibaba_lite_hourly_arrivals(normalized, **kwargs)
    second = make_alibaba_lite_hourly_arrivals(normalized, **kwargs)

    pd.testing.assert_frame_equal(first, second)
    assert tuple(first.columns) == ARRIVAL_OUTPUT_COLUMNS
    assert first["arrival_gpu_h"].sum() == pytest.approx(8 * 0.5 * 48)
    assert set(first["job_class"]) == {"training", "offline_inference"}
    assert first["slack_hours"].between(2, 48).all()
    assert first["source_mode"].unique().tolist() == ["alibaba2026_lite_calibrated_synthetic"]


def test_alibaba2026_sampler_pool_is_bounded_stratified_and_reproducible(
    tmp_path: Path,
) -> None:
    source = tmp_path / "summary.parquet"
    normalized = tmp_path / "jobs_summary.parquet"
    first_path = tmp_path / "sampler-a.parquet"
    second_path = tmp_path / "sampler-b.parquet"
    _write_summary(source)
    preprocess_alibaba_summary(source, normalized, winsorize_quantile=None)

    summary = make_alibaba_lite_sampler_pool(
        normalized,
        first_path,
        rows_per_stratum=1,
        seed=17,
        batch_size=2,
    )
    make_alibaba_lite_sampler_pool(
        normalized,
        second_path,
        rows_per_stratum=1,
        seed=17,
        batch_size=2,
    )
    sampled = pd.read_parquet(first_path)

    pd.testing.assert_frame_equal(sampled, pd.read_parquet(second_path))
    assert summary["rows"] == 2
    assert tuple(sampled.columns) == SUMMARY_OUTPUT_COLUMNS
    assert set(sampled["job_type_public"]) == {"training", "offline_inference"}
    assert sampled.groupby(["job_type_public", "priority_class"]).size().eq(1).all()


def test_alibaba2026_lite_requires_matching_flexible_samples(tmp_path: Path) -> None:
    source = tmp_path / "summary.parquet"
    normalized = tmp_path / "jobs_summary.parquet"
    _write_summary(source)
    preprocess_alibaba_summary(source, normalized)

    with pytest.raises(ValueError, match="offline_inference"):
        make_alibaba_lite_hourly_arrivals(
            normalized,
            hours=4,
            total_gpu_count=4,
            flexible_arrival_utilization=0.5,
            workload_shares={"training": 0.5, "offline_inference": 0.5},
            flexible_fractions={"training": 0.0, "offline_inference": 1.0},
            flexible_priorities=("HP",),
            seed=7,
        )


def test_hourly_environment_uses_alibaba_lite_summary_source(tmp_path: Path) -> None:
    source = tmp_path / "summary.parquet"
    normalized = tmp_path / "jobs_summary.parquet"
    _write_summary(source)
    preprocess_alibaba_summary(source, normalized)
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / "configs/env/hourly_continuous.yaml").read_text())
    assert isinstance(config, dict)
    workload = config["workload"]
    assert isinstance(workload, dict)
    workload["source"] = "alibaba2026_lite"
    workload["summary_path"] = str(normalized)
    environment = ContinuousCommunityAIDemandResponseEnv(config)

    observation, reset_info = environment.reset(seed=5)
    _, _, _, _, step_info = environment.step(np.asarray((1.0,), dtype=np.float32))

    assert environment.observation_space.contains(observation)
    assert reset_info["workload_source"] == "alibaba2026_lite"
    assert step_info["workload_source"] == "alibaba2026_lite"
    assert step_info["arrival_gpu_h"] > 0.0


def test_hourly_environment_can_replay_prebuilt_alibaba_lite_arrivals(tmp_path: Path) -> None:
    source = tmp_path / "summary.parquet"
    normalized = tmp_path / "jobs_summary.parquet"
    arrivals_path = tmp_path / "arrivals.parquet"
    _write_summary(source)
    preprocess_alibaba_summary(source, normalized)
    arrivals = make_alibaba_lite_hourly_arrivals(
        normalized,
        hours=168,
        total_gpu_count=8,
        flexible_arrival_utilization=0.5,
        workload_shares={"training": 0.5, "offline_inference": 0.5},
        flexible_fractions={"training": 1.0, "offline_inference": 1.0},
        seed=11,
    )
    arrivals.to_parquet(arrivals_path, index=False)
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / "configs/env/hourly_continuous.yaml").read_text())
    assert isinstance(config, dict)
    workload = config["workload"]
    assert isinstance(workload, dict)
    workload["source"] = "alibaba2026_lite"
    workload["arrivals_path"] = str(arrivals_path)
    workload.pop("summary_path", None)
    environment = ContinuousCommunityAIDemandResponseEnv(config)

    _, _ = environment.reset(seed=99)
    _, _, _, _, info = environment.step(np.asarray((1.0,), dtype=np.float32))

    assert len(load_hourly_arrivals(arrivals_path)) == len(arrivals)
    assert info["arrival_gpu_h"] > 0.0
