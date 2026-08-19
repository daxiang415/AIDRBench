"""Perfect-future full-horizon optimizer for the hourly fluid environment."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from aidrbench.envs.community_ai_dr_env import (
    HourlyCommunityAIDemandResponseEnv,
    HourlyPlanningSnapshot,
)
from aidrbench.fluid_planning import build_fluid_workload_decision

HIGHS_THREADS_PER_SOLVE = 1


@dataclass(frozen=True, slots=True)
class FullHorizonOracleSolution:
    """Globally solved schedule under the fluid, perfect-future MILP model.

    This is a perfect-information planning bound.  It is not a causal policy
    result and must never be labelled as certified firm capacity.
    """

    status: str
    perfect_information_capacity_kw: float
    perfect_information_capacity_fraction_of_dynamic_range: float
    configured_mean_request_kw: float
    total_deadline_miss_gpu_h: float
    terminal_backlog_gpu_h: float
    minimum_mean_delivery_ratio_for_bound: float
    minimum_interval_delivery_ratio_for_bound: float
    maximum_rebound_ratio_for_bound: float
    minimum_window_relief_fraction_for_bound: float
    objective_solve_seconds: float
    refinement_solve_seconds: float
    action_fractions: tuple[float, ...]
    execution_gpu_h: tuple[float, ...]
    execution_gpu_h_by_class: tuple[tuple[str, tuple[float, ...]], ...]

    def summary(self) -> dict[str, float | str]:
        return {
            "perfect_information_status": self.status,
            "perfect_information_capacity_kw": self.perfect_information_capacity_kw,
            "perfect_information_capacity_fraction_of_dynamic_range": (
                self.perfect_information_capacity_fraction_of_dynamic_range
            ),
            "perfect_information_configured_mean_request_kw": self.configured_mean_request_kw,
            "perfect_information_total_deadline_miss_gpu_h": self.total_deadline_miss_gpu_h,
            "perfect_information_terminal_backlog_gpu_h": self.terminal_backlog_gpu_h,
            "perfect_information_minimum_mean_delivery_ratio": (
                self.minimum_mean_delivery_ratio_for_bound
            ),
            "perfect_information_minimum_interval_delivery_ratio": (
                self.minimum_interval_delivery_ratio_for_bound
            ),
            "perfect_information_maximum_rebound_ratio": self.maximum_rebound_ratio_for_bound,
            "perfect_information_minimum_window_relief_fraction": (
                self.minimum_window_relief_fraction_for_bound
            ),
            "perfect_information_objective_solve_seconds": self.objective_solve_seconds,
            "perfect_information_refinement_solve_seconds": self.refinement_solve_seconds,
        }


def _solve(problem: Any) -> None:
    try:
        import highspy

        # Scenario-level parallelism is controlled by the caller. Keeping each
        # HiGHS instance single-threaded prevents nested oversubscription and
        # makes parallel frontier runs reproducible across machines. HiGHS has
        # a process-global thread scheduler, so reset a scheduler that another
        # optimization path may have initialized with its default thread count.
        highspy.Highs.resetGlobalScheduler(True)
        problem.solve(solver="HIGHS", threads=HIGHS_THREADS_PER_SOLVE)
    except ImportError as exc:
        raise RuntimeError(
            "full-horizon oracle requires the project 'control' dependencies"
        ) from exc
    if problem.status not in {"optimal", "optimal_inaccurate"}:
        raise RuntimeError(f"full-horizon oracle did not solve: {problem.status}")


def solve_full_horizon_oracle(
    snapshot: HourlyPlanningSnapshot,
    *,
    min_delivery_ratio: float,
    min_interval_delivery_ratio: float,
    max_deadline_miss_rate: float,
    max_rebound_ratio: float,
    min_window_peak_relief_fraction: float,
    max_terminal_backlog_fraction: float,
) -> FullHorizonOracleSolution:
    """Maximize common certified DR reduction over one known episode.

    The workload is fluid and preemptible, while binary variables express the
    evaluator's event peak-delivery denominator exactly. Consequently HiGHS
    returns a global optimum for this explicit perfect-future model.
    """

    try:
        import cvxpy as cp
    except ImportError as exc:
        raise RuntimeError(
            "full-horizon oracle requires the project 'control' dependencies"
        ) from exc

    if not snapshot.events:
        raise ValueError("full-horizon firm-flexibility oracle needs at least one DR event")
    horizon = snapshot.total_hours
    capacity = snapshot.capacity_gpu_h
    community = np.asarray(snapshot.community_power_kw, dtype="float64")
    baseline_pcc = np.asarray(snapshot.baseline_pcc_power_kw, dtype="float64")
    dynamic_power_by_class = dict(snapshot.dynamic_kw_per_gpu_h_by_class)
    if set(dynamic_power_by_class) != set(snapshot.workload_classes):
        raise ValueError("planning snapshot has incomplete class-specific power coefficients")
    dynamic_range_kw = max(dynamic_power_by_class.values()) * capacity
    big_m_kw = max(2.0 * dynamic_range_kw, 1.0)
    ratio_margin = 1e-6

    workload = build_fluid_workload_decision(snapshot, cp=cp, name_suffix="pi")
    execution_by_class = workload.execution_by_class
    execution = workload.execution_gpu_h
    dynamic_dc_power = sum(
        dynamic_power_by_class[job_class] * execution_by_class[job_class]
        for job_class in snapshot.workload_classes
    )
    firm_reduction = cp.Variable(nonneg=True, name="firm_reduction_kw")
    missed_total = workload.missed_gpu_h
    terminal_backlog = workload.terminal_backlog_gpu_h
    pcc_power = community + snapshot.fixed_dc_power_kw + dynamic_dc_power
    constraints: list[Any] = [
        *workload.constraints,
        pcc_power <= snapshot.pcc_capacity_kw,
        missed_total <= max_deadline_miss_rate * snapshot.total_arrival_gpu_h,
        terminal_backlog >= 0.0,
        terminal_backlog
        <= snapshot.baseline_terminal_backlog_gpu_h
        + max_terminal_backlog_fraction * snapshot.total_arrival_gpu_h,
        firm_reduction <= dynamic_range_kw,
    ]

    for event in snapshot.events:
        event_indices = np.arange(event.start_hour, event.stop_hour, dtype="int64")
        window_indices = np.arange(
            event.start_hour, event.recovery_stop_hour, dtype="int64"
        )
        recovery_indices = np.arange(
            event.stop_hour, event.recovery_stop_hour, dtype="int64"
        )
        reduction = baseline_pcc[event_indices] - pcc_power[event_indices]
        delivered = cp.Variable(len(event_indices), nonneg=True)
        peak_selector = cp.Variable(len(event_indices), boolean=True)
        peak_delivery = cp.Variable(nonneg=True)
        event_ones = np.ones(len(event_indices), dtype="float64")
        constraints.extend(
            [
                delivered <= firm_reduction,
                delivered <= reduction,
                event_ones @ delivered
                >= (min_delivery_ratio + ratio_margin)
                * len(event_indices)
                * firm_reduction,
                reduction
                >= (min_interval_delivery_ratio + ratio_margin) * firm_reduction,
                peak_delivery >= reduction,
                peak_delivery <= reduction + big_m_kw * (1.0 - peak_selector),
                event_ones @ peak_selector == 1.0,
            ]
        )
        baseline_window_peak = float(baseline_pcc[window_indices].max())
        constraints.append(
            pcc_power[window_indices]
            <= baseline_window_peak
            - (min_window_peak_relief_fraction + ratio_margin) * firm_reduction
        )
        if len(recovery_indices):
            constraints.append(
                pcc_power[recovery_indices] - baseline_pcc[recovery_indices]
                <= (max_rebound_ratio - ratio_margin) * peak_delivery
            )

    maximize = cp.Problem(cp.Maximize(firm_reduction), constraints)
    objective_start = time.monotonic()
    _solve(maximize)
    objective_seconds = time.monotonic() - objective_start
    if firm_reduction.value is None:
        raise RuntimeError("full-horizon oracle returned no firm-reduction optimum")
    optimum_kw = float(np.asarray(firm_reduction.value).item())

    switching = cp.abs(  # type: ignore[attr-defined]
        cp.hstack(  # type: ignore[attr-defined]
            [execution[0] - capacity, execution[1:] - execution[:-1]]
        )
    )
    constraints.extend(
        [
            firm_reduction >= optimum_kw - 1e-6,
            firm_reduction <= optimum_kw + 1e-6,
        ]
    )
    refinement = cp.Problem(
        cp.Minimize(
            1_000.0
            * missed_total
            / max(snapshot.total_arrival_gpu_h, 1.0)
            + 1_000.0 * terminal_backlog / max(snapshot.total_arrival_gpu_h, 1.0)
            + np.arange(horizon, dtype="float64") @ execution
            / max(snapshot.total_arrival_gpu_h * horizon, 1.0)
            + 0.001
            * (np.ones(horizon, dtype="float64") @ switching)
            / capacity
        ),
        constraints,
    )
    refinement_start = time.monotonic()
    _solve(refinement)
    refinement_seconds = time.monotonic() - refinement_start
    if (
        execution.value is None
        or missed_total.value is None
        or terminal_backlog.value is None
    ):
        raise RuntimeError("full-horizon oracle returned no primal schedule")
    execution_values = np.clip(np.asarray(execution.value), 0.0, capacity)
    execution_values_by_class = {
        job_class: np.clip(
            np.asarray(execution_by_class[job_class].value),
            0.0,
            capacity,
        )
        for job_class in snapshot.workload_classes
    }
    missed_gpu_h = max(float(np.asarray(missed_total.value).item()), 0.0)
    terminal_gpu_h = max(float(np.asarray(terminal_backlog.value).item()), 0.0)
    configured_requests = [event.requested_reduction_kw for event in snapshot.events]
    optimized_pcc = community + snapshot.fixed_dc_power_kw + sum(
        dynamic_power_by_class[job_class] * execution_values_by_class[job_class]
        for job_class in snapshot.workload_classes
    )
    mean_delivery_ratios: list[float] = []
    interval_delivery_ratios: list[float] = []
    rebound_ratios: list[float] = []
    window_relief_fractions: list[float] = []
    for event in snapshot.events:
        event_slice = slice(event.start_hour, event.stop_hour)
        window_slice = slice(event.start_hour, event.recovery_stop_hour)
        recovery_slice = slice(event.stop_hour, event.recovery_stop_hour)
        event_reductions = np.maximum(
            baseline_pcc[event_slice] - optimized_pcc[event_slice],
            0.0,
        )
        mean_delivery_ratios.append(
            float(np.minimum(event_reductions, optimum_kw).sum())
            / (len(event_reductions) * optimum_kw)
        )
        interval_delivery_ratios.append(float(event_reductions.min()) / optimum_kw)
        audited_peak_delivery = float(event_reductions.max())
        rebound_peak = float(
            np.maximum(
                optimized_pcc[recovery_slice] - baseline_pcc[recovery_slice],
                0.0,
            ).max(initial=0.0)
        )
        rebound_ratios.append(
            rebound_peak / audited_peak_delivery if audited_peak_delivery > 0.0 else 0.0
        )
        window_relief_fractions.append(
            float(
                baseline_pcc[window_slice].max()
                - optimized_pcc[window_slice].max()
            )
            / optimum_kw
        )
    return FullHorizonOracleSolution(
        status=str(refinement.status),
        perfect_information_capacity_kw=optimum_kw,
        perfect_information_capacity_fraction_of_dynamic_range=optimum_kw / dynamic_range_kw,
        configured_mean_request_kw=float(np.mean(configured_requests)),
        total_deadline_miss_gpu_h=missed_gpu_h,
        terminal_backlog_gpu_h=terminal_gpu_h,
        minimum_mean_delivery_ratio_for_bound=min(mean_delivery_ratios),
        minimum_interval_delivery_ratio_for_bound=min(interval_delivery_ratios),
        maximum_rebound_ratio_for_bound=max(rebound_ratios),
        minimum_window_relief_fraction_for_bound=min(window_relief_fractions),
        objective_solve_seconds=objective_seconds,
        refinement_solve_seconds=refinement_seconds,
        action_fractions=tuple(float(value / capacity) for value in execution_values),
        execution_gpu_h=tuple(float(value) for value in execution_values),
        execution_gpu_h_by_class=tuple(
            (
                job_class,
                tuple(float(value) for value in execution_values_by_class[job_class]),
            )
            for job_class in snapshot.workload_classes
        ),
    )


class HourlyFullHorizonOracleController:
    """Replay a globally solved schedule that uses perfect episode foresight."""

    name = "oracle"
    forecast_assumption = "perfect_full_episode_future"
    information_structure = "perfect_information_full_episode"

    def __init__(self) -> None:
        self._hour = 0
        self._episode_seed: int | None = None
        self.solution: FullHorizonOracleSolution | None = None

    def reset(self) -> None:
        self._hour = 0
        self._episode_seed = None
        self.solution = None

    def act(
        self,
        env: HourlyCommunityAIDemandResponseEnv,
        info: dict[str, Any],
    ) -> np.ndarray:
        if env.config.action_mode != "continuous":
            raise ValueError("full-horizon oracle requires the continuous hourly environment")
        episode_seed = int(info["episode_seed"])
        if self.solution is None or self._episode_seed != episode_seed:
            reward = env.config.reward
            self.solution = solve_full_horizon_oracle(
                env.full_horizon_planning_snapshot(),
                min_delivery_ratio=reward.min_delivery_ratio,
                min_interval_delivery_ratio=reward.min_delivery_ratio,
                max_deadline_miss_rate=reward.max_deadline_miss_rate,
                max_rebound_ratio=reward.max_rebound_ratio,
                min_window_peak_relief_fraction=reward.min_window_peak_relief_fraction,
                max_terminal_backlog_fraction=reward.max_terminal_backlog_fraction,
            )
            self._episode_seed = episode_seed
            self._hour = 0
        if self._hour >= len(self.solution.action_fractions):
            raise RuntimeError("oracle schedule is shorter than the environment episode")
        fraction = self.solution.action_fractions[self._hour]
        self._hour += 1
        return np.asarray((fraction,), dtype=np.float32)

    def summary_metadata(self) -> dict[str, float | str]:
        if self.solution is None:
            raise RuntimeError("oracle has not solved an episode")
        return self.solution.summary()
