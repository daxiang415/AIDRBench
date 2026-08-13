from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from aidrbench.envs.actions import ActionComponents
from aidrbench.hil.actuator_client import ActuationResult
from aidrbench.hil.workload_client import (
    CalibrationRunSpec,
    DryRunMixedWorkloadBackend,
    MixedWorkloadCoordinator,
    dry_run_plan,
    load_calibration_runs,
)


class StubActuator:
    def __init__(self) -> None:
        self.prepared = False
        self.actions: list[int] = []
        self.restore_reasons: list[str] = []

    def prepare(self) -> None:
        self.prepared = True

    def apply_action(self, action_id: int, *, caller: str) -> ActuationResult:
        assert caller == "calibration-runner"
        self.actions.append(action_id)
        return ActuationResult(
            action_id=action_id,
            components=ActionComponents(1.0, 2, 1.0),
            dry_run=True,
            caller=caller,
            targets=(),
            active_batch_gpus=2,
            restored_after_failure=False,
        )

    def restore(self, *, reason: str) -> None:
        self.restore_reasons.append(reason)


def _write_plan(path: Path) -> None:
    fieldnames = [
        "run_order",
        "run_id",
        "inference_cap_ratio",
        "active_batch_gpus",
        "batch_cap_ratio",
        "request_rate_level",
        "token_mix",
        "warmup_seconds",
        "measurement_seconds",
        "cooldown_seconds",
        "seed",
    ]
    rows = [
        [1, "run-1", 1.0, 2, 1.0, "p50", "medium", 30, 60, 10, 42],
        [2, "run-2", 0.84, 0, 0.84, "p90", "long", 30, 60, 10, 43],
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fieldnames)
        writer.writerows(rows)


def test_load_plan_validates_action_codec_and_order(tmp_path: Path) -> None:
    plan = tmp_path / "plan.csv"
    _write_plan(plan)
    runs = load_calibration_runs(plan)
    assert [run.run_id for run in runs] == ["run-1", "run-2"]
    assert runs[0].active_batch_gpus == 2

    text = plan.read_text(encoding="utf-8").replace("2,run-2", "3,run-2")
    plan.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="contiguous"):
        load_calibration_runs(plan)


def test_dry_run_plan_resolves_power_and_workload_without_sleeping(tmp_path: Path) -> None:
    plan = tmp_path / "plan.csv"
    output = tmp_path / "dry-run.json"
    _write_plan(plan)
    actuator = StubActuator()
    workload = DryRunMixedWorkloadBackend()
    coordinator = MixedWorkloadCoordinator(  # type: ignore[arg-type]
        actuator,
        workload,
        batch_gpu_ids=(2, 3),
    )
    summary = dry_run_plan(plan, coordinator, output=output)

    assert summary["runs"] == 2
    assert summary["total_scheduled_seconds"] == 200
    assert actuator.actions == [26, 0]
    assert actuator.restore_reasons == ["mixed_workload_complete"]
    assert not any(event.event == "sleep" for event in workload.events)
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["dry_run"] is True
    assert document["runs"][0]["active_batch_gpu_ids"] == [2, 3]
    assert document["runs"][1]["active_batch_gpu_ids"] == []


def test_coordinator_restores_when_workload_fails() -> None:
    class FailingWorkload(DryRunMixedWorkloadBackend):
        def configure(self, **kwargs: object) -> None:
            raise RuntimeError("injected workload failure")

    actuator = StubActuator()
    coordinator = MixedWorkloadCoordinator(  # type: ignore[arg-type]
        actuator,
        FailingWorkload(),
        batch_gpu_ids=(2, 3),
    )
    coordinator.prepare()
    spec = CalibrationRunSpec(1, "run", 1.0, 2, 1.0, "p50", "medium", 1, 1, 1, 42)
    with pytest.raises(RuntimeError, match="injected workload failure"):
        coordinator.run(spec)
    assert actuator.restore_reasons == ["mixed_workload_failure"]
