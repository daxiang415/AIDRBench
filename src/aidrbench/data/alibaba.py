"""Alibaba PAI GPU v2020 job/task preprocessing."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

JOB_COLUMNS = ("job_name", "inst_id", "user", "status", "start_time", "end_time")
TASK_COLUMNS = (
    "job_name",
    "task_name",
    "inst_num",
    "status",
    "start_time",
    "end_time",
    "plan_cpu",
    "plan_mem",
    "plan_gpu",
    "gpu_type",
)
OUTPUT_COLUMNS = (
    "job_id",
    "release_time_s",
    "work_gpu_seconds",
    "gpu_demand_original",
    "gpu_demand_local",
    "duration_original_s",
    "deadline_time_s",
    "deadline_is_synthetic",
    "slack_factor",
    "priority",
    "preemptible",
    "source_file",
)


def _read_table(path: str | Path, columns: tuple[str, ...]) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if not set(columns).issubset(frame.columns):
        frame = pd.read_csv(path, header=None, names=list(columns))
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")
    return frame.loc[:, columns].copy()


def preprocess_alibaba(
    job_table: str | Path,
    task_table: str | Path,
    output: str | Path,
    *,
    max_local_batch_gpus: float = 2.0,
    deadline_policy: str = "slack-mixture",
    seed: int = 42,
) -> dict[str, object]:
    """Map successful PAI jobs to the paper's local batch-work schema."""

    if max_local_batch_gpus <= 0:
        raise ValueError("max_local_batch_gpus must be greater than zero")
    if deadline_policy not in {"slack-mixture", "slack_mixture"}:
        raise ValueError("only the scenario-generated slack-mixture policy is supported")

    jobs = _read_table(job_table, JOB_COLUMNS)
    tasks = _read_table(task_table, TASK_COLUMNS)
    jobs = jobs[jobs["status"].astype("string").str.lower() == "terminated"].copy()
    tasks = tasks[tasks["status"].astype("string").str.lower() == "terminated"].copy()
    for column in ("start_time", "end_time"):
        jobs[column] = pd.to_numeric(jobs[column], errors="coerce")
        tasks[column] = pd.to_numeric(tasks[column], errors="coerce")
    for column in ("inst_num", "plan_gpu"):
        tasks[column] = pd.to_numeric(tasks[column], errors="coerce")

    jobs = jobs.dropna(subset=["job_name", "start_time", "end_time"])
    tasks = tasks.dropna(subset=["job_name", "start_time", "end_time", "inst_num", "plan_gpu"])
    jobs["duration_original_s"] = jobs["end_time"] - jobs["start_time"]
    tasks["task_duration_s"] = tasks["end_time"] - tasks["start_time"]
    tasks["task_gpu_demand"] = tasks["inst_num"] * tasks["plan_gpu"] / 100.0
    tasks = tasks[(tasks["task_duration_s"] > 0) & (tasks["task_gpu_demand"] > 0)]
    tasks["task_work_gpu_seconds"] = tasks["task_duration_s"] * tasks["task_gpu_demand"]

    task_summary = tasks.groupby("job_name", sort=False).agg(
        work_gpu_seconds=("task_work_gpu_seconds", "sum"),
        gpu_demand_original=("task_gpu_demand", "sum"),
    )
    merged = jobs.merge(task_summary, left_on="job_name", right_index=True, how="inner")
    merged = merged[merged["duration_original_s"] > 0].copy()
    merged = merged.sort_values(["start_time", "job_name"], kind="stable").reset_index(drop=True)
    if merged.empty:
        raise ValueError("Alibaba preprocessing produced no successful GPU jobs")

    rng = np.random.default_rng(seed)
    slack = rng.choice(np.array([1.5, 2.0, 4.0, 8.0]), size=len(merged), replace=True)
    release = merged["start_time"] - float(merged["start_time"].min())
    duration = merged["duration_original_s"].astype("float64")
    priority = np.where(slack <= 1.5, "urgent", np.where(slack <= 4.0, "normal", "low"))
    output_frame = pd.DataFrame(
        {
            "job_id": merged["job_name"].astype("string"),
            "release_time_s": release.astype("float64"),
            "work_gpu_seconds": merged["work_gpu_seconds"].astype("float64"),
            "gpu_demand_original": merged["gpu_demand_original"].astype("float64"),
            "gpu_demand_local": np.minimum(
                merged["gpu_demand_original"].astype("float64"), max_local_batch_gpus
            ),
            "duration_original_s": duration,
            "deadline_time_s": release + slack * duration,
            "deadline_is_synthetic": True,
            "slack_factor": slack,
            "priority": priority,
            "preemptible": priority != "urgent",
            "source_file": f"{Path(job_table).name}+{Path(task_table).name}",
        }
    )
    output_frame = output_frame.loc[:, OUTPUT_COLUMNS]
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_frame.to_parquet(output_path, index=False)
    return {
        "dataset": "alibaba_gpu_v2020",
        "input_jobs": len(jobs),
        "input_tasks": len(tasks),
        "output_rows": len(output_frame),
        "deadline_policy": "slack-mixture",
        "deadline_is_synthetic": True,
        "seed": seed,
        "output": str(output_path),
    }
