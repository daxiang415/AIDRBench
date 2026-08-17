"""Chance-constrained non-anticipative capacity on frozen scenarios.

The module exposes two deliberately restricted causal policy classes: one
common open-loop execution schedule, and a coarse observation-partition tree.
Both schedule workload-class execution explicitly and use the same calibrated
class power coefficients as the online environment. They are lower bounds on a
richer controller policy class, rather than clairvoyant planning results.
"""

from __future__ import annotations

import copy
import json
import math
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from aidrbench.data.frozen_scenarios import FrozenHourlyScenario, load_frozen_hourly_scenario
from aidrbench.envs.community_ai_dr_env import (
    HourlyCommunityAIDemandResponseEnv,
    HourlyPlanningSnapshot,
)
from aidrbench.envs.hourly_config import RewardSpecification
from aidrbench.evaluation.firm_flexibility import (
    minimum_successes_for_wilson,
    wilson_lower_bound,
)
from aidrbench.evaluation.provenance import optimization_provenance

_TOLERANCE = 1e-6


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
    confidence_level: float | None
    statistical_rule: str
    scenario_count: int
    required_success_count: int
    selected_success_count: int
    success_rate_lower_ci: float | None
    non_anticipative_policy_class: str
    information_node_count: int
    information_specification: str
    non_anticipative_capacity_kw: float
    non_anticipative_capacity_fraction_of_dynamic_range: float
    physical_dynamic_upper_bound_kw: float
    successful_scenario_hashes: tuple[str, ...]
    failed_scenario_hashes: tuple[str, ...]
    objective_solve_seconds: float
    refinement_solve_seconds: float
    common_execution_gpu_h: tuple[float, ...]
    scenario_execution_gpu_h: tuple[tuple[float, ...], ...]

    def summary(self) -> dict[str, float | int | str | None]:
        return {
            "capacity_layer": "non_anticipative_lower_bound",
            "non_anticipative_policy_class": self.non_anticipative_policy_class,
            "information_node_count": self.information_node_count,
            "information_specification": self.information_specification,
            "non_anticipative_status": self.status,
            "duration_h": self.duration_h,
            "notice_h": self.notice_h,
            "event_id": self.event_id,
            "reliability_target": self.reliability_target,
            "confidence_level": self.confidence_level,
            "statistical_rule": self.statistical_rule,
            "scenario_count": self.scenario_count,
            "required_success_count": self.required_success_count,
            "selected_success_count": self.selected_success_count,
            "success_rate_lower_ci": self.success_rate_lower_ci,
            "non_anticipative_capacity_kw": self.non_anticipative_capacity_kw,
            "non_anticipative_capacity_fraction_of_dynamic_range": (
                self.non_anticipative_capacity_fraction_of_dynamic_range
            ),
            "physical_dynamic_upper_bound_kw": self.physical_dynamic_upper_bound_kw,
            "successful_scenario_hashes": ",".join(self.successful_scenario_hashes),
            "failed_scenario_hashes": ",".join(self.failed_scenario_hashes),
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
        problem.solve(solver="HIGHS")
    except ImportError as exc:
        raise RuntimeError(
            "non-anticipative optimization requires the project 'control' dependencies"
        ) from exc
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
    snapshots = [
        _snapshot_for(
            artifact,
            duration_h=duration_h,
            event_id=event_id,
            notice_h=notice_h,
        )[0]
        for artifact in artifacts
    ]
    _assert_common_physics(snapshots)
    horizon = snapshots[0].total_hours
    pcc_capacity_kw = snapshots[0].pcc_capacity_kw
    capacity_gpu_h = snapshots[0].capacity_gpu_h
    power_bin_width_kw = spec.power_bin_width_pu * pcc_capacity_kw
    nodes_by_hour: dict[int, tuple[tuple[int, ...], ...]] = {}
    for hour in range(horizon):
        keyed_scenarios: dict[tuple[object, ...], list[int]] = {}
        event_signals: dict[int, tuple[object, ...]] = {}
        for scenario_index, snapshot in enumerate(snapshots):
            community = np.asarray(snapshot.community_power_kw, dtype="float64")
            forecast = community[hour : hour + spec.forecast_horizon_hours + 1]
            if len(forecast) < spec.forecast_horizon_hours + 1:
                forecast = np.pad(
                    forecast,
                    (0, spec.forecast_horizon_hours + 1 - len(forecast)),
                    mode="edge",
                )
            event_signal = _observation_event_signal(snapshot, hour)
            event_signals[scenario_index] = event_signal
            forecast_bins = tuple(
                _binned(float(value), power_bin_width_kw) for value in forecast
            )
            arrival_bin = _binned(
                float(snapshot.released_gpu_h[hour]) / max(capacity_gpu_h, 1e-9),
                spec.arrival_bin_width_fraction,
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
                if len(indices) >= spec.minimum_shared_node_size:
                    nodes.append(indices)
                else:
                    rare.extend(indices)
            if rare:
                nodes.append(tuple(sorted(rare)))
        nodes_by_hour[hour] = tuple(sorted(nodes))
    _validate_information_nodes(
        nodes_by_hour,
        scenario_count=len(artifacts),
        horizon=horizon,
    )
    return nodes_by_hour


def _solve_non_anticipative_capacity(
    artifacts: Sequence[FrozenHourlyScenario],
    *,
    duration_h: int,
    event_id: int = 0,
    notice_h: int | None = None,
    reliability_target: float = 1.0,
    confidence_level: float | None = None,
    information_nodes: dict[int, tuple[tuple[int, ...], ...]],
    policy_class: str,
    information_specification: str,
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
    snapshots_with_peaks = [
        _snapshot_for(
            artifact,
            duration_h=duration_h,
            event_id=event_id,
            notice_h=notice_h,
        )
        for artifact in artifacts
    ]
    snapshots = [item[0] for item in snapshots_with_peaks]
    rewards = [item[1] for item in snapshots_with_peaks]
    _assert_common_physics(snapshots)
    reward = rewards[0]
    if any(candidate != reward for candidate in rewards[1:]):
        raise ValueError("frozen scenarios must share one reward and service specification")
    reference = snapshots[0]
    try:
        import cvxpy as cp
        from scipy import sparse  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "non-anticipative optimization requires the project 'control' dependencies"
        ) from exc

    scenario_count = len(snapshots)
    if confidence_level is None:
        allowed_failures = math.floor((1.0 - reliability) * scenario_count + 1e-12)
        required_success_count = scenario_count - allowed_failures
        statistical_rule = "empirical_success_fraction"
    else:
        if not 0.0 < confidence_level < 1.0:
            raise ValueError("confidence_level must be in (0, 1)")
        if reliability >= 1.0:
            raise ValueError("a finite sample cannot statistically certify reliability 1.0")
        required_successes = minimum_successes_for_wilson(
            scenario_count,
            reliability,
            confidence_level,
        )
        if required_successes is None:
            raise ValueError(
                f"{scenario_count} scenarios are insufficient to certify reliability "
                f"{reliability:g} at confidence {confidence_level:g} even with all successes"
            )
        required_success_count = required_successes
        allowed_failures = scenario_count - required_success_count
        statistical_rule = "one_sided_wilson_lower_bound"
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
    ratio_margin = 1e-6
    firm_reduction = cp.Variable(nonneg=True, name="non_anticipative_reduction_kw")
    failures = cp.Variable(scenario_count, boolean=True, name="scenario_failure")
    constraints: list[Any] = [
        firm_reduction <= dynamic_range_kw,
        cp.sum(failures) <= allowed_failures,  # type: ignore[attr-defined]
    ]
    scenario_execution: list[Any] = []
    scenario_execution_by_class: list[dict[str, Any]] = []
    for scenario_index, snapshot in enumerate(snapshots):
        groups = snapshot.work_groups
        if not groups:
            raise ValueError("non-anticipative scenario has no flexible work groups")
        edge_groups: list[int] = []
        edge_hours: list[int] = []
        edge_classes: list[str] = []
        for group_index, (release, deadline, job_class, _) in enumerate(groups):
            for hour in range(release, min(deadline, horizon - 1) + 1):
                edge_groups.append(group_index)
                edge_hours.append(hour)
                edge_classes.append(job_class)
        if not edge_groups:
            raise ValueError("non-anticipative scenario has no schedulable work edges")
        edge_count = len(edge_groups)
        edge_ids = np.arange(edge_count, dtype="int64")
        group_incidence = sparse.coo_matrix(
            (np.ones(edge_count), (edge_groups, edge_ids)),
            shape=(len(groups), edge_count),
        ).tocsr()
        time_incidence = sparse.coo_matrix(
            (np.ones(edge_count), (edge_hours, edge_ids)),
            shape=(horizon, edge_count),
        ).tocsr()
        served = cp.Variable(edge_count, nonneg=True, name=f"served_gpu_h_s{scenario_index}")
        missed = cp.Variable(len(groups), nonneg=True, name=f"missed_gpu_h_s{scenario_index}")
        remaining = cp.Variable(
            len(groups), nonneg=True, name=f"terminal_backlog_gpu_h_s{scenario_index}"
        )
        execution_by_class = {
            job_class: time_incidence
            @ cp.multiply(  # type: ignore[attr-defined]
                np.asarray(
                    [value == job_class for value in edge_classes],
                    dtype="float64",
                ),
                served,
            )
            for job_class in reference.workload_classes
        }
        execution = sum(execution_by_class.values())
        scenario_execution.append(execution)
        scenario_execution_by_class.append(execution_by_class)
        failure = failures[scenario_index]
        group_work = np.asarray([group[3] for group in groups], dtype="float64")
        due_within_episode = np.asarray(
            [group[1] < horizon for group in groups], dtype=bool
        )
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
        terminal_backlog = cp.sum(remaining)  # type: ignore[attr-defined]
        constraints.extend(
            [
                execution <= capacity,
                group_incidence @ served + missed + remaining == group_work,
                pcc_power <= snapshot.pcc_capacity_kw + power_big_m * failure,
                cp.sum(missed)  # type: ignore[attr-defined]
                <= reward.max_deadline_miss_rate * snapshot.total_arrival_gpu_h
                + work_big_m * failure,
                terminal_backlog
                <= snapshot.baseline_terminal_backlog_gpu_h
                + reward.max_terminal_backlog_fraction * snapshot.total_arrival_gpu_h
                + work_big_m * failure,
            ]
        )
        if bool((~due_within_episode).any()):
            constraints.append(missed[~due_within_episode] == 0.0)
        if bool(due_within_episode.any()):
            constraints.append(remaining[due_within_episode] == 0.0)

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
            constraints.extend(
                [
                    delivered <= firm_reduction + power_big_m * failure,
                    delivered <= reduction + power_big_m * failure,
                    cp.sum(delivered)  # type: ignore[attr-defined]
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
                    cp.sum(peak_selector) == 1.0,  # type: ignore[attr-defined]
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
    objective_start = time.monotonic()
    _solve(maximize)
    objective_seconds = time.monotonic() - objective_start
    if firm_reduction.value is None:
        raise RuntimeError("non-anticipative optimization returned no capacity")
    optimum_kw = float(np.asarray(firm_reduction.value).item())
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
            1_000.0 * cp.sum(failures)  # type: ignore[attr-defined]
            + 0.001
            * cp.sum(cp.hstack(switching))  # type: ignore[attr-defined]
            / max(capacity * scenario_count, 1.0)
        ),
        constraints,
    )
    refinement_start = time.monotonic()
    _solve(refinement)
    refinement_seconds = time.monotonic() - refinement_start
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
    success_rate_lower_ci = (
        None
        if confidence_level is None
        else wilson_lower_bound(len(successful), scenario_count, confidence_level)
    )
    success_indices = [index for index, failure in enumerate(failure_values) if failure < 0.5]
    common_execution_values = (
        scenario_execution_values[success_indices[0]]
        if policy_class == "common_open_loop_schedule"
        else ()
    )
    return NonAnticipativeFirmSolution(
        status=str(refinement.status),
        duration_h=duration_h,
        notice_h=int(snapshots[0].events[0].notice_hours),
        event_id=event_id,
        reliability_target=reliability,
        confidence_level=confidence_level,
        statistical_rule=statistical_rule,
        scenario_count=scenario_count,
        required_success_count=required_success_count,
        selected_success_count=len(successful),
        success_rate_lower_ci=success_rate_lower_ci,
        non_anticipative_policy_class=policy_class,
        information_node_count=sum(len(nodes) for nodes in information_nodes.values()),
        information_specification=information_specification,
        non_anticipative_capacity_kw=optimum_kw,
        non_anticipative_capacity_fraction_of_dynamic_range=optimum_kw / dynamic_range_kw,
        physical_dynamic_upper_bound_kw=dynamic_range_kw,
        successful_scenario_hashes=successful,
        failed_scenario_hashes=failed,
        objective_solve_seconds=objective_seconds,
        refinement_solve_seconds=refinement_seconds,
        common_execution_gpu_h=common_execution_values,
        scenario_execution_gpu_h=scenario_execution_values,
    )


def solve_frozen_non_anticipative_capacity(
    artifacts: Sequence[FrozenHourlyScenario],
    *,
    duration_h: int,
    event_id: int = 0,
    notice_h: int | None = None,
    reliability_target: float = 1.0,
    confidence_level: float | None = None,
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
        confidence_level=confidence_level,
        information_nodes=_open_loop_information_nodes(
            scenario_count=len(artifacts),
            horizon=horizon,
        ),
        policy_class="common_open_loop_schedule",
        information_specification="all_successful_scenarios_share_each_hour",
    )


def solve_frozen_observation_partition_capacity(
    artifacts: Sequence[FrozenHourlyScenario],
    *,
    duration_h: int,
    event_id: int = 0,
    notice_h: int | None = None,
    reliability_target: float = 1.0,
    confidence_level: float | None = None,
    specification: ObservationPartitionSpecification | None = None,
) -> NonAnticipativeFirmSolution:
    """Solve a causal, coarse-observation scenario-tree lower bound.

    This is stronger than the common-open-loop policy class, but remains a
    lower bound because it intentionally omits endogenous backlog from the
    information key and merges rare observation cells.
    """

    spec = specification or ObservationPartitionSpecification()
    nodes = build_observation_information_nodes(
        artifacts,
        duration_h=duration_h,
        event_id=event_id,
        notice_h=notice_h,
        specification=spec,
    )
    return _solve_non_anticipative_capacity(
        artifacts,
        duration_h=duration_h,
        event_id=event_id,
        notice_h=notice_h,
        reliability_target=reliability_target,
        confidence_level=confidence_level,
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
    )


def validate_non_anticipative_frontier(frontier: pd.DataFrame) -> None:
    """Check chance-count and physical invariants before publishing a frontier."""

    required = {
        "duration_h",
        "notice_h",
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
    statistical = (
        frontier[frontier["confidence_level"].notna()]
        if "confidence_level" in frontier.columns
        else frontier.iloc[0:0]
    )
    if not statistical.empty and (
        statistical["success_rate_lower_ci"] + _TOLERANCE
        < statistical["reliability_target"]
    ).any():
        raise ValueError("non-anticipative frontier violates its confidence requirement")


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
    information_structure: Literal[
        "common_open_loop", "coarse_observation_partition_tree"
    ],
    observation_specification: ObservationPartitionSpecification | None,
) -> list[dict[str, float | int | str]]:
    """Materialize each solved aggregate action with its causal node ID.

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
        if information_structure == "common_open_loop":
            information_nodes = _open_loop_information_nodes(
                scenario_count=len(artifacts),
                horizon=horizon,
            )
        else:
            information_nodes = build_observation_information_nodes(
                artifacts,
                duration_h=solution.duration_h,
                event_id=event_id,
                notice_h=solution.notice_h,
                specification=observation_specification,
            )
        for hour, nodes in information_nodes.items():
            for node_id, node in enumerate(nodes):
                node_execution_gpu_h = float(
                    np.mean(
                        [
                            solution.scenario_execution_gpu_h[scenario_index][hour]
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
                            "execution_gpu_h": node_execution_gpu_h,
                        }
                    )
    return policy_rows


def compute_and_save_non_anticipative_frontier(
    scenario_path: str | Path,
    *,
    durations_h: Sequence[int],
    notice_hours: Sequence[int] = (0,),
    output_directory: str | Path,
    event_id: int = 0,
    reliability_target: float = 1.0,
    confidence_level: float | None = None,
    information_structure: Literal[
        "common_open_loop", "coarse_observation_partition_tree"
    ] = "coarse_observation_partition_tree",
    observation_specification: ObservationPartitionSpecification | None = None,
) -> dict[str, str | int]:
    """Compute and persist one declared non-anticipative lower-bound frontier."""

    artifacts = _discover_artifacts(scenario_path)
    if information_structure == "common_open_loop":

        def solve_point(duration_h: int, notice_h: int) -> NonAnticipativeFirmSolution:
            return solve_frozen_non_anticipative_capacity(
                artifacts,
                duration_h=duration_h,
                event_id=event_id,
                notice_h=notice_h,
                reliability_target=reliability_target,
                confidence_level=confidence_level,
            )

    elif information_structure == "coarse_observation_partition_tree":

        def solve_point(duration_h: int, notice_h: int) -> NonAnticipativeFirmSolution:
            return solve_frozen_observation_partition_capacity(
                artifacts,
                duration_h=duration_h,
                event_id=event_id,
                notice_h=notice_h,
                reliability_target=reliability_target,
                confidence_level=confidence_level,
                specification=observation_specification,
            )

    else:
        raise ValueError(
            "unsupported non-anticipative information structure: "
            f"{information_structure}"
        )
    solutions = [
        solve_point(duration_h, notice_h)
        for notice_h in _non_negative_notices(notice_hours)
        for duration_h in _positive_durations(durations_h)
    ]
    frontier = pd.DataFrame.from_records([solution.summary() for solution in solutions])
    validate_non_anticipative_frontier(frontier)
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
        information_structure=information_structure,
        observation_specification=observation_specification,
    )
    pd.DataFrame.from_records(policy_rows).to_parquet(policies_path, index=False)
    manifest_path.write_text(
        json.dumps(
            {
                "capacity_layer": "non_anticipative_lower_bound",
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
                "durations_h": list(_positive_durations(durations_h)),
                "notice_hours": list(_non_negative_notices(notice_hours)),
                "reliability_target": _validate_reliability(reliability_target),
                "confidence_level": confidence_level,
                "scenario_count": len(artifacts),
                "scenario_hashes": [artifact.scenario_hash for artifact in artifacts],
                "frontier": str(frontier_path),
                "policies": str(policies_path),
                "policy_row_count": len(policy_rows),
                "common_execution_gpu_h": {
                    f"N{solution.notice_h}_H{solution.duration_h}": list(
                        solution.common_execution_gpu_h
                    )
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
