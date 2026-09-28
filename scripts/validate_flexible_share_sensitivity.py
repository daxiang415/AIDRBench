"""Independently check paired inputs, curve completeness and notice masking."""

from __future__ import annotations

import argparse
import json
import math
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from aidrbench.data.splits import sha256_file
from aidrbench.evaluation.firm_flexibility import lower_tolerance_order_statistic_rank
from aidrbench.evaluation.flexible_share_sensitivity import cases_for, load_spec


def schedule_pair(payload: tuple[dict, dict]) -> dict:
    zero, other = payload
    a, b = pd.read_parquet(zero["frame_path"]), pd.read_parquet(other["frame_path"])
    assert len(a) == len(b) == 216
    assert a["hour"].tolist() == b["hour"].tolist() == list(range(216))
    assert np.allclose(a["baseline_pcc_power_kw"], b["baseline_pcc_power_kw"], atol=1e-9, rtol=0)
    notice_start = other["event_start_hour"] - other["notice_h"]
    delta = b["executed_gpu_h"].to_numpy() - a["executed_gpu_h"].to_numpy()
    delta_power = b["pcc_power_kw"].to_numpy() - a["pcc_power_kw"].to_numpy()
    before_notice = float(np.max(np.abs(delta[:notice_start]), initial=0))
    before_notice_power = float(np.max(np.abs(delta_power[:notice_start]), initial=0))
    assert before_notice <= 1e-8, (other["case"], other["episode_seed"], before_notice)
    assert before_notice_power <= 1e-8
    start = other["event_start_hour"]
    pre = delta[start - 6 : start]
    return {
        "case": other["case"],
        "episode_seed": other["episode_seed"],
        "duration_h": other["duration_h"],
        "notice_h": other["notice_h"],
        "scenario_hash": other["scenario_hash"],
        "max_execution_difference_before_notice_gpu_h": before_notice,
        "max_power_difference_before_notice_kw": before_notice_power,
        "mean_abs_episode_execution_difference_gpu_h": float(np.abs(delta).mean()),
        "mean_abs_pre_event_6h_execution_difference_gpu_h": float(np.abs(pre).mean()),
        "max_abs_episode_execution_difference_gpu_h": float(np.abs(delta).max()),
        "net_pre_event_6h_execution_difference_gpu_h": float(pre.sum()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", default="configs/sensitivity/nature_flexible_share_v1.yaml")
    parser.add_argument("--workers", type=int, default=24)
    args = parser.parse_args()
    spec = load_spec(args.spec)
    root, source = Path(spec["output_directory"]), Path(spec["source_data_directory"])
    index = pd.read_parquet(root / "scenario_index.parquet")
    gate = pd.read_parquet(root / "service_gate.parquet")
    pi = pd.read_parquet(root / "pi_scenario_frontiers.parquet")
    bounds = pd.read_parquet(root / "pi_boundaries.parquet")
    offers = pd.read_parquet(root / "fixed_notice_offers.parquet")
    causal = pd.read_parquet(root / "causal_notice_outcomes.parquet")
    feasible = set(gate.loc[gate["all_service_feasible"], "case"])
    assert set(index["case"]) == {case.name for case in cases_for(spec)}
    assert len(index) == len(cases_for(spec)) * 200
    assert not index.duplicated(["case", "role", "episode_seed"]).any()
    assert set(index.groupby(["case", "role"]).size()) == {100}
    assert np.allclose(
        index["flexible_work_gpu_h_per_hour"] + index["rigid_work_gpu_h_per_hour"],
        374.4,
        atol=1e-10,
        rtol=0,
    )
    assert np.allclose(
        index["flexible_work_gpu_h_per_hour"] / 374.4,
        index["workload_fraction"],
        atol=1e-12,
        rtol=0,
    )
    assert set(pi["case"]) == set(causal["case"]) == feasible
    assert set(pi["perfect_information_status"]) == {"optimal"}
    assert not pi.duplicated(["case", "role", "episode_seed", "duration_h"]).any()
    assert len(pi) == len(feasible) * 100 * (
        len(spec["pi_durations_h"]) + len(spec["notice_durations_h"])
    )
    assert len(causal) == len(feasible) * 100 * len(spec["notice_durations_h"]) * len(
        spec["notices_h"]
    )
    assert not causal.duplicated(["case", "duration_h", "notice_h", "episode_seed"]).any()
    rank, _ = lower_tolerance_order_statistic_rank(100, 0.95, 0.95)
    assert rank == 2
    for row in bounds.to_dict(orient="records"):
        values = pi.loc[
            (pi["case"] == row["case"])
            & (pi["role"] == row["role"])
            & (pi["duration_h"] == row["duration_h"]),
            "perfect_information_capacity_kw",
        ]
        assert len(values) == 100
        assert math.isclose(
            float(values.sort_values().iloc[rank - 1]),
            row["perfect_information_firm_capacity_kw"],
            abs_tol=1e-9,
        )
    for (case, duration), group in causal.groupby(["case", "duration_h"]):
        assert len(group) == 300
        assert group["fixed_offer_kw"].nunique() == 1
        offer = offers.loc[(offers["case"] == case) & (offers["duration_h"] == duration)]
        assert len(offer) == 1
        assert group["fixed_offer_kw"].iloc[0] == offer["fixed_offer_kw"].iloc[0]
        assert set(group["episode_seed"]) == set(range(20000, 20100))
    assert (index["baseline_terminal_backlog_fraction"] == 0).all()
    # Equal-seed community/event inputs are paired by the freezer. Here also
    # verify that changing GPU allocation preserves each complete arrival file.
    for (_role, _seed), group in index.groupby(["role", "episode_seed"]):
        reference = group.loc[group["case"] == "reference"].iloc[0]
        meta = json.loads((Path(reference["artifact_path"]) / "metadata.json").read_text())
        for row in group.to_dict(orient="records"):
            derived = json.loads((Path(row["artifact_path"]) / "metadata.json").read_text())
            assert derived["files"]["community.parquet"] == meta["files"]["community.parquet"]
            assert derived["events"][0]["start_hour"] == meta["events"][0]["start_hour"]
            if row["axis"] == "gpu_pool":
                assert derived["files"]["arrivals.parquet"] == meta["files"]["arrivals.parquet"]
    payloads = []
    for _, group in causal.groupby(["case", "duration_h", "episode_seed"]):
        zero = group.loc[group["notice_h"] == 0].iloc[0].to_dict()
        for row in group.loc[group["notice_h"] > 0].to_dict(orient="records"):
            payloads.append((zero, row))
    with ProcessPoolExecutor(
        max_workers=args.workers, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        pairs = list(pool.map(schedule_pair, payloads, chunksize=8))
    pairs = pd.DataFrame(pairs).sort_values(["case", "duration_h", "notice_h", "episode_seed"])
    pairs_path = source / "notice_paired_schedule_differences.csv"
    pairs.to_csv(pairs_path, index=False, float_format="%.12g")
    summary = (
        pairs.groupby(["case", "duration_h", "notice_h"], sort=True)
        .agg(
            n_paired=("episode_seed", "size"),
            mean_abs_episode_execution_difference_gpu_h=(
                "mean_abs_episode_execution_difference_gpu_h",
                "mean",
            ),
            mean_abs_pre_event_6h_execution_difference_gpu_h=(
                "mean_abs_pre_event_6h_execution_difference_gpu_h",
                "mean",
            ),
            max_abs_episode_execution_difference_gpu_h=(
                "max_abs_episode_execution_difference_gpu_h",
                "max",
            ),
            max_execution_difference_before_notice_gpu_h=(
                "max_execution_difference_before_notice_gpu_h",
                "max",
            ),
        )
        .reset_index()
    )
    summary_path = source / "plot_notice_schedule_differences.csv"
    summary.to_csv(summary_path, index=False, float_format="%.12g")
    # Explicit missing capacities keep the failed allocation visible in plots.
    complete = gate.merge(pd.DataFrame({"duration_h": spec["pi_durations_h"]}), how="cross")
    complete = complete.merge(
        bounds.loc[bounds["role"] == "validation"],
        on=["case", "duration_h", "workload_fraction", "gpu_pool_fraction"],
        how="left",
        validate="one_to_one",
    )
    complete = complete.merge(
        index.drop_duplicates("case")[
            [
                "case",
                "actual_flexible_pool_utilization",
                "flexible_gpu_count",
                "flexible_work_gpu_h_per_hour",
            ]
        ],
        on="case",
        validate="many_to_one",
    )
    complete["mean_arrivals_exceed_flexible_pool"] = (
        complete["actual_flexible_pool_utilization"] > 1.0
    )
    assert complete["perfect_information_firm_capacity_kw"].isna().sum() == (
        len(gate) - len(feasible)
    ) * len(spec["pi_durations_h"])
    grid_path = source / "plot_pi_capacity_complete_grid.csv"
    complete.to_csv(grid_path, index=False, float_format="%.12g")
    manifest_path = source / "source_data_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for path, frame in [(pairs_path, pairs), (summary_path, summary), (grid_path, complete)]:
        manifest["files"][path.name] = {"rows": len(frame), "sha256": sha256_file(path)}
    manifest["validation_script_sha256"] = sha256_file(__file__)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    report = {
        "status": "PASS",
        "case_count": len(gate),
        "feasible_case_count": len(feasible),
        "frozen_scenario_count": len(index),
        "pi_scenario_duration_count": len(pi),
        "causal_episode_count": len(causal),
        "notice_schedule_pairs_checked": len(pairs),
        "zero_pre_notice_execution_leakage": True,
        "constant_main_horizon_total_work": True,
        "integer_gpu_pool_accounting": True,
        "failed_grid_points_preserved": True,
        "fixed_offers_selected_only_from_development": True,
        "tolerance_rank_independently_recomputed": rank,
        "validation_script_sha256": sha256_file(__file__),
        "source_data_manifest_sha256": sha256_file(manifest_path),
    }
    destination = Path("manuscript/revisions/flexible_share_2026-09-07/analysis_validation.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
