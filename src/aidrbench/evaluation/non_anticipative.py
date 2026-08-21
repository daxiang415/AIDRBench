"""Restricted scenario-based non-anticipative capacity on frozen scenarios.

The module exposes two deliberately restricted causal policy classes: one
common open-loop execution schedule, and a coarse observation-partition tree.
Both schedule workload-class execution explicitly and use the same calibrated
class power coefficients as the online environment. They are finite-ensemble
lower bounds for a predeclared policy class, not out-of-sample certificates.
"""

from __future__ import annotations

import copy
import json
import math
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from aidrbench.controllers.hourly_oracle import HIGHS_THREADS_PER_SOLVE
from aidrbench.data.frozen_scenarios import FrozenHourlyScenario, load_frozen_hourly_scenario
from aidrbench.data.splits import sha256_file
from aidrbench.envs.community_ai_dr_env import (
    HourlyCommunityAIDemandResponseEnv,
    HourlyPlanningSnapshot,
)
from aidrbench.envs.hourly_config import RewardSpecification
from aidrbench.evaluation.non_anticipative_sparse import (
    SparseNonAnticipativeInfeasible,
    solve_fixed_sparse_non_anticipative_feasibility,
)
from aidrbench.evaluation.provenance import optimization_provenance
from aidrbench.fluid_planning import build_fluid_workload_decision

_TOLERANCE = 1e-6


class _OptimizationInfeasible(RuntimeError):
    """Internal signal that a fixed PI upper-bound candidate is infeasible."""


@dataclass(frozen=True, slots=True)
class NonAnticipativeFirmSolution:
    """A chance-constrained non-anticipative result on frozen scenarios.

    ``non_anticipative_capacity_kw`` is neither the clairvoyant
    perfect-information value nor a controller-achieved certificate.  It is a
    deterministic-policy lower bound on the non-anticipative planning layer.
    """

    status: str
    duration_h: int
    notice_h: int
    event_id: int
    reliability_target: float
    scenario_count: int
    required_success_count: int
    selected_success_count: int
    empirical_success_fraction: float
    non_anticipative_policy_class: str
    information_node_count: int
    information_specification: str
    non_anticipative_capacity_kw: float
    non_anticipative_capacity_fraction_of_dynamic_range: float
    physical_dynamic_upper_bound_kw: float
    successful_scenario_hashes: tuple[str, ...]
    failed_scenario_hashes: tuple[str, ...]
    capacity_selection_method: str
    model_build_seconds: float
    objective_solve_seconds: float
    refinement_solve_seconds: float
    common_execution_gpu_h: tuple[float, ...]
    scenario_execution_gpu_h: tuple[tuple[float, ...], ...]
    common_execution_gpu_h_by_class: tuple[tuple[str, tuple[float, ...]], ...]
    scenario_execution_gpu_h_by_class: tuple[
        tuple[tuple[str, tuple[float, ...]], ...], ...
    ]
    information_nodes_by_hour: tuple[
        tuple[int, tuple[tuple[int, ...], ...]], ...
    ]

    def summary(self) -> dict[str, float | int | str | None]:
        return {
            "capacity_layer": "restricted_scenario_based_causal_bound",
            "statistical_interpretation": "restricted_scenario_ensemble_bound",
            "non_anticipative_policy_class": self.non_anticipative_policy_class,
            "information_node_count": self.information_node_count,
            "information_specification": self.information_specification,
            "non_anticipative_status": self.status,
            "duration_h": self.duration_h,
            "notice_h": self.notice_h,
            "event_id": self.event_id,
            "ensemble_success_fraction_target": self.reliability_target,
            "scenario_count": self.scenario_count,
            "required_success_count": self.required_success_count,
            "selected_success_count": self.selected_success_count,
            "empirical_success_fraction": self.empirical_success_fraction,
            "non_anticipative_capacity_kw": self.non_anticipative_capacity_kw,
            "non_anticipative_capacity_fraction_of_dynamic_range": (
                self.non_anticipative_capacity_fraction_of_dynamic_range
            ),
            "physical_dynamic_upper_bound_kw": self.physical_dynamic_upper_bound_kw,
            "successful_scenario_hashes": ",".join(self.successful_scenario_hashes),
            "failed_scenario_hashes": ",".join(self.failed_scenario_hashes),
            "capacity_selection_method": self.capacity_selection_method,
            "model_build_seconds": self.model_build_seconds,
            "objective_solve_seconds": self.objective_solve_seconds,
            "refinement_solve_seconds": self.refinement_solve_seconds,
        }


@dataclass(frozen=True, slots=True)
class ObservationPartitionSpecification:
    """Predeclared coarse information set for the scenario-tree lower bound.

    Each node sees current net community power, the same limited load forecast
    exposed to the online environment, current released flexible work, and an
    event only after its notice time.  Rare observations are merged so an
    exact continuous value cannot identify an entire future sample path.
    """

    forecast_horizon_hours: int = 6
    power_bin_width_pu: float = 0.10
    arrival_bin_width_fraction: float = 0.10
    minimum_shared_node_size: int = 2

    def __post_init__(self) -> None:
        if self.forecast_horizon_hours <= 0:
            raise ValueError("forecast_horizon_hours must be positive")
        if not math.isfinite(self.power_bin_width_pu) or self.power_bin_width_pu <= 0.0:
            raise ValueError("power_bin_width_pu must be positive")
        if (
            not math.isfinite(self.arrival_bin_width_fraction)
            or self.arrival_bin_width_fraction <= 0.0
        ):
            raise ValueError("arrival_bin_width_fraction must be positive")
        if self.minimum_shared_node_size < 2:
            raise ValueError("minimum_shared_node_size must be at least two")


def _validate_reliability(reliability_target: float) -> float:
    if isinstance(reliability_target, bool) or not isinstance(reliability_target, int | float):
        raise ValueError("reliability_target must be numeric")
    value = float(reliability_target)
    if not math.isfinite(value) or not 0.0 < value <= 1.0:
        raise ValueError("reliability_target must be in (0, 1]")
    return value


def _positive_durations(durations: Sequence[int]) -> tuple[int, ...]:
    if not durations:
        raise ValueError("non-anticipative frontier needs at least one duration")
    if any(isinstance(duration, bool) or not isinstance(duration, int) for duration in durations):
        raise ValueError("non-anticipative durations must be positive integers")
    if any(duration <= 0 for duration in durations):
        raise ValueError("non-anticipative durations must be positive integers")
    if len(set(durations)) != len(durations):
        raise ValueError("non-anticipative durations must be unique")
    return tuple(sorted(durations))


def _non_negative_notices(notices: Sequence[int]) -> tuple[int, ...]:
    if not notices:
        raise ValueError("non-anticipative frontier needs at least one notice time")
    if any(isinstance(notice, bool) or not isinstance(notice, int) for notice in notices):
        raise ValueError("non-anticipative notice times must be non-negative integers")
    if any(notice < 0 for notice in notices):
        raise ValueError("non-anticipative notice times must be non-negative integers")
    if len(set(notices)) != len(notices):
        raise ValueError("non-anticipative notice times must be unique")
    return tuple(sorted(notices))


def _environment_document(
    artifact: FrozenHourlyScenario,
    *,
    duration_h: int,
    event_id: int,
    notice_h: int | None = None,
) -> dict[str, Any]:
    document = copy.deepcopy(artifact.config_document)
    raw_scenario = document.get("scenario")
    scenario = dict(raw_scenario) if isinstance(raw_scenario, dict) else {}
    scenario.update(
        {
            "frozen_path": str(artifact.directory),
            "frozen_event_ids": [event_id],
        }
    )
    if notice_h is not None:
        if isinstance(notice_h, bool) or not isinstance(notice_h, int) or notice_h < 0:
            raise ValueError("notice_h must be a non-negative integer")
        scenario["frozen_event_notice_hours"] = notice_h
    document["scenario"] = scenario
    raw_dr = document.get("dr")
    if not isinstance(raw_dr, dict):
        raise ValueError("frozen scenario environment config is missing a dr mapping")
    dr = dict(raw_dr)
    dr.update(
        {
            "source": "configured",
            "events_path": None,
            "event_duration_hours": duration_h,
            "event_duration_choices": None,
            "event_notice_choices": None,
            "event_reduction_fraction_range": None,
            "event_start_jitter_hours": 0,
        }
    )
    document["dr"] = dr
    return document


def _snapshot_for(
    artifact: FrozenHourlyScenario,
    *,
    duration_h: int,
    event_id: int,
    notice_h: int | None = None,
) -> tuple[HourlyPlanningSnapshot, RewardSpecification]:
    available_event_ids = {int(event["event_id"]) for event in artifact.events}
    if event_id not in available_event_ids:
        raise ValueError(f"frozen scenario does not contain event ID {event_id}")
    env = HourlyCommunityAIDemandResponseEnv(
        _environment_document(
            artifact,
            duration_h=duration_h,
            event_id=event_id,
            notice_h=notice_h,
        )
    )
    env.reset(seed=artifact.episode_seed)
    return env.full_horizon_planning_snapshot(), env.config.reward


def _retarget_snapshot(
    snapshot: HourlyPlanningSnapshot,
    *,
    duration_h: int,
    notice_h: int,
) -> HourlyPlanningSnapshot:
    """Reuse static scenario physics while changing only the declared event design."""

    if duration_h <= 0 or notice_h < 0:
        raise ValueError("retargeted event duration/notice is invalid")
    events = []
    for event in snapshot.events:
        recovery_duration_h = event.recovery_stop_hour - event.stop_hour
        stop_hour = event.start_hour + duration_h
        recovery_stop_hour = stop_hour + recovery_duration_h
        if recovery_stop_hour > snapshot.total_hours:
            raise ValueError("retargeted event recovery exceeds the planning horizon")
        events.append(
            replace(
                event,
                stop_hour=stop_hour,
                recovery_stop_hour=recovery_stop_hour,
                notice_hours=float(notice_h),
            )
        )
    return replace(snapshot, events=tuple(events))


def _assert_common_physics(snapshots: Sequence[HourlyPlanningSnapshot]) -> None:
    if not snapshots:
        raise ValueError("non-anticipative optimization needs at least one scenario")
    reference = snapshots[0]
    reference_values = (
        reference.total_hours,
        reference.capacity_gpu_h,
        reference.fixed_dc_power_kw,
        reference.pcc_capacity_kw,
    )
    reference_class_power = dict(reference.dynamic_kw_per_gpu_h_by_class)
    for snapshot in snapshots[1:]:
        values = (
            snapshot.total_hours,
            snapshot.capacity_gpu_h,
            snapshot.fixed_dc_power_kw,
            snapshot.pcc_capacity_kw,
        )
        if values[0] != reference_values[0] or any(
            not math.isclose(value, expected, rel_tol=0.0, abs_tol=1e-9)
            for value, expected in zip(values[1:], reference_values[1:], strict=True)
        ):
            raise ValueError("frozen scenarios must share one hourly physical configuration")
        candidate_class_power = dict(snapshot.dynamic_kw_per_gpu_h_by_class)
        if set(candidate_class_power) != set(reference_class_power) or any(
            not math.isclose(
                candidate_class_power[job_class],
                coefficient,
                rel_tol=0.0,
                abs_tol=1e-9,
            )
            for job_class, coefficient in reference_class_power.items()
        ):
            raise ValueError("frozen scenarios must share class-specific power coefficients")


def _solve(problem: Any) -> None:
    try:
        import highspy

        highspy.Highs.resetGlobalScheduler(True)
        problem.solve(solver="HIGHS", threads=HIGHS_THREADS_PER_SOLVE)
    except ImportError as exc:
        raise RuntimeError(
            "non-anticipative optimization requires the project 'control' dependencies"
        ) from exc
    if problem.status in {"infeasible", "infeasible_inaccurate"}:
        raise _OptimizationInfeasible(
            f"non-anticipative optimization did not solve: {problem.status}"
        )
    if problem.status not in {"optimal", "optimal_inaccurate"}:
        raise RuntimeError(f"non-anticipative optimization did not solve: {problem.status}")


def _open_loop_information_nodes(
    *, scenario_count: int, horizon: int
) -> dict[int, tuple[tuple[int, ...], ...]]:
    """One node per hour: every successful scenario takes the same action."""

    shared = tuple(range(scenario_count))
    return {hour: (shared,) for hour in range(horizon)}


def _validate_information_nodes(
    information_nodes: dict[int, tuple[tuple[int, ...], ...]],
    *,
    scenario_count: int,
    horizon: int,
) -> None:
    """Require each hourly partition to cover every scenario exactly once."""

    if set(information_nodes) != set(range(horizon)):
        raise ValueError("information nodes must define one partition for every hour")
    expected = tuple(range(scenario_count))
    for hour, nodes in information_nodes.items():
        if not nodes:
            raise ValueError(f"information nodes are empty at hour {hour}")
        observed = tuple(sorted(index for node in nodes for index in node))
        if observed != expected or any(not node for node in nodes):
            raise ValueError(f"information nodes are not a partition at hour {hour}")


def _observation_event_signal(snapshot: HourlyPlanningSnapshot, hour: int) -> tuple[object, ...]:
    """Return only DR information revealed by this hour's notice process."""

    known_events = [
        event
        for event in snapshot.events
        if hour >= max(0, event.start_hour - math.ceil(event.notice_hours))
    ]
    if not known_events:
        return ("no_event_notice",)
    return tuple(
        (
            event.source_event_id,
            event.start_hour,
            event.stop_hour,
            event.notice_hours,
        )
        for event in known_events
    )


def _binned(value: float, width: float) -> int:
    return int(math.floor(value / width))


def _validate_observation_specification_against_artifacts(
    artifacts: Sequence[FrozenHourlyScenario],
    specification: ObservationPartitionSpecification,
) -> None:
    declared_forecast_horizons: set[int] = set()
    for artifact in artifacts:
        raw_env = artifact.config_document.get("env")
        if not isinstance(raw_env, Mapping):
            raise ValueError("frozen scenario config is missing an env mapping")
        raw_horizon = raw_env.get("forecast_horizon_hours")
        if isinstance(raw_horizon, bool) or not isinstance(raw_horizon, int):
            raise ValueError("frozen scenario forecast_horizon_hours must be an integer")
        declared_forecast_horizons.add(raw_horizon)
    if len(declared_forecast_horizons) != 1:
        raise ValueError("frozen scenarios must share one forecast horizon")
    available_forecast_horizon = declared_forecast_horizons.pop()
    if specification.forecast_horizon_hours > available_forecast_horizon:
        raise ValueError(
            "observation partition cannot use a longer forecast than the online environment"
        )


def _build_observation_information_nodes_from_snapshots(
    snapshots: Sequence[HourlyPlanningSnapshot],
    *,
    specification: ObservationPartitionSpecification,
) -> dict[int, tuple[tuple[int, ...], ...]]:
    if len(snapshots) < 2:
        raise ValueError("observation-partition optimization needs at least two scenarios")
    _assert_common_physics(snapshots)
    horizon = snapshots[0].total_hours
    pcc_capacity_kw = snapshots[0].pcc_capacity_kw
    capacity_gpu_h = snapshots[0].capacity_gpu_h
    power_bin_width_kw = specification.power_bin_width_pu * pcc_capacity_kw
    nodes_by_hour: dict[int, tuple[tuple[int, ...], ...]] = {}
    for hour in range(horizon):
        keyed_scenarios: dict[tuple[object, ...], list[int]] = {}
        event_signals: dict[int, tuple[object, ...]] = {}
        for scenario_index, snapshot in enumerate(snapshots):
            community = np.asarray(snapshot.community_power_kw, dtype="float64")
            forecast = community[hour : hour + specification.forecast_horizon_hours + 1]
            if len(forecast) < specification.forecast_horizon_hours + 1:
                forecast = np.pad(
                    forecast,
                    (0, specification.forecast_horizon_hours + 1 - len(forecast)),
                    mode="edge",
                )
            event_signal = _observation_event_signal(snapshot, hour)
            event_signals[scenario_index] = event_signal
            forecast_bins = tuple(
                _binned(float(value), power_bin_width_kw) for value in forecast
            )
            arrival_bin = _binned(
                float(snapshot.released_gpu_h[hour]) / max(capacity_gpu_h, 1e-9),
                specification.arrival_bin_width_fraction,
            )
            key = (event_signal, forecast_bins, arrival_bin)
            keyed_scenarios.setdefault(key, []).append(scenario_index)

        nodes: list[tuple[int, ...]] = []
        signals = sorted(set(event_signals.values()), key=repr)
        for event_signal in signals:
            same_signal = [
                tuple(indices)
                for key, indices in keyed_scenarios.items()
                if key[0] == event_signal
            ]
            rare: list[int] = []
            for indices in same_signal:
                if len(indices) >= specification.minimum_shared_node_size:
                    nodes.append(indices)
                else:
                    rare.extend(indices)
            if rare:
                nodes.append(tuple(sorted(rare)))
        nodes_by_hour[hour] = tuple(sorted(nodes))
    _validate_information_nodes(
        nodes_by_hour,
        scenario_count=len(snapshots),
        horizon=horizon,
    )
    return nodes_by_hour


def build_observation_information_nodes(
    artifacts: Sequence[FrozenHourlyScenario],
    *,
    duration_h: int,
    event_id: int = 0,
    notice_h: int | None = None,
    specification: ObservationPartitionSpecification | None = None,
) -> dict[int, tuple[tuple[int, ...], ...]]:
    """Build a fixed causal information partition before optimization.

    The partition intentionally omits unbounded history and the endogenous
    backlog.  That restriction keeps it a conservative policy class while
    avoiding a nonlinear decision-dependent tree.  The same specification is
    used for every duration and is recorded with the result.
    """

    if len(artifacts) < 2:
        raise ValueError("observation-partition optimization needs at least two scenarios")
    spec = specification or ObservationPartitionSpecification()
    _validate_observation_specification_against_artifacts(artifacts, spec)
    snapshots = [
        _snapshot_for(
            artifact,
            duration_h=duration_h,
            event_id=event_id,
            notice_h=notice_h,
        )[0]
        for artifact in artifacts
    ]
    return _build_observation_information_nodes_from_snapshots(
        snapshots,
        specification=spec,
    )


def _solve_non_anticipative_capacity(
    artifacts: Sequence[FrozenHourlyScenario],
    *,
    duration_h: int,
    event_id: int = 0,
    notice_h: int | None = None,
    reliability_target: float = 1.0,
    information_nodes: dict[int, tuple[tuple[int, ...], ...]],
    policy_class: str,
    information_specification: str,
    fixed_capacity_kw: float | None = None,
    fixed_failed_scenario_hashes: frozenset[str] | None = None,
    prepared_snapshots_with_rewards: Sequence[
        tuple[HourlyPlanningSnapshot, RewardSpecification]
    ]
    | None = None,
) -> NonAnticipativeFirmSolution:
    """Maximize chance-constrained DR capacity under one common hourly schedule.

    A binary failure variable may relax a scenario's service and event
    constraints.  Successful scenarios are tied only within the supplied
    causal information nodes, which is the explicit non-anticipativity rule.
    """

    if isinstance(duration_h, bool) or not isinstance(duration_h, int) or duration_h <= 0:
        raise ValueError("duration_h must be a positive integer")
    if not artifacts:
        raise ValueError("non-anticipative optimization needs at least one frozen scenario")
    if len({artifact.scenario_hash for artifact in artifacts}) != len(artifacts):
        raise ValueError("non-anticipative scenarios must have unique hashes")
    reliability = _validate_reliability(reliability_target)
    snapshots_with_peaks = (
        list(prepared_snapshots_with_rewards)
        if prepared_snapshots_with_rewards is not None
        else [
            _snapshot_for(
                artifact,
                duration_h=duration_h,
                event_id=event_id,
                notice_h=notice_h,
            )
            for artifact in artifacts
        ]
    )
    if len(snapshots_with_peaks) != len(artifacts):
        raise ValueError("prepared snapshots do not match the scenario ensemble")
    snapshots = [item[0] for item in snapshots_with_peaks]
    rewards = [item[1] for item in snapshots_with_peaks]
    _assert_common_physics(snapshots)
    reward = rewards[0]
    if any(candidate != reward for candidate in rewards[1:]):
        raise ValueError("frozen scenarios must share one reward and service specification")
    reference = snapshots[0]
    scenario_count = len(snapshots)
    allowed_failures = math.floor((1.0 - reliability) * scenario_count + 1e-12)
    required_success_count = scenario_count - allowed_failures
    horizon = reference.total_hours
    capacity = reference.capacity_gpu_h
    dynamic_power_by_class = dict(reference.dynamic_kw_per_gpu_h_by_class)
    if not dynamic_power_by_class:
        raise ValueError("non-anticipative snapshots have no class power coefficients")
    dynamic_range_kw = max(dynamic_power_by_class.values()) * capacity
    _validate_information_nodes(
        information_nodes,
        scenario_count=scenario_count,
        horizon=horizon,
    )
    if (fixed_capacity_kw is None) != (fixed_failed_scenario_hashes is None):
        raise ValueError(
            "fixed_capacity_kw and fixed_failed_scenario_hashes must be supplied together"
        )
    if fixed_failed_scenario_hashes is not None:
        artifact_hashes = {artifact.scenario_hash for artifact in artifacts}
        unknown_hashes = fixed_failed_scenario_hashes - artifact_hashes
        if unknown_hashes:
            raise ValueError("fixed failed scenario hashes are not in the scenario ensemble")
        if len(fixed_failed_scenario_hashes) != allowed_failures:
            raise ValueError("fixed failed scenario count does not match the reliability target")
        if (
            isinstance(fixed_capacity_kw, bool)
            or not isinstance(fixed_capacity_kw, int | float)
            or not math.isfinite(float(fixed_capacity_kw))
            or float(fixed_capacity_kw) < 0.0
        ):
            raise ValueError("fixed_capacity_kw must be a finite non-negative number")
        failed_indices = frozenset(
            index
            for index, artifact in enumerate(artifacts)
            if artifact.scenario_hash in fixed_failed_scenario_hashes
        )
        print(
            "NA direct sparse feasibility starting: "
            f"scenarios={scenario_count}, H={duration_h}, "
            f"N={snapshots[0].events[0].notice_hours}",
            file=sys.stderr,
            flush=True,
        )
        try:
            sparse_result = solve_fixed_sparse_non_anticipative_feasibility(
                tuple(snapshots),
                reward=reward,
                information_nodes=information_nodes,
                fixed_capacity_kw=float(fixed_capacity_kw),
                failed_scenario_indices=failed_indices,
            )
        except SparseNonAnticipativeInfeasible as exc:
            raise _OptimizationInfeasible(str(exc)) from exc
        print(
            "NA direct sparse feasibility complete: "
            f"model_build={sparse_result.model_build_seconds:.1f}s, "
            f"solve={sparse_result.solve_seconds:.1f}s",
            file=sys.stderr,
            flush=True,
        )
        scenario_execution_values_by_class = tuple(
            tuple(
                (
                    job_class,
                    tuple(
                        float(value)
                        for value in sparse_result.execution_gpu_h_by_class[
                            scenario_index, class_index
                        ]
                    ),
                )
                for class_index, job_class in enumerate(reference.workload_classes)
            )
            for scenario_index in range(scenario_count)
        )
        scenario_execution_values = tuple(
            tuple(
                float(value)
                for value in sparse_result.execution_gpu_h_by_class[scenario_index].sum(
                    axis=0
                )
            )
            for scenario_index in range(scenario_count)
        )
        successful = tuple(
            artifact.scenario_hash
            for artifact in artifacts
            if artifact.scenario_hash not in fixed_failed_scenario_hashes
        )
        failed = tuple(
            artifact.scenario_hash
            for artifact in artifacts
            if artifact.scenario_hash in fixed_failed_scenario_hashes
        )
        success_indices = [
            index
            for index, artifact in enumerate(artifacts)
            if artifact.scenario_hash not in fixed_failed_scenario_hashes
        ]
        common_execution_values = (
            scenario_execution_values[success_indices[0]]
            if policy_class == "common_open_loop_schedule"
            else ()
        )
        common_execution_values_by_class = (
            scenario_execution_values_by_class[success_indices[0]]
            if policy_class == "common_open_loop_schedule"
            else ()
        )
        return NonAnticipativeFirmSolution(
            status=sparse_result.status,
            duration_h=duration_h,
            notice_h=int(snapshots[0].events[0].notice_hours),
            event_id=event_id,
            reliability_target=reliability,
            scenario_count=scenario_count,
            required_success_count=required_success_count,
            selected_success_count=len(successful),
            empirical_success_fraction=len(successful) / scenario_count,
            non_anticipative_policy_class=policy_class,
            information_node_count=sum(len(nodes) for nodes in information_nodes.values()),
            information_specification=information_specification,
            non_anticipative_capacity_kw=float(fixed_capacity_kw),
            non_anticipative_capacity_fraction_of_dynamic_range=(
                float(fixed_capacity_kw) / dynamic_range_kw
            ),
            physical_dynamic_upper_bound_kw=dynamic_range_kw,
            successful_scenario_hashes=successful,
            failed_scenario_hashes=failed,
            capacity_selection_method=(
                "matched_pi_upper_bound_direct_sparse_feasibility_"
                f"{sparse_result.rebound_reference_mode}"
            ),
            model_build_seconds=sparse_result.model_build_seconds,
            objective_solve_seconds=sparse_result.solve_seconds,
            refinement_solve_seconds=0.0,
            common_execution_gpu_h=common_execution_values,
            scenario_execution_gpu_h=scenario_execution_values,
            common_execution_gpu_h_by_class=common_execution_values_by_class,
            scenario_execution_gpu_h_by_class=scenario_execution_values_by_class,
            information_nodes_by_hour=tuple(sorted(information_nodes.items())),
        )

    model_build_start = time.monotonic()
    try:
        import cvxpy as cp
    except ImportError as exc:
        raise RuntimeError(
            "non-anticipative optimization requires the project 'control' dependencies"
        ) from exc
    ratio_margin = 1e-6
    firm_reduction = cp.Variable(nonneg=True, name="non_anticipative_reduction_kw")
    failures = cp.Variable(scenario_count, boolean=True, name="scenario_failure")
    capacity_selection_method = "joint_mixed_integer_capacity_and_failure_selection"
    scenario_ones = np.ones(scenario_count, dtype="float64")
    constraints: list[Any] = [
        firm_reduction <= dynamic_range_kw,
        scenario_ones @ failures <= allowed_failures,
    ]
    scenario_execution: list[Any] = []
    scenario_execution_by_class: list[dict[str, Any]] = []
    for scenario_index, snapshot in enumerate(snapshots):
        workload = build_fluid_workload_decision(
            snapshot,
            cp=cp,
            name_suffix=f"na_s{scenario_index}",
        )
        execution_by_class = workload.execution_by_class
        execution = workload.execution_gpu_h
        scenario_execution.append(execution)
        scenario_execution_by_class.append(execution_by_class)
        failure = failures[scenario_index]
        community = np.asarray(snapshot.community_power_kw, dtype="float64")
        baseline_pcc = np.asarray(snapshot.baseline_pcc_power_kw, dtype="float64")
        pcc_power = community + snapshot.fixed_dc_power_kw + sum(
            dynamic_power_by_class[job_class] * execution_by_class[job_class]
            for job_class in reference.workload_classes
        )
        max_pcc_kw = float(
            (community + snapshot.fixed_dc_power_kw + dynamic_range_kw).max()
        )
        power_big_m = max(2.0 * max_pcc_kw, 2.0 * dynamic_range_kw, 1.0)
        work_big_m = max(snapshot.total_arrival_gpu_h, capacity, 1.0)
        terminal_backlog = workload.terminal_backlog_gpu_h
        constraints.extend(
            [
                *workload.constraints,
                pcc_power <= snapshot.pcc_capacity_kw + power_big_m * failure,
                workload.missed_gpu_h
                <= reward.max_deadline_miss_rate * snapshot.total_arrival_gpu_h
                + work_big_m * failure,
                terminal_backlog
                <= snapshot.baseline_terminal_backlog_gpu_h
                + reward.max_terminal_backlog_fraction * snapshot.total_arrival_gpu_h
                + work_big_m * failure,
            ]
        )

        for event in snapshot.events:
            event_indices = np.arange(event.start_hour, event.stop_hour, dtype="int64")
            window_indices = np.arange(
                event.start_hour, event.recovery_stop_hour, dtype="int64"
            )
            recovery_indices = np.arange(
                event.stop_hour, event.recovery_stop_hour, dtype="int64"
            )
            reduction = baseline_pcc[event_indices] - pcc_power[event_indices]
            delivered = cp.Variable(
                len(event_indices), nonneg=True, name=f"delivered_s{scenario_index}"
            )
            peak_selector = cp.Variable(
                len(event_indices), boolean=True, name=f"peak_selector_s{scenario_index}"
            )
            peak_delivery = cp.Variable(
                nonneg=True, name=f"peak_delivery_s{scenario_index}"
            )
            event_ones = np.ones(len(event_indices), dtype="float64")
            constraints.extend(
                [
                    delivered <= firm_reduction + power_big_m * failure,
                    delivered <= reduction + power_big_m * failure,
                    event_ones @ delivered
                    >= (reward.min_delivery_ratio + ratio_margin)
                    * len(event_indices)
                    * firm_reduction
                    - len(event_indices) * power_big_m * failure,
                    reduction
                    >= (reward.min_delivery_ratio + ratio_margin) * firm_reduction
                    - power_big_m * failure,
                    peak_delivery >= reduction - power_big_m * failure,
                    peak_delivery
                    <= reduction + power_big_m * (1.0 - peak_selector) + power_big_m * failure,
                    event_ones @ peak_selector == 1.0,
                ]
            )
            baseline_window_peak = float(baseline_pcc[window_indices].max())
            constraints.append(
                pcc_power[window_indices]
                <= baseline_window_peak
                - (reward.min_window_peak_relief_fraction + ratio_margin) * firm_reduction
                + power_big_m * failure
            )
            if len(recovery_indices):
                constraints.append(
                    pcc_power[recovery_indices] - baseline_pcc[recovery_indices]
                    <= (reward.max_rebound_ratio - ratio_margin) * peak_delivery
                    + power_big_m * failure
                )

    # At a scenario-tree node the controller has received the same permitted
    # information. Its action must therefore agree in *every* scenario. A
    # chance-constraint failure relaxes delivery/service obligations, never
    # the deployed policy's information constraint: otherwise the solver
    # would be allowed to recognize in advance that it is on a failed path.
    for hour, nodes in information_nodes.items():
        for node in nodes:
            anchor = node[0]
            for scenario_index in node[1:]:
                for job_class in reference.workload_classes:
                    constraints.append(
                        scenario_execution_by_class[anchor][job_class][hour]
                        == scenario_execution_by_class[scenario_index][job_class][hour]
                    )

    maximize = cp.Problem(cp.Maximize(firm_reduction), constraints)
    model_build_seconds = time.monotonic() - model_build_start
    print(
        "NA capacity solve starting: "
        f"scenarios={scenario_count}, H={duration_h}, N={snapshots[0].events[0].notice_hours}, "
        f"method={capacity_selection_method}, model_build={model_build_seconds:.1f}s",
        file=sys.stderr,
        flush=True,
    )
    objective_start = time.monotonic()
    _solve(maximize)
    objective_seconds = time.monotonic() - objective_start
    print(
        f"NA capacity solve complete ({objective_seconds:.1f}s)",
        file=sys.stderr,
        flush=True,
    )
    if firm_reduction.value is None:
        raise RuntimeError("non-anticipative optimization returned no capacity")
    optimum_kw = float(np.asarray(firm_reduction.value).item())
    solution_status = str(maximize.status)
    refinement_seconds = 0.0
    switching = [
        cp.abs(  # type: ignore[attr-defined]
            cp.hstack(  # type: ignore[attr-defined]
                [execution[0] - capacity, execution[1:] - execution[:-1]]
            )
        )
        for execution in scenario_execution
    ]
    constraints.extend(
        [
            firm_reduction >= optimum_kw - _TOLERANCE,
            firm_reduction <= optimum_kw + _TOLERANCE,
        ]
    )
    refinement = cp.Problem(
        cp.Minimize(
            1_000.0 * (scenario_ones @ failures)
            + 0.001
            * sum(
                np.ones(horizon, dtype="float64") @ scenario_switching
                for scenario_switching in switching
            )
            / max(capacity * scenario_count, 1.0)
        ),
        constraints,
    )
    print("NA secondary refinement starting", file=sys.stderr, flush=True)
    refinement_start = time.monotonic()
    _solve(refinement)
    refinement_seconds = time.monotonic() - refinement_start
    solution_status = str(refinement.status)
    print(
        f"NA secondary refinement complete ({refinement_seconds:.1f}s)",
        file=sys.stderr,
        flush=True,
    )
    if failures.value is None or any(execution.value is None for execution in scenario_execution):
        raise RuntimeError("non-anticipative optimization returned no schedule")
    failure_values = np.asarray(failures.value, dtype="float64").reshape(-1)
    scenario_execution_values = tuple(
        tuple(
            float(value)
            for value in np.clip(
                np.asarray(execution.value, dtype="float64").reshape(-1),
                0.0,
                capacity,
            )
        )
        for execution in scenario_execution
    )
    scenario_execution_values_by_class = tuple(
        tuple(
            (
                job_class,
                tuple(
                    float(value)
                    for value in np.clip(
                        np.asarray(execution_by_class[job_class].value, dtype="float64").reshape(
                            -1
                        ),
                        0.0,
                        capacity,
                    )
                ),
            )
            for job_class in reference.workload_classes
        )
        for execution_by_class in scenario_execution_by_class
    )
    successful = tuple(
        artifact.scenario_hash
        for artifact, failure in zip(artifacts, failure_values, strict=True)
        if failure < 0.5
    )
    failed = tuple(
        artifact.scenario_hash
        for artifact, failure in zip(artifacts, failure_values, strict=True)
        if failure >= 0.5
    )
    if len(successful) < required_success_count:
        raise RuntimeError("non-anticipative solution violates its chance constraint")
    success_indices = [index for index, failure in enumerate(failure_values) if failure < 0.5]
    common_execution_values = (
        scenario_execution_values[success_indices[0]]
        if policy_class == "common_open_loop_schedule"
        else ()
    )
    common_execution_values_by_class = (
        scenario_execution_values_by_class[success_indices[0]]
        if policy_class == "common_open_loop_schedule"
        else ()
    )
    return NonAnticipativeFirmSolution(
        status=solution_status,
        duration_h=duration_h,
        notice_h=int(snapshots[0].events[0].notice_hours),
        event_id=event_id,
        reliability_target=reliability,
        scenario_count=scenario_count,
        required_success_count=required_success_count,
        selected_success_count=len(successful),
        empirical_success_fraction=len(successful) / scenario_count,
        non_anticipative_policy_class=policy_class,
        information_node_count=sum(len(nodes) for nodes in information_nodes.values()),
        information_specification=information_specification,
        non_anticipative_capacity_kw=optimum_kw,
        non_anticipative_capacity_fraction_of_dynamic_range=optimum_kw / dynamic_range_kw,
        physical_dynamic_upper_bound_kw=dynamic_range_kw,
        successful_scenario_hashes=successful,
        failed_scenario_hashes=failed,
        capacity_selection_method=capacity_selection_method,
        model_build_seconds=model_build_seconds,
        objective_solve_seconds=objective_seconds,
        refinement_solve_seconds=refinement_seconds,
        common_execution_gpu_h=common_execution_values,
        scenario_execution_gpu_h=scenario_execution_values,
        common_execution_gpu_h_by_class=common_execution_values_by_class,
        scenario_execution_gpu_h_by_class=scenario_execution_values_by_class,
        information_nodes_by_hour=tuple(sorted(information_nodes.items())),
    )


def solve_frozen_non_anticipative_capacity(
    artifacts: Sequence[FrozenHourlyScenario],
    *,
    duration_h: int,
    event_id: int = 0,
    notice_h: int | None = None,
    reliability_target: float = 1.0,
    fixed_capacity_kw: float | None = None,
    fixed_failed_scenario_hashes: frozenset[str] | None = None,
) -> NonAnticipativeFirmSolution:
    """Solve the strict common-open-loop non-anticipative lower bound."""

    if not artifacts:
        raise ValueError("non-anticipative optimization needs at least one frozen scenario")
    horizon = int(artifacts[0].metadata["horizon"]["total_hours"])
    return _solve_non_anticipative_capacity(
        artifacts,
        duration_h=duration_h,
        event_id=event_id,
        notice_h=notice_h,
        reliability_target=reliability_target,
        information_nodes=_open_loop_information_nodes(
            scenario_count=len(artifacts),
            horizon=horizon,
        ),
        policy_class="common_open_loop_schedule",
        information_specification="all_successful_scenarios_share_each_hour",
        fixed_capacity_kw=fixed_capacity_kw,
        fixed_failed_scenario_hashes=fixed_failed_scenario_hashes,
    )


def solve_frozen_observation_partition_capacity(
    artifacts: Sequence[FrozenHourlyScenario],
    *,
    duration_h: int,
    event_id: int = 0,
    notice_h: int | None = None,
    reliability_target: float = 1.0,
    specification: ObservationPartitionSpecification | None = None,
    fixed_capacity_kw: float | None = None,
    fixed_failed_scenario_hashes: frozenset[str] | None = None,
) -> NonAnticipativeFirmSolution:
    """Solve a causal, coarse-observation scenario-tree lower bound.

    This is stronger than the common-open-loop policy class, but remains a
    lower bound because it intentionally omits endogenous backlog from the
    information key and merges rare observation cells.
    """

    spec = specification or ObservationPartitionSpecification()
    _validate_observation_specification_against_artifacts(artifacts, spec)
    prepared_snapshots_with_rewards = [
        _snapshot_for(
            artifact,
            duration_h=duration_h,
            event_id=event_id,
            notice_h=notice_h,
        )
        for artifact in artifacts
    ]
    nodes = _build_observation_information_nodes_from_snapshots(
        [item[0] for item in prepared_snapshots_with_rewards],
        specification=spec,
    )
    return _solve_non_anticipative_capacity(
        artifacts,
        duration_h=duration_h,
        event_id=event_id,
        notice_h=notice_h,
        reliability_target=reliability_target,
        information_nodes=nodes,
        policy_class="coarse_observation_partition_tree",
        information_specification=json.dumps(
            {
                "forecast_horizon_hours": spec.forecast_horizon_hours,
                "power_bin_width_pu": spec.power_bin_width_pu,
                "arrival_bin_width_fraction": spec.arrival_bin_width_fraction,
                "minimum_shared_node_size": spec.minimum_shared_node_size,
            },
            sort_keys=True,
        ),
        fixed_capacity_kw=fixed_capacity_kw,
        fixed_failed_scenario_hashes=fixed_failed_scenario_hashes,
        prepared_snapshots_with_rewards=prepared_snapshots_with_rewards,
    )


def validate_non_anticipative_frontier(frontier: pd.DataFrame) -> None:
    """Check chance-count and physical invariants before publishing a frontier."""

    required = {
        "duration_h",
        "notice_h",
        "ensemble_success_fraction_target",
        "non_anticipative_capacity_kw",
        "physical_dynamic_upper_bound_kw",
        "required_success_count",
        "selected_success_count",
    }
    missing = sorted(required - set(frontier.columns))
    if missing:
        raise ValueError(f"non-anticipative frontier is missing columns: {missing}")
    if frontier.empty:
        raise ValueError("non-anticipative frontier is empty")
    if (frontier["non_anticipative_capacity_kw"] < -_TOLERANCE).any():
        raise ValueError("non-anticipative frontier contains a negative capacity")
    if (
        frontier["non_anticipative_capacity_kw"]
        > frontier["physical_dynamic_upper_bound_kw"] + _TOLERANCE
    ).any():
        raise ValueError("non-anticipative frontier exceeds the physical dynamic bound")
    if (frontier["selected_success_count"] < frontier["required_success_count"]).any():
        raise ValueError("non-anticipative frontier violates its chance constraint")
    validate_non_anticipative_notice_monotonicity(frontier)


def validate_non_anticipative_notice_monotonicity(frontier: pd.DataFrame) -> None:
    """Enforce the weak value-of-information inequality dF/dN >= 0."""

    grouping = ["duration_h", "ensemble_success_fraction_target"]
    for optional in ("event_id", "non_anticipative_policy_class"):
        if optional in frontier.columns:
            grouping.append(optional)
    for _, group in frontier.groupby(grouping, sort=False, dropna=False):
        if group["notice_h"].nunique() < 2:
            continue
        ordered = group.sort_values("notice_h")
        capacities = ordered["non_anticipative_capacity_kw"].to_numpy(dtype="float64")
        if (capacities[1:] < capacities[:-1] - _TOLERANCE).any():
            raise ValueError("non-anticipative frontier violates notice weak monotonicity")


def _discover_artifacts(path: str | Path) -> list[FrozenHourlyScenario]:
    root = Path(path)
    if (root / "metadata.json").is_file():
        return [load_frozen_hourly_scenario(root)]
    if not root.is_dir():
        raise FileNotFoundError(f"frozen scenario path does not exist: {root}")
    artifacts = [
        load_frozen_hourly_scenario(child)
        for child in sorted(root.iterdir())
        if child.is_dir() and (child / "metadata.json").is_file()
    ]
    if not artifacts:
        raise ValueError(f"no frozen scenario artifacts found in: {root}")
    return artifacts


def _policy_rows(
    artifacts: Sequence[FrozenHourlyScenario],
    solutions: Sequence[NonAnticipativeFirmSolution],
    *,
    event_id: int,
) -> list[dict[str, float | int | str]]:
    """Materialize each solved class-aware action with its causal node ID.

    Keeping node membership beside its action makes a restricted-policy
    capacity result inspectable without writing a potentially enormous dense
    scenario-tree object into the JSON manifest.
    """

    if not solutions:
        raise ValueError("non-anticipative policy export needs at least one solution")
    horizon = len(solutions[0].scenario_execution_gpu_h[0])
    policy_rows: list[dict[str, float | int | str]] = []
    for solution in solutions:
        if solution.scenario_count != len(artifacts):
            raise RuntimeError("non-anticipative policy scenario count changed during export")
        information_nodes = dict(solution.information_nodes_by_hour)
        _validate_information_nodes(
            information_nodes,
            scenario_count=len(artifacts),
            horizon=horizon,
        )
        for hour, nodes in information_nodes.items():
            for node_id, node in enumerate(nodes):
                for job_class in dict(
                    solution.scenario_execution_gpu_h_by_class[node[0]]
                ):
                    node_execution_gpu_h = float(
                        np.mean(
                            [
                                dict(
                                    solution.scenario_execution_gpu_h_by_class[
                                        scenario_index
                                    ]
                                )[job_class][hour]
                                for scenario_index in node
                            ]
                        )
                    )
                    for scenario_index in node:
                        policy_rows.append(
                            {
                                "duration_h": solution.duration_h,
                                "notice_h": solution.notice_h,
                                "event_id": event_id,
                                "policy_class": solution.non_anticipative_policy_class,
                                "scenario_hash": artifacts[scenario_index].scenario_hash,
                                "hour": hour,
                                "information_node_id": node_id,
                                "job_class": job_class,
                                "execution_gpu_h": node_execution_gpu_h,
                            }
                        )
    return policy_rows


def _matched_pi_upper_bound_candidate(
    pi_frontier: pd.DataFrame,
    *,
    artifacts: Sequence[FrozenHourlyScenario],
    duration_h: int,
    event_id: int,
    reliability_target: float,
) -> tuple[float, frozenset[str]]:
    """Return the exact empirical PI cap and a deterministic failure set.

    Any non-anticipative policy is bounded above by the matched empirical PI
    order statistic.  Testing that value with the scenarios below the order
    statistic fixed as failures is a continuous feasibility problem for a
    one-hour event (and a much smaller mixed problem otherwise).  If feasible,
    equality with the PI upper bound is proven.  If not, callers must fall back
    to joint capacity/failure selection; the fixed set is never treated as
    generally optimal.
    """

    required_columns = {
        "scenario_hash",
        "event_id",
        "duration_h",
        "perfect_information_capacity_kw",
    }
    missing = sorted(required_columns - set(pi_frontier.columns))
    if missing:
        raise ValueError(f"matched PI frontier is missing columns: {missing}")
    expected_hashes = {artifact.scenario_hash for artifact in artifacts}
    selected = pi_frontier.loc[
        (pi_frontier["event_id"].astype(int) == event_id)
        & (pi_frontier["duration_h"].astype(int) == duration_h)
        & pi_frontier["scenario_hash"].astype(str).isin(expected_hashes),
        ["scenario_hash", "perfect_information_capacity_kw"],
    ].copy()
    if selected["scenario_hash"].duplicated().any():
        raise ValueError("matched PI frontier has duplicate scenario-duration rows")
    if set(selected["scenario_hash"].astype(str)) != expected_hashes:
        raise ValueError(
            f"matched PI frontier does not cover every NA scenario at duration {duration_h}"
        )
    capacities = selected["perfect_information_capacity_kw"].astype(float)
    if not np.isfinite(capacities).all() or (capacities < 0.0).any():
        raise ValueError("matched PI frontier contains invalid per-scenario capacity")
    reliability = _validate_reliability(reliability_target)
    allowed_failures = math.floor((1.0 - reliability) * len(artifacts) + 1e-12)
    selected["scenario_hash"] = selected["scenario_hash"].astype(str)
    selected["perfect_information_capacity_kw"] = capacities
    ordered = selected.sort_values(
        ["perfect_information_capacity_kw", "scenario_hash"],
        kind="mergesort",
    ).reset_index(drop=True)
    upper_bound_kw = float(
        np.asarray(
            ordered.loc[allowed_failures, "perfect_information_capacity_kw"],
            dtype="float64",
        ).item()
    )
    fixed_failures = frozenset(
        ordered.loc[: allowed_failures - 1, "scenario_hash"].astype(str)
        if allowed_failures
        else ()
    )
    return upper_bound_kw, fixed_failures


def attach_matched_pi_ensemble_comparison(
    frontier: pd.DataFrame,
    pi_frontier: pd.DataFrame,
    *,
    scenario_hashes: Sequence[str],
    event_id: int,
) -> pd.DataFrame:
    """Attach the same-ensemble empirical PI reference for an NA information gap.

    This comparison deliberately does not use the confidence-bounded PI
    tolerance statistic. Both sides select capacity on the same finite
    scenario ensemble and allow the same number of failures, so their
    difference isolates the declared information/policy restriction. It is a
    descriptive planning gap without an independent confidence bound.
    """

    validate_non_anticipative_frontier(frontier)
    expected_hashes = tuple(str(value) for value in scenario_hashes)
    if not expected_hashes or len(set(expected_hashes)) != len(expected_hashes):
        raise ValueError("matched PI comparison needs unique scenario hashes")
    required_pi_columns = {
        "scenario_hash",
        "event_id",
        "duration_h",
        "perfect_information_capacity_kw",
    }
    missing = sorted(required_pi_columns - set(pi_frontier.columns))
    if missing:
        raise ValueError(f"matched PI frontier is missing columns: {missing}")
    selected_pi = pi_frontier.loc[
        pi_frontier["scenario_hash"].astype(str).isin(expected_hashes)
        & (pi_frontier["event_id"].astype(int) == event_id)
    ].copy()
    rows: list[dict[str, float | int | str]] = []
    for _, na_row in frontier.iterrows():
        duration_h = int(na_row["duration_h"])
        duration_pi = selected_pi.loc[selected_pi["duration_h"].astype(int) == duration_h]
        if duration_pi["scenario_hash"].duplicated().any():
            raise ValueError("matched PI frontier has duplicate scenario-duration rows")
        observed_hashes = set(duration_pi["scenario_hash"].astype(str))
        if observed_hashes != set(expected_hashes):
            raise ValueError(
                f"matched PI frontier does not cover every NA scenario at duration {duration_h}"
            )
        scenario_count = int(na_row["scenario_count"])
        required_success_count = int(na_row["required_success_count"])
        if scenario_count != len(expected_hashes):
            raise ValueError("NA scenario count does not match the declared scenario hashes")
        allowed_failures = scenario_count - required_success_count
        capacities = duration_pi["perfect_information_capacity_kw"].astype(float).sort_values()
        matched_pi_capacity_kw = float(capacities.iloc[allowed_failures])
        na_capacity_kw = float(na_row["non_anticipative_capacity_kw"])
        information_gap_kw = matched_pi_capacity_kw - na_capacity_kw
        if information_gap_kw < -_TOLERANCE:
            raise ValueError(
                "non-anticipative capacity exceeds its matched perfect-information bound"
            )
        rows.append(
            {
                "matched_pi_ensemble_capacity_kw": matched_pi_capacity_kw,
                "matched_pi_allowed_failure_count": allowed_failures,
                "matched_pi_statistical_method": (
                    "same_ensemble_empirical_order_statistic_no_confidence_bound"
                ),
                "information_restriction_gap_kw": max(information_gap_kw, 0.0),
                "information_restriction_gap_fraction_of_matched_pi": (
                    max(information_gap_kw, 0.0) / matched_pi_capacity_kw
                    if matched_pi_capacity_kw > _TOLERANCE
                    else 0.0
                ),
            }
        )
    comparison = pd.DataFrame.from_records(rows)
    comparison.index = frontier.index
    return pd.concat([frontier.copy(), comparison], axis=1)


def compute_and_save_non_anticipative_frontier(
    scenario_path: str | Path,
    *,
    durations_h: Sequence[int],
    notice_hours: Sequence[int] = (0,),
    output_directory: str | Path,
    event_id: int = 0,
    reliability_target: float = 1.0,
    information_structure: Literal[
        "common_open_loop", "coarse_observation_partition_tree"
    ] = "coarse_observation_partition_tree",
    observation_specification: ObservationPartitionSpecification | None = None,
    matched_pi_frontier_path: str | Path | None = None,
) -> dict[str, str | int]:
    """Compute and persist one declared non-anticipative lower-bound frontier."""

    artifacts = _discover_artifacts(scenario_path)
    matched_pi_path: Path | None = None
    matched_pi_frontier: pd.DataFrame | None = None
    if matched_pi_frontier_path is not None:
        matched_pi_path = Path(matched_pi_frontier_path)
        if not matched_pi_path.is_file():
            raise FileNotFoundError(f"matched PI frontier does not exist: {matched_pi_path}")
        matched_pi_frontier = pd.read_parquet(matched_pi_path)
    durations = _positive_durations(durations_h)
    notices = _non_negative_notices(notice_hours)
    if information_structure not in {
        "common_open_loop",
        "coarse_observation_partition_tree",
    }:
        raise ValueError(
            "unsupported non-anticipative information structure: "
            f"{information_structure}"
        )
    observation_spec = observation_specification or ObservationPartitionSpecification()
    if information_structure == "coarse_observation_partition_tree":
        _validate_observation_specification_against_artifacts(artifacts, observation_spec)
    base_snapshots_with_rewards = [
        _snapshot_for(
            artifact,
            duration_h=durations[0],
            event_id=event_id,
            notice_h=notices[0],
        )
        for artifact in artifacts
    ]

    def matched_candidate(
        duration_h: int,
    ) -> tuple[float, frozenset[str]] | None:
        if matched_pi_frontier is None:
            return None
        return _matched_pi_upper_bound_candidate(
            matched_pi_frontier,
            artifacts=artifacts,
            duration_h=duration_h,
            event_id=event_id,
            reliability_target=reliability_target,
        )

    def prepared_point(
        duration_h: int,
        notice_h: int,
    ) -> list[tuple[HourlyPlanningSnapshot, RewardSpecification]]:
        return [
            (
                _retarget_snapshot(
                    snapshot,
                    duration_h=duration_h,
                    notice_h=notice_h,
                ),
                reward,
            )
            for snapshot, reward in base_snapshots_with_rewards
        ]

    def solve_prepared_point(
        duration_h: int,
        notice_h: int,
        *,
        fixed_capacity_kw: float | None = None,
        fixed_failed_scenario_hashes: frozenset[str] | None = None,
    ) -> NonAnticipativeFirmSolution:
        prepared = prepared_point(duration_h, notice_h)
        snapshots = [item[0] for item in prepared]
        if information_structure == "common_open_loop":
            nodes = _open_loop_information_nodes(
                scenario_count=len(artifacts),
                horizon=snapshots[0].total_hours,
            )
            policy_class = "common_open_loop_schedule"
            information_specification = "all_successful_scenarios_share_each_hour"
        else:
            nodes = _build_observation_information_nodes_from_snapshots(
                snapshots,
                specification=observation_spec,
            )
            policy_class = "coarse_observation_partition_tree"
            information_specification = json.dumps(
                {
                    "forecast_horizon_hours": observation_spec.forecast_horizon_hours,
                    "power_bin_width_pu": observation_spec.power_bin_width_pu,
                    "arrival_bin_width_fraction": (
                        observation_spec.arrival_bin_width_fraction
                    ),
                    "minimum_shared_node_size": observation_spec.minimum_shared_node_size,
                },
                sort_keys=True,
            )
        return _solve_non_anticipative_capacity(
            artifacts,
            duration_h=duration_h,
            event_id=event_id,
            notice_h=notice_h,
            reliability_target=reliability_target,
            information_nodes=nodes,
            policy_class=policy_class,
            information_specification=information_specification,
            fixed_capacity_kw=fixed_capacity_kw,
            fixed_failed_scenario_hashes=fixed_failed_scenario_hashes,
            prepared_snapshots_with_rewards=prepared,
        )

    def solve_point(duration_h: int, notice_h: int) -> NonAnticipativeFirmSolution:
        candidate = matched_candidate(duration_h)
        if candidate is not None:
            upper_bound_kw, fixed_failures = candidate
            try:
                return solve_prepared_point(
                    duration_h,
                    notice_h,
                    fixed_capacity_kw=upper_bound_kw,
                    fixed_failed_scenario_hashes=fixed_failures,
                )
            except _OptimizationInfeasible:
                print(
                    "NA matched PI upper bound infeasible; falling back to joint "
                    f"selection for H={duration_h}, N={notice_h}",
                    file=sys.stderr,
                    flush=True,
                )
        return solve_prepared_point(duration_h, notice_h)

    points = [(duration_h, notice_h) for notice_h in notices for duration_h in durations]
    started_at = time.monotonic()
    solutions: list[NonAnticipativeFirmSolution] = []
    for completed, (duration_h, notice_h) in enumerate(points, start=1):
        solutions.append(solve_point(duration_h, notice_h))
        print(
            f"NA frontier: {completed}/{len(points)} points complete "
            f"({100.0 * completed / len(points):.0f}%, "
            f"{time.monotonic() - started_at:.1f}s elapsed)",
            file=sys.stderr,
            flush=True,
        )
    frontier = pd.DataFrame.from_records([solution.summary() for solution in solutions])
    validate_non_anticipative_frontier(frontier)
    matched_pi_reference: dict[str, str] | None = None
    if matched_pi_frontier is not None and matched_pi_path is not None:
        frontier = attach_matched_pi_ensemble_comparison(
            frontier,
            matched_pi_frontier,
            scenario_hashes=[artifact.scenario_hash for artifact in artifacts],
            event_id=event_id,
        )
        matched_pi_reference = {
            "path": str(matched_pi_path),
            "sha256": sha256_file(matched_pi_path),
            "statistical_method": (
                "same_ensemble_empirical_order_statistic_no_confidence_bound"
            ),
        }
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    frontier_path = output / "non_anticipative_frontier.parquet"
    manifest_path = output / "non_anticipative_frontier.json"
    policies_path = output / "non_anticipative_policies.parquet"
    frontier.to_parquet(frontier_path, index=False)
    policy_rows = _policy_rows(
        artifacts,
        solutions,
        event_id=event_id,
    )
    pd.DataFrame.from_records(policy_rows).to_parquet(policies_path, index=False)
    manifest_path.write_text(
        json.dumps(
            {
                "capacity_layer": "restricted_scenario_based_causal_bound",
                "statistical_interpretation": (
                    "finite_scenario_ensemble_not_independent_certificate"
                ),
                "deployable_on_unseen_scenarios": False,
                "independent_statistical_unit": "frozen_episode",
                "capacity_and_failures_selected_on": "same_finite_scenario_ensemble",
                "confidence_bound": None,
                "multiplicity_interpretation": (
                    "descriptive_preregistered_planning_grid_no_hypothesis_tests"
                ),
                "policy_export_scope": "audit_of_optimized_ensemble_only",
                "solver": {
                    "name": "HIGHS",
                    "threads_per_solve": HIGHS_THREADS_PER_SOLVE,
                },
                "capacity_selection_methods": sorted(
                    {solution.capacity_selection_method for solution in solutions}
                ),
                "information_structure": information_structure,
                "observation_partition": (
                    None
                    if observation_specification is None
                    else {
                        "forecast_horizon_hours": observation_specification.forecast_horizon_hours,
                        "power_bin_width_pu": observation_specification.power_bin_width_pu,
                        "arrival_bin_width_fraction": (
                            observation_specification.arrival_bin_width_fraction
                        ),
                        "minimum_shared_node_size": (
                            observation_specification.minimum_shared_node_size
                        ),
                    }
                ),
                "event_id": event_id,
                "durations_h": list(durations),
                "notice_hours": list(notices),
                "ensemble_success_fraction_target": _validate_reliability(
                    reliability_target
                ),
                "scenario_count": len(artifacts),
                "scenario_hashes": [artifact.scenario_hash for artifact in artifacts],
                "frontier": str(frontier_path),
                "policies": str(policies_path),
                "policy_row_count": len(policy_rows),
                "matched_pi_reference": matched_pi_reference,
                "common_execution_gpu_h": {
                    f"N{solution.notice_h}_H{solution.duration_h}": list(
                        solution.common_execution_gpu_h
                    )
                    for solution in solutions
                },
                "common_execution_gpu_h_by_class": {
                    f"N{solution.notice_h}_H{solution.duration_h}": {
                        job_class: list(values)
                        for job_class, values in solution.common_execution_gpu_h_by_class
                    }
                    for solution in solutions
                },
                "provenance": optimization_provenance(artifacts),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "scenario_count": len(artifacts),
        "row_count": len(frontier),
        "frontier": str(frontier_path),
        "manifest": str(manifest_path),
        "policies": str(policies_path),
    }


def merge_non_anticipative_frontier_partitions(
    input_directories: Sequence[str | Path],
    *,
    output_directory: str | Path,
) -> dict[str, str | int]:
    """Merge independently solved duration/notice partitions with hash provenance."""

    if len(input_directories) < 2:
        raise ValueError("NA merge needs at least two input directories")
    roots = [Path(value) for value in input_directories]
    if len({root.resolve() for root in roots}) != len(roots):
        raise ValueError("NA merge input directories must be unique")
    manifests: list[dict[str, Any]] = []
    frontiers: list[pd.DataFrame] = []
    policies: list[pd.DataFrame] = []
    source_partitions: list[dict[str, str]] = []
    required_policy_columns = {
        "duration_h",
        "notice_h",
        "event_id",
        "policy_class",
        "scenario_hash",
        "hour",
        "information_node_id",
        "job_class",
        "execution_gpu_h",
    }
    for root in roots:
        manifest_path = root / "non_anticipative_frontier.json"
        frontier_path = root / "non_anticipative_frontier.parquet"
        policies_path = root / "non_anticipative_policies.parquet"
        for path in (manifest_path, frontier_path, policies_path):
            if not path.is_file():
                raise FileNotFoundError(f"NA merge input is incomplete: {path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError(f"NA merge manifest is not a mapping: {manifest_path}")
        frontier = pd.read_parquet(frontier_path)
        validate_non_anticipative_frontier(frontier)
        policy = pd.read_parquet(policies_path)
        missing_policy_columns = sorted(required_policy_columns - set(policy.columns))
        if missing_policy_columns:
            raise ValueError(
                f"NA merge policy export is missing columns: {missing_policy_columns}"
            )
        if int(manifest.get("policy_row_count", -1)) != len(policy):
            raise ValueError("NA merge policy row count does not match its manifest")
        manifests.append(manifest)
        frontiers.append(frontier)
        policies.append(policy)
        source_partitions.append(
            {
                "directory": str(root),
                "manifest_sha256": sha256_file(manifest_path),
                "frontier_sha256": sha256_file(frontier_path),
                "policies_sha256": sha256_file(policies_path),
            }
        )

    invariant_keys = (
        "capacity_layer",
        "statistical_interpretation",
        "deployable_on_unseen_scenarios",
        "independent_statistical_unit",
        "capacity_and_failures_selected_on",
        "confidence_bound",
        "multiplicity_interpretation",
        "policy_export_scope",
        "solver",
        "information_structure",
        "observation_partition",
        "event_id",
        "ensemble_success_fraction_target",
        "scenario_count",
        "scenario_hashes",
        "matched_pi_reference",
        "provenance",
    )
    reference = manifests[0]
    for manifest in manifests[1:]:
        for key in invariant_keys:
            if manifest.get(key) != reference.get(key):
                raise ValueError(f"NA merge manifests disagree on {key}")

    frontier = pd.concat(frontiers, ignore_index=True).sort_values(
        ["notice_h", "duration_h", "event_id"]
    )
    if frontier.duplicated(["notice_h", "duration_h", "event_id"]).any():
        raise ValueError("NA merge contains duplicate duration/notice/event points")
    validate_non_anticipative_frontier(frontier)
    policy = pd.concat(policies, ignore_index=True).sort_values(
        ["notice_h", "duration_h", "hour", "information_node_id", "scenario_hash", "job_class"]
    )
    policy_key = [
        "notice_h",
        "duration_h",
        "event_id",
        "scenario_hash",
        "hour",
        "job_class",
    ]
    if policy.duplicated(policy_key).any():
        raise ValueError("NA merge contains duplicate policy actions")

    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    frontier_path = output / "non_anticipative_frontier.parquet"
    manifest_path = output / "non_anticipative_frontier.json"
    policies_path = output / "non_anticipative_policies.parquet"
    if any(path.exists() for path in (frontier_path, manifest_path, policies_path)):
        raise FileExistsError("NA merge output already contains result artifacts")
    frontier.to_parquet(frontier_path, index=False)
    policy.to_parquet(policies_path, index=False)
    merged_common_execution: dict[str, Any] = {}
    merged_common_execution_by_class: dict[str, Any] = {}
    for manifest in manifests:
        for target, key in (
            (merged_common_execution, "common_execution_gpu_h"),
            (merged_common_execution_by_class, "common_execution_gpu_h_by_class"),
        ):
            raw_values = manifest.get(key, {})
            if not isinstance(raw_values, dict):
                raise ValueError(f"NA merge manifest field {key} is not a mapping")
            overlap = set(target) & set(raw_values)
            if overlap:
                raise ValueError(f"NA merge contains duplicate {key} entries")
            target.update(raw_values)
    merged_manifest = dict(reference)
    merged_manifest.update(
        {
            "durations_h": sorted(int(value) for value in frontier["duration_h"].unique()),
            "notice_hours": sorted(int(value) for value in frontier["notice_h"].unique()),
            "frontier": str(frontier_path),
            "policies": str(policies_path),
            "policy_row_count": len(policy),
            "capacity_selection_methods": sorted(
                str(value) for value in frontier["capacity_selection_method"].unique()
            ),
            "common_execution_gpu_h": merged_common_execution,
            "common_execution_gpu_h_by_class": merged_common_execution_by_class,
            "merged_from_partitions": source_partitions,
        }
    )
    manifest_path.write_text(
        json.dumps(merged_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "scenario_count": int(reference["scenario_count"]),
        "row_count": len(frontier),
        "frontier": str(frontier_path),
        "manifest": str(manifest_path),
        "policies": str(policies_path),
        "partition_count": len(roots),
    }
