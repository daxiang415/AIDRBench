"""Capacity planning and homogeneous virtual-fleet aggregation."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from aidrbench.datacenter.hardware import (
    ComputeWorkload,
    EvidenceClass,
    GpuHardwareProfile,
    compute_workload_from_mapping,
    estimate_roofline_capacity,
    load_gpu_profile,
)
from aidrbench.datacenter.power_model import (
    ControlResponseCurve,
    NodeControlInput,
    NodeOperatingBaseline,
    NodePrediction,
    predict_node_response,
)


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _positive_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be a number")
    result = float(value)
    if result <= 0.0:
        raise ValueError(f"{name} must be positive")
    return result


def _optional_positive_float(value: object, name: str) -> float | None:
    if value is None:
        return None
    return _positive_float(value, name)


def _positive_int(value: object, name: str, *, allow_zero: bool = False) -> int:
    minimum = 0 if allow_zero else 1
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{name} must be a {qualifier} integer")
    return value


def _string_sequence(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    return tuple(_text(item, f"{name} entry") for item in value)


@dataclass(frozen=True, slots=True)
class NodeTopology:
    """Virtual node layout shared by all candidates in one comparison."""

    gpus_per_node: int
    inference_gpus_per_node: int
    batch_gpus_per_node: int
    host_nameplate_power_w: float

    def __post_init__(self) -> None:
        if self.gpus_per_node <= 0 or self.inference_gpus_per_node <= 0:
            raise ValueError("node and inference GPU counts must be positive")
        if self.batch_gpus_per_node < 0:
            raise ValueError("batch_gpus_per_node must be non-negative")
        if self.inference_gpus_per_node + self.batch_gpus_per_node != self.gpus_per_node:
            raise ValueError("inference and batch GPU counts must sum to gpus_per_node")
        if self.host_nameplate_power_w <= 0.0:
            raise ValueError("host_nameplate_power_w must be positive")


@dataclass(frozen=True, slots=True)
class CapacityRequest:
    """Power and optional service constraints for a virtual data center."""

    it_power_budget_mw: float
    target_inference_work_units_per_second: float | None
    safe_utilization: float
    pue: float

    def __post_init__(self) -> None:
        if self.it_power_budget_mw <= 0.0:
            raise ValueError("it_power_budget_mw must be positive")
        if (
            self.target_inference_work_units_per_second is not None
            and self.target_inference_work_units_per_second <= 0.0
        ):
            raise ValueError("target inference work must be positive when supplied")
        if not 0.0 < self.safe_utilization <= 1.0:
            raise ValueError("safe_utilization must be in (0, 1]")
        if self.pue < 1.0:
            raise ValueError("pue must be at least 1.0")


@dataclass(frozen=True, slots=True)
class CapacityPlan:
    """Auditable plan for one candidate GPU profile."""

    profile_id: str
    gpu_model: str
    evidence_class: EvidenceClass
    feasible: bool
    infeasible_reason: str | None
    bottleneck: str
    node_nameplate_power_w: float
    node_inference_capacity_per_second: float
    safe_node_inference_capacity_per_second: float
    maximum_nodes_by_power: int
    required_nodes_by_service: int | None
    deployed_nodes: int
    total_gpus: int
    inference_gpus: int
    batch_gpus: int
    planned_it_nameplate_mw: float
    facility_nameplate_mw: float
    spare_it_power_mw: float
    planned_inference_capacity_per_second: float
    work_unit: str
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CapacityComparison:
    """All candidate plans and the selected profile under an explicit objective."""

    scenario_id: str
    objective: str
    selected_profile_id: str | None
    plans: tuple[CapacityPlan, ...]


@dataclass(frozen=True, slots=True)
class FleetPrediction:
    """Aggregate transition quantities for homogeneous virtual nodes."""

    virtual_nodes: int
    facility_power_w: float
    it_power_w: float
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
    evidence_class: EvidenceClass
    evidence_chain: tuple[str, ...]


def plan_capacity(
    profile: GpuHardwareProfile,
    workload: ComputeWorkload,
    topology: NodeTopology,
    request: CapacityRequest,
) -> CapacityPlan:
    """Plan a fleet without presenting a spec-derived estimate as measurement."""

    roofline = estimate_roofline_capacity(
        profile,
        workload,
        gpu_count=topology.inference_gpus_per_node,
    )
    node_nameplate = (
        topology.host_nameplate_power_w + topology.gpus_per_node * profile.max_power_w
    )
    power_budget_w = request.it_power_budget_mw * 1_000_000.0
    maximum_nodes = math.floor(power_budget_w / node_nameplate)
    safe_node_capacity = roofline.work_units_per_second * request.safe_utilization
    required_nodes: int | None = None
    if request.target_inference_work_units_per_second is not None:
        required_nodes = math.ceil(
            request.target_inference_work_units_per_second / safe_node_capacity
        )
        deployed_nodes = required_nodes
    else:
        deployed_nodes = maximum_nodes

    infeasible_reason: str | None = None
    if maximum_nodes < 1:
        infeasible_reason = "the IT power budget cannot hold one configured node"
    elif required_nodes is not None and required_nodes > maximum_nodes:
        infeasible_reason = (
            f"service target requires {required_nodes} nodes but the power budget allows "
            f"only {maximum_nodes}"
        )
    feasible = infeasible_reason is None
    if not feasible:
        deployed_nodes = 0

    planned_it_mw = deployed_nodes * node_nameplate / 1_000_000.0
    warnings = list(roofline.warnings)
    warnings.append(
        "nameplate power is a capacity constraint, not predicted operating power"
    )
    warnings.append(
        "a measured or benchmark-anchored operating baseline is still required "
        "by the control environment"
    )
    return CapacityPlan(
        profile_id=profile.profile_id,
        gpu_model=profile.model,
        evidence_class=EvidenceClass.SPEC_DERIVED_SYNTHETIC,
        feasible=feasible,
        infeasible_reason=infeasible_reason,
        bottleneck=roofline.bottleneck,
        node_nameplate_power_w=node_nameplate,
        node_inference_capacity_per_second=roofline.work_units_per_second,
        safe_node_inference_capacity_per_second=safe_node_capacity,
        maximum_nodes_by_power=maximum_nodes,
        required_nodes_by_service=required_nodes,
        deployed_nodes=deployed_nodes,
        total_gpus=deployed_nodes * topology.gpus_per_node,
        inference_gpus=deployed_nodes * topology.inference_gpus_per_node,
        batch_gpus=deployed_nodes * topology.batch_gpus_per_node,
        planned_it_nameplate_mw=planned_it_mw,
        facility_nameplate_mw=planned_it_mw * request.pue,
        spare_it_power_mw=max(request.it_power_budget_mw - planned_it_mw, 0.0),
        planned_inference_capacity_per_second=(
            deployed_nodes * safe_node_capacity
        ),
        work_unit=workload.work_unit,
        warnings=tuple(warnings),
    )


def aggregate_homogeneous_fleet(
    *,
    virtual_nodes: int,
    pue: float,
    baseline: NodeOperatingBaseline,
    inference_curve: ControlResponseCurve,
    batch_curve: ControlResponseCurve,
    fleet_control: NodeControlInput,
) -> FleetPrediction:
    """Split aggregate demand evenly, predict each node, and conserve work."""

    if isinstance(virtual_nodes, bool) or not isinstance(virtual_nodes, int) or virtual_nodes <= 0:
        raise ValueError("virtual_nodes must be a positive integer")
    if pue < 1.0:
        raise ValueError("pue must be at least 1.0")
    per_node_control = NodeControlInput(
        inference_demand_per_second=(
            fleet_control.inference_demand_per_second / virtual_nodes
        ),
        batch_demand_per_second=fleet_control.batch_demand_per_second / virtual_nodes,
        inference_cap_ratio=fleet_control.inference_cap_ratio,
        batch_cap_ratio=fleet_control.batch_cap_ratio,
        active_batch_gpus=fleet_control.active_batch_gpus,
    )
    node: NodePrediction = predict_node_response(
        baseline,
        inference_curve,
        batch_curve,
        per_node_control,
    )
    it_power = virtual_nodes * node.power_w
    return FleetPrediction(
        virtual_nodes=virtual_nodes,
        facility_power_w=it_power * pue,
        it_power_w=it_power,
        inference_capacity_per_second=(
            virtual_nodes * node.inference_capacity_per_second
        ),
        inference_served_per_second=(
            virtual_nodes * node.inference_served_per_second
        ),
        inference_unserved_per_second=(
            virtual_nodes * node.inference_unserved_per_second
        ),
        batch_capacity_per_second=virtual_nodes * node.batch_capacity_per_second,
        batch_served_per_second=virtual_nodes * node.batch_served_per_second,
        batch_unserved_per_second=virtual_nodes * node.batch_unserved_per_second,
        ttft_p99_ms=node.ttft_p99_ms,
        tpot_p99_ms=node.tpot_p99_ms,
        inference_utilization=node.inference_utilization,
        batch_utilization=node.batch_utilization,
        evidence_class=EvidenceClass.HOMOGENEOUS_SCALED,
        evidence_chain=node.evidence_chain,
    )


def _topology_from_mapping(document: object) -> NodeTopology:
    node = _mapping(document, "node")
    return NodeTopology(
        gpus_per_node=_positive_int(node.get("gpus_per_node"), "node.gpus_per_node"),
        inference_gpus_per_node=_positive_int(
            node.get("inference_gpus_per_node"), "node.inference_gpus_per_node"
        ),
        batch_gpus_per_node=_positive_int(
            node.get("batch_gpus_per_node"),
            "node.batch_gpus_per_node",
            allow_zero=True,
        ),
        host_nameplate_power_w=_positive_float(
            node.get("host_nameplate_power_w"), "node.host_nameplate_power_w"
        ),
    )


def _request_from_mapping(capacity_document: object, facility_document: object) -> CapacityRequest:
    capacity = _mapping(capacity_document, "capacity")
    facility = _mapping(facility_document, "facility")
    return CapacityRequest(
        it_power_budget_mw=_positive_float(
            capacity.get("it_power_budget_mw"), "capacity.it_power_budget_mw"
        ),
        target_inference_work_units_per_second=_optional_positive_float(
            capacity.get("target_inference_work_units_per_second"),
            "capacity.target_inference_work_units_per_second",
        ),
        safe_utilization=_positive_float(
            capacity.get("safe_utilization", 0.75), "capacity.safe_utilization"
        ),
        pue=_positive_float(facility.get("pue", 1.0), "facility.pue"),
    )


def compare_capacity_options(config: str | Path) -> CapacityComparison:
    """Compare GPU profiles using an explicit, auditable planning objective."""

    config_path = Path(config)
    with config_path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    root = _mapping(document, "capacity scenario")
    raw_schema = root.get("schema_version")
    if raw_schema != 1:
        raise ValueError(f"unsupported capacity scenario schema_version: {raw_schema}")
    scenario_id = _text(root.get("scenario_id"), "scenario_id")
    relative_profiles = _string_sequence(root.get("profiles"), "profiles")
    topology = _topology_from_mapping(root.get("node"))
    request = _request_from_mapping(root.get("capacity"), root.get("facility"))
    workload = compute_workload_from_mapping(root.get("workload"))
    selection = _mapping(root.get("selection"), "selection")
    objective = _text(selection.get("objective"), "selection.objective")
    allowed_objectives = {"min_it_nameplate_power", "min_gpu_count", "min_node_count"}
    if objective not in allowed_objectives:
        raise ValueError(f"unsupported selection objective: {objective}")

    plans: list[CapacityPlan] = []
    for relative_path in relative_profiles:
        profile_path = (config_path.parent / relative_path).resolve()
        profile = load_gpu_profile(profile_path)
        try:
            plan = plan_capacity(profile, workload, topology, request)
        except ValueError as exc:
            plans.append(
                CapacityPlan(
                    profile_id=profile.profile_id,
                    gpu_model=profile.model,
                    evidence_class=EvidenceClass.SPEC_DERIVED_SYNTHETIC,
                    feasible=False,
                    infeasible_reason=str(exc),
                    bottleneck="unknown",
                    node_nameplate_power_w=(
                        topology.host_nameplate_power_w
                        + topology.gpus_per_node * profile.max_power_w
                    ),
                    node_inference_capacity_per_second=0.0,
                    safe_node_inference_capacity_per_second=0.0,
                    maximum_nodes_by_power=0,
                    required_nodes_by_service=None,
                    deployed_nodes=0,
                    total_gpus=0,
                    inference_gpus=0,
                    batch_gpus=0,
                    planned_it_nameplate_mw=0.0,
                    facility_nameplate_mw=0.0,
                    spare_it_power_mw=request.it_power_budget_mw,
                    planned_inference_capacity_per_second=0.0,
                    work_unit=workload.work_unit,
                    warnings=("candidate rejected during validation",),
                )
            )
        else:
            plans.append(plan)

    feasible = [plan for plan in plans if plan.feasible]
    key_functions = {
        "min_it_nameplate_power": lambda plan: (
            plan.planned_it_nameplate_mw,
            plan.total_gpus,
            plan.profile_id,
        ),
        "min_gpu_count": lambda plan: (
            float(plan.total_gpus),
            plan.planned_it_nameplate_mw,
            plan.profile_id,
        ),
        "min_node_count": lambda plan: (
            float(plan.deployed_nodes),
            plan.planned_it_nameplate_mw,
            plan.profile_id,
        ),
    }
    selected = min(feasible, key=key_functions[objective]) if feasible else None
    return CapacityComparison(
        scenario_id=scenario_id,
        objective=objective,
        selected_profile_id=selected.profile_id if selected is not None else None,
        plans=tuple(plans),
    )


def capacity_comparison_dict(comparison: CapacityComparison) -> dict[str, object]:
    """Return a JSON-ready comparison with explicit evidence labels."""

    plans: list[dict[str, object]] = []
    for plan in comparison.plans:
        item = asdict(plan)
        item["evidence_class"] = plan.evidence_class.value
        plans.append(item)
    return {
        "scenario_id": comparison.scenario_id,
        "objective": comparison.objective,
        "selected_profile_id": comparison.selected_profile_id,
        "plans": plans,
    }


def write_capacity_comparison(
    comparison: CapacityComparison,
    output: str | Path,
) -> None:
    """Write one deterministic JSON planning artifact."""

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(capacity_comparison_dict(comparison), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
