"""Versioned, hash-verified inputs for hourly hardware power models."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from aidrbench.datacenter.hardware import EvidenceClass

HARDWARE_CALIBRATION_SCHEMA_VERSION = "aidrbench.hardware_calibration.v2"


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _positive(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return result


@dataclass(frozen=True, slots=True)
class PowerParameterEstimate:
    """One power estimate with an explicitly labelled uncertainty source."""

    estimate_w: float
    uncertainty_interval_w: tuple[float, float]
    uncertainty_method: str
    statistical_unit: str
    independent_unit_count: int
    confidence_level: float | None


def _estimate_and_interval(value: object, name: str) -> PowerParameterEstimate:
    entry = _mapping(value, name)
    required = {
        "estimate_w",
        "uncertainty_interval_w",
        "uncertainty_method",
        "statistical_unit",
        "independent_unit_count",
    }
    optional = {"confidence_level"}
    if not required.issubset(entry) or set(entry) - required - optional:
        raise ValueError(
            f"{name} must contain the power estimate and explicit uncertainty metadata"
        )
    estimate = _positive(entry["estimate_w"], f"{name}.estimate_w")
    interval = entry["uncertainty_interval_w"]
    if not isinstance(interval, list) or len(interval) != 2:
        raise ValueError(f"{name}.uncertainty_interval_w must be [lower, upper]")
    lower = _positive(interval[0], f"{name}.uncertainty_interval_w[0]")
    upper = _positive(interval[1], f"{name}.uncertainty_interval_w[1]")
    if lower > estimate or estimate > upper:
        raise ValueError(f"{name} estimate must lie inside its uncertainty interval")
    raw_count = entry["independent_unit_count"]
    if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count < 0:
        raise ValueError(f"{name}.independent_unit_count must be a non-negative integer")
    raw_confidence = entry.get("confidence_level")
    if raw_confidence is None:
        confidence_level = None
    else:
        confidence_level = float(raw_confidence)
        if not math.isfinite(confidence_level) or not 0.0 < confidence_level < 1.0:
            raise ValueError(f"{name}.confidence_level must be in (0, 1)")
    return PowerParameterEstimate(
        estimate_w=estimate,
        uncertainty_interval_w=(lower, upper),
        uncertainty_method=_text(entry["uncertainty_method"], f"{name}.uncertainty_method"),
        statistical_unit=_text(entry["statistical_unit"], f"{name}.statistical_unit"),
        independent_unit_count=raw_count,
        confidence_level=confidence_level,
    )


def _canonical_json(document: Mapping[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def calibration_artifact_sha256(document: Mapping[str, Any]) -> str:
    """Hash a calibration document, excluding its self-referential checksum."""

    payload = dict(document)
    payload.pop("artifact_sha256", None)
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class HardwareCalibrationArtifact:
    """Calibrated power inputs plus their provenance and uncertainty bounds."""

    path: Path
    schema_version: str
    artifact_id: str
    hardware_identifier: str
    topology_identifier: str
    measurement_method: str
    idle_power: PowerParameterEstimate
    node_fixed_overhead: PowerParameterEstimate
    active_power_parameters_by_class: tuple[tuple[str, PowerParameterEstimate], ...]
    held_out_power_mae_w: float
    evidence_class: EvidenceClass
    artifact_sha256: str

    @property
    def active_power_by_class(self) -> dict[str, float]:
        return {
            name: parameter.estimate_w for name, parameter in self.active_power_parameters_by_class
        }

    @property
    def active_power_intervals_by_class(self) -> dict[str, tuple[float, float]]:
        return {
            name: parameter.uncertainty_interval_w
            for name, parameter in self.active_power_parameters_by_class
        }

    @property
    def idle_power_w_per_gpu(self) -> float:
        return self.idle_power.estimate_w

    @property
    def idle_power_uncertainty_interval_w(self) -> tuple[float, float]:
        return self.idle_power.uncertainty_interval_w

    @property
    def node_fixed_overhead_w(self) -> float:
        return self.node_fixed_overhead.estimate_w

    @property
    def node_fixed_overhead_uncertainty_interval_w(self) -> tuple[float, float]:
        return self.node_fixed_overhead.uncertainty_interval_w

    def summary(self) -> dict[str, object]:
        """Return a compact provenance record suitable for result metadata."""

        return {
            "artifact_id": self.artifact_id,
            "artifact_sha256": self.artifact_sha256,
            "hardware_identifier": self.hardware_identifier,
            "topology_identifier": self.topology_identifier,
            "measurement_method": self.measurement_method,
            "evidence_class": self.evidence_class.value,
            "workload_classes": [name for name, _ in self.active_power_parameters_by_class],
            "uncertainty_methods": {
                "idle_power_w_per_gpu": self.idle_power.uncertainty_method,
                "node_fixed_overhead_w": self.node_fixed_overhead.uncertainty_method,
                "active_power_w_per_gpu_by_class": {
                    name: parameter.uncertainty_method
                    for name, parameter in self.active_power_parameters_by_class
                },
            },
            "held_out_power_mae_w": self.held_out_power_mae_w,
        }


def load_hardware_calibration_artifact(path: str | Path) -> HardwareCalibrationArtifact:
    """Load and cryptographically verify one strict calibration artifact."""

    artifact_path = Path(path)
    if not artifact_path.is_file():
        raise FileNotFoundError(f"hardware calibration artifact does not exist: {artifact_path}")
    document = _mapping(yaml.safe_load(artifact_path.read_text(encoding="utf-8")), "artifact")
    if document.get("schema_version") != HARDWARE_CALIBRATION_SCHEMA_VERSION:
        raise ValueError("unsupported hardware calibration artifact schema_version")
    expected_sha256 = _text(document.get("artifact_sha256"), "artifact_sha256")
    if len(expected_sha256) != 64 or calibration_artifact_sha256(document) != expected_sha256:
        raise ValueError("hardware calibration artifact SHA-256 does not match its contents")
    hardware = _mapping(document.get("hardware"), "hardware")
    measurement = _mapping(document.get("measurement"), "measurement")
    parameters = _mapping(document.get("parameters"), "parameters")
    validation = _mapping(document.get("validation"), "validation")
    idle_power = _estimate_and_interval(
        parameters.get("idle_power_w_per_gpu"), "parameters.idle_power_w_per_gpu"
    )
    node_overhead = _estimate_and_interval(
        parameters.get("node_fixed_overhead_w"), "parameters.node_fixed_overhead_w"
    )
    class_parameters = _mapping(
        parameters.get("active_power_w_per_gpu_by_class"),
        "parameters.active_power_w_per_gpu_by_class",
    )
    if not class_parameters:
        raise ValueError("hardware calibration artifact must contain workload classes")
    active_parameters: list[tuple[str, PowerParameterEstimate]] = []
    for job_class, value in sorted(class_parameters.items()):
        if not job_class.strip():
            raise ValueError("workload class must not be empty")
        estimate = _estimate_and_interval(value, f"active power for {job_class}")
        if estimate.estimate_w < idle_power.estimate_w:
            raise ValueError("class active power must be at least idle power")
        active_parameters.append((job_class, estimate))
    try:
        evidence_class = EvidenceClass(_text(document.get("evidence_class"), "evidence_class"))
    except ValueError as error:
        allowed = ", ".join(member.value for member in EvidenceClass)
        raise ValueError(f"evidence_class must be one of: {allowed}") from error
    return HardwareCalibrationArtifact(
        path=artifact_path,
        schema_version=HARDWARE_CALIBRATION_SCHEMA_VERSION,
        artifact_id=_text(document.get("artifact_id"), "artifact_id"),
        hardware_identifier=_text(hardware.get("identifier"), "hardware.identifier"),
        topology_identifier=_text(
            hardware.get("topology_identifier"), "hardware.topology_identifier"
        ),
        measurement_method=_text(measurement.get("method"), "measurement.method"),
        idle_power=idle_power,
        node_fixed_overhead=node_overhead,
        active_power_parameters_by_class=tuple(active_parameters),
        held_out_power_mae_w=_positive(
            validation.get("held_out_power_mae_w"), "validation.held_out_power_mae_w"
        ),
        evidence_class=evidence_class,
        artifact_sha256=expected_sha256,
    )
