"""Allow-listed GPU power actuator with dry-run default and restoration."""

from __future__ import annotations

import csv
import hashlib
import json
import socket
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import yaml

from aidrbench.envs.actions import ActionComponents, decode_action
from aidrbench.hil.topology import (
    TopologyBackend,
    TopologySnapshot,
    check_inference_topology,
)

POWER_QUERY_FIELDS = (
    "index",
    "uuid",
    "power.default_limit",
    "power.min_limit",
    "power.max_limit",
    "power.limit",
    "temperature.gpu",
)


class ActuatorError(RuntimeError):
    """Raised when the actuator cannot prove that a mutation is safe."""


@dataclass(frozen=True, slots=True)
class GpuPowerState:
    """Fresh device-reported power and temperature limits."""

    gpu_id: int
    gpu_uuid: str
    default_limit_w: float
    minimum_limit_w: float
    maximum_limit_w: float
    current_limit_w: float
    temperature_c: float


class PowerBackend(Protocol):
    """Minimal backend kept injectable for mutation-free tests."""

    def query(self) -> tuple[GpuPowerState, ...]: ...

    def set_power_limit(self, gpu_id: int, watts: float) -> None: ...


@dataclass(frozen=True, slots=True)
class PowerActuatorConfig:
    """Hardware allow-list and safe action levels loaded from tracked YAML."""

    config_path: str
    config_sha256: str
    expected_gpu_count: int
    inference_gpu_ids: tuple[int, ...]
    batch_gpu_ids: tuple[int, ...]
    inference_cap_ratios: tuple[float, ...]
    batch_cap_ratios: tuple[float, ...]
    maximum_temperature_c: float | None
    allow_hardware_mutation: bool
    reject_collapsed_cap_levels: bool
    require_topology_check: bool
    require_inference_p2p: bool

    @property
    def allowed_gpu_ids(self) -> tuple[int, ...]:
        return self.inference_gpu_ids + self.batch_gpu_ids


@dataclass(frozen=True, slots=True)
class ResolvedPowerTarget:
    """One validated absolute limit derived from a normalized action."""

    gpu_id: int
    requested_ratio: float
    target_limit_w: float
    effective_ratio: float


@dataclass(frozen=True, slots=True)
class ActuatorPreflight:
    """Read-only decision record produced before any power mutation."""

    ready_for_dry_run: bool
    ready_for_execute: bool
    dry_run_only_reasons: tuple[str, ...]
    gpu_states: tuple[GpuPowerState, ...]
    inference_cap_levels_w: tuple[float, ...]
    batch_cap_levels_w: tuple[float, ...]
    canonical_action_count: int
    unique_physical_action_count: int
    collapsed_inference_levels: bool
    collapsed_batch_levels: bool
    inference_pair_paths: tuple[str, ...]
    inference_p2p_read_write_ok: bool | None
    topology_warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ActuationResult:
    """Machine-readable record for one dry-run or applied action."""

    action_id: int
    components: ActionComponents
    dry_run: bool
    caller: str
    targets: tuple[ResolvedPowerTarget, ...]
    active_batch_gpus: int
    restored_after_failure: bool


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _id_sequence(value: object, name: str) -> tuple[int, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    ids: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int) or item < 0:
            raise ValueError(f"{name} entries must be non-negative integers")
        if item in ids:
            raise ValueError(f"{name} contains duplicate GPU ID {item}")
        ids.append(item)
    return tuple(ids)


def _ratio_sequence(value: object, name: str) -> tuple[float, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    result: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int | float):
            raise ValueError(f"{name} entries must be numbers")
        ratio = float(item)
        if not 0.0 < ratio <= 1.0:
            raise ValueError(f"{name} entries must be in (0, 1]")
        if ratio in result:
            raise ValueError(f"{name} contains duplicate ratio {ratio:g}")
        result.append(ratio)
    return tuple(result)


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _optional_positive_float(value: object, name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        raise ValueError(f"{name} must be positive or null")
    return float(value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_power_actuator_config(path: str | Path) -> PowerActuatorConfig:
    """Load the mutation boundary from the tracked hardware configuration."""

    config_path = Path(path)
    with config_path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    root = _mapping(document, "hardware config")
    power = _mapping(root.get("power"), "power")
    safety = _mapping(root.get("safety"), "safety")
    inference_ids = _id_sequence(root.get("inference_gpu_ids"), "inference_gpu_ids")
    batch_ids = _id_sequence(root.get("batch_gpu_ids"), "batch_gpu_ids")
    if set(inference_ids) & set(batch_ids):
        raise ValueError("inference and batch GPU allow-lists must be disjoint")
    expected_gpu_count = _positive_int(root.get("expected_gpu_count"), "expected_gpu_count")
    if len(inference_ids) + len(batch_ids) != expected_gpu_count:
        raise ValueError("configured GPU role counts do not match expected_gpu_count")
    allow_mutation = safety.get("allow_hardware_mutation", False)
    reject_collapsed = safety.get("reject_collapsed_cap_levels", True)
    require_topology = root.get("require_topology_check", True)
    require_p2p = safety.get("require_inference_p2p", True)
    if not isinstance(allow_mutation, bool):
        raise ValueError("safety.allow_hardware_mutation must be a boolean")
    if not isinstance(reject_collapsed, bool):
        raise ValueError("safety.reject_collapsed_cap_levels must be a boolean")
    if not isinstance(require_topology, bool):
        raise ValueError("require_topology_check must be a boolean")
    if not isinstance(require_p2p, bool):
        raise ValueError("safety.require_inference_p2p must be a boolean")
    return PowerActuatorConfig(
        config_path=str(config_path),
        config_sha256=_sha256(config_path),
        expected_gpu_count=expected_gpu_count,
        inference_gpu_ids=inference_ids,
        batch_gpu_ids=batch_ids,
        inference_cap_ratios=_ratio_sequence(
            power.get("infer_cap_ratios"), "power.infer_cap_ratios"
        ),
        batch_cap_ratios=_ratio_sequence(
            power.get("batch_cap_ratios"), "power.batch_cap_ratios"
        ),
        maximum_temperature_c=_optional_positive_float(
            safety.get("max_gpu_temperature_c"), "safety.max_gpu_temperature_c"
        ),
        allow_hardware_mutation=allow_mutation,
        reject_collapsed_cap_levels=reject_collapsed,
        require_topology_check=require_topology,
        require_inference_p2p=require_p2p,
    )


def parse_power_query(output: str) -> tuple[GpuPowerState, ...]:
    """Parse the exact nounits CSV emitted by :class:`NvidiaSmiPowerBackend`."""

    states: list[GpuPowerState] = []
    for row_number, row in enumerate(csv.reader(output.splitlines()), start=1):
        if not row or all(not value.strip() for value in row):
            continue
        if len(row) != len(POWER_QUERY_FIELDS):
            raise ActuatorError(
                f"power query row {row_number} has {len(row)} fields; "
                f"expected {len(POWER_QUERY_FIELDS)}"
            )
        values = [value.strip() for value in row]
        try:
            gpu_id_float = float(values[0])
            if not gpu_id_float.is_integer():
                raise ValueError
            state = GpuPowerState(
                gpu_id=int(gpu_id_float),
                gpu_uuid=values[1],
                default_limit_w=float(values[2]),
                minimum_limit_w=float(values[3]),
                maximum_limit_w=float(values[4]),
                current_limit_w=float(values[5]),
                temperature_c=float(values[6]),
            )
        except ValueError as exc:
            raise ActuatorError(f"invalid numeric value in power query row {row_number}") from exc
        if not state.gpu_uuid:
            raise ActuatorError(f"missing GPU UUID in power query row {row_number}")
        if not (
            0.0 < state.minimum_limit_w
            <= state.default_limit_w
            <= state.maximum_limit_w
        ):
            raise ActuatorError(f"invalid device power range for GPU {state.gpu_id}")
        states.append(state)
    if not states:
        raise ActuatorError("power query returned no GPUs")
    if len({state.gpu_id for state in states}) != len(states):
        raise ActuatorError("power query returned duplicate GPU IDs")
    if len({state.gpu_uuid for state in states}) != len(states):
        raise ActuatorError("power query returned duplicate GPU UUIDs")
    return tuple(sorted(states, key=lambda state: state.gpu_id))


class NvidiaSmiPowerBackend:
    """No-shell nvidia-smi adapter; privilege is external to this process."""

    def __init__(self, executable: str = "nvidia-smi", *, timeout_seconds: float = 5.0) -> None:
        if not executable:
            raise ValueError("nvidia-smi executable must not be empty")
        if timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be positive")
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    def _run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise ActuatorError(f"executable not found: {command[0]}") from exc
        except subprocess.TimeoutExpired as exc:
            raise ActuatorError("nvidia-smi command timed out") from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "no diagnostic output"
            raise ActuatorError(
                f"nvidia-smi failed with exit code {completed.returncode}: {detail}"
            )
        return completed

    def query(self) -> tuple[GpuPowerState, ...]:
        completed = self._run(
            [
                self.executable,
                f"--query-gpu={','.join(POWER_QUERY_FIELDS)}",
                "--format=csv,noheader,nounits",
            ]
        )
        return parse_power_query(completed.stdout)

    def set_power_limit(self, gpu_id: int, watts: float) -> None:
        self._run(
            [
                self.executable,
                "--id",
                str(gpu_id),
                "--power-limit",
                f"{watts:.2f}",
            ]
        )


def _resolve_limit(state: GpuPowerState, ratio: float) -> ResolvedPowerTarget:
    target = min(max(ratio * state.default_limit_w, state.minimum_limit_w), state.default_limit_w)
    return ResolvedPowerTarget(
        gpu_id=state.gpu_id,
        requested_ratio=ratio,
        target_limit_w=round(target, 6),
        effective_ratio=round(target / state.default_limit_w, 6),
    )


def _state_by_id(states: Sequence[GpuPowerState]) -> dict[int, GpuPowerState]:
    return {state.gpu_id: state for state in states}


def _validate_inventory(
    config: PowerActuatorConfig,
    states: Sequence[GpuPowerState],
) -> dict[int, GpuPowerState]:
    by_id = _state_by_id(states)
    returned = set(by_id)
    allowed = set(config.allowed_gpu_ids)
    if len(states) != config.expected_gpu_count or returned != allowed:
        raise ActuatorError(
            f"GPU inventory mismatch; expected IDs {sorted(allowed)}, got {sorted(returned)}"
        )
    return by_id


def preflight_power_actuator(
    config: PowerActuatorConfig,
    backend: PowerBackend,
    topology_snapshot: TopologySnapshot | None = None,
) -> ActuatorPreflight:
    """Perform fresh read-only checks and detect collapsed physical actions."""

    states = backend.query()
    by_id = _validate_inventory(config, states)
    inference_reference = by_id[config.inference_gpu_ids[0]]
    batch_reference = by_id[config.batch_gpu_ids[0]]
    inference_levels = tuple(
        _resolve_limit(inference_reference, ratio).target_limit_w
        for ratio in config.inference_cap_ratios
    )
    batch_levels = tuple(
        _resolve_limit(batch_reference, ratio).target_limit_w
        for ratio in config.batch_cap_ratios
    )
    collapsed_inference = len(set(inference_levels)) != len(inference_levels)
    collapsed_batch = len(set(batch_levels)) != len(batch_levels)
    physical_actions = {
        (inference_limit, active_batch_gpus, batch_limit)
        for inference_limit in inference_levels
        for active_batch_gpus in range(len(config.batch_gpu_ids) + 1)
        for batch_limit in batch_levels
    }
    reasons: list[str] = []
    if not config.allow_hardware_mutation:
        reasons.append("safety.allow_hardware_mutation is false")
    if config.maximum_temperature_c is None:
        reasons.append("safety.max_gpu_temperature_c is not configured")
    elif any(state.temperature_c > config.maximum_temperature_c for state in states):
        reasons.append("one or more GPU temperatures exceed the configured limit")
    if config.reject_collapsed_cap_levels and (collapsed_inference or collapsed_batch):
        reasons.append("configured cap ratios collapse to duplicate device power limits")
    inference_pair_paths: tuple[str, ...] = ()
    inference_p2p_ok: bool | None = None
    topology_warnings: tuple[str, ...] = ()
    if topology_snapshot is None:
        if config.require_topology_check:
            reasons.append("required GPU topology/P2P check was not supplied")
    else:
        topology_check = check_inference_topology(
            topology_snapshot,
            config.inference_gpu_ids,
            require_p2p=config.require_inference_p2p,
        )
        inference_pair_paths = topology_check.pair_paths
        inference_p2p_ok = topology_check.p2p_read_write_ok
        topology_warnings = topology_check.warnings
        if not topology_check.valid:
            reasons.extend(topology_check.errors)
    return ActuatorPreflight(
        ready_for_dry_run=True,
        ready_for_execute=not reasons,
        dry_run_only_reasons=tuple(reasons),
        gpu_states=tuple(states),
        inference_cap_levels_w=inference_levels,
        batch_cap_levels_w=batch_levels,
        canonical_action_count=(
            len(config.inference_cap_ratios)
            * (len(config.batch_gpu_ids) + 1)
            * len(config.batch_cap_ratios)
        ),
        unique_physical_action_count=len(physical_actions),
        collapsed_inference_levels=collapsed_inference,
        collapsed_batch_levels=collapsed_batch,
        inference_pair_paths=inference_pair_paths,
        inference_p2p_read_write_ok=inference_p2p_ok,
        topology_warnings=topology_warnings,
    )


def write_restore_manifest(
    config: PowerActuatorConfig,
    states: Sequence[GpuPowerState],
    output: str | Path,
    *,
    topology_snapshot: TopologySnapshot | None = None,
) -> None:
    """Persist defaults before mutation so another process can restore them."""

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "schema_version": 1,
        "created_at_utc": datetime.now(UTC).isoformat(timespec="microseconds"),
        "hostname": socket.gethostname(),
        "config_path": config.config_path,
        "config_sha256": config.config_sha256,
        "allowed_gpu_ids": list(config.allowed_gpu_ids),
        "gpus": [asdict(state) for state in states],
    }
    if topology_snapshot is not None:
        document["topology"] = {
            "links": asdict(topology_snapshot.links),
            "p2p_read": asdict(topology_snapshot.p2p_read),
            "p2p_write": asdict(topology_snapshot.p2p_write),
            "raw_links": topology_snapshot.raw_links,
            "raw_p2p_read": topology_snapshot.raw_p2p_read,
            "raw_p2p_write": topology_snapshot.raw_p2p_write,
        }
    output_path.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _audit(path: Path, event: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="microseconds"),
        **event,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


class PowerActuator:
    """Validated action adapter; mutation requires two independent gates."""

    def __init__(
        self,
        config: PowerActuatorConfig,
        backend: PowerBackend,
        *,
        restore_manifest: str | Path,
        audit_log: str | Path,
        dry_run: bool = True,
        topology_backend: TopologyBackend | None = None,
    ) -> None:
        self.config = config
        self.backend = backend
        self.restore_manifest = Path(restore_manifest)
        self.audit_log = Path(audit_log)
        self.dry_run = dry_run
        self.topology_backend = topology_backend
        self._initial_states: tuple[GpuPowerState, ...] | None = None
        self._preflight: ActuatorPreflight | None = None

    def prepare(self) -> ActuatorPreflight:
        """Capture immutable defaults and prove readiness before the first action."""

        topology_snapshot = (
            self.topology_backend.query_topology()
            if self.topology_backend is not None
            else None
        )
        preflight = preflight_power_actuator(
            self.config,
            self.backend,
            topology_snapshot,
        )
        if not self.dry_run and not preflight.ready_for_execute:
            raise ActuatorError(
                "hardware execution is blocked: " + "; ".join(preflight.dry_run_only_reasons)
            )
        self._initial_states = preflight.gpu_states
        self._preflight = preflight
        write_restore_manifest(
            self.config,
            preflight.gpu_states,
            self.restore_manifest,
            topology_snapshot=topology_snapshot,
        )
        _audit(
            self.audit_log,
            {
                "event": "prepare",
                "dry_run": self.dry_run,
                "ready_for_execute": preflight.ready_for_execute,
                "reasons": preflight.dry_run_only_reasons,
            },
        )
        return preflight

    def _targets(self, components: ActionComponents) -> tuple[ResolvedPowerTarget, ...]:
        if self._initial_states is None:
            raise ActuatorError("actuator.prepare() must be called before applying actions")
        by_id = _validate_inventory(self.config, self.backend.query())
        if self.config.maximum_temperature_c is not None:
            overheated = [
                state.gpu_id
                for state in by_id.values()
                if state.temperature_c > self.config.maximum_temperature_c
            ]
            if overheated:
                raise ActuatorError(f"GPU temperature limit exceeded on IDs {overheated}")
        targets: list[ResolvedPowerTarget] = []
        for gpu_id in self.config.inference_gpu_ids:
            targets.append(_resolve_limit(by_id[gpu_id], components.inference_cap_ratio))
        for gpu_id in self.config.batch_gpu_ids:
            targets.append(_resolve_limit(by_id[gpu_id], components.batch_cap_ratio))
        return tuple(targets)

    def apply_action(self, action_id: int, *, caller: str) -> ActuationResult:
        """Decode one canonical action, validate it, and optionally apply limits."""

        if not caller.strip():
            raise ValueError("caller must not be empty")
        if self._preflight is None:
            raise ActuatorError("actuator.prepare() must be called before applying actions")
        components = decode_action(action_id)
        if (
            components.inference_cap_ratio not in self.config.inference_cap_ratios
            or components.batch_cap_ratio not in self.config.batch_cap_ratios
            or components.batch_gpu_count > len(self.config.batch_gpu_ids)
        ):
            raise ActuatorError("canonical action is not allowed by the hardware configuration")
        targets = self._targets(components)
        restored_after_failure = False
        if not self.dry_run:
            if not self._preflight.ready_for_execute:
                raise ActuatorError("preflight did not authorize hardware execution")
            try:
                for target in targets:
                    self.backend.set_power_limit(target.gpu_id, target.target_limit_w)
                actual = _state_by_id(self.backend.query())
                mismatched = [
                    target.gpu_id
                    for target in targets
                    if target.gpu_id not in actual
                    or abs(actual[target.gpu_id].current_limit_w - target.target_limit_w) > 0.51
                ]
                if mismatched:
                    raise ActuatorError(f"power-limit verification failed for GPUs {mismatched}")
            except Exception:
                restored_after_failure = True
                self.restore(reason="actuation_failure")
                raise
        result = ActuationResult(
            action_id=action_id,
            components=components,
            dry_run=self.dry_run,
            caller=caller,
            targets=targets,
            active_batch_gpus=components.batch_gpu_count,
            restored_after_failure=restored_after_failure,
        )
        _audit(
            self.audit_log,
            {
                "event": "apply_action",
                "action_id": action_id,
                "caller": caller,
                "dry_run": self.dry_run,
                "components": asdict(components),
                "targets": [asdict(target) for target in targets],
            },
        )
        return result

    def restore(self, *, reason: str) -> None:
        """Restore every captured default; attempt all GPUs even after one failure."""

        if self._initial_states is None:
            return
        failures: list[str] = []
        if not self.dry_run:
            current = _state_by_id(self.backend.query())
            for initial in self._initial_states:
                actual = current.get(initial.gpu_id)
                if actual is None or actual.gpu_uuid != initial.gpu_uuid:
                    failures.append(f"GPU {initial.gpu_id} identity mismatch")
                    continue
                try:
                    self.backend.set_power_limit(initial.gpu_id, initial.default_limit_w)
                except Exception as exc:  # continue restoration of the other allow-listed GPUs
                    failures.append(f"GPU {initial.gpu_id}: {exc}")
        _audit(
            self.audit_log,
            {
                "event": "restore",
                "reason": reason,
                "dry_run": self.dry_run,
                "failures": failures,
            },
        )
        if failures:
            raise ActuatorError("power restoration failed: " + "; ".join(failures))


def restore_power_from_manifest(
    manifest: str | Path,
    backend: PowerBackend,
    *,
    dry_run: bool = True,
) -> dict[str, object]:
    """Independent emergency restore path that validates GPU UUIDs first."""

    manifest_path = Path(manifest)
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = _mapping(document, "restore manifest")
    if root.get("schema_version") != 1:
        raise ActuatorError("unsupported restore manifest schema_version")
    raw_gpus = root.get("gpus")
    if not isinstance(raw_gpus, list) or not raw_gpus:
        raise ActuatorError("restore manifest must contain GPU defaults")
    defaults: list[GpuPowerState] = []
    for index, raw_state in enumerate(raw_gpus):
        state = _mapping(raw_state, f"gpus[{index}]")
        try:
            defaults.append(
                GpuPowerState(
                    gpu_id=int(state["gpu_id"]),
                    gpu_uuid=str(state["gpu_uuid"]),
                    default_limit_w=float(state["default_limit_w"]),
                    minimum_limit_w=float(state["minimum_limit_w"]),
                    maximum_limit_w=float(state["maximum_limit_w"]),
                    current_limit_w=float(state["current_limit_w"]),
                    temperature_c=float(state["temperature_c"]),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ActuatorError(f"invalid restore manifest GPU entry {index}") from exc
    current = _state_by_id(backend.query())
    for default in defaults:
        actual = current.get(default.gpu_id)
        if actual is None or actual.gpu_uuid != default.gpu_uuid:
            raise ActuatorError(f"GPU {default.gpu_id} UUID does not match restore manifest")
    if not dry_run:
        failures: list[str] = []
        for default in defaults:
            try:
                backend.set_power_limit(default.gpu_id, default.default_limit_w)
            except Exception as exc:
                failures.append(f"GPU {default.gpu_id}: {exc}")
        if failures:
            raise ActuatorError("power restoration failed: " + "; ".join(failures))
    return {
        "manifest": str(manifest_path),
        "dry_run": dry_run,
        "gpu_ids": [default.gpu_id for default in defaults],
        "default_limits_w": [default.default_limit_w for default in defaults],
        "verified_gpu_uuids": True,
    }


def preflight_dict(preflight: ActuatorPreflight) -> dict[str, object]:
    """Convert a preflight result to JSON-ready primitives."""

    result = asdict(preflight)
    return result


def actuation_result_dict(result: ActuationResult) -> dict[str, object]:
    """Convert an actuation result to JSON-ready primitives."""

    return asdict(result)
