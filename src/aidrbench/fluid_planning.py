"""Compact release/deadline constraints for preemptible fluid GPU work."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

from aidrbench.envs.community_ai_dr_env import HourlyPlanningSnapshot


@dataclass(frozen=True, slots=True)
class FluidWorkloadDecision:
    """CVXPY expressions for one scenario's class-aware fluid workload."""

    execution_by_class: dict[str, Any]
    execution_gpu_h: Any
    missed_gpu_h: Any
    terminal_backlog_gpu_h: Any
    constraints: tuple[Any, ...]


def build_fluid_workload_decision(
    snapshot: HourlyPlanningSnapshot,
    *,
    cp: Any,
    name_suffix: str,
) -> FluidWorkloadDecision:
    """Build an exact compact model for interval-released preemptible work.

    For each workload class, cumulative executed-plus-missed work cannot exceed
    cumulative releases and must cover cumulative deadlines. Misses can occur
    only in the hour of a declared deadline. These are the compact feasibility
    conditions for the repository's fluid, preemptible workload model and are
    equivalent to the larger job-to-hour edge formulation.
    """

    horizon = snapshot.total_hours
    capacity = snapshot.capacity_gpu_h
    workload_classes = tuple(snapshot.workload_classes)
    if not workload_classes:
        raise ValueError("fluid planning needs at least one workload class")
    class_set = set(workload_classes)
    released_by_class = {
        job_class: np.zeros(horizon, dtype="float64") for job_class in workload_classes
    }
    due_by_class = {
        job_class: np.zeros(horizon, dtype="float64") for job_class in workload_classes
    }
    total_by_class = {job_class: 0.0 for job_class in workload_classes}
    for release, deadline, job_class, work_gpu_h in snapshot.work_groups:
        if job_class not in class_set:
            raise ValueError(f"unknown workload class in planning group: {job_class}")
        if release < 0 or deadline < release or work_gpu_h < 0.0:
            raise ValueError("invalid release/deadline fluid work group")
        total_by_class[job_class] += work_gpu_h
        if release < horizon:
            released_by_class[job_class][release] += work_gpu_h
        if deadline < horizon:
            due_by_class[job_class][deadline] += work_gpu_h
    if sum(total_by_class.values()) <= 0.0:
        raise ValueError("fluid planning needs positive flexible work")

    cumulative = sparse.tril(
        sparse.csr_matrix(np.ones((horizon, horizon), dtype="float64")),
        format="csr",
    )
    hour_ones = np.ones(horizon, dtype="float64")
    execution_by_class: dict[str, Any] = {}
    missed_by_class: dict[str, Any] = {}
    constraints: list[Any] = []
    remaining_by_class: list[Any] = []
    for job_class in workload_classes:
        execution = cp.Variable(
            horizon,
            nonneg=True,
            name=f"execution_{job_class}_{name_suffix}",
        )
        missed = cp.Variable(
            horizon,
            nonneg=True,
            name=f"missed_{job_class}_{name_suffix}",
        )
        cumulative_execution = cumulative @ execution
        cumulative_missed = cumulative @ missed
        cumulative_released = np.cumsum(released_by_class[job_class])
        cumulative_due = np.cumsum(due_by_class[job_class])
        handled = cumulative_execution + cumulative_missed
        remaining = (
            total_by_class[job_class]
            - hour_ones @ execution
            - hour_ones @ missed
        )
        constraints.extend(
            [
                handled <= cumulative_released,
                handled >= cumulative_due,
                missed <= due_by_class[job_class],
                remaining >= 0.0,
            ]
        )
        execution_by_class[job_class] = execution
        missed_by_class[job_class] = missed
        remaining_by_class.append(remaining)

    execution_gpu_h = sum(execution_by_class.values())
    missed_gpu_h = sum(hour_ones @ values for values in missed_by_class.values())
    terminal_backlog_gpu_h = sum(remaining_by_class)
    constraints.append(execution_gpu_h <= capacity)
    return FluidWorkloadDecision(
        execution_by_class=execution_by_class,
        execution_gpu_h=execution_gpu_h,
        missed_gpu_h=missed_gpu_h,
        terminal_backlog_gpu_h=terminal_backlog_gpu_h,
        constraints=tuple(constraints),
    )
