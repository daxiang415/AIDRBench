"""Incremental compute, delay and service-cost terms for economic screening."""

from __future__ import annotations

import math


def _finite_nonnegative(value: float, *, name: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0.0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return numeric


def incremental_opportunity_cost(
    *,
    deferred_gpu_h: float,
    economically_displaced_fraction: float,
    value_per_gpu_h: float,
) -> float:
    """Value only the declared displaced fraction of delayed computation."""

    deferred = _finite_nonnegative(deferred_gpu_h, name="deferred_gpu_h")
    exposure = _finite_nonnegative(
        economically_displaced_fraction,
        name="economically_displaced_fraction",
    )
    if exposure > 1.0:
        raise ValueError("economically_displaced_fraction must lie in [0, 1]")
    value = _finite_nonnegative(value_per_gpu_h, name="value_per_gpu_h")
    return deferred * exposure * value


def delay_cost(*, backlog_area_gpu_h_h: float, value_per_gpu_h_h: float) -> float:
    """Map incremental backlog-area exposure to a separately declared delay cost."""

    return _finite_nonnegative(backlog_area_gpu_h_h, name="backlog_area_gpu_h_h") * (
        _finite_nonnegative(value_per_gpu_h_h, name="value_per_gpu_h_h")
    )


def service_cost(
    *,
    missed_gpu_h: float,
    terminal_backlog_gpu_h: float,
    missed_work_cost_per_gpu_h: float,
    terminal_backlog_cost_per_gpu_h: float,
) -> float:
    """Cost incremental missed work and terminal backlog without a hidden proxy."""

    return _finite_nonnegative(missed_gpu_h, name="missed_gpu_h") * _finite_nonnegative(
        missed_work_cost_per_gpu_h, name="missed_work_cost_per_gpu_h"
    ) + _finite_nonnegative(
        terminal_backlog_gpu_h, name="terminal_backlog_gpu_h"
    ) * _finite_nonnegative(
        terminal_backlog_cost_per_gpu_h,
        name="terminal_backlog_cost_per_gpu_h",
    )
