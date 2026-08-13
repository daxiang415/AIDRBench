"""Evidence-aware hardware profiles and Roofline capacity estimates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml


class EvidenceClass(StrEnum):
    """Provenance classes used to keep measurements separate from assumptions."""

    MEASURED = "measured"
    HOMOGENEOUS_SCALED = "homogeneous_scaled"
    BENCHMARK_ANCHORED_SYNTHETIC = "benchmark_anchored_synthetic"
    SPEC_DERIVED_SYNTHETIC = "spec_derived_synthetic"


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


def _non_negative_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be a number")
    result = float(value)
    if result < 0.0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _fraction(value: object, name: str) -> float:
    result = _positive_float(value, name)
    if result > 1.0:
        raise ValueError(f"{name} must be in (0, 1]")
    return result


def _optional_positive_float(value: object, name: str) -> float | None:
    if value is None:
        return None
    return _positive_float(value, name)


def _strings(value: object, name: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if value is None and allow_empty:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, str):
        raise ValueError(f"{name} must be a list of strings")
    result = tuple(_text(item, f"{name} entry") for item in value)
    if not result and not allow_empty:
        raise ValueError(f"{name} must not be empty")
    return result


@dataclass(frozen=True, slots=True)
class GpuHardwareProfile:
    """One explicitly versioned GPU SKU, not an ambiguous product family."""

    schema_version: int
    profile_id: str
    evidence_class: EvidenceClass
    manufacturer: str
    model: str
    form_factor: str
    compute_precision: str
    memory_gb: float
    memory_bandwidth_tb_s: float
    dense_tensor_tflops: float
    max_power_w: float
    interconnect_bandwidth_gb_s: float | None
    sources: tuple[str, ...]
    notes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("unsupported GPU profile schema_version")
        if any(
            value <= 0.0
            for value in (
                self.memory_gb,
                self.memory_bandwidth_tb_s,
                self.dense_tensor_tflops,
                self.max_power_w,
            )
        ):
            raise ValueError("GPU capacity and power values must be positive")
        if (
            self.interconnect_bandwidth_gb_s is not None
            and self.interconnect_bandwidth_gb_s <= 0.0
        ):
            raise ValueError("GPU interconnect bandwidth must be positive when supplied")
        if not self.sources:
            raise ValueError("GPU profile must cite at least one source")


@dataclass(frozen=True, slots=True)
class ComputeWorkload:
    """Hardware-independent work required for one modeled service unit."""

    workload_id: str
    model_id: str
    work_unit: str
    flops_per_work_unit: float
    hbm_bytes_per_work_unit: float
    communication_bytes_per_work_unit: float
    model_memory_gb: float
    compute_efficiency: float
    memory_efficiency: float
    communication_efficiency: float
    memory_reserve_fraction: float
    evidence_class: EvidenceClass
    notes: tuple[str, ...]

    def __post_init__(self) -> None:
        if any(
            value <= 0.0
            for value in (
                self.flops_per_work_unit,
                self.hbm_bytes_per_work_unit,
                self.model_memory_gb,
            )
        ):
            raise ValueError("workload demand values must be positive")
        if self.communication_bytes_per_work_unit < 0.0:
            raise ValueError("communication_bytes_per_work_unit must be non-negative")
        for value, name in (
            (self.compute_efficiency, "compute_efficiency"),
            (self.memory_efficiency, "memory_efficiency"),
            (self.communication_efficiency, "communication_efficiency"),
            (self.memory_reserve_fraction, "memory_reserve_fraction"),
        ):
            if not 0.0 < value <= 1.0:
                raise ValueError(f"{name} must be in (0, 1]")


@dataclass(frozen=True, slots=True)
class RooflineEstimate:
    """Transparent compute-vs-memory capacity estimate for one GPU pool."""

    profile_id: str
    workload_id: str
    gpu_count: int
    work_unit: str
    work_units_per_second: float
    compute_ceiling_per_second: float
    memory_ceiling_per_second: float
    communication_ceiling_per_second: float | None
    compute_or_memory_time_per_work_unit_s: float
    communication_time_per_work_unit_s: float
    bottleneck: str
    model_memory_required_per_gpu_gb: float
    model_memory_available_per_gpu_gb: float
    evidence_class: EvidenceClass
    warnings: tuple[str, ...]


def gpu_profile_from_mapping(document: object) -> GpuHardwareProfile:
    """Validate and construct a GPU profile from a YAML-like mapping."""

    root = _mapping(document, "GPU profile")
    gpu = _mapping(root.get("gpu"), "gpu")
    sources = _strings(root.get("sources"), "sources")
    notes = _strings(root.get("notes"), "notes", allow_empty=True)
    raw_schema_version = root.get("schema_version")
    if isinstance(raw_schema_version, bool) or not isinstance(raw_schema_version, int):
        raise ValueError("schema_version must be an integer")
    if raw_schema_version != 1:
        raise ValueError(f"unsupported GPU profile schema_version: {raw_schema_version}")
    try:
        evidence_class = EvidenceClass(_text(root.get("evidence_class"), "evidence_class"))
    except ValueError as exc:
        raise ValueError("GPU profile has an unsupported evidence_class") from exc
    return GpuHardwareProfile(
        schema_version=raw_schema_version,
        profile_id=_text(root.get("profile_id"), "profile_id"),
        evidence_class=evidence_class,
        manufacturer=_text(gpu.get("manufacturer"), "gpu.manufacturer"),
        model=_text(gpu.get("model"), "gpu.model"),
        form_factor=_text(gpu.get("form_factor"), "gpu.form_factor"),
        compute_precision=_text(gpu.get("compute_precision"), "gpu.compute_precision"),
        memory_gb=_positive_float(gpu.get("memory_gb"), "gpu.memory_gb"),
        memory_bandwidth_tb_s=_positive_float(
            gpu.get("memory_bandwidth_tb_s"), "gpu.memory_bandwidth_tb_s"
        ),
        dense_tensor_tflops=_positive_float(
            gpu.get("dense_tensor_tflops"), "gpu.dense_tensor_tflops"
        ),
        max_power_w=_positive_float(gpu.get("max_power_w"), "gpu.max_power_w"),
        interconnect_bandwidth_gb_s=_optional_positive_float(
            gpu.get("interconnect_bandwidth_gb_s"),
            "gpu.interconnect_bandwidth_gb_s",
        ),
        sources=sources,
        notes=notes,
    )


def load_gpu_profile(path: str | Path) -> GpuHardwareProfile:
    """Load an evidence-aware GPU profile from YAML."""

    profile_path = Path(path)
    with profile_path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    return gpu_profile_from_mapping(document)


def compute_workload_from_mapping(document: object) -> ComputeWorkload:
    """Validate an embedded hardware-independent workload description."""

    root = _mapping(document, "workload")
    try:
        evidence_class = EvidenceClass(_text(root.get("evidence_class"), "evidence_class"))
    except ValueError as exc:
        raise ValueError("workload has an unsupported evidence_class") from exc
    return ComputeWorkload(
        workload_id=_text(root.get("workload_id"), "workload.workload_id"),
        model_id=_text(root.get("model_id"), "workload.model_id"),
        work_unit=_text(root.get("work_unit"), "workload.work_unit"),
        flops_per_work_unit=_positive_float(
            root.get("flops_per_work_unit"), "workload.flops_per_work_unit"
        ),
        hbm_bytes_per_work_unit=_positive_float(
            root.get("hbm_bytes_per_work_unit"), "workload.hbm_bytes_per_work_unit"
        ),
        communication_bytes_per_work_unit=_non_negative_float(
            root.get("communication_bytes_per_work_unit", 0.0),
            "workload.communication_bytes_per_work_unit",
        ),
        model_memory_gb=_positive_float(
            root.get("model_memory_gb"), "workload.model_memory_gb"
        ),
        compute_efficiency=_fraction(
            root.get("compute_efficiency"), "workload.compute_efficiency"
        ),
        memory_efficiency=_fraction(
            root.get("memory_efficiency"), "workload.memory_efficiency"
        ),
        communication_efficiency=_fraction(
            root.get("communication_efficiency", 1.0),
            "workload.communication_efficiency",
        ),
        memory_reserve_fraction=_fraction(
            root.get("memory_reserve_fraction", 0.90),
            "workload.memory_reserve_fraction",
        ),
        evidence_class=evidence_class,
        notes=_strings(root.get("notes"), "workload.notes", allow_empty=True),
    )


def estimate_roofline_capacity(
    profile: GpuHardwareProfile,
    workload: ComputeWorkload,
    *,
    gpu_count: int,
) -> RooflineEstimate:
    """Estimate idealized pool capacity with explicit efficiency assumptions."""

    if isinstance(gpu_count, bool) or not isinstance(gpu_count, int) or gpu_count <= 0:
        raise ValueError("gpu_count must be a positive integer")
    required_memory = workload.model_memory_gb / gpu_count
    available_memory = profile.memory_gb * workload.memory_reserve_fraction
    if required_memory > available_memory:
        raise ValueError(
            f"{profile.profile_id}: model requires {required_memory:.3f} GB per GPU but "
            f"only {available_memory:.3f} GB is allowed after the memory reserve"
        )

    compute_ceiling = (
        gpu_count
        * profile.dense_tensor_tflops
        * 1_000_000_000_000.0
        * workload.compute_efficiency
        / workload.flops_per_work_unit
    )
    memory_ceiling = (
        gpu_count
        * profile.memory_bandwidth_tb_s
        * 1_000_000_000_000.0
        * workload.memory_efficiency
        / workload.hbm_bytes_per_work_unit
    )
    base_time = max(1.0 / compute_ceiling, 1.0 / memory_ceiling)
    communication_ceiling: float | None = None
    communication_time = 0.0
    if workload.communication_bytes_per_work_unit > 0.0:
        if profile.interconnect_bandwidth_gb_s is None:
            raise ValueError(
                f"{profile.profile_id}: communication work is configured but the profile "
                "has no interconnect bandwidth"
            )
        communication_ceiling = (
            profile.interconnect_bandwidth_gb_s
            * 1_000_000_000.0
            * workload.communication_efficiency
            / workload.communication_bytes_per_work_unit
        )
        communication_time = 1.0 / communication_ceiling
    component_times = {
        "compute": 1.0 / compute_ceiling,
        "memory": 1.0 / memory_ceiling,
        "communication": communication_time,
    }
    bottleneck = max(component_times, key=component_times.__getitem__)
    capacity = 1.0 / (base_time + communication_time)
    warnings = [
        "capacity is a Roofline estimate, not a serving benchmark measurement",
        "software, scheduler, CPU, network, and queueing overhead are not modeled",
    ]
    if gpu_count > 1:
        if workload.communication_bytes_per_work_unit == 0.0:
            warnings.append(
                "multi-GPU communication bytes are zero; topology overhead is not included"
            )
        else:
            warnings.append(
                "collective communication is a serialized link-time approximation"
            )
    return RooflineEstimate(
        profile_id=profile.profile_id,
        workload_id=workload.workload_id,
        gpu_count=gpu_count,
        work_unit=workload.work_unit,
        work_units_per_second=capacity,
        compute_ceiling_per_second=compute_ceiling,
        memory_ceiling_per_second=memory_ceiling,
        communication_ceiling_per_second=communication_ceiling,
        compute_or_memory_time_per_work_unit_s=base_time,
        communication_time_per_work_unit_s=communication_time,
        bottleneck=bottleneck,
        model_memory_required_per_gpu_gb=required_memory,
        model_memory_available_per_gpu_gb=available_memory,
        evidence_class=EvidenceClass.SPEC_DERIVED_SYNTHETIC,
        warnings=tuple(warnings),
    )


def hardware_profile_dict(profile: GpuHardwareProfile) -> dict[str, object]:
    """Return a JSON-ready profile representation."""

    result = asdict(profile)
    result["evidence_class"] = profile.evidence_class.value
    return result


def roofline_dict(estimate: RooflineEstimate) -> dict[str, object]:
    """Return a JSON-ready Roofline representation."""

    result = asdict(estimate)
    result["evidence_class"] = estimate.evidence_class.value
    return result
