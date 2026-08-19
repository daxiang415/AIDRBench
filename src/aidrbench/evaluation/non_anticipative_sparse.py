"""Direct sparse feasibility model for a fixed non-anticipative PI upper bound."""

from __future__ import annotations

import math
import time
import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]
from scipy.optimize import OptimizeWarning, linprog  # type: ignore[import-untyped]

from aidrbench.envs.community_ai_dr_env import HourlyPlanningSnapshot
from aidrbench.envs.hourly_config import RewardSpecification


class SparseNonAnticipativeInfeasible(RuntimeError):
    """The fixed capacity/failure-set feasibility problem is infeasible."""


@dataclass(frozen=True, slots=True)
class SparseNonAnticipativeResult:
    """A fixed-capacity feasibility witness returned by direct sparse HiGHS."""

    status: str
    model_build_seconds: float
    solve_seconds: float
    execution_gpu_h_by_class: np.ndarray
    rebound_reference_mode: str


class _Variables:
    def __init__(self) -> None:
        self.lower: list[float] = []
        self.upper: list[float] = []
        self.integrality: list[int] = []

    def allocate(
        self,
        shape: tuple[int, ...],
        *,
        lower: float | np.ndarray = 0.0,
        upper: float | np.ndarray = np.inf,
        integer: bool = False,
    ) -> np.ndarray:
        size = math.prod(shape)
        start = len(self.lower)
        lower_values = np.broadcast_to(np.asarray(lower, dtype="float64"), shape).reshape(-1)
        upper_values = np.broadcast_to(np.asarray(upper, dtype="float64"), shape).reshape(-1)
        self.lower.extend(float(value) for value in lower_values)
        self.upper.extend(float(value) for value in upper_values)
        self.integrality.extend([1 if integer else 0] * size)
        return np.arange(start, start + size, dtype="int64").reshape(shape)


class _Rows:
    def __init__(self) -> None:
        self.row: list[int] = []
        self.column: list[int] = []
        self.value: list[float] = []
        self.lower: list[float] = []
        self.upper: list[float] = []

    def add(
        self,
        columns: np.ndarray | list[int],
        values: np.ndarray | list[float],
        *,
        lower: float = -np.inf,
        upper: float = np.inf,
    ) -> None:
        column_values = np.asarray(columns, dtype="int64").reshape(-1)
        coefficients = np.asarray(values, dtype="float64").reshape(-1)
        if len(column_values) != len(coefficients):
            raise ValueError("sparse constraint columns and values have different lengths")
        nonzero = np.abs(coefficients) > 0.0
        row_index = len(self.lower)
        kept_columns = column_values[nonzero]
        kept_values = coefficients[nonzero]
        self.row.extend([row_index] * len(kept_columns))
        self.column.extend(int(value) for value in kept_columns)
        self.value.extend(float(value) for value in kept_values)
        self.lower.append(float(lower))
        self.upper.append(float(upper))


def _workload_arrays(
    snapshot: HourlyPlanningSnapshot,
    workload_classes: tuple[str, ...],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    horizon = snapshot.total_hours
    class_index = {job_class: index for index, job_class in enumerate(workload_classes)}
    released = np.zeros((len(workload_classes), horizon), dtype="float64")
    due = np.zeros_like(released)
    total = np.zeros(len(workload_classes), dtype="float64")
    for release, deadline, job_class, work_gpu_h in snapshot.work_groups:
        if job_class not in class_index:
            raise ValueError(f"unknown workload class in planning group: {job_class}")
        if release < 0 or deadline < release or work_gpu_h < 0.0:
            raise ValueError("invalid release/deadline fluid work group")
        index = class_index[job_class]
        total[index] += work_gpu_h
        if release < horizon:
            released[index, release] += work_gpu_h
        if deadline < horizon:
            due[index, deadline] += work_gpu_h
    if total.sum() <= 0.0:
        raise ValueError("sparse non-anticipative planning needs positive flexible work")
    return released, due, total


def solve_fixed_sparse_non_anticipative_feasibility(
    snapshots: tuple[HourlyPlanningSnapshot, ...],
    *,
    reward: RewardSpecification,
    information_nodes: dict[int, tuple[tuple[int, ...], ...]],
    fixed_capacity_kw: float,
    failed_scenario_indices: frozenset[int],
) -> SparseNonAnticipativeResult:
    """Test one fixed capacity and failure set with a direct sparse model.

    The formulation is equivalent to the CVXPY fluid model. A cumulative
    handled-work state replaces dense cumulative expressions, reducing the
    constraint matrix to linear size in scenarios, classes, and hours.
    """

    build_start = time.monotonic()
    if not snapshots:
        raise ValueError("sparse non-anticipative planning needs scenarios")
    scenario_count = len(snapshots)
    horizon = snapshots[0].total_hours
    capacity = snapshots[0].capacity_gpu_h
    workload_classes = tuple(snapshots[0].workload_classes)
    if not workload_classes:
        raise ValueError("sparse non-anticipative planning needs workload classes")
    if not math.isfinite(fixed_capacity_kw) or fixed_capacity_kw < 0.0:
        raise ValueError("fixed_capacity_kw must be finite and non-negative")
    if any(index < 0 or index >= scenario_count for index in failed_scenario_indices):
        raise ValueError("failed scenario index is outside the ensemble")
    if set(information_nodes) != set(range(horizon)):
        raise ValueError("information nodes must cover every planning hour")
    if any(len(snapshot.events) != 1 for snapshot in snapshots):
        raise ValueError("direct sparse NA currently requires exactly one event per scenario")
    event_lengths = {
        snapshot.events[0].stop_hour - snapshot.events[0].start_hour
        for snapshot in snapshots
    }
    if len(event_lengths) != 1:
        raise ValueError("direct sparse NA requires one common event duration")
    event_length = event_lengths.pop()
    if event_length <= 0:
        raise ValueError("direct sparse NA event duration must be positive")

    class_power = dict(snapshots[0].dynamic_kw_per_gpu_h_by_class)
    if set(class_power) != set(workload_classes):
        raise ValueError("sparse non-anticipative planning has incomplete class power")
    power_coefficients = np.asarray(
        [class_power[job_class] for job_class in workload_classes],
        dtype="float64",
    )
    dynamic_range_kw = float(power_coefficients.max() * capacity)
    if fixed_capacity_kw > dynamic_range_kw + 1e-6:
        raise SparseNonAnticipativeInfeasible(
            "fixed capacity exceeds the physical dynamic range"
        )

    released = np.zeros(
        (scenario_count, len(workload_classes), horizon), dtype="float64"
    )
    due = np.zeros_like(released)
    total = np.zeros((scenario_count, len(workload_classes)), dtype="float64")
    for scenario_index, snapshot in enumerate(snapshots):
        scenario_released, scenario_due, scenario_total = _workload_arrays(
            snapshot,
            workload_classes,
        )
        released[scenario_index] = scenario_released
        due[scenario_index] = scenario_due
        total[scenario_index] = scenario_total

    variables = _Variables()
    execution = variables.allocate(
        (scenario_count, len(workload_classes), horizon),
        lower=0.0,
    )
    missed = variables.allocate(
        (scenario_count, len(workload_classes), horizon),
        lower=0.0,
        upper=due,
    )
    handled = variables.allocate(
        (scenario_count, len(workload_classes), horizon),
        lower=np.cumsum(due, axis=2),
        upper=np.cumsum(released, axis=2),
    )
    if event_length == 1:
        peak_delivery = variables.allocate((scenario_count,), lower=0.0)
        rebound_reference_mode = "exact_single_interval_peak"
    else:
        peak_delivery = None
        rebound_reference_mode = "conservative_minimum_guaranteed_peak"

    rows = _Rows()
    for scenario_index, snapshot in enumerate(snapshots):
        failed = 1.0 if scenario_index in failed_scenario_indices else 0.0
        community = np.asarray(snapshot.community_power_kw, dtype="float64")
        baseline_pcc = np.asarray(snapshot.baseline_pcc_power_kw, dtype="float64")
        if len(community) != horizon or len(baseline_pcc) != horizon:
            raise ValueError("sparse non-anticipative scenario horizon mismatch")
        if tuple(snapshot.workload_classes) != workload_classes:
            raise ValueError("sparse non-anticipative workload classes changed by scenario")
        candidate_power = dict(snapshot.dynamic_kw_per_gpu_h_by_class)
        if any(
            not math.isclose(
                candidate_power.get(job_class, math.nan),
                class_power[job_class],
                rel_tol=0.0,
                abs_tol=1e-9,
            )
            for job_class in workload_classes
        ):
            raise ValueError("sparse non-anticipative class power changed by scenario")

        for class_index in range(len(workload_classes)):
            for hour in range(horizon):
                state_columns = [
                    int(handled[scenario_index, class_index, hour]),
                    int(execution[scenario_index, class_index, hour]),
                    int(missed[scenario_index, class_index, hour]),
                ]
                state_values = [1.0, -1.0, -1.0]
                if hour:
                    state_columns.append(int(handled[scenario_index, class_index, hour - 1]))
                    state_values.append(-1.0)
                rows.add(state_columns, state_values, lower=0.0, upper=0.0)

        for hour in range(horizon):
            rows.add(
                execution[scenario_index, :, hour],
                np.ones(len(workload_classes), dtype="float64"),
                upper=capacity,
            )

        max_pcc_kw = float(
            (community + snapshot.fixed_dc_power_kw + dynamic_range_kw).max()
        )
        power_big_m = max(2.0 * max_pcc_kw, 2.0 * dynamic_range_kw, 1.0)
        work_big_m = max(snapshot.total_arrival_gpu_h, capacity, 1.0)
        for hour in range(horizon):
            rows.add(
                execution[scenario_index, :, hour],
                power_coefficients,
                upper=(
                    snapshot.pcc_capacity_kw
                    - community[hour]
                    - snapshot.fixed_dc_power_kw
                    + power_big_m * failed
                ),
            )
        rows.add(
            missed[scenario_index].reshape(-1),
            np.ones(len(workload_classes) * horizon, dtype="float64"),
            upper=(
                reward.max_deadline_miss_rate * snapshot.total_arrival_gpu_h
                + work_big_m * failed
            ),
        )
        terminal_allowance = (
            snapshot.baseline_terminal_backlog_gpu_h
            + reward.max_terminal_backlog_fraction * snapshot.total_arrival_gpu_h
            + work_big_m * failed
        )
        rows.add(
            handled[scenario_index, :, -1],
            np.ones(len(workload_classes), dtype="float64"),
            lower=float(total[scenario_index].sum() - terminal_allowance),
        )

        event = snapshot.events[0]
        event_indices = np.arange(event.start_hour, event.stop_hour, dtype="int64")
        window_indices = np.arange(event.start_hour, event.recovery_stop_hour, dtype="int64")
        recovery_indices = np.arange(event.stop_hour, event.recovery_stop_hour, dtype="int64")
        event_baseline_minus_fixed = (
            baseline_pcc[event_indices]
            - community[event_indices]
            - snapshot.fixed_dc_power_kw
        )
        ratio_margin = 1e-6
        for event_offset, hour in enumerate(event_indices):
            rows.add(
                execution[scenario_index, :, hour],
                power_coefficients,
                upper=float(
                    event_baseline_minus_fixed[event_offset]
                    - (reward.min_delivery_ratio + ratio_margin) * fixed_capacity_kw
                    + power_big_m * failed
                ),
            )
            if peak_delivery is not None:
                # A one-interval event has no peak-selection disjunction: the
                # peak is exactly that interval's delivered reduction.
                rows.add(
                    np.concatenate(
                        (
                            execution[scenario_index, :, hour],
                            [peak_delivery[scenario_index]],
                        )
                    ),
                    np.concatenate((-power_coefficients, [-1.0])),
                    upper=float(
                        -event_baseline_minus_fixed[event_offset]
                        + power_big_m * failed
                    ),
                )
                rows.add(
                    np.concatenate(
                        (
                            execution[scenario_index, :, hour],
                            [peak_delivery[scenario_index]],
                        )
                    ),
                    np.concatenate((power_coefficients, [1.0])),
                    upper=float(
                        event_baseline_minus_fixed[event_offset]
                        + power_big_m * failed
                    ),
                )
        baseline_window_peak = float(baseline_pcc[window_indices].max())
        for hour in window_indices:
            rows.add(
                execution[scenario_index, :, hour],
                power_coefficients,
                upper=float(
                    baseline_window_peak
                    - (reward.min_window_peak_relief_fraction + ratio_margin)
                    * fixed_capacity_kw
                    - community[hour]
                    - snapshot.fixed_dc_power_kw
                    + power_big_m * failed
                ),
            )
        for hour in recovery_indices:
            if peak_delivery is not None:
                rows.add(
                    np.concatenate(
                        (
                            execution[scenario_index, :, hour],
                            [peak_delivery[scenario_index]],
                        )
                    ),
                    np.concatenate(
                        (power_coefficients, [-reward.max_rebound_ratio + ratio_margin])
                    ),
                    upper=float(
                        baseline_pcc[hour]
                        - community[hour]
                        - snapshot.fixed_dc_power_kw
                        + power_big_m * failed
                    ),
                )
            else:
                guaranteed_peak_kw = (
                    reward.min_delivery_ratio + ratio_margin
                ) * fixed_capacity_kw
                rows.add(
                    execution[scenario_index, :, hour],
                    power_coefficients,
                    upper=float(
                        baseline_pcc[hour]
                        - community[hour]
                        - snapshot.fixed_dc_power_kw
                        + (reward.max_rebound_ratio - ratio_margin)
                        * guaranteed_peak_kw
                        + power_big_m * failed
                    ),
                )

    for hour, nodes in information_nodes.items():
        for node in nodes:
            anchor = node[0]
            for scenario_index in node[1:]:
                for class_index in range(len(workload_classes)):
                    rows.add(
                        [
                            int(execution[anchor, class_index, hour]),
                            int(execution[scenario_index, class_index, hour]),
                        ],
                        [1.0, -1.0],
                        lower=0.0,
                        upper=0.0,
                    )

    variable_count = len(variables.lower)
    matrix = sparse.coo_matrix(
        (rows.value, (rows.row, rows.column)),
        shape=(len(rows.lower), variable_count),
        dtype="float64",
    ).tocsr()
    model_build_seconds = time.monotonic() - build_start
    solve_start = time.monotonic()
    row_lower = np.asarray(rows.lower, dtype="float64")
    row_upper = np.asarray(rows.upper, dtype="float64")
    equality = np.isfinite(row_lower) & np.isfinite(row_upper) & np.isclose(
        row_lower,
        row_upper,
        rtol=0.0,
        atol=1e-12,
    )
    upper_bounded = np.isfinite(row_upper) & ~equality
    lower_bounded = np.isfinite(row_lower) & ~equality
    inequality_blocks = []
    inequality_bounds = []
    if upper_bounded.any():
        inequality_blocks.append(matrix[upper_bounded])
        inequality_bounds.append(row_upper[upper_bounded])
    if lower_bounded.any():
        inequality_blocks.append(-matrix[lower_bounded])
        inequality_bounds.append(-row_lower[lower_bounded])
    inequality_matrix = (
        sparse.vstack(inequality_blocks, format="csr")
        if inequality_blocks
        else None
    )
    inequality_bound = (
        np.concatenate(inequality_bounds) if inequality_bounds else None
    )
    with warnings.catch_warnings():
        # SciPy forwards this valid HiGHS option but labels backend-specific
        # keys as unrecognized at the scipy.optimize API boundary.
        warnings.filterwarnings(
            "ignore",
            message="Unrecognized options detected:.*threads",
            category=OptimizeWarning,
        )
        result: Any = linprog(
            np.zeros(variable_count, dtype="float64"),
            A_ub=inequality_matrix,
            b_ub=inequality_bound,
            A_eq=matrix[equality] if equality.any() else None,
            b_eq=row_upper[equality] if equality.any() else None,
            bounds=np.column_stack(
                (
                    np.asarray(variables.lower, dtype="float64"),
                    np.asarray(variables.upper, dtype="float64"),
                )
            ),
            method="highs",
            options={"disp": False, "presolve": True, "threads": 1},
        )
    solve_seconds = time.monotonic() - solve_start
    if result.status == 2:
        raise SparseNonAnticipativeInfeasible(str(result.message))
    if not result.success or result.x is None:
        raise RuntimeError(
            f"direct sparse non-anticipative optimization did not solve: {result.message}"
        )
    solution = np.asarray(result.x, dtype="float64")
    execution_values = np.clip(
        solution[execution.reshape(-1)].reshape(execution.shape),
        0.0,
        capacity,
    )
    return SparseNonAnticipativeResult(
        status="optimal",
        model_build_seconds=model_build_seconds,
        solve_seconds=solve_seconds,
        execution_gpu_h_by_class=execution_values,
        rebound_reference_mode=rebound_reference_mode,
    )
