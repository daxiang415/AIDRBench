"""Reliable, rebound-aware flexibility certificates for hourly controllers."""

from __future__ import annotations

import copy
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

import pandas as pd
import yaml

from aidrbench.controllers.hourly import make_hourly_controller
from aidrbench.controllers.hourly_sb3 import SB3AlgorithmName, SB3HourlyPolicyController
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv
from aidrbench.evaluation.firm_flexibility import (
    FirmFlexibilityCriteria,
    derive_event_outcomes,
    event_outcomes_frame,
    wilson_lower_bound,
)
from aidrbench.evaluation.hourly_rollout import HourlyController, rollout_hourly_episode

ControllerName = Literal[
    "no_control",
    "threshold",
    "edf_valley",
    "mpc",
    "robust_mpc",
    "dqn",
    "ppo",
    "sac",
]
_RL_NAMES = frozenset(("dqn", "ppo", "sac"))


@dataclass(frozen=True, slots=True)
class FlexibilityCertificate:
    """One event-program capacity result under a frozen success protocol."""

    controller: str
    duration_h: int
    notice_h: int
    event_start_hours: tuple[int, ...]
    event_start_jitter_hours: int
    event_count_per_episode: int
    certificate_scope: str
    reliability_target: float
    confidence_level: float
    certified_reduction_kw: float
    certified_reduction_fraction_of_dc_peak: float
    success_count: int
    episode_count: int
    success_rate: float
    success_rate_lower_ci: float
    mean_delivery_ratio: float
    minimum_interval_delivery_ratio: float
    p95_deadline_miss_rate: float
    p95_rebound_ratio: float
    mean_window_peak_relief_kw: float
    p05_window_peak_relief_fraction: float
    p95_recovery_time_h: float
    dc_peak_kw: float


def _read_mapping(config: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(config, str | Path):
        with Path(config).open(encoding="utf-8") as handle:
            raw: object = yaml.safe_load(handle)
    else:
        raw = config
    if not isinstance(raw, Mapping):
        raise ValueError("hourly certificate config must be a mapping")
    return copy.deepcopy({str(key): value for key, value in raw.items()})


def make_certificate_scenario(
    config: str | Path | Mapping[str, Any],
    *,
    duration_h: int,
    requested_reduction_kw: float,
    notice_h: int = 0,
    event_start_hours: Sequence[int] | None = None,
    event_start_jitter_hours: int | None = None,
) -> dict[str, Any]:
    """Freeze one repeated-event certificate program without mutating its config."""

    if isinstance(duration_h, bool) or duration_h <= 0:
        raise ValueError("duration_h must be positive")
    if not math.isfinite(requested_reduction_kw) or requested_reduction_kw < 0.0:
        raise ValueError("requested_reduction_kw must be finite and non-negative")
    if isinstance(notice_h, bool) or not isinstance(notice_h, int) or notice_h < 0:
        raise ValueError("notice_h must be a non-negative integer")
    document = _read_mapping(config)
    raw_dr = document.get("dr")
    if not isinstance(raw_dr, Mapping):
        raise ValueError("hourly certificate config requires a dr mapping")
    dr = dict(raw_dr)
    raw_starts = dr.get("event_start_hours") if event_start_hours is None else event_start_hours
    if (
        not isinstance(raw_starts, Sequence)
        or isinstance(raw_starts, str | bytes)
        or not raw_starts
        or any(
            isinstance(hour, bool) or not isinstance(hour, int) or hour < 0
            for hour in raw_starts
        )
    ):
        raise ValueError("event_start_hours must contain non-negative integer hours")
    starts = tuple(int(hour) for hour in raw_starts)
    if len(set(starts)) != len(starts) or tuple(sorted(starts)) != starts:
        raise ValueError("event_start_hours must be unique and increasing")
    raw_jitter = (
        dr.get("event_start_jitter_hours", 0)
        if event_start_jitter_hours is None
        else event_start_jitter_hours
    )
    if isinstance(raw_jitter, bool) or not isinstance(raw_jitter, int) or raw_jitter < 0:
        raise ValueError("event_start_jitter_hours must be a non-negative integer")
    dr.update(
        {
            "source": "configured",
            "events_path": None,
            "event_start_hours": list(starts),
            "event_duration_hours": duration_h,
            "event_notice_hours": notice_h,
            "event_reduction_kw": float(requested_reduction_kw),
            "event_start_jitter_hours": raw_jitter,
            "event_duration_choices": None,
            "event_notice_choices": None,
            "event_reduction_fraction_range": None,
        }
    )
    document["dr"] = dr
    return document


def _certificate_program(
    config: str | Path | Mapping[str, Any],
    *,
    duration_h: int,
    notice_h: int,
    event_start_hours: Sequence[int] | None,
    event_start_jitter_hours: int | None,
) -> tuple[tuple[int, ...], int]:
    scenario = make_certificate_scenario(
        config,
        duration_h=duration_h,
        notice_h=notice_h,
        requested_reduction_kw=0.0,
        event_start_hours=event_start_hours,
        event_start_jitter_hours=event_start_jitter_hours,
    )
    dr = cast(dict[str, Any], scenario["dr"])
    return tuple(int(value) for value in dr["event_start_hours"]), int(
        dr["event_start_jitter_hours"]
    )


def _certificate_key(duration_h: int, notice_h: int, event_start_hours: Sequence[int]) -> str:
    sequence = "-".join(str(value) for value in event_start_hours)
    return f"duration_{duration_h}h_notice_{notice_h}h_events_{sequence}"


def _make_controller(name: ControllerName, model_path: str | Path | None) -> HourlyController:
    if name in _RL_NAMES:
        if model_path is None:
            raise ValueError(f"controller '{name}' requires a saved --model path")
        return SB3HourlyPolicyController(cast(SB3AlgorithmName, name), model_path)
    if model_path is not None:
        raise ValueError("--model is only accepted for DQN, PPO, or SAC")
    return make_hourly_controller(name)


def _environment_for(
    document: Mapping[str, Any], controller: ControllerName
) -> HourlyCommunityAIDemandResponseEnv:
    if controller == "dqn":
        return HourlyCommunityAIDemandResponseEnv(document, action_mode="discrete")
    return HourlyCommunityAIDemandResponseEnv(document)


def evaluate_flexibility_candidate(
    *,
    config: str | Path | Mapping[str, Any],
    controller: ControllerName,
    model_path: str | Path | None,
    duration_h: int,
    requested_reduction_kw: float,
    seeds: Sequence[int],
    criteria: FirmFlexibilityCriteria,
    notice_h: int = 0,
    event_start_hours: Sequence[int] | None = None,
    event_start_jitter_hours: int | None = None,
) -> tuple[pd.DataFrame, float]:
    """Run matched repeated-event episodes for one candidate capacity."""

    if not seeds:
        raise ValueError("candidate evaluation needs at least one seed")
    if len(set(seeds)) != len(seeds):
        raise ValueError("candidate evaluation seeds must be unique")
    scenario = make_certificate_scenario(
        config,
        duration_h=duration_h,
        notice_h=notice_h,
        requested_reduction_kw=requested_reduction_kw,
        event_start_hours=event_start_hours,
        event_start_jitter_hours=event_start_jitter_hours,
    )
    first_env = _environment_for(scenario, controller)
    dc_peak_kw = first_env.power_model.predict(
        first_env.power_model.flexible_capacity_gpu_h
    ).dc_power_kw
    evaluator = _make_controller(controller, model_path)
    rows: list[pd.DataFrame] = []
    for seed in seeds:
        env = _environment_for(scenario, controller)
        frame, _ = rollout_hourly_episode(env, evaluator, seed=seed)
        outcomes = derive_event_outcomes(
            frame,
            env.event_manifest,
            recovery_tolerance_gpu_h=(
                env.config.recovery_backlog_tolerance_fraction
                * env.power_model.flexible_capacity_gpu_h
            ),
        )
        table = event_outcomes_frame(outcomes, criteria)
        table.insert(0, "seed", seed)
        table.insert(1, "controller", controller)
        table.insert(2, "candidate_reduction_kw", requested_reduction_kw)
        table.insert(3, "notice_h", notice_h)
        table.insert(4, "event_count_in_episode", len(outcomes))
        rows.append(table)
    return pd.concat(rows, ignore_index=True), dc_peak_kw


def _quantile(values: pd.Series, quantile: float) -> float:
    cleaned = values.dropna()
    return float(cleaned.quantile(quantile)) if not cleaned.empty else math.nan


def summarize_candidate_outcomes(
    outcomes: pd.DataFrame,
    *,
    criteria: FirmFlexibilityCriteria,
    dc_peak_kw: float,
) -> dict[str, float | int | bool]:
    if "seed" not in outcomes:
        raise ValueError("candidate outcomes must identify their episode seed")
    event_counts = outcomes.groupby("seed", sort=False).size()
    if event_counts.empty or event_counts.nunique() != 1:
        raise ValueError("candidate outcomes must contain one complete event program per seed")
    episode_success = outcomes.groupby("seed", sort=False)["success"].all().astype(bool)
    count = int(episode_success.sum())
    episodes = int(len(episode_success))
    lower_ci = wilson_lower_bound(count, episodes, criteria.confidence_level)
    candidate = float(outcomes["candidate_reduction_kw"].iloc[0])
    return {
        "candidate_reduction_kw": candidate,
        "candidate_reduction_fraction_of_dc_peak": candidate / dc_peak_kw,
        "success_count": count,
        "episode_count": episodes,
        "event_count_per_episode": int(event_counts.iloc[0]),
        "success_rate": count / episodes,
        "success_rate_lower_ci": lower_ci,
        "certified": lower_ci + 1e-12 >= criteria.reliability_target,
        "mean_delivery_ratio": float(outcomes["delivery_ratio"].mean()),
        "minimum_interval_delivery_ratio": float(
            outcomes["minimum_interval_delivery_ratio"].min()
        ),
        "p95_deadline_miss_rate": _quantile(outcomes["deadline_miss_rate"], 0.95),
        "p95_rebound_ratio": _quantile(outcomes["rebound_ratio"], 0.95),
        "mean_window_peak_relief_kw": float(outcomes["window_peak_relief_kw"].mean()),
        "p05_window_peak_relief_fraction": _quantile(
            outcomes["window_peak_relief_fraction"], 0.05
        ),
        "p95_recovery_time_h": _quantile(outcomes["recovery_time_h"], 0.95),
    }


def certify_firm_flexibility(
    *,
    config: str | Path | Mapping[str, Any],
    controller: ControllerName,
    model_path: str | Path | None,
    duration_h: int,
    notice_h: int = 0,
    event_start_hours: Sequence[int] | None = None,
    event_start_jitter_hours: int | None = None,
    candidate_reduction_fractions: Sequence[float],
    seeds: Sequence[int],
    criteria: FirmFlexibilityCriteria,
    search_method: Literal["grid", "binary"] = "grid",
    binary_iterations: int = 8,
) -> tuple[FlexibilityCertificate, pd.DataFrame, pd.DataFrame]:
    """Certify the largest tested reduction with a one-sided Wilson guarantee."""

    if not candidate_reduction_fractions:
        raise ValueError("certification needs at least one candidate fraction")
    candidates = sorted({float(value) for value in candidate_reduction_fractions})
    valid_range = candidates[0] >= 0.0 and candidates[-1] <= 1.0
    if not all(math.isfinite(value) for value in candidates) or not valid_range:
        raise ValueError("candidate reduction fractions must be in [0, 1]")
    if search_method not in {"grid", "binary"}:
        raise ValueError("search_method must be 'grid' or 'binary'")
    if search_method == "binary" and len(candidates) < 2:
        raise ValueError(
            "binary certification needs at least lower and upper candidate-fraction bounds"
        )
    if binary_iterations <= 0:
        raise ValueError("binary_iterations must be positive")
    program_starts, program_jitter = _certificate_program(
        config,
        duration_h=duration_h,
        notice_h=notice_h,
        event_start_hours=event_start_hours,
        event_start_jitter_hours=event_start_jitter_hours,
    )
    reference_env = _environment_for(_read_mapping(config), controller)
    dc_peak_kw = reference_env.power_model.predict(
        reference_env.power_model.flexible_capacity_gpu_h
    ).dc_power_kw
    all_outcomes: list[pd.DataFrame] = []
    candidate_rows: list[dict[str, float | int | bool]] = []
    evaluated: dict[float, bool] = {}

    def evaluate_fraction(fraction: float) -> bool:
        if fraction in evaluated:
            return evaluated[fraction]
        outcomes, candidate_dc_peak_kw = evaluate_flexibility_candidate(
            config=config,
            controller=controller,
            model_path=model_path,
            duration_h=duration_h,
            notice_h=notice_h,
            requested_reduction_kw=fraction * dc_peak_kw,
            seeds=seeds,
            criteria=criteria,
            event_start_hours=program_starts,
            event_start_jitter_hours=program_jitter,
        )
        if not math.isclose(candidate_dc_peak_kw, dc_peak_kw, rel_tol=1e-12):
            raise RuntimeError("certificate scenario unexpectedly changed the data-center peak")
        all_outcomes.append(outcomes)
        row = summarize_candidate_outcomes(outcomes, criteria=criteria, dc_peak_kw=dc_peak_kw)
        candidate_rows.append(row)
        evaluated[fraction] = bool(row["certified"])
        return evaluated[fraction]

    if search_method == "grid":
        for fraction in candidates:
            evaluate_fraction(fraction)
    else:
        lower, upper = candidates[0], candidates[-1]
        lower_certified = evaluate_fraction(lower)
        evaluate_fraction(upper)
        if lower_certified and not evaluated[upper]:
            for _ in range(binary_iterations):
                midpoint = (lower + upper) / 2.0
                if evaluate_fraction(midpoint):
                    lower = midpoint
                else:
                    upper = midpoint
    candidate_table = pd.DataFrame.from_records(candidate_rows).sort_values(
        "candidate_reduction_kw", ignore_index=True
    )
    certified = candidate_table.loc[candidate_table["certified"]]
    selected = certified.iloc[-1] if not certified.empty else candidate_table.iloc[0]
    certificate = FlexibilityCertificate(
        controller=controller,
        duration_h=duration_h,
        notice_h=notice_h,
        event_start_hours=program_starts,
        event_start_jitter_hours=program_jitter,
        event_count_per_episode=int(selected["event_count_per_episode"]),
        certificate_scope=(
            "repeated_event_joint_episode"
            if len(program_starts) > 1
            else "isolated_event_joint_episode"
        ),
        reliability_target=criteria.reliability_target,
        confidence_level=criteria.confidence_level,
        certified_reduction_kw=(
            float(selected["candidate_reduction_kw"]) if not certified.empty else 0.0
        ),
        certified_reduction_fraction_of_dc_peak=(
            float(selected["candidate_reduction_fraction_of_dc_peak"])
            if not certified.empty
            else 0.0
        ),
        success_count=int(selected["success_count"]),
        episode_count=int(selected["episode_count"]),
        success_rate=float(selected["success_rate"]),
        success_rate_lower_ci=float(selected["success_rate_lower_ci"]),
        mean_delivery_ratio=float(selected["mean_delivery_ratio"]),
        minimum_interval_delivery_ratio=float(
            selected["minimum_interval_delivery_ratio"]
        ),
        p95_deadline_miss_rate=float(selected["p95_deadline_miss_rate"]),
        p95_rebound_ratio=float(selected["p95_rebound_ratio"]),
        mean_window_peak_relief_kw=float(selected["mean_window_peak_relief_kw"]),
        p05_window_peak_relief_fraction=float(selected["p05_window_peak_relief_fraction"]),
        p95_recovery_time_h=float(selected["p95_recovery_time_h"]),
        dc_peak_kw=dc_peak_kw,
    )
    return certificate, candidate_table, pd.concat(all_outcomes, ignore_index=True)


def save_flexibility_certificate(
    certificate: FlexibilityCertificate,
    candidates: pd.DataFrame,
    outcomes: pd.DataFrame,
    criteria: FirmFlexibilityCriteria,
    output_directory: str | Path,
) -> dict[str, str]:
    """Persist the certificate, tested candidates and raw event decisions."""

    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    certificate_path = output / "certificate.json"
    candidates_path = output / "candidates.parquet"
    outcomes_path = output / "outcomes.parquet"
    certificate_path.write_text(
        json.dumps(
            {**asdict(certificate), "criteria": criteria.as_dict()},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    candidates.to_parquet(candidates_path, index=False)
    outcomes.to_parquet(outcomes_path, index=False)
    return {
        "certificate": str(certificate_path),
        "candidates": str(candidates_path),
        "outcomes": str(outcomes_path),
    }


def _protocol_split(
    protocol_manifest: str | Path,
    *,
    split_name: Literal["validation", "test"],
) -> tuple[Path, tuple[int, ...], FirmFlexibilityCriteria, str]:
    """Read the declared config, seeds and frozen criteria for one protocol split."""

    document = _read_mapping(protocol_manifest)
    protocol_id = document.get("protocol_id")
    if not isinstance(protocol_id, str) or not protocol_id:
        raise ValueError("protocol manifest must define protocol_id")
    raw_splits = document.get("splits")
    if not isinstance(raw_splits, Mapping):
        raise ValueError("protocol manifest must define splits")
    split = raw_splits.get(split_name)
    if not isinstance(split, Mapping):
        raise ValueError(f"protocol manifest is missing the {split_name} split")
    expected_role = (
        "controller_and_hyperparameter_selection"
        if split_name == "validation"
        else "locked_ood_evaluation"
    )
    if split.get("role") != expected_role:
        raise ValueError(f"protocol {split_name} split does not have role {expected_role}")
    raw_range = split.get("episode_seed_range")
    if (
        not isinstance(raw_range, list)
        or len(raw_range) != 2
        or any(isinstance(value, bool) or not isinstance(value, int) for value in raw_range)
        or raw_range[0] < 0
        or raw_range[1] < raw_range[0]
    ):
        raise ValueError(f"protocol {split_name} episode_seed_range must be [first, last]")
    raw_configs = split.get("configs")
    if (
        not isinstance(raw_configs, list)
        or len(raw_configs) != 1
        or not isinstance(raw_configs[0], str)
    ):
        raise ValueError(f"protocol {split_name} split must declare exactly one environment config")
    raw_criteria = document.get("frozen_criteria")
    if not isinstance(raw_criteria, Mapping):
        raise ValueError("protocol manifest must define frozen_criteria")
    criteria = FirmFlexibilityCriteria(**dict(raw_criteria))
    return (
        Path(raw_configs[0]),
        tuple(range(raw_range[0], raw_range[1] + 1)),
        criteria,
        protocol_id,
    )


def _certificate_from_candidate_summary(
    *,
    controller: str,
    duration_h: int,
    notice_h: int,
    event_start_hours: tuple[int, ...],
    event_start_jitter_hours: int,
    criteria: FirmFlexibilityCriteria,
    summary: Mapping[str, float | int | bool],
    dc_peak_kw: float,
) -> FlexibilityCertificate:
    """Convert one fixed-capacity outcome summary to the public certificate schema."""

    return FlexibilityCertificate(
        controller=controller,
        duration_h=duration_h,
        notice_h=notice_h,
        event_start_hours=event_start_hours,
        event_start_jitter_hours=event_start_jitter_hours,
        event_count_per_episode=int(summary["event_count_per_episode"]),
        certificate_scope=(
            "repeated_event_joint_episode"
            if len(event_start_hours) > 1
            else "isolated_event_joint_episode"
        ),
        reliability_target=criteria.reliability_target,
        confidence_level=criteria.confidence_level,
        certified_reduction_kw=float(summary["candidate_reduction_kw"]),
        certified_reduction_fraction_of_dc_peak=float(
            summary["candidate_reduction_fraction_of_dc_peak"]
        ),
        success_count=int(summary["success_count"]),
        episode_count=int(summary["episode_count"]),
        success_rate=float(summary["success_rate"]),
        success_rate_lower_ci=float(summary["success_rate_lower_ci"]),
        mean_delivery_ratio=float(summary["mean_delivery_ratio"]),
        minimum_interval_delivery_ratio=float(summary["minimum_interval_delivery_ratio"]),
        p95_deadline_miss_rate=float(summary["p95_deadline_miss_rate"]),
        p95_rebound_ratio=float(summary["p95_rebound_ratio"]),
        mean_window_peak_relief_kw=float(summary["mean_window_peak_relief_kw"]),
        p05_window_peak_relief_fraction=float(summary["p05_window_peak_relief_fraction"]),
        p95_recovery_time_h=float(summary["p95_recovery_time_h"]),
        dc_peak_kw=dc_peak_kw,
    )


def select_firm_capacity_on_validation(
    *,
    protocol_manifest: str | Path,
    controller: ControllerName,
    model_path: str | Path | None,
    durations_h: Sequence[int],
    notices_h: Sequence[int] | None = None,
    candidate_reduction_fractions: Sequence[float],
    output_directory: str | Path,
    search_method: Literal["grid", "binary"] = "binary",
    binary_iterations: int = 8,
) -> dict[str, str | int]:
    """Select capacities only on the protocol's validation split and freeze them."""

    if not durations_h or any(duration <= 0 for duration in durations_h):
        raise ValueError("validation selection needs positive event durations")
    if len(set(durations_h)) != len(durations_h):
        raise ValueError("validation selection durations must be unique")
    config, seeds, criteria, protocol_id = _protocol_split(
        protocol_manifest, split_name="validation"
    )
    config_document = _read_mapping(config)
    raw_dr = config_document.get("dr")
    if not isinstance(raw_dr, Mapping):
        raise ValueError("validation config requires a dr mapping")
    raw_notices = (
        raw_dr.get("event_notice_choices") or (raw_dr.get("event_notice_hours", 0),)
        if notices_h is None
        else notices_h
    )
    if (
        not isinstance(raw_notices, Sequence)
        or isinstance(raw_notices, str | bytes)
        or not raw_notices
        or any(
            isinstance(notice, bool) or not isinstance(notice, int) or notice < 0
            for notice in raw_notices
        )
    ):
        raise ValueError("validation selection notices must be non-negative integers")
    notices = tuple(sorted(set(int(notice) for notice in raw_notices)))
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    selected: list[dict[str, object]] = []
    saved: dict[str, dict[str, str]] = {}
    for duration_h in sorted(durations_h):
        for notice_h in notices:
            certificate, candidates, outcomes = certify_firm_flexibility(
                config=config,
                controller=controller,
                model_path=model_path,
                duration_h=duration_h,
                notice_h=notice_h,
                candidate_reduction_fractions=candidate_reduction_fractions,
                seeds=seeds,
                criteria=criteria,
                search_method=search_method,
                binary_iterations=binary_iterations,
            )
            key = _certificate_key(
                duration_h,
                notice_h,
                certificate.event_start_hours,
            )
            saved[key] = save_flexibility_certificate(
                certificate, candidates, outcomes, criteria, output / key
            )
            selected.append(asdict(certificate))
    selection_path = output / "selection.json"
    selection_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "protocol_id": protocol_id,
                "protocol_manifest": str(protocol_manifest),
                "selection_split": "validation",
                "controller": controller,
                "model_path": str(model_path) if model_path is not None else None,
                "criteria": criteria.as_dict(),
                "validation_seed_count": len(seeds),
                "search_method": search_method,
                "candidate_reduction_fractions": list(candidate_reduction_fractions),
                "notices_h": list(notices),
                "selected_capacities": selected,
                "artifacts": saved,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"selection": str(selection_path), "certificate_key_count": len(selected)}


def evaluate_selected_capacity_on_locked_test(
    *,
    selection_path: str | Path,
    output_directory: str | Path,
    expected_protocol_manifest: str | Path | None = None,
) -> dict[str, str | int]:
    """Evaluate frozen validation selections once on the declared locked test split.

    This routine contains no candidate search. Calling it is intentionally an
    explicit user action because its episode seeds belong to the locked OOD set.
    """

    selection_raw = json.loads(Path(selection_path).read_text(encoding="utf-8"))
    if not isinstance(selection_raw, Mapping):
        raise ValueError("selection file must be a mapping")
    if (
        selection_raw.get("schema_version") != 2
        or selection_raw.get("selection_split") != "validation"
    ):
        raise ValueError("selection file is not a frozen validation selection")
    manifest = selection_raw.get("protocol_manifest")
    controller = selection_raw.get("controller")
    raw_selected = selection_raw.get("selected_capacities")
    if (
        not isinstance(manifest, str)
        or not isinstance(controller, str)
        or not isinstance(raw_selected, list)
    ):
        raise ValueError("selection file is missing protocol, controller, or selected capacities")
    if (
        expected_protocol_manifest is not None
        and Path(manifest).resolve() != Path(expected_protocol_manifest).resolve()
    ):
        raise ValueError(
            "selection protocol manifest does not match the requested locked-test protocol"
        )
    if controller not in {
        *_RL_NAMES,
        "no_control",
        "threshold",
        "edf_valley",
        "mpc",
        "robust_mpc",
    }:
        raise ValueError("selection file has an unsupported controller")
    config, seeds, criteria, protocol_id = _protocol_split(manifest, split_name="test")
    if selection_raw.get("protocol_id") != protocol_id:
        raise ValueError("selection protocol ID does not match its locked-test protocol")
    model_raw = selection_raw.get("model_path")
    model_path = Path(model_raw) if isinstance(model_raw, str) else None
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    certificates: list[dict[str, object]] = []
    saved: dict[str, dict[str, str]] = {}
    for entry in raw_selected:
        if not isinstance(entry, Mapping):
            raise ValueError("selection contains a malformed capacity entry")
        duration_h = entry.get("duration_h")
        notice_h = entry.get("notice_h")
        event_start_hours = entry.get("event_start_hours")
        reduction_kw = entry.get("certified_reduction_kw")
        if (
            isinstance(duration_h, bool)
            or not isinstance(duration_h, int)
            or duration_h <= 0
            or isinstance(notice_h, bool)
            or not isinstance(notice_h, int)
            or notice_h < 0
            or not isinstance(event_start_hours, list)
            or not event_start_hours
            or any(
                isinstance(hour, bool) or not isinstance(hour, int) or hour < 0
                for hour in event_start_hours
            )
            or isinstance(reduction_kw, bool)
            or not isinstance(reduction_kw, int | float)
        ):
            raise ValueError("selection contains invalid duration or capacity")
        program_starts, test_jitter = _certificate_program(
            config,
            duration_h=duration_h,
            notice_h=notice_h,
            event_start_hours=event_start_hours,
            event_start_jitter_hours=None,
        )
        outcomes, dc_peak_kw = evaluate_flexibility_candidate(
            config=config,
            controller=cast(ControllerName, controller),
            model_path=model_path,
            duration_h=duration_h,
            notice_h=notice_h,
            requested_reduction_kw=float(reduction_kw),
            seeds=seeds,
            criteria=criteria,
            event_start_hours=program_starts,
            event_start_jitter_hours=test_jitter,
        )
        summary = summarize_candidate_outcomes(outcomes, criteria=criteria, dc_peak_kw=dc_peak_kw)
        certificate = _certificate_from_candidate_summary(
            controller=controller,
            duration_h=duration_h,
            notice_h=notice_h,
            event_start_hours=program_starts,
            event_start_jitter_hours=test_jitter,
            criteria=criteria,
            summary=summary,
            dc_peak_kw=dc_peak_kw,
        )
        key = _certificate_key(duration_h, notice_h, program_starts)
        candidate_table = pd.DataFrame.from_records([summary])
        saved[key] = save_flexibility_certificate(
            certificate, candidate_table, outcomes, criteria, output / key
        )
        certificates.append(asdict(certificate))
    summary_path = output / "locked_certificates.parquet"
    pd.DataFrame.from_records(certificates).to_parquet(summary_path, index=False)
    manifest_path = output / "locked_certificate.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "protocol_id": protocol_id,
                "selection": str(selection_path),
                "evaluation_split": "locked_test",
                "test_seed_count": len(seeds),
                "criteria": criteria.as_dict(),
                "certificates": saved,
                "summary": str(summary_path),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "summary": str(summary_path),
        "manifest": str(manifest_path),
        "certificate_key_count": len(certificates),
    }
