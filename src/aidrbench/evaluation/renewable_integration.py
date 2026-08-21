"""Community renewable-integration planning with a fixed data-centre scale.

The existing hosting-capacity model asks how much data-centre capacity can be
connected for a fixed photovoltaic (PV) portfolio.  This module evaluates the
orthogonal slice of the same feasible set: for a fixed data-centre scale, how
much curtailment-constrained PV can be connected, and how much of a fixed PV
installation can be used.  All schedules are perfect-information planning
bounds; they are not causal controller certificates.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

from aidrbench.data.frozen_scenarios import FrozenHourlyScenario
from aidrbench.envs.community_ai_dr_env import HourlyPlanningSnapshot
from aidrbench.evaluation.hosting_capacity import (
    CommunityPortfolio,
    _assert_common_physics,
)
from aidrbench.evaluation.non_anticipative import _snapshot_for

_TOLERANCE = 1e-6


@dataclass(slots=True)
class _RenewableProblem:
    cp: Any
    constraints: list[Any]
    pv_rated_kw: Any
    pv_used_kw: Any
    pv_available_kw: Any
    pcc_power_kw: Any
    dc_power_kw: Any
    battery_charge_kw: Any
    battery_discharge_kw: Any
    battery_soc_kwh: Any
    missed_gpu_h: Any
    terminal_backlog_gpu_h: Any
    snapshot: HourlyPlanningSnapshot
    total_arrival_gpu_h: float
    community_load_kw: np.ndarray


@dataclass(frozen=True, slots=True)
class RenewableIntegrationSolution:
    """One scenario-level PV-hosting or fixed-capacity operating result."""

    status: str
    analysis: Literal["pv_hosting", "fixed_pv_operation"]
    dc_operation: Literal["rigid", "flexible"]
    bess_enabled: bool
    bess_dispatch_mode: str
    pcc_capacity_kw: float
    target_dc_peak_kw: float
    dc_scale_of_reference_mix: float
    reference_mix_operating_peak_kw: float
    pv_rated_kw: float
    maximum_pv_curtailment_fraction: float | None
    total_community_load_kwh: float
    total_dc_energy_kwh: float
    total_pv_available_kwh: float
    total_pv_used_kwh: float
    total_pv_curtailed_kwh: float
    pv_utilisation_fraction: float
    renewable_demand_share: float
    total_grid_import_kwh: float
    maximum_pcc_import_kw: float
    hours_near_pcc_limit: int
    near_pcc_limit_fraction: float
    total_bess_charge_kwh: float
    total_bess_discharge_kwh: float
    total_bess_throughput_kwh: float
    maximum_simultaneous_bess_charge_discharge_kw: float
    terminal_soc_deviation_kwh: float
    deadline_miss_gpu_h: float
    deadline_miss_fraction: float
    terminal_backlog_gpu_h: float
    terminal_backlog_fraction: float
    objective_solve_seconds: float

    def summary(self) -> dict[str, object]:
        return {
            "capacity_layer": "perfect_information_renewable_planning_bound",
            "analysis": self.analysis,
            "status": self.status,
            "dc_operation": self.dc_operation,
            "bess_enabled": self.bess_enabled,
            "bess_dispatch_mode": self.bess_dispatch_mode,
            "pcc_capacity_kw": self.pcc_capacity_kw,
            "target_dc_peak_kw": self.target_dc_peak_kw,
            "dc_scale_of_reference_mix": self.dc_scale_of_reference_mix,
            "reference_mix_operating_peak_kw": self.reference_mix_operating_peak_kw,
            "pv_rated_kw": self.pv_rated_kw,
            "maximum_pv_curtailment_fraction": self.maximum_pv_curtailment_fraction,
            "total_community_load_kwh": self.total_community_load_kwh,
            "total_dc_energy_kwh": self.total_dc_energy_kwh,
            "total_pv_available_kwh": self.total_pv_available_kwh,
            "total_pv_used_kwh": self.total_pv_used_kwh,
            "total_pv_curtailed_kwh": self.total_pv_curtailed_kwh,
            "pv_utilisation_fraction": self.pv_utilisation_fraction,
            "renewable_demand_share": self.renewable_demand_share,
            "total_grid_import_kwh": self.total_grid_import_kwh,
            "maximum_pcc_import_kw": self.maximum_pcc_import_kw,
            "hours_near_pcc_limit": self.hours_near_pcc_limit,
            "near_pcc_limit_fraction": self.near_pcc_limit_fraction,
            "total_bess_charge_kwh": self.total_bess_charge_kwh,
            "total_bess_discharge_kwh": self.total_bess_discharge_kwh,
            "total_bess_throughput_kwh": self.total_bess_throughput_kwh,
            "maximum_simultaneous_bess_charge_discharge_kw": (
                self.maximum_simultaneous_bess_charge_discharge_kw
            ),
            "terminal_soc_deviation_kwh": self.terminal_soc_deviation_kwh,
            "deadline_miss_gpu_h": self.deadline_miss_gpu_h,
            "deadline_miss_fraction": self.deadline_miss_fraction,
            "terminal_backlog_gpu_h": self.terminal_backlog_gpu_h,
            "terminal_backlog_fraction": self.terminal_backlog_fraction,
            "objective_solve_seconds": self.objective_solve_seconds,
        }


def _validate_fraction(value: float, name: str, *, allow_one: bool = False) -> None:
    upper_ok = value <= 1.0 if allow_one else value < 1.0
    if not math.isfinite(value) or value < 0.0 or not upper_ok:
        interval = "[0, 1]" if allow_one else "[0, 1)"
        raise ValueError(f"{name} must lie in {interval}")


def _solve(problem: Any, *, allow_infeasible: bool = False) -> str:
    try:
        problem.solve(solver="HIGHS", highs_options={"threads": 1})
    except ImportError as exc:
        raise RuntimeError(
            "renewable-integration optimization requires control dependencies"
        ) from exc
    status = str(problem.status)
    if status in {"optimal", "optimal_inaccurate"}:
        return status
    if allow_infeasible and status in {"infeasible", "infeasible_inaccurate"}:
        return status
    raise RuntimeError(f"renewable-integration optimization did not solve: {status}")


def _unit_pv_profile_kw(artifact: FrozenHourlyScenario, horizon: int) -> np.ndarray:
    potential = artifact.community["pv_generation_kw"].iloc[:horizon].to_numpy(
        dtype="float64"
    )
    peak = float(potential.max(initial=0.0))
    if peak <= _TOLERANCE:
        raise ValueError(
            "the frozen scenario contains no PV potential; freeze it from a PV-enabled profile"
        )
    return potential / peak


def _build_problem(
    artifact: FrozenHourlyScenario,
    *,
    portfolio: CommunityPortfolio,
    dc_operation: Literal["rigid", "flexible"],
    dc_scale_of_reference_mix: float,
    pv_rated_kw: float | None,
) -> _RenewableProblem:
    if dc_operation not in {"rigid", "flexible"}:
        raise ValueError("dc_operation must be 'rigid' or 'flexible'")
    if not math.isfinite(dc_scale_of_reference_mix) or dc_scale_of_reference_mix < 0.0:
        raise ValueError("dc_scale_of_reference_mix must be finite and non-negative")
    if pv_rated_kw is not None and (not math.isfinite(pv_rated_kw) or pv_rated_kw <= 0.0):
        raise ValueError("pv_rated_kw must be positive when fixed")
    try:
        import cvxpy as cp
    except ImportError as exc:
        raise RuntimeError(
            "renewable-integration optimization requires control dependencies"
        ) from exc

    snapshot, reward = _snapshot_for(artifact, duration_h=1, event_id=0)
    _assert_common_physics([snapshot])
    horizon = snapshot.total_hours
    timestep_h = 1.0
    scale = float(dc_scale_of_reference_mix)
    dynamic_power_by_class = dict(snapshot.dynamic_kw_per_gpu_h_by_class)
    if not dynamic_power_by_class:
        raise ValueError("renewable-integration snapshot has no class power coefficients")

    constraints: list[Any] = []
    unit_pv = _unit_pv_profile_kw(artifact, horizon)
    if pv_rated_kw is None:
        pv_capacity = cp.Variable(nonneg=True, name="pv_rated_kw")
    else:
        pv_capacity = cp.Constant(float(pv_rated_kw))
    pv_available = unit_pv * pv_capacity
    pv_used = cp.Variable(horizon, nonneg=True, name="pv_used_kw")
    constraints.append(pv_used <= pv_available)

    battery_charge: Any
    battery_discharge: Any
    battery_soc: Any
    if portfolio.bess_enabled:
        battery_charge = cp.Variable(horizon, nonneg=True, name="bess_charge_kw")
        battery_discharge = cp.Variable(horizon, nonneg=True, name="bess_discharge_kw")
        battery_soc = cp.Variable(horizon + 1, name="bess_soc_kwh")
        constraints.extend(
            [
                battery_charge <= portfolio.bess_power_kw,
                battery_discharge <= portfolio.bess_power_kw,
                battery_soc >= 0.0,
                battery_soc <= portfolio.bess_energy_kwh,
                battery_soc[0]
                == portfolio.initial_soc_fraction * portfolio.bess_energy_kwh,
                battery_soc[-1]
                == portfolio.terminal_soc_fraction * portfolio.bess_energy_kwh,
                battery_soc[1:]
                == battery_soc[:-1]
                + portfolio.charge_efficiency * battery_charge * timestep_h
                - battery_discharge * timestep_h / portfolio.discharge_efficiency,
            ]
        )
        if portfolio.bess_dispatch_mode != "milp_exclusive":
            raise ValueError(
                "renewable-integration PV accounting requires milp_exclusive BESS dispatch"
            )
        charging_mode = cp.Variable(horizon, boolean=True, name="bess_charging_mode")
        constraints.extend(
            [
                battery_charge <= portfolio.bess_power_kw * charging_mode,
                battery_discharge <= portfolio.bess_power_kw * (1.0 - charging_mode),
            ]
        )
    else:
        battery_charge = np.zeros(horizon, dtype="float64")
        battery_discharge = np.zeros(horizon, dtype="float64")
        battery_soc = np.zeros(horizon + 1, dtype="float64")

    if dc_operation == "rigid":
        baseline_by_class = dict(snapshot.baseline_execution_gpu_h_by_class)
        execution_by_class = {
            job_class: scale * np.asarray(baseline_by_class[job_class], dtype="float64")
            for job_class in snapshot.workload_classes
        }
        missed: Any = float(snapshot.baseline_deadline_miss_gpu_h) * scale
        terminal_backlog: Any = float(snapshot.baseline_terminal_backlog_gpu_h) * scale
    else:
        edge_groups: list[int] = []
        edge_hours: list[int] = []
        edge_classes: list[str] = []
        for group_index, (release, deadline, job_class, _) in enumerate(snapshot.work_groups):
            for hour in range(release, min(deadline, horizon - 1) + 1):
                edge_groups.append(group_index)
                edge_hours.append(hour)
                edge_classes.append(job_class)
        if not edge_groups:
            raise ValueError("renewable-integration scenario has no schedulable flexible workload")
        edge_ids = np.arange(len(edge_groups), dtype="int64")
        group_incidence = sparse.coo_matrix(
            (np.ones(len(edge_groups)), (edge_groups, edge_ids)),
            shape=(len(snapshot.work_groups), len(edge_groups)),
        ).tocsr()
        time_incidence = sparse.coo_matrix(
            (np.ones(len(edge_groups)), (edge_hours, edge_ids)),
            shape=(horizon, len(edge_groups)),
        ).tocsr()
        served = cp.Variable(len(edge_groups), nonneg=True, name="served_gpu_h")
        missed = cp.Variable(len(snapshot.work_groups), nonneg=True, name="missed_gpu_h")
        terminal_backlog = cp.Variable(
            len(snapshot.work_groups), nonneg=True, name="terminal_backlog_gpu_h"
        )
        group_work = np.asarray(
            [group[3] for group in snapshot.work_groups], dtype="float64"
        )
        due = np.asarray(
            [group[1] < horizon for group in snapshot.work_groups], dtype=bool
        )
        execution_by_class = {
            job_class: time_incidence
            @ cp.multiply(  # type: ignore[attr-defined]
                np.asarray(
                    [value == job_class for value in edge_classes], dtype="float64"
                ),
                served,
            )
            for job_class in snapshot.workload_classes
        }
        execution = sum(execution_by_class.values())
        constraints.extend(
            [
                execution <= snapshot.capacity_gpu_h * scale,
                group_incidence @ served + missed + terminal_backlog == group_work * scale,
                cp.sum(missed)  # type: ignore[attr-defined]
                <= reward.max_deadline_miss_rate * snapshot.total_arrival_gpu_h * scale,
                cp.sum(terminal_backlog)  # type: ignore[attr-defined]
                <= (
                    snapshot.baseline_terminal_backlog_gpu_h
                    + reward.max_terminal_backlog_fraction * snapshot.total_arrival_gpu_h
                )
                * scale,
            ]
        )
        if bool((~due).any()):
            constraints.append(missed[~due] == 0.0)
        if bool(due.any()):
            constraints.append(terminal_backlog[due] == 0.0)

    dc_power = snapshot.fixed_dc_power_kw * scale + sum(
        dynamic_power_by_class[job_class] * execution_by_class[job_class]
        for job_class in snapshot.workload_classes
    )
    community_load = artifact.community["community_load_kw"].iloc[:horizon].to_numpy(
        dtype="float64"
    )
    pcc_power = community_load - pv_used + dc_power + battery_charge - battery_discharge
    constraints.append(pcc_power <= snapshot.pcc_capacity_kw)
    if portfolio.prohibit_export:
        constraints.append(pcc_power >= 0.0)

    return _RenewableProblem(
        cp=cp,
        constraints=constraints,
        pv_rated_kw=pv_capacity,
        pv_used_kw=pv_used,
        pv_available_kw=pv_available,
        pcc_power_kw=pcc_power,
        dc_power_kw=dc_power,
        battery_charge_kw=battery_charge,
        battery_discharge_kw=battery_discharge,
        battery_soc_kwh=battery_soc,
        missed_gpu_h=missed,
        terminal_backlog_gpu_h=terminal_backlog,
        snapshot=snapshot,
        total_arrival_gpu_h=snapshot.total_arrival_gpu_h * scale,
        community_load_kw=community_load,
    )


def _value_sum(value: Any) -> float:
    if hasattr(value, "value"):
        if value.value is None:
            return float("nan")
        return float(np.asarray(value.value, dtype="float64").sum())
    return float(np.asarray(value, dtype="float64").sum())


def _solution(
    model: _RenewableProblem,
    *,
    status: str,
    analysis: Literal["pv_hosting", "fixed_pv_operation"],
    dc_operation: Literal["rigid", "flexible"],
    portfolio: CommunityPortfolio,
    dc_scale_of_reference_mix: float,
    maximum_pv_curtailment_fraction: float | None,
    near_pcc_limit_fraction: float,
    solve_seconds: float,
) -> RenewableIntegrationSolution:
    snapshot = model.snapshot
    scale = dc_scale_of_reference_mix
    pv_rated_kw = _value_sum(model.pv_rated_kw)
    pv_available = _value_sum(model.pv_available_kw)
    pv_used = _value_sum(model.pv_used_kw)
    dc_energy = _value_sum(model.dc_power_kw)
    grid_import = _value_sum(model.pcc_power_kw)
    charge = _value_sum(model.battery_charge_kw)
    discharge = _value_sum(model.battery_discharge_kw)
    pcc_values = np.asarray(model.pcc_power_kw.value, dtype="float64")
    charge_values = (
        np.asarray(model.battery_charge_kw.value, dtype="float64")
        if hasattr(model.battery_charge_kw, "value")
        else np.asarray(model.battery_charge_kw, dtype="float64")
    )
    discharge_values = (
        np.asarray(model.battery_discharge_kw.value, dtype="float64")
        if hasattr(model.battery_discharge_kw, "value")
        else np.asarray(model.battery_discharge_kw, dtype="float64")
    )
    if hasattr(model.battery_soc_kwh, "value"):
        terminal_soc = float(np.asarray(model.battery_soc_kwh.value)[-1])
    else:
        terminal_soc = float(np.asarray(model.battery_soc_kwh)[-1])
    missed = _value_sum(model.missed_gpu_h)
    terminal_backlog = _value_sum(model.terminal_backlog_gpu_h)
    demand_energy = float(model.community_load_kw.sum()) + dc_energy
    curtailed = max(pv_available - pv_used, 0.0)
    return RenewableIntegrationSolution(
        status=status,
        analysis=analysis,
        dc_operation=dc_operation,
        bess_enabled=portfolio.bess_enabled,
        bess_dispatch_mode=portfolio.bess_dispatch_mode,
        pcc_capacity_kw=snapshot.pcc_capacity_kw,
        target_dc_peak_kw=scale * snapshot.reference_mix_operating_peak_kw,
        dc_scale_of_reference_mix=scale,
        reference_mix_operating_peak_kw=snapshot.reference_mix_operating_peak_kw,
        pv_rated_kw=pv_rated_kw,
        maximum_pv_curtailment_fraction=maximum_pv_curtailment_fraction,
        total_community_load_kwh=float(model.community_load_kw.sum()),
        total_dc_energy_kwh=dc_energy,
        total_pv_available_kwh=pv_available,
        total_pv_used_kwh=pv_used,
        total_pv_curtailed_kwh=curtailed,
        pv_utilisation_fraction=pv_used / max(pv_available, _TOLERANCE),
        renewable_demand_share=pv_used / max(demand_energy, _TOLERANCE),
        total_grid_import_kwh=grid_import,
        maximum_pcc_import_kw=float(pcc_values.max(initial=0.0)),
        hours_near_pcc_limit=int(
            np.count_nonzero(pcc_values >= near_pcc_limit_fraction * snapshot.pcc_capacity_kw)
        ),
        near_pcc_limit_fraction=near_pcc_limit_fraction,
        total_bess_charge_kwh=charge,
        total_bess_discharge_kwh=discharge,
        total_bess_throughput_kwh=charge + discharge,
        maximum_simultaneous_bess_charge_discharge_kw=float(
            np.minimum(charge_values, discharge_values).max(initial=0.0)
        ),
        terminal_soc_deviation_kwh=abs(
            terminal_soc - portfolio.terminal_soc_fraction * portfolio.bess_energy_kwh
        ),
        deadline_miss_gpu_h=missed,
        deadline_miss_fraction=missed / max(model.total_arrival_gpu_h, _TOLERANCE),
        terminal_backlog_gpu_h=terminal_backlog,
        terminal_backlog_fraction=terminal_backlog
        / max(model.total_arrival_gpu_h, _TOLERANCE),
        objective_solve_seconds=solve_seconds,
    )


def solve_curtailment_constrained_pv_hosting(
    artifact: FrozenHourlyScenario,
    *,
    portfolio: CommunityPortfolio,
    dc_operation: Literal["rigid", "flexible"],
    dc_scale_of_reference_mix: float,
    maximum_pv_curtailment_fraction: float,
    near_pcc_limit_fraction: float = 0.95,
) -> RenewableIntegrationSolution | None:
    """Maximize PV nameplate subject to an energy-curtailment ceiling."""

    _validate_fraction(maximum_pv_curtailment_fraction, "maximum_pv_curtailment_fraction")
    _validate_fraction(near_pcc_limit_fraction, "near_pcc_limit_fraction", allow_one=True)
    model = _build_problem(
        artifact,
        portfolio=portfolio,
        dc_operation=dc_operation,
        dc_scale_of_reference_mix=dc_scale_of_reference_mix,
        pv_rated_kw=None,
    )
    model.constraints.append(
        model.cp.sum(model.pv_available_kw - model.pv_used_kw)
        <= maximum_pv_curtailment_fraction * model.cp.sum(model.pv_available_kw)
    )
    problem = model.cp.Problem(model.cp.Maximize(model.pv_rated_kw), model.constraints)
    start = time.monotonic()
    status = _solve(problem, allow_infeasible=True)
    seconds = time.monotonic() - start
    if status in {"infeasible", "infeasible_inaccurate"}:
        return None
    return _solution(
        model,
        status=status,
        analysis="pv_hosting",
        dc_operation=dc_operation,
        portfolio=portfolio,
        dc_scale_of_reference_mix=dc_scale_of_reference_mix,
        maximum_pv_curtailment_fraction=maximum_pv_curtailment_fraction,
        near_pcc_limit_fraction=near_pcc_limit_fraction,
        solve_seconds=seconds,
    )


def solve_fixed_capacity_pv_operation(
    artifact: FrozenHourlyScenario,
    *,
    portfolio: CommunityPortfolio,
    dc_operation: Literal["rigid", "flexible"],
    dc_scale_of_reference_mix: float,
    pv_rated_kw: float,
    near_pcc_limit_fraction: float = 0.95,
    lexicographic_tolerance_kwh: float = 1e-5,
) -> RenewableIntegrationSolution:
    """Optimize fixed-capacity PV use, grid import and BESS throughput in order."""

    _validate_fraction(near_pcc_limit_fraction, "near_pcc_limit_fraction", allow_one=True)
    if not math.isfinite(lexicographic_tolerance_kwh) or lexicographic_tolerance_kwh <= 0.0:
        raise ValueError("lexicographic_tolerance_kwh must be positive")
    model = _build_problem(
        artifact,
        portfolio=portfolio,
        dc_operation=dc_operation,
        dc_scale_of_reference_mix=dc_scale_of_reference_mix,
        pv_rated_kw=pv_rated_kw,
    )
    start = time.monotonic()
    primary = model.cp.Problem(model.cp.Maximize(model.cp.sum(model.pv_used_kw)), model.constraints)
    status = _solve(primary)
    optimum_pv_used = _value_sum(model.pv_used_kw)
    model.constraints.append(
        model.cp.sum(model.pv_used_kw) >= optimum_pv_used - lexicographic_tolerance_kwh
    )
    secondary = model.cp.Problem(
        model.cp.Minimize(model.cp.sum(model.pcc_power_kw)), model.constraints
    )
    status = _solve(secondary)
    optimum_grid_import = _value_sum(model.pcc_power_kw)
    model.constraints.append(
        model.cp.sum(model.pcc_power_kw) <= optimum_grid_import + lexicographic_tolerance_kwh
    )
    throughput = model.cp.sum(model.battery_charge_kw) + model.cp.sum(
        model.battery_discharge_kw
    )
    tertiary = model.cp.Problem(model.cp.Minimize(throughput), model.constraints)
    status = _solve(tertiary)
    seconds = time.monotonic() - start
    return _solution(
        model,
        status=status,
        analysis="fixed_pv_operation",
        dc_operation=dc_operation,
        portfolio=portfolio,
        dc_scale_of_reference_mix=dc_scale_of_reference_mix,
        maximum_pv_curtailment_fraction=None,
        near_pcc_limit_fraction=near_pcc_limit_fraction,
        solve_seconds=seconds,
    )
