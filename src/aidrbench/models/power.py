"""Run-level GPU-energy calibrated hourly data-center power model."""

from __future__ import annotations

import math
from dataclasses import dataclass


def _positive(value: float, name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be positive")
    return result


def _fraction(value: float, name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be in [0, 1]")
    return result


@dataclass(frozen=True, slots=True)
class VirtualDataCenter:
    """Homogeneous virtual cluster derived from one calibrated GPU node."""

    gpus_per_node: int
    node_count: int
    flexible_gpu_fraction: float

    def __post_init__(self) -> None:
        if isinstance(self.gpus_per_node, bool) or self.gpus_per_node <= 0:
            raise ValueError("gpus_per_node must be positive")
        if isinstance(self.node_count, bool) or self.node_count <= 0:
            raise ValueError("node_count must be positive")
        _fraction(self.flexible_gpu_fraction, "flexible_gpu_fraction")
        if self.flexible_gpu_count <= 0:
            raise ValueError("virtual data center must contain at least one flexible GPU")

    @property
    def total_gpu_count(self) -> int:
        return self.gpus_per_node * self.node_count

    @property
    def flexible_gpu_count(self) -> int:
        return int(round(self.total_gpu_count * self.flexible_gpu_fraction))

    @property
    def rigid_gpu_count(self) -> int:
        return self.total_gpu_count - self.flexible_gpu_count


@dataclass(frozen=True, slots=True)
class HourlyPowerPrediction:
    """IT/facility power for one hour after choosing flexible execution."""

    active_flexible_gpus: float
    rigid_it_power_kw: float
    flexible_it_power_kw: float
    dc_power_kw: float
    flexible_energy_kwh: float
    dc_energy_kwh: float


@dataclass(frozen=True, slots=True)
class HourlyDataCenterPowerModel:
    """V0 average-power model; no power-cap or temperature state is included."""

    data_center: VirtualDataCenter
    idle_power_w_per_gpu: float
    flexible_active_power_w_per_gpu: float
    rigid_active_power_w_per_gpu: float
    node_fixed_overhead_w: float
    rigid_gpu_utilization: float
    pue: float

    def __post_init__(self) -> None:
        _positive(self.idle_power_w_per_gpu, "idle_power_w_per_gpu")
        _positive(self.flexible_active_power_w_per_gpu, "flexible_active_power_w_per_gpu")
        _positive(self.rigid_active_power_w_per_gpu, "rigid_active_power_w_per_gpu")
        _positive(self.node_fixed_overhead_w, "node_fixed_overhead_w")
        _fraction(self.rigid_gpu_utilization, "rigid_gpu_utilization")
        if self.flexible_active_power_w_per_gpu < self.idle_power_w_per_gpu:
            raise ValueError("flexible active power must be at least idle power")
        if self.rigid_active_power_w_per_gpu < self.idle_power_w_per_gpu:
            raise ValueError("rigid active power must be at least idle power")
        if self.pue < 1.0:
            raise ValueError("pue must be at least 1.0")

    @property
    def flexible_capacity_gpu_h(self) -> float:
        return float(self.data_center.flexible_gpu_count)

    @property
    def flexible_active_energy_per_gpu_h_kwh(self) -> float:
        """Facility-equivalent energy needed to complete one flexible GPU-hour.

        This is the workload-energy coefficient used to express queued work as
        compute debt.  It deliberately excludes the always-on idle pool: that
        pool is not an additional future service obligation created by a
        deferred job.
        """

        return self.pue * self.flexible_active_power_w_per_gpu / 1_000.0

    @property
    def rigid_it_power_kw(self) -> float:
        rigid_gpu_power_w = self.data_center.rigid_gpu_count * (
            self.idle_power_w_per_gpu
            + self.rigid_gpu_utilization
            * (self.rigid_active_power_w_per_gpu - self.idle_power_w_per_gpu)
        )
        fixed_power_w = self.data_center.node_count * self.node_fixed_overhead_w
        return (rigid_gpu_power_w + fixed_power_w) / 1_000.0

    def predict(
        self, executed_gpu_h: float, *, timestep_hours: float = 1.0
    ) -> HourlyPowerPrediction:
        """Map completed flexible GPU-hours to mean power and integrated energy."""

        duration = _positive(timestep_hours, "timestep_hours")
        executed = float(executed_gpu_h)
        if not math.isfinite(executed) or executed < 0.0:
            raise ValueError("executed_gpu_h must be finite and non-negative")
        capacity = self.flexible_capacity_gpu_h * duration
        if executed > capacity + 1e-9:
            raise ValueError("executed_gpu_h exceeds flexible pool capacity")
        active_flexible_gpus = executed / duration
        flexible_power_w = self.data_center.flexible_gpu_count * self.idle_power_w_per_gpu
        flexible_power_w += active_flexible_gpus * (
            self.flexible_active_power_w_per_gpu - self.idle_power_w_per_gpu
        )
        flexible_it_power_kw = flexible_power_w / 1_000.0
        rigid_it_power_kw = self.rigid_it_power_kw
        dc_power_kw = self.pue * (rigid_it_power_kw + flexible_it_power_kw)
        return HourlyPowerPrediction(
            active_flexible_gpus=active_flexible_gpus,
            rigid_it_power_kw=rigid_it_power_kw,
            flexible_it_power_kw=flexible_it_power_kw,
            dc_power_kw=dc_power_kw,
            flexible_energy_kwh=flexible_it_power_kw * duration,
            dc_energy_kwh=dc_power_kw * duration,
        )
