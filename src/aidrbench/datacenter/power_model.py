"""Gray-box node response used between measured P2 curves and the P3 fleet."""

from __future__ import annotations

from dataclasses import dataclass

from aidrbench.datacenter.hardware import EvidenceClass


def _validate_fraction(value: float, name: str, *, allow_zero: bool = False) -> None:
    lower_ok = value >= 0.0 if allow_zero else value > 0.0
    if not lower_ok or value > 1.0:
        interval = "[0, 1]" if allow_zero else "(0, 1]"
        raise ValueError(f"{name} must be in {interval}")


def _interpolate(xs: tuple[float, ...], ys: tuple[float, ...], x: float) -> float:
    if x < xs[0] or x > xs[-1]:
        raise ValueError(f"cap ratio {x:g} is outside the calibrated range [{xs[0]}, {xs[-1]}]")
    for index, right in enumerate(xs):
        if x == right:
            return ys[index]
        if x < right:
            left = xs[index - 1]
            weight = (x - left) / (right - left)
            return ys[index - 1] + weight * (ys[index] - ys[index - 1])
    return ys[-1]


@dataclass(frozen=True, slots=True)
class ResponsePoint:
    """Normalized node response at one cap ratio."""

    dynamic_power_ratio: float
    service_ratio: float
    latency_ratio: float


@dataclass(frozen=True, slots=True)
class ControlResponseCurve:
    """Measured or benchmark-anchored response ratios over safe power caps."""

    cap_ratios: tuple[float, ...]
    dynamic_power_ratios: tuple[float, ...]
    service_ratios: tuple[float, ...]
    latency_ratios: tuple[float, ...]
    evidence_class: EvidenceClass
    source: str

    def __post_init__(self) -> None:
        lengths = {
            len(self.cap_ratios),
            len(self.dynamic_power_ratios),
            len(self.service_ratios),
            len(self.latency_ratios),
        }
        if lengths == {0} or len(lengths) != 1:
            raise ValueError("response-curve arrays must have the same non-zero length")
        if tuple(sorted(self.cap_ratios)) != self.cap_ratios:
            raise ValueError("cap_ratios must be sorted")
        if len(set(self.cap_ratios)) != len(self.cap_ratios):
            raise ValueError("cap_ratios must be unique")
        for cap_ratio in self.cap_ratios:
            _validate_fraction(cap_ratio, "cap ratio")
        for value in self.dynamic_power_ratios:
            _validate_fraction(value, "dynamic power ratio", allow_zero=True)
        for value in self.service_ratios:
            _validate_fraction(value, "service ratio", allow_zero=True)
        for value in self.latency_ratios:
            if value <= 0.0:
                raise ValueError("latency ratios must be positive")
        if not self.source.strip():
            raise ValueError("response curve source must not be empty")

    def at(self, cap_ratio: float) -> ResponsePoint:
        """Interpolate only inside the calibrated cap range."""

        return ResponsePoint(
            dynamic_power_ratio=_interpolate(
                self.cap_ratios, self.dynamic_power_ratios, cap_ratio
            ),
            service_ratio=_interpolate(self.cap_ratios, self.service_ratios, cap_ratio),
            latency_ratio=_interpolate(self.cap_ratios, self.latency_ratios, cap_ratio),
        )


@dataclass(frozen=True, slots=True)
class NodeOperatingBaseline:
    """Default-cap measurements for one concrete node and serving workload."""

    host_idle_power_w: float
    inference_gpu_count: int
    batch_gpu_count: int
    inference_gpu_idle_power_w: float
    batch_gpu_idle_power_w: float
    inference_gpu_dynamic_power_w: float
    batch_gpu_dynamic_power_w: float
    inference_capacity_per_second: float
    batch_capacity_per_gpu_second: float
    ttft_p99_ms: float
    tpot_p99_ms: float
    load_power_exponent: float
    evidence_class: EvidenceClass
    source: str

    def __post_init__(self) -> None:
        numeric_values = (
            self.host_idle_power_w,
            self.inference_gpu_idle_power_w,
            self.batch_gpu_idle_power_w,
            self.inference_gpu_dynamic_power_w,
            self.batch_gpu_dynamic_power_w,
            self.inference_capacity_per_second,
            self.batch_capacity_per_gpu_second,
            self.ttft_p99_ms,
            self.tpot_p99_ms,
            self.load_power_exponent,
        )
        if any(value < 0.0 for value in numeric_values):
            raise ValueError("node baseline numeric values must be non-negative")
        if self.inference_gpu_count <= 0 or self.batch_gpu_count < 0:
            raise ValueError("node GPU counts are invalid")
        if self.load_power_exponent <= 0.0:
            raise ValueError("load_power_exponent must be positive")
        if not self.source.strip():
            raise ValueError("node baseline source must not be empty")


@dataclass(frozen=True, slots=True)
class NodeControlInput:
    """One instantaneous node demand/action pair."""

    inference_demand_per_second: float
    batch_demand_per_second: float
    inference_cap_ratio: float
    batch_cap_ratio: float
    active_batch_gpus: int


@dataclass(frozen=True, slots=True)
class NodePrediction:
    """Raw quantities consumed by RL, MPC, and rule-based backends."""

    power_w: float
    inference_capacity_per_second: float
    inference_served_per_second: float
    inference_unserved_per_second: float
    batch_capacity_per_second: float
    batch_served_per_second: float
    batch_unserved_per_second: float
    ttft_p99_ms: float
    tpot_p99_ms: float
    inference_utilization: float
    batch_utilization: float
    evidence_chain: tuple[str, ...]


def predict_node_response(
    baseline: NodeOperatingBaseline,
    inference_curve: ControlResponseCurve,
    batch_curve: ControlResponseCurve,
    control: NodeControlInput,
) -> NodePrediction:
    """Predict one node without extrapolating beyond measured cap ratios."""

    if control.inference_demand_per_second < 0.0 or control.batch_demand_per_second < 0.0:
        raise ValueError("node demands must be non-negative")
    if not 0 <= control.active_batch_gpus <= baseline.batch_gpu_count:
        raise ValueError("active_batch_gpus is outside the node topology")
    inference = inference_curve.at(control.inference_cap_ratio)
    batch = batch_curve.at(control.batch_cap_ratio)

    inference_capacity = baseline.inference_capacity_per_second * inference.service_ratio
    batch_capacity = (
        control.active_batch_gpus
        * baseline.batch_capacity_per_gpu_second
        * batch.service_ratio
    )
    inference_served = min(control.inference_demand_per_second, inference_capacity)
    batch_served = min(control.batch_demand_per_second, batch_capacity)
    inference_utilization = (
        inference_served / inference_capacity if inference_capacity > 0.0 else 0.0
    )
    batch_utilization = batch_served / batch_capacity if batch_capacity > 0.0 else 0.0

    inference_power = baseline.inference_gpu_count * (
        baseline.inference_gpu_idle_power_w
        + baseline.inference_gpu_dynamic_power_w
        * inference.dynamic_power_ratio
        * inference_utilization**baseline.load_power_exponent
    )
    batch_idle_power = baseline.batch_gpu_count * baseline.batch_gpu_idle_power_w
    batch_dynamic_power = (
        control.active_batch_gpus
        * baseline.batch_gpu_dynamic_power_w
        * batch.dynamic_power_ratio
        * batch_utilization**baseline.load_power_exponent
    )
    return NodePrediction(
        power_w=(
            baseline.host_idle_power_w
            + inference_power
            + batch_idle_power
            + batch_dynamic_power
        ),
        inference_capacity_per_second=inference_capacity,
        inference_served_per_second=inference_served,
        inference_unserved_per_second=max(
            control.inference_demand_per_second - inference_served, 0.0
        ),
        batch_capacity_per_second=batch_capacity,
        batch_served_per_second=batch_served,
        batch_unserved_per_second=max(control.batch_demand_per_second - batch_served, 0.0),
        ttft_p99_ms=baseline.ttft_p99_ms * inference.latency_ratio,
        tpot_p99_ms=baseline.tpot_p99_ms * inference.latency_ratio,
        inference_utilization=inference_utilization,
        batch_utilization=batch_utilization,
        evidence_chain=(
            baseline.evidence_class.value,
            inference_curve.evidence_class.value,
            batch_curve.evidence_class.value,
        ),
    )
