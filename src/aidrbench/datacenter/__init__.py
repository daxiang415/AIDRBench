"""P2/P3 measured surrogate and virtual-fleet modules."""

from aidrbench.datacenter.hardware import (
    ComputeWorkload,
    EvidenceClass,
    GpuHardwareProfile,
    RooflineEstimate,
    estimate_roofline_capacity,
    load_gpu_profile,
)
from aidrbench.datacenter.scaling import (
    CapacityComparison,
    CapacityPlan,
    CapacityRequest,
    FleetPrediction,
    NodeTopology,
    aggregate_homogeneous_fleet,
    compare_capacity_options,
    plan_capacity,
)

__all__ = [
    "CapacityComparison",
    "CapacityPlan",
    "CapacityRequest",
    "ComputeWorkload",
    "EvidenceClass",
    "FleetPrediction",
    "GpuHardwareProfile",
    "NodeTopology",
    "RooflineEstimate",
    "aggregate_homogeneous_fleet",
    "compare_capacity_options",
    "estimate_roofline_capacity",
    "load_gpu_profile",
    "plan_capacity",
]
