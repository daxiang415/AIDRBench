"""Inference/batch workload coordination behind the safe power actuator."""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from aidrbench.envs.actions import ActionComponents, encode_action
from aidrbench.hil.actuator_client import ActuationResult, PowerActuator


@dataclass(frozen=True, slots=True)
class CalibrationRunSpec:
    """One validated row from the deterministic P2 plan."""

    run_order: int
    run_id: str
    inference_cap_ratio: float
    active_batch_gpus: int
    batch_cap_ratio: float
    request_rate_level: str
    token_mix: str
    warmup_seconds: int
    measurement_seconds: int
    cooldown_seconds: int
    seed: int


@dataclass(frozen=True, slots=True)
class WorkloadPhase:
    """One phase delegated to a workload backend."""

    name: str
    duration_seconds: int


@dataclass(frozen=True, slots=True)
class WorkloadEvent:
    """Dry-run or real-client event suitable for a run manifest."""

    event: str
    details: Mapping[str, object]


class MixedWorkloadBackend(Protocol):
    """Backend contract for vLLM/AIPerf plus the batch worker."""

    def prepare(self) -> None: ...

    def configure(
        self,
        *,
        request_rate_level: str,
        token_mix: str,
        active_batch_gpu_ids: tuple[int, ...],
        seed: int,
    ) -> None: ...

    def run_phase(self, phase: WorkloadPhase) -> None: ...

    def stop(self) -> None: ...


class DryRunMixedWorkloadBackend:
    """Manifest-only backend; it never starts a process or sleeps."""

    def __init__(self) -> None:
        self.events: list[WorkloadEvent] = []

    def prepare(self) -> None:
        self.events.append(WorkloadEvent("prepare", {}))

    def configure(
        self,
        *,
        request_rate_level: str,
        token_mix: str,
        active_batch_gpu_ids: tuple[int, ...],
        seed: int,
    ) -> None:
        self.events.append(
            WorkloadEvent(
                "configure",
                {
                    "request_rate_level": request_rate_level,
                    "token_mix": token_mix,
                    "active_batch_gpu_ids": active_batch_gpu_ids,
                    "seed": seed,
                },
            )
        )

    def run_phase(self, phase: WorkloadPhase) -> None:
        self.events.append(WorkloadEvent("phase", asdict(phase)))

    def stop(self) -> None:
        self.events.append(WorkloadEvent("stop", {}))


@dataclass(frozen=True, slots=True)
class MixedWorkloadRunResult:
    """Resolved action and workload schedule for one P2 run."""

    run_id: str
    action_id: int
    actuation: ActuationResult
    active_batch_gpu_ids: tuple[int, ...]
    phases: tuple[WorkloadPhase, ...]


class MixedWorkloadCoordinator:
    """Order power/workload changes and restore on every failure path."""

    def __init__(
        self,
        actuator: PowerActuator,
        workload: MixedWorkloadBackend,
        *,
        batch_gpu_ids: tuple[int, ...],
    ) -> None:
        self.actuator = actuator
        self.workload = workload
        self.batch_gpu_ids = batch_gpu_ids
        self._prepared = False
        self._closed = False

    def prepare(self) -> None:
        self.actuator.prepare()
        try:
            self.workload.prepare()
        except Exception:
            self.actuator.restore(reason="workload_prepare_failure")
            raise
        self._prepared = True

    def run(self, spec: CalibrationRunSpec) -> MixedWorkloadRunResult:
        if not self._prepared or self._closed:
            raise RuntimeError("coordinator must be prepared and open")
        if not 0 <= spec.active_batch_gpus <= len(self.batch_gpu_ids):
            raise ValueError("active_batch_gpus is outside the batch GPU allow-list")
        components = ActionComponents(
            inference_cap_ratio=spec.inference_cap_ratio,
            batch_gpu_count=spec.active_batch_gpus,
            batch_cap_ratio=spec.batch_cap_ratio,
        )
        action_id = encode_action(components)
        active_gpu_ids = self.batch_gpu_ids[: spec.active_batch_gpus]
        phases = (
            WorkloadPhase("warmup", spec.warmup_seconds),
            WorkloadPhase("measurement", spec.measurement_seconds),
            WorkloadPhase("cooldown", spec.cooldown_seconds),
        )
        try:
            actuation = self.actuator.apply_action(action_id, caller="calibration-runner")
            self.workload.configure(
                request_rate_level=spec.request_rate_level,
                token_mix=spec.token_mix,
                active_batch_gpu_ids=active_gpu_ids,
                seed=spec.seed,
            )
            for phase in phases:
                self.workload.run_phase(phase)
        except Exception:
            try:
                self.workload.stop()
            finally:
                self.actuator.restore(reason="mixed_workload_failure")
                self._closed = True
            raise
        return MixedWorkloadRunResult(
            run_id=spec.run_id,
            action_id=action_id,
            actuation=actuation,
            active_batch_gpu_ids=active_gpu_ids,
            phases=phases,
        )

    def close(self) -> None:
        if self._closed:
            return
        workload_error: Exception | None = None
        try:
            self.workload.stop()
        except Exception as exc:
            workload_error = exc
        try:
            self.actuator.restore(reason="mixed_workload_complete")
        finally:
            self._closed = True
        if workload_error is not None:
            raise workload_error


def _integer(row: Mapping[str, str], name: str, *, allow_zero: bool = False) -> int:
    try:
        result = int(row[name])
    except (KeyError, ValueError) as exc:
        raise ValueError(f"plan field {name} must be an integer") from exc
    minimum = 0 if allow_zero else 1
    if result < minimum:
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"plan field {name} must be {qualifier}")
    return result


def _float(row: Mapping[str, str], name: str) -> float:
    try:
        result = float(row[name])
    except (KeyError, ValueError) as exc:
        raise ValueError(f"plan field {name} must be numeric") from exc
    if not 0.0 < result <= 1.0:
        raise ValueError(f"plan field {name} must be in (0, 1]")
    return result


def _label(row: Mapping[str, str], name: str) -> str:
    try:
        result = row[name].strip()
    except KeyError as exc:
        raise ValueError(f"plan field {name} is missing") from exc
    if not result:
        raise ValueError(f"plan field {name} must not be empty")
    return result


def load_calibration_runs(path: str | Path) -> tuple[CalibrationRunSpec, ...]:
    """Load and validate a generated plan before touching workloads."""

    plan_path = Path(path)
    with plan_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("calibration plan contains no runs")
    runs: list[CalibrationRunSpec] = []
    for row in rows:
        spec = CalibrationRunSpec(
            run_order=_integer(row, "run_order"),
            run_id=_label(row, "run_id"),
            inference_cap_ratio=_float(row, "inference_cap_ratio"),
            active_batch_gpus=_integer(row, "active_batch_gpus", allow_zero=True),
            batch_cap_ratio=_float(row, "batch_cap_ratio"),
            request_rate_level=_label(row, "request_rate_level"),
            token_mix=_label(row, "token_mix"),
            warmup_seconds=_integer(row, "warmup_seconds", allow_zero=True),
            measurement_seconds=_integer(row, "measurement_seconds"),
            cooldown_seconds=_integer(row, "cooldown_seconds", allow_zero=True),
            seed=_integer(row, "seed", allow_zero=True),
        )
        # Fail before execution if a plan level is incompatible with the
        # canonical 27-action codec.
        encode_action(
            ActionComponents(
                spec.inference_cap_ratio,
                spec.active_batch_gpus,
                spec.batch_cap_ratio,
            )
        )
        runs.append(spec)
    orders = [run.run_order for run in runs]
    if orders != list(range(1, len(runs) + 1)):
        raise ValueError("calibration plan run_order must be contiguous and sorted")
    if len({run.run_id for run in runs}) != len(runs):
        raise ValueError("calibration plan run_id values must be unique")
    return tuple(runs)


def dry_run_plan(
    plan: str | Path,
    coordinator: MixedWorkloadCoordinator,
    *,
    output: str | Path,
    limit: int | None = None,
) -> dict[str, object]:
    """Resolve a calibration plan without launching workloads or mutating GPUs."""

    runs = load_calibration_runs(plan)
    if limit is not None:
        if limit <= 0:
            raise ValueError("dry-run limit must be positive")
        runs = runs[:limit]
    coordinator.prepare()
    results: list[MixedWorkloadRunResult] = []
    try:
        for run in runs:
            results.append(coordinator.run(run))
    finally:
        coordinator.close()
    document = {
        "schema_version": 1,
        "dry_run": True,
        "plan": str(plan),
        "runs": [
            {
                "run_id": result.run_id,
                "action_id": result.action_id,
                "actuation": asdict(result.actuation),
                "active_batch_gpu_ids": result.active_batch_gpu_ids,
                "phases": [asdict(phase) for phase in result.phases],
            }
            for result in results
        ],
    }
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(document, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    return {
        "output": str(output_path),
        "dry_run": True,
        "runs": len(results),
        "total_scheduled_seconds": sum(
            phase.duration_seconds for result in results for phase in result.phases
        ),
    }
