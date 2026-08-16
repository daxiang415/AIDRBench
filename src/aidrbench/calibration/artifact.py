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

HARDWARE_CALIBRATION_SCHEMA_VERSION = "aidrbench.hardware_calibration.v1"


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


def _estimate_and_interval(value: object, name: str) -> tuple[float, tuple[float, float]]:
    entry = _mapping(value, name)
    if set(entry) != {"estimate_w", "confidence_interval_w"}:
        raise ValueError(f"{name} must contain estimate_w and confidence_interval_w")
    estimate = _positive(entry["estimate_w"], f"{name}.estimate_w")
    interval = entry["confidence_interval_w"]
    if not isinstance(interval, list) or len(interval) != 2:
        raise ValueError(f"{name}.confidence_interval_w must be [lower, upper]")
    lower = _positive(interval[0], f"{name}.confidence_interval_w[0]")
    upper = _positive(interval[1], f"{name}.confidence_interval_w[1]")
    if lower > estimate or estimate > upper:
        raise ValueError(f"{name} estimate must lie inside its confidence interval")
    return estimate, (lower, upper)


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
    idle_power_w_per_gpu: float
    idle_power_confidence_interval_w: tuple[float, float]
    node_fixed_overhead_w: float
    node_fixed_overhead_confidence_interval_w: tuple[float, float]
    active_power_w_per_gpu_by_class: tuple[tuple[str, float], ...]
    active_power_confidence_interval_w_by_class: tuple[tuple[str, tuple[float, float]], ...]
    held_out_power_mae_w: float
    evidence_class: EvidenceClass
    artifact_sha256: str

    @property
    def active_power_by_class(self) -> dict[str, float]:
        return dict(self.active_power_w_per_gpu_by_class)

    @property
    def active_power_intervals_by_class(self) -> dict[str, tuple[float, float]]:
        return dict(self.active_power_confidence_interval_w_by_class)

    def summary(self) -> dict[str, object]:
        """Return a compact provenance record suitable for result metadata."""

        return {
            "artifact_id": self.artifact_id,
            "artifact_sha256": self.artifact_sha256,
            "hardware_identifier": self.hardware_identifier,
            "topology_identifier": self.topology_identifier,
            "measurement_method": self.measurement_method,
            "evidence_class": self.evidence_class.value,
            "workload_classes": [name for name, _ in self.active_power_w_per_gpu_by_class],
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
    idle_power, idle_interval = _estimate_and_interval(
        parameters.get("idle_power_w_per_gpu"), "parameters.idle_power_w_per_gpu"
    )
    node_overhead, node_overhead_interval = _estimate_and_interval(
        parameters.get("node_fixed_overhead_w"), "parameters.node_fixed_overhead_w"
    )
    class_parameters = _mapping(
        parameters.get("active_power_w_per_gpu_by_class"),
        "parameters.active_power_w_per_gpu_by_class",
    )
    if not class_parameters:
        raise ValueError("hardware calibration artifact must contain workload classes")
    active_power: list[tuple[str, float]] = []
    active_intervals: list[tuple[str, tuple[float, float]]] = []
    for job_class, value in sorted(class_parameters.items()):
        if not job_class.strip():
            raise ValueError("workload class must not be empty")
        estimate, interval = _estimate_and_interval(value, f"active power for {job_class}")
        if estimate < idle_power:
            raise ValueError("class active power must be at least idle power")
        active_power.append((job_class, estimate))
        active_intervals.append((job_class, interval))
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
        idle_power_w_per_gpu=idle_power,
        idle_power_confidence_interval_w=idle_interval,
        node_fixed_overhead_w=node_overhead,
        node_fixed_overhead_confidence_interval_w=node_overhead_interval,
        active_power_w_per_gpu_by_class=tuple(active_power),
        active_power_confidence_interval_w_by_class=tuple(active_intervals),
        held_out_power_mae_w=_positive(
            validation.get("held_out_power_mae_w"), "validation.held_out_power_mae_w"
        ),
        evidence_class=evidence_class,
        artifact_sha256=expected_sha256,
    )
