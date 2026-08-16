"""Frozen-scenario community hosting-capacity optimization.

This is an absolute-PCC planning model, not a DR-baseline calculation.  It
maximizes one shared data-centre scale over matched frozen scenarios while
making PV use/curtailment and battery state of charge explicit.  Operations
are perfect-information planning schedules, so outputs are planning bounds
rather than online-controller results.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
import pandas as pd
import yaml

from aidrbench.data.frozen_scenarios import FrozenHourlyScenario
from aidrbench.envs.community_ai_dr_env import HourlyPlanningSnapshot
from aidrbench.evaluation.non_anticipative import _discover_artifacts, _snapshot_for

_TOLERANCE = 1e-6


@dataclass(frozen=True, slots=True)
class CommunityPortfolio:
    """Physical DER assumptions expressed on stable kW/kWh bases."""

    pv_enabled: bool = False
    pv_rated_kw: float = 0.0
    bess_enabled: bool = False
    bess_power_kw: float = 0.0
    bess_energy_kwh: float = 0.0
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95
    initial_soc_fraction: float = 0.50
    terminal_soc_fraction: float = 0.50
    prohibit_export: bool = True
    bess_dispatch_mode: Literal["convex_relaxation", "milp_exclusive"] = "convex_relaxation"

    def __post_init__(self) -> None:
        for name, value in (
            ("pv_rated_kw", self.pv_rated_kw),
            ("bess_power_kw", self.bess_power_kw),
            ("bess_energy_kwh", self.bess_energy_kwh),
        ):
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and non-negative")
        for name, value in (
            ("charge_efficiency", self.charge_efficiency),
            ("discharge_efficiency", self.discharge_efficiency),
        ):
            if not math.isfinite(value) or not 0.0 < value <= 1.0:
                raise ValueError(f"{name} must be in (0, 1]")
        for name, value in (
            ("initial_soc_fraction", self.initial_soc_fraction),
            ("terminal_soc_fraction", self.terminal_soc_fraction),
        ):
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if self.pv_enabled != (self.pv_rated_kw > 0.0):
            raise ValueError("pv_enabled must agree with whether pv_rated_kw is positive")
        battery_sizes = (self.bess_power_kw, self.bess_energy_kwh)
        if self.bess_enabled != all(value > 0.0 for value in battery_sizes):
            raise ValueError(
                "bess_enabled requires both bess_power_kw and bess_energy_kwh to be positive"
            )
        if self.bess_dispatch_mode not in {"convex_relaxation", "milp_exclusive"}:
            raise ValueError("bess_dispatch_mode must be convex_relaxation or milp_exclusive")


@dataclass(frozen=True, slots=True)
class HostingCapacitySolution:
    """One portfolio's perfect-information absolute-PCC hosting bound."""

    status: str
    dc_operation: Literal["rigid", "flexible"]
    scenario_count: int
    pv_enabled: bool
    bess_enabled: bool
    bess_dispatch_mode: str
    pcc_capacity_kw: float
    reference_dc_peak_kw: float
    hosting_dc_peak_kw: float
    hosting_scale_of_reference: float
    minimum_background_gross_headroom_kw: float
    objective_solve_seconds: float
    maximum_pcc_power_kw: float
    total_pv_available_kwh: float
    total_pv_used_kwh: float
    total_pv_curtailed_kwh: float
    total_bess_charge_kwh: float
    total_bess_discharge_kwh: float
    maximum_simultaneous_bess_charge_discharge_kw: float
    terminal_soc_deviation_kwh: float

    def summary(self) -> dict[str, float | int | str | bool]:
        return {
            "capacity_layer": "perfect_information_hosting_bound",
            "hosting_status": self.status,
            "dc_operation": self.dc_operation,
            "scenario_count": self.scenario_count,
            "pv_enabled": self.pv_enabled,
            "bess_enabled": self.bess_enabled,
            "bess_dispatch_mode": self.bess_dispatch_mode,
            "pcc_capacity_kw": self.pcc_capacity_kw,
            "reference_dc_peak_kw": self.reference_dc_peak_kw,
            "hosting_dc_peak_kw": self.hosting_dc_peak_kw,
            "hosting_scale_of_reference": self.hosting_scale_of_reference,
            "minimum_background_gross_headroom_kw": self.minimum_background_gross_headroom_kw,
            "objective_solve_seconds": self.objective_solve_seconds,
            "maximum_pcc_power_kw": self.maximum_pcc_power_kw,
            "total_pv_available_kwh": self.total_pv_available_kwh,
            "total_pv_used_kwh": self.total_pv_used_kwh,
            "total_pv_curtailed_kwh": self.total_pv_curtailed_kwh,
            "total_bess_charge_kwh": self.total_bess_charge_kwh,
            "total_bess_discharge_kwh": self.total_bess_discharge_kwh,
            "maximum_simultaneous_bess_charge_discharge_kw": (
                self.maximum_simultaneous_bess_charge_discharge_kw
            ),
            "terminal_soc_deviation_kwh": self.terminal_soc_deviation_kwh,
        }


def _as_positive(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be positive")
    return result


def _as_non_negative(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


def load_community_portfolio(path: str | Path) -> CommunityPortfolio:
    """Read an explicit PV/BESS portfolio YAML document."""

    document = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise ValueError("community portfolio must be a YAML mapping")
    raw_pv = document.get("pv", {})
    raw_bess = document.get("bess", {})
    if not isinstance(raw_pv, Mapping) or not isinstance(raw_bess, Mapping):
        raise ValueError("community portfolio pv and bess entries must be mappings")
    pv_enabled = bool(raw_pv.get("enabled", False))
    bess_enabled = bool(raw_bess.get("enabled", False))
    raw_dispatch_mode = raw_bess.get("dispatch_mode", "convex_relaxation")
    if (
        not isinstance(raw_dispatch_mode, str)
        or raw_dispatch_mode not in {"convex_relaxation", "milp_exclusive"}
    ):
        raise ValueError("bess.dispatch_mode must be convex_relaxation or milp_exclusive")
    return CommunityPortfolio(
        pv_enabled=pv_enabled,
        pv_rated_kw=_as_non_negative(raw_pv.get("rated_capacity_kw", 0.0), "pv.rated_capacity_kw"),
        bess_enabled=bess_enabled,
        bess_power_kw=_as_non_negative(
            raw_bess.get("power_capacity_kw", 0.0), "bess.power_capacity_kw"
        ),
        bess_energy_kwh=_as_non_negative(
            raw_bess.get("energy_capacity_kwh", 0.0), "bess.energy_capacity_kwh"
        ),
        charge_efficiency=_as_positive(
            raw_bess.get("charge_efficiency", 0.95), "bess.charge_efficiency"
        ),
        discharge_efficiency=_as_positive(
            raw_bess.get("discharge_efficiency", 0.95), "bess.discharge_efficiency"
        ),
        initial_soc_fraction=_as_non_negative(
            raw_bess.get("initial_soc_fraction", 0.50), "bess.initial_soc_fraction"
        ),
        terminal_soc_fraction=_as_non_negative(
            raw_bess.get("terminal_soc_fraction", 0.50), "bess.terminal_soc_fraction"
        ),
        prohibit_export=bool(document.get("prohibit_export", True)),
        bess_dispatch_mode=cast(
            Literal["convex_relaxation", "milp_exclusive"], raw_dispatch_mode
        ),
    )


def _solve(problem: Any) -> None:
    try:
        problem.solve(solver="HIGHS")
    except ImportError as exc:
        raise RuntimeError("hosting-capacity optimization requires control dependencies") from exc
    if problem.status not in {"optimal", "optimal_inaccurate"}:
        raise RuntimeError(f"hosting-capacity optimization did not solve: {problem.status}")


def _assert_common_physics(snapshots: Sequence[HourlyPlanningSnapshot]) -> None:
    if not snapshots:
        raise ValueError("hosting-capacity optimization needs at least one scenario")
    reference = snapshots[0]
    fields = ("total_hours", "capacity_gpu_h", "fixed_dc_power_kw", "dynamic_kw_per_gpu_h")
    for snapshot in snapshots[1:]:
        for field in fields:
            if not math.isclose(
                float(getattr(snapshot, field)), float(getattr(reference, field)), abs_tol=1e-9
            ):
                raise ValueError("hosting scenarios must share one data-centre physical model")
        if not math.isclose(snapshot.pcc_capacity_kw, reference.pcc_capacity_kw, abs_tol=1e-9):
            raise ValueError("hosting scenarios must share one PCC capacity")


def _pv_profile_kw(artifact: FrozenHourlyScenario, *, rated_kw: float, horizon: int) -> np.ndarray:
    potential = artifact.community["pv_generation_kw"].iloc[:horizon].to_numpy(dtype="float64")
    peak = float(potential.max(initial=0.0))
    if peak <= _TOLERANCE:
        raise ValueError(
            "the frozen scenario contains no PV potential; freeze it from a PV-enabled profile"
        )
    return potential * (rated_kw / peak)


def solve_frozen_hosting_capacity(
    artifacts: Sequence[FrozenHourlyScenario],
    *,
    portfolio: CommunityPortfolio,
    dc_operation: Literal["rigid", "flexible"],
) -> HostingCapacitySolution:
    """Maximize a shared DC capacity scale over matched frozen scenarios.

    For ``rigid``, each workload realization follows its frozen no-control
    execution profile. For ``flexible``, fluid work can be rescheduled subject
    to release, deadline-miss and terminal-backlog requirements. PV and BESS
    dispatch remain scenario-specific perfect-information planning variables.
    """

    if dc_operation not in {"rigid", "flexible"}:
        raise ValueError("dc_operation must be 'rigid' or 'flexible'")
    if not artifacts:
        raise ValueError("hosting-capacity optimization needs at least one frozen scenario")
    if len({artifact.scenario_hash for artifact in artifacts}) != len(artifacts):
        raise ValueError("hosting scenarios must have unique hashes")
    try:
        import cvxpy as cp
        from scipy import sparse  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("hosting-capacity optimization requires control dependencies") from exc

    pairs = [_snapshot_for(artifact, duration_h=1, event_id=0) for artifact in artifacts]
    snapshots = [pair[0] for pair in pairs]
    rewards = [pair[1] for pair in pairs]
    _assert_common_physics(snapshots)
    if any(reward != rewards[0] for reward in rewards[1:]):
        raise ValueError("hosting scenarios must share one service specification")
    snapshot = snapshots[0]
    reward = rewards[0]
    horizon = snapshot.total_hours
    timestep_h = 1.0
    reference_dc_peak_kw = (
        snapshot.fixed_dc_power_kw + snapshot.dynamic_kw_per_gpu_h * snapshot.capacity_gpu_h
    )
    scale = cp.Variable(nonneg=True, name="dc_scale_of_reference")
    constraints: list[Any] = []
    pcc_expressions: list[Any] = []
    pv_available_kwh = 0.0
    pv_used: list[Any] = []
    charge: list[Any] = []
    discharge: list[Any] = []
    terminal_soc: list[Any] = []

    for scenario_index, (artifact, scenario) in enumerate(zip(artifacts, snapshots, strict=True)):
        community_gross = artifact.community["community_load_kw"].iloc[:horizon].to_numpy(
            dtype="float64"
        )
        if portfolio.pv_enabled:
            pv_available_kw = _pv_profile_kw(
                artifact,
                rated_kw=portfolio.pv_rated_kw,
                horizon=horizon,
            )
        else:
            pv_available_kw = np.zeros(horizon, dtype="float64")
        pv_available_kwh += float(pv_available_kw.sum() * timestep_h)
        pv_dispatch = cp.Variable(horizon, nonneg=True, name=f"pv_used_kw_s{scenario_index}")
        constraints.append(pv_dispatch <= pv_available_kw)
        pv_used.append(pv_dispatch)

        battery_charge: Any
        battery_discharge: Any
        soc: Any
        if portfolio.bess_enabled:
            battery_charge = cp.Variable(
                horizon, nonneg=True, name=f"bess_charge_kw_s{scenario_index}"
            )
            battery_discharge = cp.Variable(
                horizon, nonneg=True, name=f"bess_discharge_kw_s{scenario_index}"
            )
            soc = cp.Variable(horizon + 1, name=f"bess_soc_kwh_s{scenario_index}")
            constraints.extend(
                [
                    battery_charge <= portfolio.bess_power_kw,
                    battery_discharge <= portfolio.bess_power_kw,
                    soc >= 0.0,
                    soc <= portfolio.bess_energy_kwh,
                    soc[0] == portfolio.initial_soc_fraction * portfolio.bess_energy_kwh,
                    soc[-1] == portfolio.terminal_soc_fraction * portfolio.bess_energy_kwh,
                    soc[1:]
                    == soc[:-1]
                    + portfolio.charge_efficiency * battery_charge * timestep_h
                    - battery_discharge * timestep_h / portfolio.discharge_efficiency,
                ]
            )
            if portfolio.bess_dispatch_mode == "milp_exclusive":
                battery_charging = cp.Variable(
                    horizon, boolean=True, name=f"bess_charging_mode_s{scenario_index}"
                )
                constraints.extend(
                    [
                        battery_charge <= portfolio.bess_power_kw * battery_charging,
                        battery_discharge
                        <= portfolio.bess_power_kw * (1.0 - battery_charging),
                    ]
                )
        else:
            battery_charge = np.zeros(horizon, dtype="float64")
            battery_discharge = np.zeros(horizon, dtype="float64")
            soc = np.zeros(horizon + 1, dtype="float64")
        charge.append(battery_charge)
        discharge.append(battery_discharge)
        terminal_soc.append(soc[-1])

        if dc_operation == "rigid":
            execution = scale * np.asarray(scenario.baseline_execution_gpu_h, dtype="float64")
        else:
            groups = scenario.work_groups
            edge_groups: list[int] = []
            edge_hours: list[int] = []
            for group_index, (release, deadline, _) in enumerate(groups):
                for hour in range(release, min(deadline, horizon - 1) + 1):
                    edge_groups.append(group_index)
                    edge_hours.append(hour)
            if not edge_groups:
                raise ValueError("hosting scenario has no schedulable flexible workload")
            edge_ids = np.arange(len(edge_groups), dtype="int64")
            group_incidence = sparse.coo_matrix(
                (np.ones(len(edge_groups)), (edge_groups, edge_ids)),
                shape=(len(groups), len(edge_groups)),
            ).tocsr()
            time_incidence = sparse.coo_matrix(
                (np.ones(len(edge_groups)), (edge_hours, edge_ids)),
                shape=(horizon, len(edge_groups)),
            ).tocsr()
            served = cp.Variable(
                len(edge_groups), nonneg=True, name=f"served_gpu_h_s{scenario_index}"
            )
            missed = cp.Variable(len(groups), nonneg=True, name=f"missed_gpu_h_s{scenario_index}")
            remaining = cp.Variable(
                len(groups), nonneg=True, name=f"terminal_backlog_gpu_h_s{scenario_index}"
            )
            group_work = np.asarray([group[2] for group in groups], dtype="float64")
            due = np.asarray([group[1] < horizon for group in groups], dtype=bool)
            execution = time_incidence @ served
            constraints.extend(
                [
                    execution <= scenario.capacity_gpu_h * scale,
                    group_incidence @ served + missed + remaining == group_work * scale,
                    cp.sum(missed)  # type: ignore[attr-defined]
                    <= reward.max_deadline_miss_rate * scenario.total_arrival_gpu_h * scale,
                    cp.sum(remaining)  # type: ignore[attr-defined]
                    <= (
                        scenario.baseline_terminal_backlog_gpu_h
                        + reward.max_terminal_backlog_fraction * scenario.total_arrival_gpu_h
                    )
                    * scale,
                ]
            )
            if bool((~due).any()):
                constraints.append(missed[~due] == 0.0)
            if bool(due.any()):
                constraints.append(remaining[due] == 0.0)

        dc_power = snapshot.fixed_dc_power_kw * scale + snapshot.dynamic_kw_per_gpu_h * execution
        pcc_power = community_gross - pv_dispatch + dc_power + battery_charge - battery_discharge
        constraints.append(pcc_power <= snapshot.pcc_capacity_kw)
        if portfolio.prohibit_export:
            constraints.append(pcc_power >= 0.0)
        pcc_expressions.append(pcc_power)

    problem = cp.Problem(cp.Maximize(scale * reference_dc_peak_kw), constraints)
    solve_start = time.monotonic()
    _solve(problem)
    solve_seconds = time.monotonic() - solve_start
    if scale.value is None:
        raise RuntimeError("hosting-capacity optimization returned no data-centre scale")
    scale_value = max(float(np.asarray(scale.value).item()), 0.0)
    pcc_values = [np.asarray(expression.value, dtype="float64") for expression in pcc_expressions]
    pv_used_kwh = sum(float(np.asarray(value.value, dtype="float64").sum()) for value in pv_used)
    charge_kwh = sum(
        float(np.asarray(value.value, dtype="float64").sum())
        if hasattr(value, "value") and value.value is not None
        else 0.0
        for value in charge
    )
    discharge_kwh = sum(
        float(np.asarray(value.value, dtype="float64").sum())
        if hasattr(value, "value") and value.value is not None
        else 0.0
        for value in discharge
    )
    simultaneous_charge_discharge_kw = max(
        (
            float(
                np.minimum(
                    np.asarray(charge_value.value, dtype="float64"),
                    np.asarray(discharge_value.value, dtype="float64"),
                ).max(initial=0.0)
            )
            if hasattr(charge_value, "value")
            and hasattr(discharge_value, "value")
            and charge_value.value is not None
            and discharge_value.value is not None
            else 0.0
        )
        for charge_value, discharge_value in zip(charge, discharge, strict=True)
    )
    terminal_deviation = sum(
        abs(
            float(np.asarray(value.value).item())
            - portfolio.terminal_soc_fraction * portfolio.bess_energy_kwh
        )
        if hasattr(value, "value") and value.value is not None
        else 0.0
        for value in terminal_soc
    )
    background_minimum = min(
        float(artifact.community["community_load_kw"].iloc[:horizon].min())
        for artifact in artifacts
    )
    return HostingCapacitySolution(
        status=str(problem.status),
        dc_operation=dc_operation,
        scenario_count=len(artifacts),
        pv_enabled=portfolio.pv_enabled,
        bess_enabled=portfolio.bess_enabled,
        bess_dispatch_mode=portfolio.bess_dispatch_mode,
        pcc_capacity_kw=snapshot.pcc_capacity_kw,
        reference_dc_peak_kw=reference_dc_peak_kw,
        hosting_dc_peak_kw=scale_value * reference_dc_peak_kw,
        hosting_scale_of_reference=scale_value,
        minimum_background_gross_headroom_kw=max(
            snapshot.pcc_capacity_kw - background_minimum, 0.0
        ),
        objective_solve_seconds=solve_seconds,
        maximum_pcc_power_kw=max(float(values.max()) for values in pcc_values),
        total_pv_available_kwh=pv_available_kwh,
        total_pv_used_kwh=pv_used_kwh,
        total_pv_curtailed_kwh=max(pv_available_kwh - pv_used_kwh, 0.0),
        total_bess_charge_kwh=charge_kwh,
        total_bess_discharge_kwh=discharge_kwh,
        maximum_simultaneous_bess_charge_discharge_kw=simultaneous_charge_discharge_kw,
        terminal_soc_deviation_kwh=terminal_deviation,
    )


def compute_and_save_hosting_capacity(
    scenario_path: str | Path,
    *,
    portfolio: CommunityPortfolio,
    output_directory: str | Path,
    dc_operation: Literal["rigid", "flexible", "matrix"] = "matrix",
) -> dict[str, str | int]:
    """Compute declared rigid/flexible and DER portfolio hosting bounds."""

    artifacts = _discover_artifacts(scenario_path)
    combinations: list[tuple[bool, bool, Literal["rigid", "flexible"]]] = []
    if dc_operation == "matrix":
        operations: tuple[Literal["rigid", "flexible"], ...] = ("rigid", "flexible")
    elif dc_operation == "rigid":
        operations = ("rigid",)
    elif dc_operation == "flexible":
        operations = ("flexible",)
    else:
        raise ValueError("dc_operation must be 'rigid', 'flexible', or 'matrix'")
    pv_choices = (False, True) if dc_operation == "matrix" else (portfolio.pv_enabled,)
    bess_choices = (False, True) if dc_operation == "matrix" else (portfolio.bess_enabled,)
    for pv_enabled in pv_choices:
        for bess_enabled in bess_choices:
            for operation in operations:
                combinations.append((pv_enabled, bess_enabled, operation))
    solutions: list[HostingCapacitySolution] = []
    for pv_enabled, bess_enabled, operation in combinations:
        candidate = CommunityPortfolio(
            pv_enabled=pv_enabled,
            pv_rated_kw=portfolio.pv_rated_kw if pv_enabled else 0.0,
            bess_enabled=bess_enabled,
            bess_power_kw=portfolio.bess_power_kw if bess_enabled else 0.0,
            bess_energy_kwh=portfolio.bess_energy_kwh if bess_enabled else 0.0,
            charge_efficiency=portfolio.charge_efficiency,
            discharge_efficiency=portfolio.discharge_efficiency,
            initial_soc_fraction=portfolio.initial_soc_fraction,
            terminal_soc_fraction=portfolio.terminal_soc_fraction,
            prohibit_export=portfolio.prohibit_export,
            bess_dispatch_mode=portfolio.bess_dispatch_mode,
        )
        solutions.append(
            solve_frozen_hosting_capacity(
                artifacts,
                portfolio=candidate,
                dc_operation=operation,
            )
        )
    result = pd.DataFrame.from_records([solution.summary() for solution in solutions])
    result["hosting_capacity_gain_vs_rigid_kw"] = np.nan
    result["hosting_capacity_multiplier_vs_rigid"] = np.nan
    for _, index in result.groupby(["pv_enabled", "bess_enabled"], sort=False).groups.items():
        group = result.loc[index]
        rigid = group.loc[group["dc_operation"] == "rigid", "hosting_dc_peak_kw"]
        if rigid.empty:
            continue
        rigid_capacity_kw = float(rigid.iloc[0])
        result.loc[index, "hosting_capacity_gain_vs_rigid_kw"] = (
            result.loc[index, "hosting_dc_peak_kw"] - rigid_capacity_kw
        )
        result.loc[index, "hosting_capacity_multiplier_vs_rigid"] = (
            result.loc[index, "hosting_dc_peak_kw"] / max(rigid_capacity_kw, _TOLERANCE)
        )
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    result_path = output / "hosting_capacity.parquet"
    manifest_path = output / "hosting_capacity.json"
    result.to_parquet(result_path, index=False)
    manifest_path.write_text(
        json.dumps(
            {
                "capacity_layer": "perfect_information_hosting_bound",
                "scenario_count": len(artifacts),
                "scenario_hashes": [artifact.scenario_hash for artifact in artifacts],
                "requested_dc_operation": dc_operation,
                "bess_dispatch_model": portfolio.bess_dispatch_mode,
                "portfolio": {
                    "pv_enabled": portfolio.pv_enabled,
                    "pv_rated_kw": portfolio.pv_rated_kw,
                    "bess_enabled": portfolio.bess_enabled,
                    "bess_power_kw": portfolio.bess_power_kw,
                    "bess_energy_kwh": portfolio.bess_energy_kwh,
                    "charge_efficiency": portfolio.charge_efficiency,
                    "discharge_efficiency": portfolio.discharge_efficiency,
                    "initial_soc_fraction": portfolio.initial_soc_fraction,
                    "terminal_soc_fraction": portfolio.terminal_soc_fraction,
                    "prohibit_export": portfolio.prohibit_export,
                    "bess_dispatch_mode": portfolio.bess_dispatch_mode,
                },
                "result": str(result_path),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "scenario_count": len(artifacts),
        "row_count": len(result),
        "result": str(result_path),
        "manifest": str(manifest_path),
    }
