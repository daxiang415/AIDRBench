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

ControllerName = Literal["no_control", "threshold", "edf_valley", "mpc", "dqn", "ppo", "sac"]
_RL_NAMES = frozenset(("dqn", "ppo", "sac"))


@dataclass(frozen=True, slots=True)
class FlexibilityCertificate:
    """One duration-specific capacity result under a frozen success protocol."""

    controller: str
    duration_h: int
    reliability_target: float
    confidence_level: float
    certified_reduction_kw: float
    certified_reduction_fraction_of_dc_peak: float
    success_count: int
    episode_count: int
    success_rate: float
    success_rate_lower_ci: float
    mean_delivery_ratio: float
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
    event_start_hours: Sequence[int] = (17,),
) -> dict[str, Any]:
    """Make an isolated event scenario without mutating the source config."""

    if isinstance(duration_h, bool) or duration_h <= 0:
        raise ValueError("duration_h must be positive")
    if not math.isfinite(requested_reduction_kw) or requested_reduction_kw < 0.0:
        raise ValueError("requested_reduction_kw must be finite and non-negative")
    invalid_start = any(isinstance(hour, bool) or hour < 0 for hour in event_start_hours)
    if not event_start_hours or invalid_start:
        raise ValueError("event_start_hours must contain non-negative integer hours")
    document = _read_mapping(config)
    raw_dr = document.get("dr")
    if not isinstance(raw_dr, Mapping):
        raise ValueError("hourly certificate config requires a dr mapping")
    dr = dict(raw_dr)
    dr.update(
        {
            "source": "configured",
            "events_path": None,
            "event_start_hours": list(event_start_hours),
            "event_duration_hours": duration_h,
            "event_notice_hours": 0,
            "event_reduction_kw": float(requested_reduction_kw),
            "event_start_jitter_hours": 0,
            "event_duration_choices": None,
            "event_notice_choices": None,
            "event_reduction_fraction_range": None,
        }
    )
    document["dr"] = dr
    return document


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
    event_start_hours: Sequence[int] = (17,),
) -> tuple[pd.DataFrame, float]:
    """Run matched episodes for one candidate capacity and return event outcomes."""

    if not seeds:
        raise ValueError("candidate evaluation needs at least one seed")
    if len(set(seeds)) != len(seeds):
        raise ValueError("candidate evaluation seeds must be unique")
    scenario = make_certificate_scenario(
        config,
        duration_h=duration_h,
        requested_reduction_kw=requested_reduction_kw,
        event_start_hours=event_start_hours,
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
    success = outcomes["success"].astype(bool)
    count = int(success.sum())
    episodes = int(len(success))
    lower_ci = wilson_lower_bound(count, episodes, criteria.confidence_level)
    candidate = float(outcomes["candidate_reduction_kw"].iloc[0])
    return {
        "candidate_reduction_kw": candidate,
        "candidate_reduction_fraction_of_dc_peak": candidate / dc_peak_kw,
        "success_count": count,
        "episode_count": episodes,
        "success_rate": count / episodes,
        "success_rate_lower_ci": lower_ci,
        "certified": lower_ci + 1e-12 >= criteria.reliability_target,
        "mean_delivery_ratio": float(outcomes["delivery_ratio"].mean()),
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
            requested_reduction_kw=fraction * dc_peak_kw,
            seeds=seeds,
            criteria=criteria,
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
