"""Matched observed count versus measured task-allocation-time weights."""

import argparse
import copy
import json
import shutil
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import refine_offers as f

r = f.r
SOURCE = f.SOURCE
COUNTS = SOURCE / "production_hourly_work.csv"
LOCK = f.HERE / "workload_protocol.json"


def freeze_week_rep(payload):
    weight, week, rep = payload
    seed = 990000 + week * 100 + rep
    root = r.OUT / "weighted_templates" / str(seed) / weight
    root.mkdir(parents=True, exist_ok=True)
    doc, _ = r.m.make_document(0.6, "confirmation", seed)
    env = r.m.HourlyCommunityAIDemandResponseEnv(doc)
    env.reset(seed=seed)
    template = env._arrivals.copy()
    shape = pd.read_csv(COUNTS).query("week_index == @week")[weight].to_numpy(dtype=float)
    shape /= shape.mean()
    case = r.m.case_definition(0.1)
    for cls in ["training", "offline_inference"]:
        mask = template.job_class == cls
        marginal = (
            template[mask]
            .groupby("timestamp_index")
            .arrival_gpu_h.sum()
            .reindex(range(168), fill_value=0.0)
        )
        assert (marginal > 0).all(), "Retain all hours; do not silently impute empty class blocks"
        target = shape * (374.4 * case["eligible_shares"][cls])
        template.loc[mask, "arrival_gpu_h"] *= template.loc[mask, "timestamp_index"].map(
            dict(enumerate(target / marginal.to_numpy()))
        )
    template = template[template.arrival_gpu_h > 0].copy()
    template["source_mode"] = (
        "alibaba2020_" + weight + "_submission_intensity_with_synthetic_classes_and_deadlines"
    )
    permutation = np.random.default_rng(seed + 700000).permutation(168)
    records = []
    paired = {}
    for ordering in ["chronological", "permuted"]:
        jobs = template.copy()
        if ordering == "permuted":
            jobs["timestamp_index"] = permutation[jobs.timestamp_index.to_numpy(dtype=int)]
        jobs = jobs.sort_values(["timestamp_index", "job_class", "slack_hours"]).reset_index(
            drop=True
        )
        paired[ordering] = jobs
        input_path = root / f"{ordering}_arrivals.parquet"
        jobs.to_parquet(input_path, index=False)
        for g in [0.1]:
            name = f"w{week}_{weight}_{ordering}_g{int(g * 100)}"
            path = r.scenario("workload", name, seed)
            if (path / "baseline_receipt.json").exists():
                records.append(json.loads((path / "baseline_receipt.json").read_text()))
                continue
            d, _ = r.m.make_document(0.1, "confirmation", seed)
            d["virtual_datacenter"]["flexible_gpu_fraction"] = g
            d["virtual_datacenter"]["rigid_gpu_utilization"] = 374.4 * 0.9 / (576 - round(576 * g))
            d["workload"]["flexible_arrival_utilization"] = 0.65 * 0.1 / g
            d["workload"]["arrivals_path"] = str(input_path)
            for key in [
                "event_start_hour_choices",
                "event_duration_choices",
                "event_notice_choices",
                "event_reduction_fraction_range",
            ]:
                d["dr"].pop(key, None)
            d["dr"].update(
                source="configured",
                events_path=None,
                event_start_hours=r.starts(seed, 16),
                event_duration_hours=8,
                event_notice_hours=0,
                event_reduction_kw=1.0,
                event_start_jitter_hours=0,
            )
            r.m.freeze_hourly_scenario(d, seed=seed, output_directory=path.parent)
            parent = r.m.load_frozen_hourly_scenario(path)
            baseline_env = r.m.HourlyCommunityAIDemandResponseEnv(
                r.m._repeated_environment_document(parent, notice_h=0, requested_reduction_kw=0)
            )
            baseline, summary = r.m.rollout_hourly_episode(
                baseline_env, r.m.make_hourly_controller("no_control"), seed=seed
            )
            baseline = baseline.drop(columns=["controller_action_time_ms"])
            baseline.to_parquet(path / "no_response_full.parquet", index=False)
            receipt = dict(
                name=name,
                role="workload",
                seed=seed,
                week=week,
                replicate=rep,
                ordering=ordering,
                gpu_share=g,
                utilization=0.65,
                slack_multiplier=1.0,
                baseline_missed_gpu_h=float(baseline.missed_gpu_h.sum()),
                baseline_miss_rate=float(summary["deadline_miss_rate"]),
                baseline_service_feasible=r.m.baseline_service_gate(
                    baseline,
                    float(summary["deadline_miss_rate"]),
                    baseline_env.config.pcc_capacity_kw,
                ),
                baseline_zero_service=float(baseline.missed_gpu_h.sum()) <= 1e-7,
                operating_peak_kw=baseline_env.power_model.reference_mix_operating_peak_kw,
                flexible_gpu_count=round(576 * g),
                phase=r.starts(seed, 16)[-1] - 111,
                total_arrival_gpu_h=float(parent.arrivals.arrival_gpu_h.sum()),
                source=str(path),
                scenario_hash=parent.scenario_hash,
                baseline_sha256=r.m.sha(path / "no_response_full.parquet"),
            )
            for p in r.programs(name):
                dest = r.scenario("workload", name, seed, p["name"])
                if dest == path:
                    continue
                dest.mkdir(parents=True, exist_ok=True)
                meta = copy.deepcopy(parent.metadata)
                for filename in meta["files"]:
                    shutil.copyfile(path / filename, dest / filename)
                meta["events"] = [
                    dict(
                        event_id=i,
                        source_event_id=f"temporal_{i}",
                        start_hour=s,
                        stop_hour=s + p["h"],
                        requested_reduction_kw=1.0,
                        notice_hours=0.0,
                    )
                    for i, s in enumerate(r.starts(seed, p["period"]))
                ]
                meta.pop("scenario_hash")
                meta["scenario_hash"] = r.m.digest(meta)
                r.m.save(dest / "metadata.json", meta)
                r.m.load_frozen_hourly_scenario(dest)
            r.m.save(path / "baseline_receipt.json", receipt)
            records.append(receipt)
    for fields in [["job_class"], ["job_class", "slack_hours"]]:
        a = paired["chronological"].groupby(fields).arrival_gpu_h.sum()
        b = paired["permuted"].groupby(fields).arrival_gpu_h.sum()
        assert np.allclose(a, b, atol=1e-8)
    a = (
        paired["chronological"]
        .groupby("timestamp_index")
        .arrival_gpu_h.sum()
        .reindex(range(168), fill_value=0.0)
    )
    b = (
        paired["permuted"]
        .groupby("timestamp_index")
        .arrival_gpu_h.sum()
        .reindex(range(168), fill_value=0.0)
    )
    assert np.allclose(np.sort(a), np.sort(b), atol=1e-8)
    return records


def audit_source():
    raw = f.ROOT / "data/raw/alibaba_v2020"
    j = pd.read_csv(
        raw / "pai_job_table.csv",
        header=None,
        names=["job_id", "inst_id", "user", "status", "start", "end"],
    )
    t = pd.read_csv(
        raw / "pai_task_table.csv",
        header=None,
        names=[
            "job_id",
            "task_name",
            "instances",
            "status",
            "start",
            "end",
            "cpu",
            "mem",
            "gpu_pct",
            "gpu_type",
        ],
    )
    t["resource_gpu_seconds"] = (t.end - t.start) * t.instances * t.gpu_pct / 100
    valid = t[(t.status == "Terminated") & (t.resource_gpu_seconds > 0)].copy()
    byjob = valid.groupby("job_id").resource_gpu_seconds.sum()
    b = (
        pd.read_parquet(f.ROOT / "data/processed/batch_jobs.parquet")
        .set_index("job_id")
        .join(byjob)
    )
    assert b.resource_gpu_seconds.notna().all() and np.allclose(
        b.resource_gpu_seconds, b.work_gpu_seconds, rtol=1e-10, atol=1e-8
    )
    j = j.set_index("job_id").reindex(b.index)
    offset = j.start - b.release_time_s
    assert offset.nunique() == 1 and (j.status == "Terminated").all()
    b["raw_submission_time_s"] = j.start
    b["trace_hour"] = np.floor(b.release_time_s / 3600).astype(int)
    b["job_count"] = 1
    b["resource_gpu_h"] = b.resource_gpu_seconds / 3600
    hours = (
        b.groupby("trace_hour")[["job_count", "resource_gpu_h"]]
        .sum()
        .reindex(range(168, 1512), fill_value=0)
        .reset_index()
    )
    hours["week_index"] = (hours.trace_hour - 168) // 168
    hours["hour_in_week"] = (hours.trace_hour - 168) % 168
    hours.to_csv(COUNTS, index=False)
    old = pd.read_csv(
        f.ROOT / "results/nature_mainline/repeat_capacity_v1/production_timing/hourly_counts.csv"
    )
    assert np.array_equal(hours.job_count.to_numpy(), old.job_count.to_numpy())
    cols = [
        "release_time_s",
        "raw_submission_time_s",
        "resource_gpu_seconds",
        "work_gpu_seconds",
        "gpu_demand_original",
        "duration_original_s",
        "trace_hour",
    ]
    b[cols].reset_index().to_parquet(SOURCE / "production_job_resource_time.parquet", index=False)
    selected = valid[valid.job_id.isin(b.index)]
    selected[
        [
            "job_id",
            "task_name",
            "instances",
            "status",
            "start",
            "end",
            "gpu_pct",
            "resource_gpu_seconds",
        ]
    ].to_parquet(SOURCE / "production_task_resource_time.parquet", index=False)
    record = dict(
        status="PASS",
        jobs=len(b),
        tasks=len(selected),
        source_job_sha256=r.m.sha(raw / "pai_job_table.csv"),
        source_task_sha256=r.m.sha(raw / "pai_task_table.csv"),
        processed_sha256=r.m.sha(f.ROOT / "data/processed/batch_jobs.parquet"),
        reconstructed_work_max_abs_error_gpu_s=float(
            (b.resource_gpu_seconds - b.work_gpu_seconds).abs().max()
        ),
        naive_job_duration_times_total_gpu_mismatches=int(
            (~np.isclose(b.gpu_demand_original * b.duration_original_s, b.work_gpu_seconds)).sum()
        ),
        release_origin_offset_s=float(offset.iloc[0]),
        weeks=8,
        trace_hours=[168, 1511],
        definition=(
            "sum over terminated positive-resource tasks: instances * req"
            "uested_GPU_percent/100 * (task completion - task launch)"
        ),
        boundary=(
            "allocated resource-time, not sensor-measured busy GPU-hours;"
            " job sojourn time is NOT task execution time; normalised wee"
            "ks, synthetic classes/deadlines, fluid execution"
        ),
        schema_url="https://github.com/alibaba/clusterdata/blob/master/cluster-trace-gpu-v2020/README.md",
    )
    r.m.save(SOURCE / "resource_time_source_audit.json", record)
    print(json.dumps(record, indent=2), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["audit_source", "freeze", "run"])
    ap.add_argument("--workers", type=int, default=24)
    args = ap.parse_args()
    if args.stage == "audit_source":
        audit_source()
        return
    if args.stage == "freeze":
        assert not LOCK.exists() and not (r.OUT / "runs/workload").exists()
        confirmed = pd.read_csv(SOURCE / "refinement_selected_confirmed.csv")
        fractions = sorted(
            {0.5, 0.75}
            | set(
                confirmed.loc[
                    (confirmed.program == "H8P16") & confirmed.offerable, "selected_fraction"
                ]
            )
        )
        tasks = [
            dict(
                role="workload",
                variant=f"w{w}_{weight}_{order}_g10",
                seed=990000 + w * 100 + i,
                program="H8P16",
                fraction=float(frac),
                kind="repeated",
            )
            for w in range(8)
            for i in range(10)
            for weight in ["job_count", "resource_gpu_h"]
            for order in ["chronological", "permuted"]
            for frac in fractions
        ]
        r.m.save(
            LOCK,
            dict(
                frozen_at_utc=datetime.now(UTC).isoformat(),
                runner_sha256=r.m.sha(__file__),
                parent_runner_sha256=r.m.sha(r.__file__),
                source_audit_sha256=r.m.sha(SOURCE / "resource_time_source_audit.json"),
                hourly_weights_sha256=r.m.sha(COUNTS),
                selection_sha256=r.m.sha(f.HERE / "refinement_selection.json"),
                tasks=tasks,
                mapping=(
                    "same seeds, class sizes/deadlines, weekly class totals, comm"
                    "unity and events; only hourly submission weights change from"
                    " counts to observed task resource-time; paired whole-hour pe"
                    "rmutations"
                ),
                inference=(
                    "eight observed weeks with ten synthetic realizations each; r"
                    "etain baseline failures, no external reselection, no reliabi"
                    "lity certification or application pause/restart measurement"
                ),
            ),
        )
        print("Frozen workload tasks", len(tasks))
        return
    p = json.loads(LOCK.read_text())
    assert p["runner_sha256"] == r.m.sha(__file__) and p["hourly_weights_sha256"] == r.m.sha(COUNTS)
    records = r.m.parallel(
        freeze_week_rep,
        [
            (weight, w, i)
            for weight in ["job_count", "resource_gpu_h"]
            for w in range(8)
            for i in range(10)
        ],
        args.workers,
        "freeze weighted timing",
    )
    r.m.save(r.OUT / "workload_baseline_receipts.json", records)
    results = r.m.parallel(r.evaluate, p["tasks"], args.workers, "weighted timing")
    data = pd.DataFrame([x["row"] for x in results])
    data.to_csv(r.OUT / "workload_ledgers.csv", index=False)
    fields = data.variant.str.extract(
        r"w(?P<week>\d+)_(?P<weight>job_count|resource_gpu_h)_(?P<ordering>chronological|permuted)_g10"
    )
    data = pd.concat([data, fields], axis=1)
    rows = []
    for key, g in data.groupby(["week", "weight", "ordering", "fraction"]):
        rows.append(
            dict(zip(["week", "weight", "ordering", "fraction"], key, strict=False))
            | dict(
                trials=len(g),
                successes_1pct=int(g.success_1pct.sum()),
                successes_zero=int(g.success_zero.sum()),
                baseline_failures=int((~g.baseline_service_feasible).sum()),
                baseline_nonzero_miss=int((~g.baseline_zero_service).sum()),
                instantaneous_shortage=int((g.instantaneous_supply_shortfall_hours > 0).sum()),
                deadline_failures=int(g.failure_deadline_miss.sum()),
                mean_missed_gpu_h=float(g.missed_gpu_h.mean()),
                mean_waiting_exposure=float(g.delay_exposure_gpu_h_h.mean()),
            )
        )
    pd.DataFrame(rows).to_csv(SOURCE / "weighted_week_summary.csv", index=False)
    print(
        data.groupby(["weight", "ordering", "fraction"])[
            ["success_1pct", "success_zero", "baseline_service_feasible", "baseline_zero_service"]
        ]
        .sum()
        .to_string(),
        flush=True,
    )


if __name__ == "__main__":
    main()
