from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from aidrbench.hil.actuator_client import (
    ActuatorError,
    GpuPowerState,
    PowerActuator,
    load_power_actuator_config,
    parse_power_query,
    preflight_power_actuator,
    restore_power_from_manifest,
)


class FakePowerBackend:
    def __init__(self, states: tuple[GpuPowerState, ...]) -> None:
        self.states = {state.gpu_id: state for state in states}
        self.set_calls: list[tuple[int, float]] = []
        self.fail_once_on_call: int | None = None

    def query(self) -> tuple[GpuPowerState, ...]:
        return tuple(self.states[gpu_id] for gpu_id in sorted(self.states))

    def set_power_limit(self, gpu_id: int, watts: float) -> None:
        self.set_calls.append((gpu_id, watts))
        if self.fail_once_on_call == len(self.set_calls):
            self.fail_once_on_call = None
            raise ActuatorError("injected set failure")
        old = self.states[gpu_id]
        self.states[gpu_id] = replace(old, current_limit_w=watts)


@pytest.fixture
def gpu_states() -> tuple[GpuPowerState, ...]:
    return tuple(
        GpuPowerState(
            gpu_id=gpu_id,
            gpu_uuid=f"GPU-{gpu_id}",
            default_limit_w=300.0,
            minimum_limit_w=250.0,
            maximum_limit_w=325.0,
            current_limit_w=300.0,
            temperature_c=40.0 + gpu_id,
        )
        for gpu_id in range(4)
    )


def _config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "configs/hardware/four_gpu_node.yaml"


def test_power_query_parser_validates_exact_fields() -> None:
    output = (
        "0, GPU-zero, 300.00, 250.00, 325.00, 300.00, 41\n"
        "1, GPU-one, 300.00, 250.00, 325.00, 300.00, 42\n"
    )
    states = parse_power_query(output)
    assert [state.gpu_id for state in states] == [0, 1]
    assert states[0].default_limit_w == 300.0
    with pytest.raises(ActuatorError, match="expected 7"):
        parse_power_query("0, GPU-zero\n")


def test_preflight_resolves_distinct_device_limits_and_blocks_disabled_execute(
    gpu_states: tuple[GpuPowerState, ...],
) -> None:
    config = load_power_actuator_config(_config_path())
    result = preflight_power_actuator(config, FakePowerBackend(gpu_states))
    assert result.ready_for_dry_run
    assert not result.ready_for_execute
    assert result.inference_cap_levels_w == (252.0, 276.0, 300.0)
    assert result.batch_cap_levels_w == (252.0, 276.0, 300.0)
    assert not result.collapsed_inference_levels
    assert not result.collapsed_batch_levels
    assert result.canonical_action_count == 27
    assert result.unique_physical_action_count == 27
    assert not any("duplicate" in reason for reason in result.dry_run_only_reasons)


def test_preflight_detects_ratios_that_collapse_at_device_minimum(
    gpu_states: tuple[GpuPowerState, ...],
) -> None:
    config = replace(
        load_power_actuator_config(_config_path()),
        batch_cap_ratios=(0.6, 0.8, 1.0),
    )
    result = preflight_power_actuator(config, FakePowerBackend(gpu_states))
    assert result.batch_cap_levels_w == (250.0, 250.0, 300.0)
    assert result.collapsed_batch_levels
    assert result.unique_physical_action_count == 18
    assert any("duplicate" in reason for reason in result.dry_run_only_reasons)


def test_dry_run_captures_restore_manifest_without_setting_power(
    tmp_path: Path,
    gpu_states: tuple[GpuPowerState, ...],
) -> None:
    backend = FakePowerBackend(gpu_states)
    actuator = PowerActuator(
        load_power_actuator_config(_config_path()),
        backend,
        restore_manifest=tmp_path / "restore.json",
        audit_log=tmp_path / "audit.jsonl",
    )
    actuator.prepare()
    result = actuator.apply_action(0, caller="pytest")
    actuator.restore(reason="test_complete")

    assert result.dry_run
    assert not backend.set_calls
    assert [target.target_limit_w for target in result.targets] == [252.0] * 4
    manifest = json.loads((tmp_path / "restore.json").read_text(encoding="utf-8"))
    assert manifest["allowed_gpu_ids"] == [0, 1, 2, 3]
    assert len(manifest["gpus"]) == 4
    assert len((tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()) == 3


def test_execute_requires_all_gates_and_restores_after_partial_failure(
    tmp_path: Path,
    gpu_states: tuple[GpuPowerState, ...],
) -> None:
    base_config = load_power_actuator_config(_config_path())
    config = replace(
        base_config,
        allow_hardware_mutation=True,
        maximum_temperature_c=85.0,
        reject_collapsed_cap_levels=False,
        require_topology_check=False,
    )
    backend = FakePowerBackend(gpu_states)
    backend.fail_once_on_call = 2
    actuator = PowerActuator(
        config,
        backend,
        restore_manifest=tmp_path / "restore.json",
        audit_log=tmp_path / "audit.jsonl",
        dry_run=False,
    )
    actuator.prepare()

    with pytest.raises(ActuatorError, match="injected set failure"):
        actuator.apply_action(0, caller="pytest")

    assert all(state.current_limit_w == 300.0 for state in backend.query())
    assert backend.set_calls[-4:] == [(0, 300.0), (1, 300.0), (2, 300.0), (3, 300.0)]


def test_independent_restore_checks_uuid_before_mutation(
    tmp_path: Path,
    gpu_states: tuple[GpuPowerState, ...],
) -> None:
    backend = FakePowerBackend(gpu_states)
    actuator = PowerActuator(
        load_power_actuator_config(_config_path()),
        backend,
        restore_manifest=tmp_path / "restore.json",
        audit_log=tmp_path / "audit.jsonl",
    )
    actuator.prepare()
    summary = restore_power_from_manifest(tmp_path / "restore.json", backend)
    assert summary["dry_run"] is True
    assert not backend.set_calls

    backend.states[0] = replace(backend.states[0], gpu_uuid="GPU-replaced")
    with pytest.raises(ActuatorError, match="UUID does not match"):
        restore_power_from_manifest(tmp_path / "restore.json", backend, dry_run=False)
    assert not backend.set_calls
