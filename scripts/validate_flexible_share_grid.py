"""Independently check the joint grid, reused evidence and new notice traces."""

from __future__ import annotations

import argparse
import ast
import json
import math
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from validate_flexible_share_extension import schedule_pair

from aidrbench.data.splits import sha256_file
from aidrbench.evaluation.firm_flexibility import lower_tolerance_order_statistic_rank
from aidrbench.evaluation.flexible_share_grid import TABLES, design
from aidrbench.evaluation.flexible_share_grid_analysis import contrast_plan
from aidrbench.evaluation.flexible_share_sensitivity import load_spec


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", default="configs/sensitivity/nature_flexible_share_v3.yaml")
    parser.add_argument("--workers", type=int, default=24)
    args = parser.parse_args()
    spec = load_spec(args.spec)
    root, source, prior, revision = [
        Path(spec[k])
        for k in [
            "output_directory",
            "source_data_directory",
            "prior_results",
            "revision_directory",
        ]
    ]
    frozen = json.loads((Path(spec["extension_directory"]) / "execution_inputs.json").read_text())
    assert all(sha256_file(p) == h for p, h in frozen["sha256"].items())
    if "non_runtime_amendments" in frozen:
        for record in frozen["non_runtime_amendments"]:
            old = revision / "execution_core_before_typing_comments.py.txt"
            assert sha256_file(old) == record["before_sha256"]
            assert sha256_file(record["file"]) == record["after_sha256"]
            assert ast.dump(ast.parse(old.read_text())) == ast.dump(
                ast.parse(Path(record["file"]).read_text())
            )
    for name in TABLES:
        old, combined = pd.read_parquet(prior / name), pd.read_parquet(root / name)
        keys = [k for k in ["case", "role", "duration_h", "notice_h", "episode_seed"] if k in old]
        retained = combined.loc[combined.case.isin(old.case), old.columns]
        pd.testing.assert_frame_equal(
            old.sort_values(keys).reset_index(drop=True),
            retained.sort_values(keys).reset_index(drop=True),
        )
    grid = design(spec)
    assert len(grid) == 54 and grid.structurally_feasible.sum() == 32
    index = pd.read_parquet(root / "scenario_index.parquet")
    gate = pd.read_parquet(root / "service_gate.parquet")
    pi = pd.read_parquet(root / "pi_scenario_frontiers.parquet")
    bounds = pd.read_parquet(root / "pi_boundaries.parquet")
    offers = pd.read_parquet(root / "fixed_notice_offers.parquet")
    causal = pd.read_parquet(root / "causal_notice_outcomes.parquet")
    assert len(index) == 8400
    assert not index.duplicated(["case", "role", "episode_seed"]).any()
    assert set(index.groupby(["case", "role"]).size()) == {100}
    assert np.allclose(
        index.flexible_work_gpu_h_per_hour + index.rigid_work_gpu_h_per_hour,
        374.4,
        rtol=0,
        atol=1e-10,
    )
    assert (index.flexible_gpu_count + index.rigid_gpu_count).eq(576).all()
    assert np.allclose(
        index.flexible_work_gpu_h_per_hour / 374.4, index.workload_fraction, rtol=0, atol=1e-12
    )
    feasible = set(gate.loc[gate.all_service_feasible, "case"])
    assert set(pi.case) == set(causal.case) == feasible
    assert set(pi.perfect_information_status) == {"optimal"}
    assert len(pi) == len(feasible) * 800
    assert len(causal) == len(feasible) * 600
    assert not pi.duplicated(["case", "role", "episode_seed", "duration_h"]).any()
    assert not causal.duplicated(["case", "duration_h", "notice_h", "episode_seed"]).any()
    rank, achieved = lower_tolerance_order_statistic_rank(100, 0.95, 0.95)
    assert rank == 2
    for row in bounds.itertuples():
        values = pi.loc[
            (pi.case == row.case) & (pi.role == row.role) & (pi.duration_h == row.duration_h),
            "perfect_information_capacity_kw",
        ]
        assert len(values) == 100
        assert math.isclose(
            float(values.sort_values().iloc[rank - 1]),
            float(row.perfect_information_firm_capacity_kw),
            abs_tol=1e-9,
        )
    for (_case, _duration), group in causal.groupby(["case", "duration_h"]):
        assert len(group) == 300 and group.fixed_offer_kw.nunique() == 1
        selected = offers.loc[
            (offers.case == group.case.iloc[0]) & (offers.duration_h == group.duration_h.iloc[0])
        ]
        assert len(selected) == 1 and float(selected.fixed_offer_kw.iloc[0]) == float(
            group.fixed_offer_kw.iloc[0]
        )

    # Pairing and releases/deadlines use the same frozen arrivals at each f, even across GPU pools.
    inspected = 0
    for (_role, _seed), group in index.groupby(["role", "episode_seed"]):
        meta = [json.loads((Path(p) / "metadata.json").read_text()) for p in group.artifact_path]
        assert len({m["files"]["community.parquet"] for m in meta}) == 1
        assert len({m["events"][0]["start_hour"] for m in meta}) == 1
        for f in sorted(group.workload_fraction.unique()):
            indices = np.flatnonzero(group.workload_fraction.to_numpy() == f)
            assert len({meta[i]["files"]["arrivals.parquet"] for i in indices}) == 1
        inspected += len(meta)

    prior_source = Path("manuscript/source_data/nature_flexible_share_v2")
    prior_manifest = json.loads((prior_source / "source_data_manifest.json").read_text())
    assert all(
        sha256_file(prior_source / name) == info["sha256"]
        for name, info in prior_manifest["files"].items()
    )
    old_pairs = pd.read_csv(prior_source / "notice_paired_schedule_differences.csv")
    old_cases = set(pd.read_parquet(prior / "causal_notice_outcomes.parquet").case)
    payloads = []
    for _, group in causal.loc[~causal.case.isin(old_cases)].groupby(
        ["case", "duration_h", "episode_seed"]
    ):
        zero = group.loc[group.notice_h == 0].iloc[0].to_dict()
        payloads.extend(
            (zero, row) for row in group.loc[group.notice_h > 0].to_dict(orient="records")
        )
    with ProcessPoolExecutor(
        max_workers=args.workers, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        records = list(pool.map(schedule_pair, payloads, chunksize=8))
    pairs = pd.concat([old_pairs, pd.DataFrame(records)], ignore_index=True)
    assert len(pairs) == len(feasible) * 400
    assert not pairs.duplicated(["case", "duration_h", "notice_h", "episode_seed"]).any()
    pairs = pairs.sort_values(["case", "duration_h", "notice_h", "episode_seed"])
    summary = (
        pairs.groupby(["case", "duration_h", "notice_h"])
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
    manifest_path = source / "source_data_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for name, frame in [
        ("notice_paired_schedule_differences", pairs),
        ("plot_notice_schedule_differences", summary),
    ]:
        path = source / f"{name}.csv"
        frame.to_csv(path, index=False, float_format="%.12g")
        manifest["files"][path.name] = {"rows": len(frame), "sha256": sha256_file(path)}
    manifest["validation_script_sha256"] = sha256_file(__file__)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    # Recompute contrast values and multiplicity, including four-corner interactions.
    from scipy.stats import binomtest, t

    notice = pd.read_csv(source / "notice_paired_contrasts.csv")
    assert len(notice) == len(feasible) * 4
    exact = []
    for row in notice.itertuples():
        paired = causal.loc[
            (causal.case == row.case) & (causal.duration_h == row.duration_h)
        ].pivot(index="episode_seed", columns="notice_h", values="success")
        improved = int((paired[row.notice_h] & ~paired[0]).sum())
        worsened = int((~paired[row.notice_h] & paired[0]).sum())
        assert improved == row.improved_success_count
        assert worsened == row.worsened_success_count
        assert len(paired) == row.n_paired == 100
        n = improved + worsened
        exact.append(float(binomtest(improved, n, 0.5).pvalue) if n else 1.0)
    order = np.argsort(exact, kind="stable")
    adjusted = np.empty(len(exact))
    adjusted[order] = np.minimum(
        1, np.maximum.accumulate(np.asarray(exact)[order] * np.arange(len(exact), 0, -1))
    )
    assert np.allclose(notice.mcnemar_exact_p, exact, rtol=0, atol=1e-10)
    assert np.allclose(notice.mcnemar_holm_p, adjusted, rtol=0, atol=1e-10)

    plan, _ = contrast_plan(spec, grid, feasible)
    contrasts = pd.read_csv(source / "pi_paired_contrasts.csv")
    family = len(plan) * 6
    assert len(contrasts) == family and contrasts.family_size.eq(family).all()
    pivots = {
        h: group.pivot(
            index="episode_seed", columns="case", values="perfect_information_capacity_kw"
        )
        for h, group in pi.loc[pi.role == "validation"].groupby("duration_h")
    }
    for row in contrasts.itertuples():
        terms = json.loads(row.term_coefficients_json)
        assert sum(terms.values()) == 0
        difference = np.sum(
            [pivots[row.duration_h][case].to_numpy() * value for case, value in terms.items()],
            axis=0,
        )
        mean = float(difference.mean())
        half = float(t.ppf(1 - 0.05 / (2 * family), 99) * difference.std(ddof=1) / 10)
        assert np.allclose(
            [mean, mean - half, mean + half],
            [
                row.mean_capacity_difference_kw,
                row.simultaneous_ci_low_kw,
                row.simultaneous_ci_high_kw,
            ],
            rtol=0,
            atol=1e-8,
        )
    for name, info in manifest["files"].items():
        assert sha256_file(source / name) == info["sha256"]
        assert len(pd.read_csv(source / name)) == info["rows"]
    primary = pd.read_csv(source / "plot_joint_share_grid.csv")
    assert len(primary) == 54 * 6
    assert primary.loc[~primary.all_service_feasible, "y_kw"].isna().all()
    assert primary.loc[primary.all_service_feasible, "y_kw"].notna().all()
    report = {
        "status": "PASS",
        "primary_grid_case_count": 54,
        "primary_service_feasible_case_count": int(
            primary.loc[primary.duration_h == 4, "all_service_feasible"].sum()
        ),
        "primary_structural_failure_count": 22,
        "complete_case_count_with_legacy": len(gate) + 22,
        "all_service_feasible_case_count_with_legacy": len(feasible),
        "scenario_count": len(index),
        "scenario_pairing_metadata_checked": inspected,
        "pi_scenario_duration_count": len(pi),
        "causal_episode_count": len(causal),
        "paired_schedule_count": len(pairs),
        "new_paired_schedule_count": len(records),
        "old_results_reused_exactly": True,
        "tolerance_rank": rank,
        "achieved_pointwise_tolerance_confidence": achieved,
        "pi_mean_contrast_family_size": family,
        "notice_contrast_family_size": len(pd.read_csv(source / "notice_paired_contrasts.csv")),
        "notice_discordant_pairs": int(
            notice.improved_success_count.sum() + notice.worsened_success_count.sum()
        ),
        "notice_exact_tests_and_holm_independently_verified": True,
        "source_data_manifest_sha256": sha256_file(manifest_path),
        "statistical_effects_are_paired_means_not_tolerance_bound_differences": True,
    }
    (revision / "analysis_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
