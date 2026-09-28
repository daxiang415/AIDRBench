"""Matched repeated-offer qualification with separately held-out confirmation episodes."""

from __future__ import annotations

import copy
import hashlib
import json
import multiprocessing
import shutil
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import yaml

from aidrbench.controllers.hourly import make_hourly_controller
from aidrbench.data.frozen_scenarios import (
    freeze_hourly_scenario,
    load_frozen_hourly_scenario,
)
from aidrbench.data.splits import sha256_file
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv
from aidrbench.evaluation.exhaustion import (
    _local_event_decision,
    _repeated_environment_document,
    _rollout_exhaustion_program,
)
from aidrbench.evaluation.firm_flexibility import FirmFlexibilityCriteria, wilson_lower_bound
from aidrbench.evaluation.hourly_rollout import rollout_hourly_episode

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "configs/experiment/nature_repeat_capacity_v1.yaml"
OUTPUT = ROOT / "results/nature_mainline/repeat_capacity_v1"
CRITERIA = FirmFlexibilityCriteria()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".incomplete")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def load_protocol() -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(PROTOCOL.read_text()))


def reference_capacities(protocol: dict[str, Any]) -> dict[int, float]:
    data = pd.read_parquet(ROOT / protocol["reference_certificates"])
    result = {}
    for h in protocol["duration_hours"]:
        rows = data[
            (data.duration_h == h) & (data.notice_h == 0) & (data.reliability_target == 0.95)
        ]
        if len(rows) != 1 or not bool(rows.iloc[0].certified):
            raise ValueError("reference requires one previously qualified offer per duration")
        result[h] = float(rows.iloc[0].candidate_reduction_kw)
    return result


def event_starts(
    h: int, gap: int, count: int = 4, first: int = 63, main_hours: int = 168
) -> list[int]:
    starts = [first + i * (h + gap) for i in range(count)]
    if h <= 0 or gap < 0 or count < 1 or starts[-1] + h > main_hours:
        raise ValueError("invalid repeated schedule or last event exceeds the main horizon")
    return starts


def baseline_service_gate(
    frame: pd.DataFrame, deadline_miss_rate: float, physical_pcc_limit_kw: float
) -> bool:
    """Check the physical PCC rating, independently of any active DR contract."""
    return bool(
        deadline_miss_rate <= 0.01 + 1e-9
        and float(frame.terminal_backlog_excess_fraction.iloc[-1]) <= 0.02 + 1e-9
        and float(frame.pcc_power_kw.max()) <= physical_pcc_limit_kw + 1e-6
    )


def _program_document(
    base: dict[str, Any], seed: int, h: int, gap: int, capacity: float
) -> dict[str, Any]:
    doc = copy.deepcopy(base)
    doc["env"]["episode_seed_range"] = [seed, seed]
    doc["scenario"] = {"dataset_role": "repeat_capacity_extension"}
    for key in (
        "event_start_hour_choices",
        "event_duration_choices",
        "event_notice_choices",
        "event_reduction_fraction_range",
    ):
        doc["dr"].pop(key, None)
    doc["dr"].update(
        source="configured",
        events_path=None,
        event_start_hours=event_starts(h, gap),
        event_duration_hours=h,
        event_notice_hours=0,
        event_reduction_kw=capacity,
        event_start_jitter_hours=0,
    )
    return doc


def _freeze_seed(payload: tuple[str, int, str]) -> dict[str, Any]:
    role, seed, output_string = payload
    output = Path(output_string)
    protocol = load_protocol()
    capacities = reference_capacities(protocol)
    base = yaml.safe_load((ROOT / protocol[f"{role}_environment"]).read_text())
    seed_directory = output / role / "scenarios" / f"seed_{seed}"
    record_path = seed_directory / "freeze_receipt.json"
    if record_path.is_file():
        receipt = cast(dict[str, Any], json.loads(record_path.read_text()))
        if receipt["protocol_sha256"] != sha256_file(PROTOCOL):
            raise ValueError("freeze protocol changed")
        for row in receipt["programs"]:
            artifact = load_frozen_hourly_scenario(row["path"])
            if artifact.scenario_hash != row["scenario_hash"]:
                raise ValueError("frozen program hash changed")
        if sha256_file(seed_directory / "no_response.parquet") != receipt["no_response_sha256"]:
            raise ValueError("baseline checksum changed")
        return receipt
    programs = []
    parent = None
    for h in protocol["duration_hours"]:
        for gap in protocol["recovery_gaps_hours"]:
            doc = _program_document(base, seed, h, gap, capacities[h])
            directory = seed_directory / f"H{h}_G{gap}" / f"hourly_seed_{seed}"
            if parent is None:
                if not directory.exists():
                    freeze_hourly_scenario(doc, seed=seed, output_directory=directory.parent)
                parent = load_frozen_hourly_scenario(directory)
            elif not directory.exists():
                directory.mkdir(parents=True)
                metadata = copy.deepcopy(parent.metadata)
                for name in metadata["files"]:
                    shutil.copyfile(parent.directory / name, directory / name)
                config_name = next(n for n in metadata["files"] if n.endswith("yaml"))
                (directory / config_name).write_text(yaml.safe_dump(doc, sort_keys=False))
                metadata["files"][config_name] = sha256_file(directory / config_name)
                metadata["events"] = [
                    dict(
                        event_id=i,
                        source_event_id=f"repeat_{i}",
                        start_hour=start,
                        stop_hour=start + h,
                        requested_reduction_kw=capacities[h],
                        notice_hours=0.0,
                    )
                    for i, start in enumerate(event_starts(h, gap))
                ]
                metadata.pop("scenario_hash")
                # Match the canonical metadata format in frozen_scenarios.py.
                metadata["scenario_hash"] = hashlib.sha256(
                    json.dumps(
                        metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                    ).encode()
                ).hexdigest()
                write_json(directory / "metadata.json", metadata)
            artifact = load_frozen_hourly_scenario(directory)
            for key in ("arrivals.parquet", "community.parquet", "baseline.parquet"):
                if artifact.metadata["files"][key] != parent.metadata["files"][key]:
                    raise ValueError("programs do not share exogenous and baseline inputs")
            programs.append(
                dict(
                    duration_h=h,
                    recovery_gap_h=gap,
                    path=str(directory),
                    scenario_hash=artifact.scenario_hash,
                )
            )
    assert parent is not None
    env = HourlyCommunityAIDemandResponseEnv(
        _repeated_environment_document(parent, notice_h=0, requested_reduction_kw=capacities[4])
    )
    baseline, summary = rollout_hourly_episode(env, make_hourly_controller("no_control"), seed=seed)
    baseline = baseline.drop(columns=["controller_action_time_ms"])
    seed_directory.mkdir(parents=True, exist_ok=True)
    baseline.to_parquet(seed_directory / "no_response.parquet", index=False)
    gate = baseline_service_gate(
        baseline, float(summary["deadline_miss_rate"]), env.config.pcc_capacity_kw
    )
    receipt = dict(
        role=role,
        seed=seed,
        protocol_sha256=sha256_file(PROTOCOL),
        programs=programs,
        no_response_sha256=sha256_file(seed_directory / "no_response.parquet"),
        baseline_service_feasible=gate,
        flexible_capacity_gpu_h=env.power_model.flexible_capacity_gpu_h,
        operating_peak_kw=env.power_model.reference_mix_operating_peak_kw,
    )
    write_json(record_path, receipt)
    return receipt


def deadline_features(remaining: Any, capacity_gpu_h: float, h: int) -> dict[str, float]:
    due = np.asarray(remaining, dtype=float)
    if (
        capacity_gpu_h <= 0
        or due.ndim != 1
        or len(due) < h
        or not np.isfinite(due).all()
        or (due < -1e-8).any()
    ):
        raise ValueError("invalid hourly deadline state")
    cumulative = np.cumsum(due)
    pressure = cumulative / (capacity_gpu_h * np.arange(1, len(due) + 1))
    backlog = float(due.sum())
    return dict(
        deadline_pressure=float(pressure.max()),
        event_due_work_gpu_h=float(cumulative[h - 1]),
        event_due_fraction=float(cumulative[h - 1] / max(backlog, 1e-12)),
        minimum_deadline_reserve_gpu_h=float(
            (capacity_gpu_h * np.arange(1, len(due) + 1) - cumulative).min()
        ),
    )


def series_ledger(
    frame: pd.DataFrame, baseline: pd.DataFrame, capacity: float, start: int
) -> dict[str, float]:
    """Account each hour once across all calls and the complete clearance tail."""
    if len(frame) != len(baseline) or not frame.hour.equals(baseline.hour):
        raise ValueError("series ledger needs matched complete hourly indices")
    for key in ("baseline_pcc_power_kw", "arrival_gpu_h", "community_power_kw"):
        if not np.allclose(frame[key], baseline[key], rtol=0, atol=1e-8):
            raise ValueError(f"paired inputs mismatch: {key}")
    ledger = frame.hour >= start
    active = frame.event_active
    reduction = (baseline.pcc_power_kw - frame.pcc_power_kw).clip(lower=0.0)
    delivered = np.minimum(reduction[active].to_numpy(), capacity)
    delay = (frame.backlog_gpu_h - baseline.backlog_gpu_h).clip(lower=0.0)
    return dict(
        event_hours=float(active.sum()),
        contracted_energy_kwh=float(capacity * active.sum()),
        capped_delivered_energy_kwh=float(delivered.sum()),
        shortfall_energy_kwh=float(capacity * active.sum() - delivered.sum()),
        incremental_energy_kwh=float((frame.pcc_power_kw - baseline.pcc_power_kw)[ledger].sum()),
        delay_exposure_gpu_h_h=float(delay[ledger].sum()),
        deferred_work_gpu_h=float(
            (baseline.executed_gpu_h - frame.executed_gpu_h).clip(lower=0.0)[active].sum()
        ),
        incremental_missed_gpu_h=float((frame.missed_gpu_h - baseline.missed_gpu_h)[ledger].sum()),
        terminal_incremental_backlog_gpu_h=float(
            frame.backlog_gpu_h.iloc[-1] - baseline.backlog_gpu_h.iloc[-1]
        ),
        peak_excess_backlog_gpu_h=float(delay[ledger].max()),
    )


def _evaluate_task(task: dict[str, Any]) -> dict[str, Any]:
    path = Path(task["checkpoint"])
    identity = canonical_hash(task)
    if path.exists():
        saved = cast(dict[str, Any], json.loads(path.read_text()))
        if (
            saved["task_sha256"] != identity
            or sha256_file(Path(saved["trace_path"])) != saved["trace_sha256"]
        ):
            raise ValueError("repeated-offer checkpoint identity or trace changed")
        return saved
    artifact = load_frozen_hourly_scenario(task["artifact"])
    seed_dir = artifact.directory.parents[1]
    receipt = json.loads((seed_dir / "freeze_receipt.json").read_text())
    baseline = pd.read_parquet(seed_dir / "no_response.parquet")
    frame, outcomes = _rollout_exhaustion_program(
        artifact,
        capacity_kw=task["capacity_kw"],
        controller_config=str(ROOT / load_protocol()["controller_config"]),
        event_ids=task["event_ids"],
    )
    frame = frame.drop(columns=["controller_action_time_ms"])
    event_rows = []
    for ordinal, outcome in enumerate(outcomes, start=1):
        row = frame.loc[frame.hour == outcome.start_hour].iloc[0]
        no = baseline.loc[baseline.hour == outcome.start_hour].iloc[0]
        success, failures = outcome.success(CRITERIA)
        local_success, local_failures = _local_event_decision(outcome, CRITERIA)
        event_rows.append(
            {
                **asdict(outcome),
                "event_ordinal": ordinal,
                "success": success,
                "failure_labels": list(failures),
                "local_success": local_success,
                "local_failure_labels": list(local_failures),
                "pre_event_excess_queue_energy_kwh": float(
                    row.decision_compute_debt_kwh - no.decision_compute_debt_kwh
                ),
                "pre_event_excess_backlog_gpu_h": float(
                    row.decision_backlog_gpu_h - no.decision_backlog_gpu_h
                ),
                "pre_event_backlog_gpu_h": float(row.decision_backlog_gpu_h),
                **deadline_features(
                    row.decision_remaining_by_deadline_gpu_h,
                    receipt["flexible_capacity_gpu_h"],
                    task["duration_h"],
                ),
            }
        )
    trace = path.with_suffix(".parquet")
    trace.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(trace, index=False)
    result = dict(
        task_sha256=identity,
        task=task,
        scenario_hash=artifact.scenario_hash,
        baseline_service_feasible=receipt["baseline_service_feasible"],
        joint_success=all(x["success"] for x in event_rows),
        event_rows=event_rows,
        ledger=series_ledger(frame, baseline, task["capacity_kw"], outcomes[0].start_hour),
        trace_path=str(trace),
        trace_sha256=sha256_file(trace),
        operating_peak_kw=receipt["operating_peak_kw"],
    )
    write_json(path, result)
    return result


def _parallel(function: Any, tasks: list[Any], workers: int, label: str) -> list[Any]:
    completed = []
    start = time.monotonic()
    with ProcessPoolExecutor(
        max_workers=workers, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        futures = {pool.submit(function, task): task for task in tasks}
        for future in as_completed(futures):
            completed.append(future.result())
            if len(completed) % max(1, min(100, len(tasks) // 10)) == 0 or len(completed) == len(
                tasks
            ):
                print(
                    f"{label} {len(completed)}/{len(tasks)} "
                    f"elapsed={time.monotonic() - start:.1f}s",
                    flush=True,
                )
    return completed


def run_stage(stage: str, *, workers: int, output: Path = OUTPUT, pilot: bool = False) -> None:
    protocol = load_protocol()
    output.mkdir(parents=True, exist_ok=True)
    identity = {
        "protocol_sha256": sha256_file(PROTOCOL),
        "pilot": pilot,
        "source_sha256": {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in sorted((ROOT / "src/aidrbench").rglob("*.py"))
        },
        "inputs": {
            name: sha256_file(ROOT / protocol[name])
            for name in (
                "development_environment",
                "confirmation_environment",
                "controller_config",
                "reference_certificates",
            )
        },
    }
    lock = output / "study_identity.json"
    if lock.exists() and json.loads(lock.read_text()) != identity:
        raise ValueError("study code, protocol or input identity changed; use a new output")
    write_json(lock, identity)
    capacities = reference_capacities(protocol)
    role = "development" if stage in {"freeze-development", "development"} else "confirmation"
    lo, hi = protocol[f"{role}_seeds"]
    seeds = list(range(lo, lo + 2 if pilot else hi + 1))
    if stage.startswith("freeze-"):
        rows = _parallel(
            _freeze_seed, [(role, seed, str(output)) for seed in seeds], workers, stage
        )
        write_json(
            output / role / "freeze_summary.json",
            {
                "seed_count": len(rows),
                "baseline_feasible_count": sum(r["baseline_service_feasible"] for r in rows),
                "seeds": seeds,
            },
        )
        return
    if stage not in {"development", "confirmation"}:
        raise ValueError("unsupported stage")
    selections = {}
    if role == "confirmation":
        selections = json.loads((output / "development/selected_offers.json").read_text())
    tasks = {}
    for seed in seeds:
        seed_dir = output / role / "scenarios" / f"seed_{seed}"
        receipt = json.loads((seed_dir / "freeze_receipt.json").read_text())
        for program in receipt["programs"]:
            h, gap = program["duration_h"], program["recovery_gap_h"]
            fractions = (
                protocol["offer_fractions"]
                if role == "development"
                else sorted({1.0, float(selections[f"H{h}_G{gap}"]["selected_fraction"])} - {0.0})
            )
            for fraction in fractions:
                name = f"seed{seed}_H{h}_G{gap}_f{round(fraction * 1000):04d}_repeated"
                tasks[name] = dict(
                    role=role,
                    seed=seed,
                    duration_h=h,
                    recovery_gap_h=gap,
                    fraction=fraction,
                    capacity_kw=capacities[h] * fraction,
                    kind="repeated",
                    event_ids=None,
                    artifact=program["path"],
                    checkpoint=str(output / role / "checkpoints" / (name + ".json")),
                    study_sha256=canonical_hash(identity),
                )
            if role == "confirmation":
                for ordinal, start in enumerate(event_starts(h, gap)):
                    name = f"seed{seed}_H{h}_T{start}_fresh"
                    if name not in tasks:
                        tasks[name] = dict(
                            role=role,
                            seed=seed,
                            duration_h=h,
                            recovery_gap_h=gap,
                            fraction=1.0,
                            capacity_kw=capacities[h],
                            kind="fresh",
                            event_ids=[ordinal],
                            artifact=program["path"],
                            checkpoint=str(output / role / "checkpoints" / (name + ".json")),
                            study_sha256=canonical_hash(identity),
                        )
    results = _parallel(_evaluate_task, list(tasks.values()), workers, stage)
    episodes: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    for result in results:
        task = result["task"]
        common = {
            k: task[k]
            for k in (
                "role",
                "seed",
                "duration_h",
                "recovery_gap_h",
                "fraction",
                "capacity_kw",
                "kind",
            )
        }
        episodes.append(
            {
                **common,
                "joint_success": result["joint_success"],
                "baseline_service_feasible": result["baseline_service_feasible"],
                "operating_peak_kw": result["operating_peak_kw"],
                **result["ledger"],
            }
        )
        events.extend({**common, **row} for row in result["event_rows"])
    frame = pd.DataFrame(episodes).sort_values(
        ["seed", "duration_h", "recovery_gap_h", "fraction", "kind"]
    )
    frame.to_parquet(output / role / "episode_results.parquet", index=False)
    pd.DataFrame(events).to_parquet(output / role / "event_results.parquet", index=False)
    summaries = []
    for _key, group in frame[frame.kind == "repeated"].groupby(
        ["duration_h", "recovery_gap_h", "fraction"]
    ):
        k, n = int(group.joint_success.sum()), len(group)
        summaries.append(
            dict(
                duration_h=int(group.duration_h.iloc[0]),
                recovery_gap_h=int(group.recovery_gap_h.iloc[0]),
                fraction=float(group.fraction.iloc[0]),
                capacity_kw=float(group.capacity_kw.iloc[0]),
                successes=k,
                n=n,
                success_fraction=k / n,
                wilson_lower_bound=wilson_lower_bound(k, n, 0.95),
            )
        )
    summary = pd.DataFrame(summaries)
    summary.to_csv(output / role / "capacity_summary.csv", index=False)
    if role == "development":
        for (h, gap), group in summary.groupby(["duration_h", "recovery_gap_h"]):
            eligible = group[group.wilson_lower_bound >= 0.95]
            selected = float(eligible.fraction.max()) if len(eligible) else 0.0
            selections[f"H{h}_G{gap}"] = dict(
                selected_fraction=selected,
                capacity_kw=selected * capacities[int(group.duration_h.iloc[0])],
                status="candidate_selected"
                if selected
                else "no_positive_candidate_qualified_in_development",
            )
        write_json(output / role / "selected_offers.json", selections)
    print(summary.to_string(index=False), flush=True)
