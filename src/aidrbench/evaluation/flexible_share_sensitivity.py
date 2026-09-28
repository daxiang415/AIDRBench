"""Post-hoc paired workload-eligibility and GPU-pool sensitivity.

This module derives new, non-locked artifacts. It does not modify the original
scenario generator, oracle, controller, or sealed paper results.
"""

from __future__ import annotations

import copy
import json
import math
import multiprocessing
import time
from collections.abc import Callable, Mapping
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from aidrbench.controllers.hourly import make_hourly_controller
from aidrbench.controllers.robust_mpc_spec import load_robust_mpc_specification
from aidrbench.data.frozen_scenarios import (
    freeze_hourly_scenario,
    load_frozen_hourly_scenario,
)
from aidrbench.data.splits import sha256_file
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv
from aidrbench.envs.hourly_config import load_hourly_environment_config
from aidrbench.evaluation.firm_flexibility import (
    FirmFlexibilityCriteria,
    derive_event_outcomes,
    event_outcomes_frame,
    wilson_lower_bound,
)
from aidrbench.evaluation.frozen_causal_certificate import (
    _environment_document as causal_document,
)
from aidrbench.evaluation.hourly_rollout import rollout_hourly_episode
from aidrbench.evaluation.notice_diagnostics import _eligible_pre_execution_work_gpu_h
from aidrbench.evaluation.pi_frontier import (
    solve_frozen_pi_frontier,
    summarize_pi_firm_boundary,
)


@dataclass(frozen=True)
class ShareCase:
    name: str
    axis: str
    workload_fraction: float
    gpu_pool_fraction: float


def load_spec(path: str | Path) -> dict[str, Any]:
    spec = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(spec, dict) or spec.get("schema_version") != 1:
        raise ValueError("invalid flexible-share specification")
    if spec.get("evidence_scope") != "post_hoc_nonlocked_paired_sensitivity":
        raise ValueError("this analysis must remain explicitly post-hoc and nonlocked")
    for role in ("development", "validation"):
        if "locked" in str(spec[f"{role}_scenarios"]):
            raise ValueError("flexible-share analysis cannot open locked inputs")
    if spec["eligibility_rule"] != "training_first_then_offline_inference":
        raise ValueError("unimplemented eligibility allocation")
    return dict(spec)


def cases_for(spec: Mapping[str, Any]) -> list[ShareCase]:
    reference_f = float(spec["reference_workload_fraction"])
    reference_g = float(spec["reference_gpu_pool_fraction"])
    result = [ShareCase("reference", "reference", reference_f, reference_g)]
    for fraction in spec["workload_fractions"]:
        if float(fraction) != reference_f:
            result.append(
                ShareCase(
                    f"work_{round(100 * fraction):03d}", "workload", float(fraction), reference_g
                )
            )
    for fraction in spec["gpu_pool_fractions"]:
        if float(fraction) != reference_g:
            result.append(
                ShareCase(
                    f"pool_{round(100 * fraction):03d}", "gpu_pool", reference_f, float(fraction)
                )
            )
    if len({case.name for case in result}) != len(result):
        raise ValueError("duplicate case names")
    return result


def case_document(
    parent: Mapping[str, Any],
    case: ShareCase,
    *,
    total_work_gpu_h_per_hour: float,
) -> tuple[dict[str, Any], dict[str, float | int]]:
    """Hold total work fixed while explicitly accounting for integer GPU pools."""
    f, g = case.workload_fraction, case.gpu_pool_fraction
    if not (0 < f < 1 and 0 < g < 1):
        raise ValueError("workload and GPU fractions must be strictly between zero and one")
    document = copy.deepcopy(dict(parent))
    document.pop("scenario", None)
    dc, work = document["virtual_datacenter"], document["workload"]
    total_gpus = int(dc["node_count"]) * int(dc["gpus_per_node"])
    flexible_gpus = round(total_gpus * g)
    rigid_gpus = total_gpus - flexible_gpus
    rigid_work = total_work_gpu_h_per_hour * (1 - f)
    rigid_utilization = rigid_work / rigid_gpus
    if rigid_utilization > 1 + 1e-12:
        raise ValueError("rigid demand exceeds its physical GPU pool")
    for key in ("target_total_utilization", "target_flexible_utilization"):
        dc.pop(key, None)
        work.pop(key, None)
    dc["flexible_gpu_fraction"] = g
    dc["rigid_gpu_utilization"] = rigid_utilization
    work["flexible_arrival_utilization"] = total_work_gpu_h_per_hour / total_gpus
    fractions = {"training": min(2 * f, 1.0), "offline_inference": max(2 * f - 1, 0.0)}
    work["workload_mix"] = {
        "shares": {"training": 0.5, "offline_inference": 0.5},
        "flexible_fractions": fractions,
    }
    facts: dict[str, float | int] = {
        "total_gpu_count": total_gpus,
        "flexible_gpu_count": flexible_gpus,
        "rigid_gpu_count": rigid_gpus,
        "realized_gpu_pool_fraction": flexible_gpus / total_gpus,
        "total_work_gpu_h_per_hour": total_work_gpu_h_per_hour,
        "flexible_work_gpu_h_per_hour": total_work_gpu_h_per_hour * f,
        "rigid_work_gpu_h_per_hour": rigid_work,
        "actual_flexible_pool_utilization": total_work_gpu_h_per_hour * f / flexible_gpus,
        "rigid_gpu_utilization": rigid_utilization,
        "training_eligible_fraction": fractions["training"],
        "offline_inference_eligible_fraction": fractions["offline_inference"],
    }
    return document, facts


def scaled_arrivals(parent: pd.DataFrame, case: ShareCase) -> pd.DataFrame:
    """Preserve paired release/deadline records, scaling divisible class work."""
    fractions = {
        "training": min(2 * case.workload_fraction, 1.0),
        "offline_inference": max(2 * case.workload_fraction - 1, 0.0) / 0.5,
    }
    result = parent.copy()
    weights = result["job_class"].map(fractions)
    if weights.isna().any():
        raise ValueError("parent arrivals contain an unexpected class")
    result["arrival_gpu_h"] = result["arrival_gpu_h"] * weights
    return result.loc[result["arrival_gpu_h"] > 0].reset_index(drop=True)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _write_table(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_parquet(temporary, index=False)
    temporary.replace(path)


def _parallel(
    worker: Callable[[dict[str, Any]], dict[str, Any]],
    payloads: list[dict[str, Any]],
    *,
    workers: int,
    label: str,
) -> list[dict[str, Any]]:
    start = time.monotonic()
    rows = []
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=workers, mp_context=context) as pool:
        futures = [pool.submit(worker, payload) for payload in payloads]
        interval = max(1, math.ceil(len(futures) / 40))
        for completed, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if completed % interval == 0 or completed == len(futures):
                print(
                    f"{label}: {completed}/{len(futures)}, {time.monotonic() - start:.1f}s",
                    flush=True,
                )
    return rows


def _freeze_worker(payload: dict[str, Any]) -> dict[str, Any]:
    root = Path(payload["output"])
    role, seed = str(payload["role"]), int(payload["seed"])
    case = ShareCase(**payload["case"])
    parent = load_frozen_hourly_scenario(Path(payload["parent"]) / f"hourly_seed_{seed}")
    doc, facts = case_document(
        parent.config_document, case, total_work_gpu_h_per_hour=float(payload["total_work"])
    )
    parent_mix = parent.config_document["workload"]["workload_mix"]
    if parent_mix != {
        "shares": {"training": 0.5, "offline_inference": 0.5},
        "flexible_fractions": {"training": 1.0, "offline_inference": 0.5},
    }:
        raise ValueError("unexpected parent class mix")
    arrivals = scaled_arrivals(parent.arrivals, case)
    expected = float(facts["flexible_work_gpu_h_per_hour"]) * 168
    if not math.isclose(float(arrivals["arrival_gpu_h"].sum()), expected, abs_tol=1e-7):
        raise ValueError("paired arrivals do not preserve the specified total work")
    arrival_path = root / "inputs" / role / case.name / f"{seed}.parquet"
    if not arrival_path.exists():
        _write_table(arrival_path, arrivals)
    elif not pd.read_parquet(arrival_path).equals(arrivals):
        raise ValueError("existing derived arrivals differ")
    doc["workload"]["arrivals_path"] = str(arrival_path)
    destination = root / "scenarios" / role / case.name
    artifact_path = destination / f"hourly_seed_{seed}"
    if not (artifact_path / "metadata.json").exists():
        freeze_hourly_scenario(doc, seed=seed, output_directory=destination)
    artifact = load_frozen_hourly_scenario(artifact_path)
    if not artifact.arrivals.equals(arrivals) or not artifact.community.equals(parent.community):
        raise ValueError("frozen paired exogenous inputs changed")
    if artifact.config_document != doc:
        raise ValueError("existing case configuration differs")
    if artifact.events[0]["start_hour"] != parent.events[0]["start_hour"]:
        raise ValueError("paired event anchor changed")
    if (
        artifact.metadata["exogenous_random_stream_seeds"]
        != parent.metadata["exogenous_random_stream_seeds"]
    ):
        raise ValueError("paired random streams changed")
    config = load_hourly_environment_config(doc)
    baseline = artifact.metadata["no_dr_baseline"]
    missed = float(baseline["deadline_miss_gpu_h"]) / expected
    terminal = float(baseline["terminal_backlog_gpu_h"]) / expected
    pcc_excess = max(
        float(artifact.baseline["baseline_pcc_power_kw"].max()) - config.pcc_capacity_kw, 0
    )
    return {
        "case": case.name,
        "axis": case.axis,
        "workload_fraction": case.workload_fraction,
        "gpu_pool_fraction": case.gpu_pool_fraction,
        "role": role,
        "episode_seed": seed,
        "parent_scenario_hash": parent.scenario_hash,
        "scenario_hash": artifact.scenario_hash,
        "artifact_path": str(artifact_path),
        **facts,
        "reference_mix_operating_peak_kw": artifact.metadata["scenario_bases"][
            "reference_mix_operating_peak_kw"
        ],
        "baseline_deadline_miss_rate": missed,
        "baseline_terminal_backlog_fraction": terminal,
        "baseline_pcc_excess_kw": pcc_excess,
        "service_feasible": bool(
            missed <= config.reward.max_deadline_miss_rate + 1e-12
            and terminal <= config.reward.max_terminal_backlog_fraction + 1e-12
            and pcc_excess <= 1e-6
        ),
    }


def freeze(spec: Mapping[str, Any], *, workers: int) -> None:
    root = Path(spec["output_directory"])
    payloads = []
    for role in ("development", "validation"):
        lower, upper = spec[f"{role}_seeds"]
        for case in cases_for(spec):
            for seed in range(lower, upper + 1):
                payloads.append(
                    {
                        "role": role,
                        "seed": seed,
                        "case": asdict(case),
                        "output": str(root),
                        "parent": spec[f"{role}_scenarios"],
                        "total_work": spec["total_work_gpu_h_per_hour"],
                    }
                )
    rows = _parallel(_freeze_worker, payloads, workers=workers, label="freeze/gate")
    frame = pd.DataFrame(rows).sort_values(["case", "role", "episode_seed"])
    _write_table(root / "scenario_index.parquet", frame)
    gate = (
        frame.groupby("case", sort=True)
        .agg(
            workload_fraction=("workload_fraction", "first"),
            gpu_pool_fraction=("gpu_pool_fraction", "first"),
            scenario_count=("service_feasible", "size"),
            feasible_count=("service_feasible", "sum"),
            all_service_feasible=("service_feasible", "all"),
            maximum_baseline_deadline_miss_rate=("baseline_deadline_miss_rate", "max"),
            maximum_baseline_terminal_backlog_fraction=(
                "baseline_terminal_backlog_fraction",
                "max",
            ),
            maximum_baseline_pcc_excess_kw=("baseline_pcc_excess_kw", "max"),
        )
        .reset_index()
    )
    _write_table(root / "service_gate.parquet", gate)
    print(gate.to_string(index=False), flush=True)


def _pi_worker(payload: dict[str, Any]) -> dict[str, Any]:
    artifact = load_frozen_hourly_scenario(payload["artifact_path"])
    destination = Path(payload["result_path"])
    if destination.exists():
        frame = pd.read_parquet(destination)
    else:
        frame = solve_frozen_pi_frontier(artifact, durations_h=payload["durations"])
        frame["case"] = payload["case"]
        frame["role"] = payload["role"]
        frame["workload_fraction"] = payload["workload_fraction"]
        frame["gpu_pool_fraction"] = payload["gpu_pool_fraction"]
        _write_table(destination, frame)
    if (
        set(frame["scenario_hash"]) != {artifact.scenario_hash}
        or set(frame["duration_h"]) != set(payload["durations"])
        or set(frame["perfect_information_status"]) != {"optimal"}
    ):
        raise ValueError("PI output incomplete, nonoptimal or from a different scenario")
    return {"path": str(destination)}


def pi(spec: Mapping[str, Any], *, workers: int) -> None:
    root = Path(spec["output_directory"])
    index = pd.read_parquet(root / "scenario_index.parquet")
    gate = pd.read_parquet(root / "service_gate.parquet")
    feasible = set(gate.loc[gate["all_service_feasible"], "case"])
    payloads = []
    for raw_row in index.loc[index["case"].isin(feasible)].to_dict(orient="records"):
        row = {str(key): value for key, value in raw_row.items()}
        durations = (
            spec["pi_durations_h"] if row["role"] == "validation" else spec["notice_durations_h"]
        )
        destination = root / "pi" / row["role"] / row["case"] / f"{row['episode_seed']}.parquet"
        payloads.append({**row, "durations": durations, "result_path": str(destination)})
    outputs = _parallel(_pi_worker, payloads, workers=workers, label="PI scenario frontiers")
    frame = pd.concat([pd.read_parquet(row["path"]) for row in outputs], ignore_index=True)
    frame = frame.sort_values(["case", "role", "episode_seed", "duration_h"])
    _write_table(root / "pi_scenario_frontiers.parquet", frame)
    boundaries = []
    for (case, role), group in frame.groupby(["case", "role"], sort=True):
        boundary = summarize_pi_firm_boundary(
            group,
            reliability_targets=[spec["reliability_target"]],
            confidence_level=spec["confidence_level"],
            nominal_flexibility_fraction=0.5,
        )
        boundary["case"], boundary["role"] = str(case), str(role)
        boundary["workload_fraction"] = float(group["workload_fraction"].iloc[0])
        boundary["gpu_pool_fraction"] = float(group["gpu_pool_fraction"].iloc[0])
        boundaries.append(boundary)
    summary = pd.concat(boundaries, ignore_index=True)
    _write_table(root / "pi_boundaries.parquet", summary)
    selected = summary.loc[summary["role"] == "development"].copy()
    selected = selected.rename(columns={"perfect_information_firm_capacity_kw": "fixed_offer_kw"})
    _write_table(root / "fixed_notice_offers.parquet", selected)
    _write_json(
        root / "fixed_notice_offers_receipt.json",
        {
            "rule": spec["fixed_offer_rule"],
            "source": "development_only",
            "selection_sha256": sha256_file(root / "fixed_notice_offers.parquet"),
            "controller_sha256": sha256_file(spec["controller_config"]),
            "notice_evaluation_started": False,
        },
    )


def _causal_worker(payload: dict[str, Any]) -> dict[str, Any]:
    artifact = load_frozen_hourly_scenario(payload["artifact_path"])
    destination = Path(payload["result_path"])
    record_path = destination.with_suffix(".json")
    if record_path.exists() and destination.exists():
        cached: dict[str, Any] = json.loads(record_path.read_text(encoding="utf-8"))
        if (
            cached["scenario_hash"] != artifact.scenario_hash
            or cached["fixed_offer_kw"] != payload["fixed_offer_kw"]
            or cached["controller_sha256"] != payload["controller_sha256"]
        ):
            raise ValueError("cached causal output provenance mismatch")
        return cached
    duration, notice = int(payload["duration_h"]), int(payload["notice_h"])
    document = causal_document(
        artifact,
        duration_h=duration,
        notice_h=notice,
        requested_reduction_kw=float(payload["fixed_offer_kw"]),
        event_id=0,
    )
    env = HourlyCommunityAIDemandResponseEnv(document)
    env.reset(seed=artifact.episode_seed)
    snapshot = env.full_horizon_planning_snapshot()
    reward = env.config.reward
    criteria = FirmFlexibilityCriteria(
        reliability_target=0.95,
        confidence_level=0.95,
        min_delivery_ratio=reward.min_delivery_ratio,
        min_interval_delivery_ratio=reward.min_delivery_ratio,
        max_deadline_miss_rate=reward.max_deadline_miss_rate,
        max_rebound_ratio=reward.max_rebound_ratio,
        min_window_peak_relief_fraction=reward.min_window_peak_relief_fraction,
        max_terminal_backlog_fraction=reward.max_terminal_backlog_fraction,
    )
    specification = load_robust_mpc_specification(payload["controller_config"])
    controller = make_hourly_controller("robust_mpc", robust_mpc_specification=specification)
    frame, _ = rollout_hourly_episode(env, controller, seed=artifact.episode_seed)
    outcomes = derive_event_outcomes(
        frame,
        env.event_manifest,
        recovery_tolerance_gpu_h=(
            env.config.recovery_backlog_tolerance_fraction * snapshot.capacity_gpu_h
        ),
    )
    outcome = event_outcomes_frame(outcomes, criteria)
    if len(outcome) != 1:
        raise ValueError("expected a single-event notice evaluation")
    event = env.event_manifest[0]
    notice_start = max(0, event.start_hour - notice)
    before = frame.loc[(frame["hour"] >= event.start_hour - 6) & (frame["hour"] < event.start_hour)]
    start_row = frame.loc[frame["hour"] == event.start_hour].iloc[0]
    record: dict[str, Any] = {
        "case": payload["case"],
        "scenario_hash": artifact.scenario_hash,
        "episode_seed": artifact.episode_seed,
        "duration_h": duration,
        "notice_h": notice,
        "fixed_offer_kw": float(payload["fixed_offer_kw"]),
        "controller_sha256": payload["controller_sha256"],
        "event_start_hour": event.start_hour,
        **{str(key): value for key, value in outcome.iloc[0].to_dict().items()},
        "eligible_pre_execution_work_gpu_h": _eligible_pre_execution_work_gpu_h(
            snapshot, frame, notice_start=notice_start, event_start=event.start_hour
        ),
        "pre_event_spare_capacity_gpu_h": sum(
            max(snapshot.capacity_gpu_h - snapshot.baseline_execution_gpu_h[h], 0.0)
            for h in range(notice_start, event.start_hour)
        ),
        "pre_event_6h_executed_gpu_h": float(before["executed_gpu_h"].sum()),
        "event_start_backlog_gpu_h": float(start_row["decision_backlog_gpu_h"]),
        "frame_path": str(destination),
    }
    # Event metrics such as recovery time can be undefined; preserve this as
    # JSON null, with an explicit field list, rather than nonstandard NaN.
    missing = [
        key for key, value in record.items() if isinstance(value, float) and math.isnan(value)
    ]
    for key in missing:
        record[key] = None
    record["undefined_metric_fields"] = missing
    _write_table(destination, frame)
    _write_json(record_path, record)
    return record


def causal(spec: Mapping[str, Any], *, workers: int) -> None:
    root = Path(spec["output_directory"])
    index = pd.read_parquet(root / "scenario_index.parquet")
    offers = pd.read_parquet(root / "fixed_notice_offers.parquet")
    receipt = json.loads((root / "fixed_notice_offers_receipt.json").read_text())
    controller_hash = sha256_file(spec["controller_config"])
    if (
        receipt["selection_sha256"] != sha256_file(root / "fixed_notice_offers.parquet")
        or receipt["controller_sha256"] != controller_hash
    ):
        raise ValueError("frozen requests or controller changed before notice evaluation")
    payloads = []
    for offer in offers.to_dict(orient="records"):
        selected = index.loc[(index["role"] == "validation") & (index["case"] == offer["case"])]
        for row in selected.to_dict(orient="records"):
            for notice in spec["notices_h"]:
                duration = int(offer["duration_h"])
                destination = (
                    root
                    / "causal"
                    / row["case"]
                    / f"h{duration}_n{notice}"
                    / f"{row['episode_seed']}.parquet"
                )
                payloads.append(
                    {
                        **row,
                        "duration_h": duration,
                        "notice_h": notice,
                        "fixed_offer_kw": float(offer["fixed_offer_kw"]),
                        "controller_config": spec["controller_config"],
                        "controller_sha256": controller_hash,
                        "result_path": str(destination),
                    }
                )
    receipt["notice_evaluation_started"] = True
    _write_json(root / "fixed_notice_offers_receipt.json", receipt)
    rows = _parallel(_causal_worker, payloads, workers=workers, label="causal notice episodes")
    frame = pd.DataFrame(rows).sort_values(["case", "duration_h", "notice_h", "episode_seed"])
    _write_table(root / "causal_notice_outcomes.parquet", frame)


def export(spec: Mapping[str, Any]) -> None:
    from scipy.stats import binomtest, t  # type: ignore[import-untyped]

    root, source = Path(spec["output_directory"]), Path(spec["source_data_directory"])
    source.mkdir(parents=True, exist_ok=True)
    index = pd.read_parquet(root / "scenario_index.parquet")
    gate = pd.read_parquet(root / "service_gate.parquet")
    pi_frame = pd.read_parquet(root / "pi_scenario_frontiers.parquet")
    boundaries = pd.read_parquet(root / "pi_boundaries.parquet")
    outcomes = pd.read_parquet(root / "causal_notice_outcomes.parquet")
    tables = {
        "scenario_parameters_and_service_gate": index,
        "service_gate_summary": gate,
        "pi_scenario_capacities": pi_frame,
        "pi_tolerance_bounds": boundaries,
        "fixed_notice_offers": pd.read_parquet(root / "fixed_notice_offers.parquet"),
        "causal_notice_outcomes": outcomes,
    }
    parameters = index.drop_duplicates("case").drop(
        columns=[
            "episode_seed",
            "role",
            "parent_scenario_hash",
            "scenario_hash",
            "artifact_path",
            "baseline_deadline_miss_rate",
            "baseline_terminal_backlog_fraction",
            "baseline_pcc_excess_kw",
            "service_feasible",
        ]
    )
    tables["plot_pi_capacity_by_fraction"] = boundaries.loc[
        boundaries["role"] == "validation"
    ].merge(
        parameters,
        on=["case", "workload_fraction", "gpu_pool_fraction"],
        suffixes=("", "_parameter"),
        validate="many_to_one",
    )
    contrasts = []
    validation_pi = pi_frame.loc[pi_frame["role"] == "validation"]
    reference = validation_pi.loc[validation_pi["case"] == "reference"]
    family_size = (validation_pi["case"].nunique() - 1) * len(spec["pi_durations_h"])
    for (case, duration), group in validation_pi.groupby(["case", "duration_h"]):
        if case == "reference":
            continue
        joined = group.merge(
            reference.loc[reference["duration_h"] == duration],
            on=["episode_seed", "duration_h"],
            suffixes=("", "_ref"),
            validate="one_to_one",
        )
        difference = (
            joined["perfect_information_capacity_kw"]
            - joined["perfect_information_capacity_kw_ref"]
        ).to_numpy()
        n = len(difference)
        mean = float(np.mean(difference))
        half = float(
            t.ppf(1 - 0.05 / (2 * family_size), n - 1) * np.std(difference, ddof=1) / np.sqrt(n)
        )
        contrasts.append(
            {
                "case": case,
                "duration_h": duration,
                "n_paired": n,
                "mean_difference_kw": mean,
                "simultaneous_ci_lower_kw": mean - half,
                "simultaneous_ci_upper_kw": mean + half,
                "family_size": family_size,
                "minimum_difference_kw": float(np.min(difference)),
                "maximum_difference_kw": float(np.max(difference)),
            }
        )
    tables["pi_paired_contrasts"] = pd.DataFrame(contrasts)
    notice_summary = []
    for (case, duration, notice), group in outcomes.groupby(["case", "duration_h", "notice_h"]):
        count, n = int(group["success"].sum()), len(group)
        lower = wilson_lower_bound(count, n, spec["confidence_level"])
        notice_summary.append(
            {
                "case": case,
                "duration_h": duration,
                "notice_h": notice,
                "fixed_offer_kw": float(group["fixed_offer_kw"].iloc[0]),
                "success_count": count,
                "n": n,
                "success_fraction": count / n,
                "wilson_lower_bound": lower,
                "meets_pointwise_q95": lower + 1e-12 >= spec["reliability_target"],
                "mean_eligible_pre_execution_work_gpu_h": float(
                    group["eligible_pre_execution_work_gpu_h"].mean()
                ),
                "mean_pre_event_spare_capacity_gpu_h": float(
                    group["pre_event_spare_capacity_gpu_h"].mean()
                ),
                "mean_event_start_backlog_gpu_h": float(group["event_start_backlog_gpu_h"].mean()),
            }
        )
    tables["plot_causal_notice_summary"] = pd.DataFrame(notice_summary).merge(
        parameters, on="case", validate="many_to_one"
    )
    notice_contrasts = []
    for (case, duration), group in outcomes.groupby(["case", "duration_h"]):
        zero = group.loc[group["notice_h"] == 0]
        for notice in spec["notices_h"]:
            if notice == 0:
                continue
            paired = group.loc[group["notice_h"] == notice].merge(
                zero,
                on=["scenario_hash", "episode_seed"],
                suffixes=("", "_n0"),
                validate="one_to_one",
            )
            improved = int((paired["success"] & ~paired["success_n0"]).sum())
            worsened = int((~paired["success"] & paired["success_n0"]).sum())
            discordant = improved + worsened
            difference = (
                paired["pre_event_6h_executed_gpu_h"] - paired["pre_event_6h_executed_gpu_h_n0"]
            )
            notice_contrasts.append(
                {
                    "case": case,
                    "duration_h": duration,
                    "notice_h": notice,
                    "n_paired": len(paired),
                    "improved_success_count": improved,
                    "worsened_success_count": worsened,
                    "success_difference_pp": 100 * (improved - worsened) / len(paired),
                    "mcnemar_exact_p": float(binomtest(improved, discordant, 0.5).pvalue)
                    if discordant
                    else 1.0,
                    "mean_pre_event_execution_difference_gpu_h": float(difference.mean()),
                    "max_abs_pre_event_execution_difference_gpu_h": float(difference.abs().max()),
                    "max_abs_event_backlog_difference_gpu_h": float(
                        (
                            paired["event_start_backlog_gpu_h"]
                            - paired["event_start_backlog_gpu_h_n0"]
                        )
                        .abs()
                        .max()
                    ),
                }
            )
    contrast = pd.DataFrame(notice_contrasts)
    order = np.argsort(contrast["mcnemar_exact_p"].to_numpy(), kind="stable")
    adjusted = np.zeros(len(contrast))
    running = 0.0
    for rank, position in enumerate(order):
        running = max(
            running, float(contrast.iloc[position]["mcnemar_exact_p"]) * (len(contrast) - rank)
        )
        adjusted[position] = min(running, 1.0)
    contrast["mcnemar_holm_p"] = adjusted
    contrast["family_size"] = len(contrast)
    tables["notice_paired_contrasts"] = contrast
    nominal = []
    ref_bounds = boundaries.loc[
        (boundaries["role"] == "validation") & (boundaries["case"] == "reference")
    ]
    for row in ref_bounds.to_dict(orient="records"):
        for fraction in spec["nominal_proxy_fractions"]:
            proxy = fraction * row["reference_mix_operating_peak_kw"]
            bound = row["perfect_information_firm_capacity_kw"]
            nominal.append(
                {
                    "duration_h": row["duration_h"],
                    "nominal_proxy_fraction": fraction,
                    "nominal_proxy_kw": proxy,
                    "pi_tolerance_bound_kw": bound,
                    "proxy_minus_bound_kw": proxy - bound,
                    "relative_gap_percent": 100 * (proxy - bound) / proxy,
                    "interpretation": "algebraic_comparison_only_no_model_change",
                }
            )
    tables["plot_nominal_proxy_comparison"] = pd.DataFrame(nominal)
    manifest: dict[str, Any] = {"evidence_scope": spec["evidence_scope"], "files": {}}
    for name, table in tables.items():
        path = source / f"{name}.csv"
        table.to_csv(path, index=False, float_format="%.12g")
        manifest["files"][path.name] = {"rows": len(table), "sha256": sha256_file(path)}
    _write_json(source / "source_data_manifest.json", manifest)
    print(json.dumps({name: len(table) for name, table in tables.items()}, indent=2), flush=True)


def run_stage(specification: str | Path, *, stage: str, workers: int) -> None:
    spec = load_spec(specification)
    root = Path(spec["output_directory"])
    root.mkdir(parents=True, exist_ok=True)
    source_files = [
        Path(specification),
        Path(__file__),
        Path("docs/flexible_share_sensitivity/protocol_v1.md"),
        Path(spec["controller_config"]),
    ]
    fingerprint = {str(path): sha256_file(path) for path in source_files}
    receipt_path = root / "execution_inputs.json"
    if receipt_path.exists():
        previous = json.loads(receipt_path.read_text(encoding="utf-8"))
        if previous["sha256"] != fingerprint:
            raise ValueError("execution source/specification changed; use a versioned output root")
    else:
        _write_json(receipt_path, {"sha256": fingerprint, "specification": spec})
    if stage == "freeze":
        freeze(spec, workers=workers)
    elif stage == "pi":
        pi(spec, workers=workers)
    elif stage == "causal":
        causal(spec, workers=workers)
    elif stage == "export":
        export(spec)
    else:
        raise ValueError("unknown stage")
