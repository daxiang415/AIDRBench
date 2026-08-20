"""Preregistered development and validation repeated-event exhaustion diagnostics."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import multiprocessing
from collections import Counter
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

import pandas as pd
import yaml

from aidrbench.controllers.hourly import make_hourly_controller
from aidrbench.controllers.robust_mpc_spec import load_robust_mpc_specification
from aidrbench.data.frozen_scenarios import (
    FrozenHourlyScenario,
    freeze_hourly_scenario,
    load_frozen_hourly_scenario,
)
from aidrbench.data.splits import sha256_file
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv
from aidrbench.evaluation.firm_flexibility import (
    EventOutcome,
    FirmFlexibilityCriteria,
    derive_event_outcomes,
)
from aidrbench.evaluation.frozen_causal_certificate import (
    _controller_provenance,
    _git_commit,
)
from aidrbench.evaluation.hourly_rollout import rollout_hourly_episode

_INDEX_NAME = "repeated_scenario_index.json"
_FREEZE_STATE_NAME = "repeated_scenario_freeze_state.json"
_RUN_STATE_NAME = "exhaustion_diagnostics_run.json"
_SOURCE_PATHS = (
    "src/aidrbench/evaluation/exhaustion.py",
    "src/aidrbench/evaluation/firm_flexibility.py",
    "src/aidrbench/evaluation/hourly_rollout.py",
)


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _exact_fields(document: Mapping[str, Any], expected: set[str], name: str) -> None:
    observed = set(document)
    if observed != expected:
        missing = sorted(expected - observed)
        unknown = sorted(observed - expected)
        raise ValueError(f"{name} fields mismatch; missing={missing}, unknown={unknown}")


@dataclass(frozen=True, slots=True)
class RepeatedEventExhaustionSpecification:
    """Strict preregistration for a separate exhaustion mechanism study."""

    schema_version: int
    model_a_git_commit: str
    dataset_role: Literal[
        "development_repeated_event_exhaustion",
        "validation_repeated_event_exhaustion",
    ]
    base_environment_config: str
    base_environment_config_sha256: str | None
    controller_config: str
    controller_config_sha256: str | None
    expected_seed_range: tuple[int, int] | None
    first_event_start_hour: int
    max_event_count: int
    duration_hours: tuple[int, ...]
    recovery_gaps_hours: tuple[int, ...]
    notice_hours: int
    reliability_target: float
    confidence_level: float
    capacity_source_path: str
    capacity_source_sha256: str
    capacity_column: Literal["na_capacity_kw", "pi_empirical_capacity_kw"]
    capacity_notice_hours: int
    criteria: FirmFlexibilityCriteria

    def __post_init__(self) -> None:
        if self.schema_version not in {1, 2}:
            raise ValueError("unsupported exhaustion specification schema_version")
        if len(self.model_a_git_commit) != 40 or any(
            value not in "0123456789abcdef" for value in self.model_a_git_commit
        ):
            raise ValueError("model_a_git_commit must be a lowercase 40-character SHA-1")
        if self.dataset_role not in {
            "development_repeated_event_exhaustion",
            "validation_repeated_event_exhaustion",
        }:
            raise ValueError("unsupported exhaustion dataset_role")
        if self.schema_version == 1:
            if any(
                value is not None
                for value in (
                    self.base_environment_config_sha256,
                    self.controller_config_sha256,
                    self.expected_seed_range,
                )
            ):
                raise ValueError("schema v1 cannot contain v2 provenance fields")
        else:
            for name, provenance_value in (
                ("base_environment_config_sha256", self.base_environment_config_sha256),
                ("controller_config_sha256", self.controller_config_sha256),
            ):
                if provenance_value is None or len(provenance_value) != 64 or any(
                    character not in "0123456789abcdef"
                    for character in provenance_value
                ):
                    raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
            if self.expected_seed_range is None:
                raise ValueError("schema v2 requires expected_seed_range")
            seed_start, seed_end = self.expected_seed_range
            if seed_start < 0 or seed_end < seed_start:
                raise ValueError("expected_seed_range must be increasing and non-negative")
        if self.first_event_start_hour < 0 or self.max_event_count < 2:
            raise ValueError("exhaustion study needs a non-negative start and at least two events")
        if not self.duration_hours or any(value <= 0 for value in self.duration_hours):
            raise ValueError("duration_hours must contain positive integers")
        if tuple(sorted(set(self.duration_hours))) != self.duration_hours:
            raise ValueError("duration_hours must be unique and increasing")
        if not self.recovery_gaps_hours or any(value < 0 for value in self.recovery_gaps_hours):
            raise ValueError("recovery_gaps_hours must contain non-negative integers")
        if tuple(sorted(set(self.recovery_gaps_hours))) != self.recovery_gaps_hours:
            raise ValueError("recovery_gaps_hours must be unique and increasing")
        if self.notice_hours < 0 or self.capacity_notice_hours < 0:
            raise ValueError("notice hours must be non-negative")
        if self.notice_hours != self.capacity_notice_hours:
            raise ValueError("event notice must match the frozen capacity-source notice")
        for name, value in (
            ("reliability_target", self.reliability_target),
            ("confidence_level", self.confidence_level),
        ):
            if not 0.0 < value < 1.0:
                raise ValueError(f"{name} must be in (0, 1)")
        if self.criteria.reliability_target != self.reliability_target:
            raise ValueError("criteria reliability_target must match the study target")
        if self.criteria.confidence_level != self.confidence_level:
            raise ValueError("criteria confidence_level must match the study confidence")
        if len(self.capacity_source_sha256) != 64 or any(
            character not in "0123456789abcdef"
            for character in self.capacity_source_sha256
        ):
            raise ValueError("capacity_source_sha256 must be a lowercase SHA-256 hex digest")
        if self.capacity_column not in {"na_capacity_kw", "pi_empirical_capacity_kw"}:
            raise ValueError("unsupported exhaustion capacity column")

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        if self.schema_version == 1:
            result.pop("base_environment_config_sha256")
            result.pop("controller_config_sha256")
            result.pop("expected_seed_range")
        result["duration_hours"] = list(self.duration_hours)
        result["recovery_gaps_hours"] = list(self.recovery_gaps_hours)
        if self.expected_seed_range is not None:
            result["expected_seed_range"] = list(self.expected_seed_range)
        return result

    @property
    def sha256(self) -> str:
        return _canonical_sha256(self.as_dict())


def load_repeated_event_exhaustion_specification(
    path: str | Path,
) -> RepeatedEventExhaustionSpecification:
    """Load the strict repeated-event study specification."""

    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    document = _mapping(raw, "exhaustion specification")
    expected = {
        "schema_version",
        "model_a_git_commit",
        "dataset_role",
        "base_environment_config",
        "controller_config",
        "first_event_start_hour",
        "max_event_count",
        "duration_hours",
        "recovery_gaps_hours",
        "notice_hours",
        "reliability_target",
        "confidence_level",
        "capacity_source",
        "criteria",
    }
    schema_version = int(document.get("schema_version", -1))
    if schema_version == 2:
        expected.update(
            {
                "base_environment_config_sha256",
                "controller_config_sha256",
                "expected_seed_range",
            }
        )
    _exact_fields(document, expected, "exhaustion specification")
    capacity = _mapping(document["capacity_source"], "capacity_source")
    _exact_fields(
        capacity,
        {"path", "sha256", "column", "notice_hours"},
        "capacity_source",
    )
    criteria = _mapping(document["criteria"], "criteria")
    _exact_fields(
        criteria,
        {
            "min_delivery_ratio",
            "min_interval_delivery_ratio",
            "max_deadline_miss_rate",
            "max_rebound_ratio",
            "min_window_peak_relief_fraction",
            "max_terminal_backlog_fraction",
        },
        "criteria",
    )
    reliability = float(document["reliability_target"])
    confidence = float(document["confidence_level"])
    raw_expected_seed_range = document.get("expected_seed_range")
    expected_seed_range: tuple[int, int] | None = None
    if isinstance(raw_expected_seed_range, list):
        if len(raw_expected_seed_range) != 2:
            raise ValueError("expected_seed_range must contain exactly two integers")
        expected_seed_range = (
            int(raw_expected_seed_range[0]),
            int(raw_expected_seed_range[1]),
        )
    return RepeatedEventExhaustionSpecification(
        schema_version=schema_version,
        model_a_git_commit=str(document["model_a_git_commit"]),
        dataset_role=str(document["dataset_role"]),  # type: ignore[arg-type]
        base_environment_config=str(document["base_environment_config"]),
        base_environment_config_sha256=(
            str(document["base_environment_config_sha256"])
            if document.get("base_environment_config_sha256") is not None
            else None
        ),
        controller_config=str(document["controller_config"]),
        controller_config_sha256=(
            str(document["controller_config_sha256"])
            if document.get("controller_config_sha256") is not None
            else None
        ),
        expected_seed_range=expected_seed_range,
        first_event_start_hour=int(document["first_event_start_hour"]),
        max_event_count=int(document["max_event_count"]),
        duration_hours=tuple(int(value) for value in document["duration_hours"]),
        recovery_gaps_hours=tuple(
            int(value) for value in document["recovery_gaps_hours"]
        ),
        notice_hours=int(document["notice_hours"]),
        reliability_target=reliability,
        confidence_level=confidence,
        capacity_source_path=str(capacity["path"]),
        capacity_source_sha256=str(capacity["sha256"]),
        capacity_column=str(capacity["column"]),  # type: ignore[arg-type]
        capacity_notice_hours=int(capacity["notice_hours"]),
        criteria=FirmFlexibilityCriteria(
            reliability_target=reliability,
            confidence_level=confidence,
            min_delivery_ratio=float(criteria["min_delivery_ratio"]),
            min_interval_delivery_ratio=float(criteria["min_interval_delivery_ratio"]),
            max_deadline_miss_rate=float(criteria["max_deadline_miss_rate"]),
            max_rebound_ratio=float(criteria["max_rebound_ratio"]),
            min_window_peak_relief_fraction=float(
                criteria["min_window_peak_relief_fraction"]
            ),
            max_terminal_backlog_fraction=float(
                criteria["max_terminal_backlog_fraction"]
            ),
        ),
    )


def _validate_v2_provenance_files(
    specification: RepeatedEventExhaustionSpecification,
) -> None:
    if specification.schema_version < 2:
        return
    declared_files = (
        (
            "base environment config",
            Path(specification.base_environment_config),
            specification.base_environment_config_sha256,
        ),
        (
            "controller config",
            Path(specification.controller_config),
            specification.controller_config_sha256,
        ),
    )
    for label, path, expected_sha256 in declared_files:
        if not path.is_file():
            raise FileNotFoundError(path)
        actual_sha256 = sha256_file(path)
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"exhaustion {label} SHA-256 mismatch: expected "
                f"{expected_sha256}, got {actual_sha256}"
            )


def _validate_declared_seeds(
    specification: RepeatedEventExhaustionSpecification,
    seeds: Sequence[int],
) -> None:
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("exhaustion seeds must be non-empty and unique")
    if specification.expected_seed_range is None:
        return
    start, end = specification.expected_seed_range
    expected = tuple(range(start, end + 1))
    if tuple(seeds) != expected:
        raise ValueError(
            "exhaustion seeds must exactly match expected_seed_range "
            f"[{start}, {end}] in increasing order"
        )


def repeated_event_start_hours(
    specification: RepeatedEventExhaustionSpecification,
    *,
    duration_h: int,
    recovery_gap_h: int,
    main_hours: int,
) -> tuple[int, ...]:
    """Return the declared event chain and reject a truncated last event."""

    starts = tuple(
        specification.first_event_start_hour
        + ordinal * (duration_h + recovery_gap_h)
        for ordinal in range(specification.max_event_count)
    )
    if starts[-1] + duration_h > main_hours:
        raise ValueError(
            f"H={duration_h}, gap={recovery_gap_h} repeated-event chain exceeds horizon"
        )
    return starts


def _capacity_by_duration(
    specification: RepeatedEventExhaustionSpecification,
) -> dict[int, float]:
    path = Path(specification.capacity_source_path)
    if sha256_file(path) != specification.capacity_source_sha256:
        raise ValueError("exhaustion capacity-source SHA-256 mismatch")
    frame = pd.read_parquet(path)
    capacities: dict[int, float] = {}
    for duration_h in specification.duration_hours:
        selected = frame.loc[
            (frame["duration_h"].astype(int) == duration_h)
            & (
                frame["notice_h"].astype(int)
                == specification.capacity_notice_hours
            )
        ]
        if len(selected) != 1:
            raise ValueError("capacity source needs exactly one row per duration/notice")
        value = float(selected[specification.capacity_column].iloc[0])
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError("capacity source contains a non-positive capacity")
        capacities[duration_h] = value
    return capacities


def freeze_repeated_event_scenarios(
    specification_path: str | Path,
    *,
    seeds: Sequence[int],
    output_directory: str | Path,
) -> dict[str, Any]:
    """Freeze or resume separate development/validation scenarios per H/gap program."""

    specification = load_repeated_event_exhaustion_specification(specification_path)
    _validate_v2_provenance_files(specification)
    _validate_declared_seeds(specification, seeds)
    base_path = Path(specification.base_environment_config)
    raw = yaml.safe_load(base_path.read_text(encoding="utf-8"))
    base = _mapping(raw, "base_environment_config")
    env = _mapping(base.get("env"), "base_environment_config.env")
    if specification.expected_seed_range is not None:
        declared_seed_range = env.get("episode_seed_range")
        if declared_seed_range != list(specification.expected_seed_range):
            raise ValueError(
                "base environment episode_seed_range does not match exhaustion specification"
            )
    main_hours = int(env["episode_days"]) * 24
    capacity_by_duration = _capacity_by_duration(specification)
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    expected_program_names = {
        f"duration_{duration_h}h_gap_{recovery_gap_h}h"
        for duration_h in specification.duration_hours
        for recovery_gap_h in specification.recovery_gaps_hours
    }
    allowed_top_level = expected_program_names | {_INDEX_NAME, _FREEZE_STATE_NAME}
    unexpected_top_level = sorted(
        child.name for child in output.iterdir() if child.name not in allowed_top_level
    )
    if unexpected_top_level:
        raise ValueError(
            "repeated-event scenario output contains unexpected entries: "
            f"{unexpected_top_level}"
        )
    freeze_state_path = output / _FREEZE_STATE_NAME
    freeze_identity = {
        "schema_version": 1,
        "dataset_role": specification.dataset_role,
        "locked_data_read": False,
        "model_a_git_commit": specification.model_a_git_commit,
        "specification_sha256": specification.sha256,
        "specification_file_sha256": sha256_file(Path(specification_path)),
        "seeds": list(seeds),
    }
    completed_by_program: dict[str, dict[str, Any]]
    if freeze_state_path.is_file():
        freeze_state = json.loads(freeze_state_path.read_text(encoding="utf-8"))
        if not isinstance(freeze_state, Mapping):
            raise ValueError("repeated-event freeze state must be a mapping")
        if {key: freeze_state.get(key) for key in freeze_identity} != freeze_identity:
            raise ValueError("repeated-event scenario freeze state mismatch")
        completed = freeze_state.get("completed")
        if not isinstance(completed, Mapping):
            raise ValueError("repeated-event freeze state has no completed mapping")
        completed_by_program = {
            str(key): dict(value)
            for key, value in completed.items()
            if isinstance(value, Mapping)
        }
        if len(completed_by_program) != len(completed):
            raise ValueError("repeated-event freeze state completed entry is invalid")
    else:
        if (output / _INDEX_NAME).is_file():
            raise ValueError(
                "legacy repeated-event output has no resumable freeze state"
            )
        completed_by_program = {}
        freeze_state_path.write_text(
            json.dumps(
                {**freeze_identity, "completed": completed_by_program},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    programs: list[dict[str, Any]] = []
    resumed_scenario_count = 0
    frozen_scenario_count = 0
    for duration_h in specification.duration_hours:
        for recovery_gap_h in specification.recovery_gaps_hours:
            starts = repeated_event_start_hours(
                specification,
                duration_h=duration_h,
                recovery_gap_h=recovery_gap_h,
                main_hours=main_hours,
            )
            document = copy.deepcopy(base)
            raw_scenario = document.get("scenario")
            scenario = dict(raw_scenario) if isinstance(raw_scenario, Mapping) else {}
            scenario["dataset_role"] = specification.dataset_role
            document["scenario"] = scenario
            dr = _mapping(document.get("dr"), "base_environment_config.dr")
            for field in (
                "event_start_hour_choices",
                "event_duration_choices",
                "event_notice_choices",
                "event_reduction_fraction_range",
            ):
                dr.pop(field, None)
            dr.update(
                {
                    "source": "configured",
                    "events_path": None,
                    "event_start_hours": list(starts),
                    "event_duration_hours": duration_h,
                    "event_notice_hours": specification.notice_hours,
                    "event_reduction_kw": capacity_by_duration[duration_h],
                    "event_start_jitter_hours": 0,
                }
            )
            document["dr"] = dr
            program_name = f"duration_{duration_h}h_gap_{recovery_gap_h}h"
            program_directory = output / program_name
            program_directory.mkdir(exist_ok=True)
            completed_program = completed_by_program.setdefault(program_name, {})
            expected_scenario_names = {
                str(record["scenario_id"])
                for record in completed_program.values()
                if isinstance(record, Mapping) and "scenario_id" in record
            }
            unexpected_program_entries = sorted(
                child.name
                for child in program_directory.iterdir()
                if child.name not in expected_scenario_names
            )
            if unexpected_program_entries:
                raise ValueError(
                    "repeated-event program contains unexpected entries: "
                    f"{unexpected_program_entries}"
                )
            frozen: list[dict[str, Any]] = []
            expected_document_sha256 = _canonical_sha256(document)
            for seed in seeds:
                seed_key = str(seed)
                raw_record = completed_program.get(seed_key)
                if raw_record is not None:
                    record = _mapping(raw_record, "completed exhaustion scenario")
                    _exact_fields(
                        record,
                        {"scenario_id", "scenario_hash", "directory"},
                        "completed exhaustion scenario",
                    )
                    scenario_directory = Path(str(record["directory"]))
                    if scenario_directory != program_directory / str(
                        record["scenario_id"]
                    ):
                        raise ValueError("resumed exhaustion scenario directory mismatch")
                    artifact = load_frozen_hourly_scenario(scenario_directory)
                    if artifact.scenario_hash != record["scenario_hash"]:
                        raise ValueError("resumed exhaustion scenario hash mismatch")
                    if (
                        _canonical_sha256(artifact.config_document)
                        != expected_document_sha256
                    ):
                        raise ValueError("resumed exhaustion scenario config mismatch")
                    frozen.append(
                        {
                            "scenario_id": artifact.scenario_id,
                            "episode_seed": artifact.episode_seed,
                            "scenario_hash": artifact.scenario_hash,
                            "output": str(artifact.directory),
                        }
                    )
                    resumed_scenario_count += 1
                else:
                    result = freeze_hourly_scenario(
                        document,
                        seed=seed,
                        output_directory=program_directory,
                    )
                    frozen.append(result)
                    completed_program[seed_key] = {
                        "scenario_id": result["scenario_id"],
                        "scenario_hash": result["scenario_hash"],
                        "directory": result["output"],
                    }
                    temporary_state_path = freeze_state_path.with_name(
                        f".{freeze_state_path.name}.incomplete"
                    )
                    if temporary_state_path.exists():
                        raise FileExistsError(
                            "incomplete repeated-event freeze state exists: "
                            f"{temporary_state_path}"
                        )
                    temporary_state_path.write_text(
                        json.dumps(
                            {**freeze_identity, "completed": completed_by_program},
                            ensure_ascii=False,
                            indent=2,
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                    temporary_state_path.replace(freeze_state_path)
                    frozen_scenario_count += 1
            programs.append(
                {
                    "duration_h": duration_h,
                    "recovery_gap_h": recovery_gap_h,
                    "event_start_hours": list(starts),
                    "fixed_capacity_kw": capacity_by_duration[duration_h],
                    "directory": str(program_directory),
                    "scenario_hashes": [item["scenario_hash"] for item in frozen],
                }
            )
    index_path = output / _INDEX_NAME
    index_document = {
        "schema_version": 1,
        "dataset_role": specification.dataset_role,
        "locked_data_read": False,
        "model_a_git_commit": specification.model_a_git_commit,
        "specification": specification.as_dict(),
        "specification_sha256": specification.sha256,
        "specification_file_sha256": sha256_file(Path(specification_path)),
        "seeds": list(seeds),
        "programs": programs,
    }
    if index_path.is_file():
        observed_index = json.loads(index_path.read_text(encoding="utf-8"))
        if observed_index != index_document:
            raise ValueError("repeated-event scenario resume index mismatch")
    else:
        index_path.write_text(
            json.dumps(index_document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return {
        "index": str(index_path),
        "program_count": len(programs),
        "scenario_count": len(programs) * len(seeds),
        "resumed_scenario_count": resumed_scenario_count,
        "frozen_scenario_count": frozen_scenario_count,
    }


def _repeated_environment_document(
    artifact: FrozenHourlyScenario,
    *,
    notice_h: int,
    requested_reduction_kw: float,
    event_ids: Sequence[int] | None = None,
) -> dict[str, Any]:
    document = copy.deepcopy(artifact.config_document)
    raw_scenario = document.get("scenario")
    scenario = dict(raw_scenario) if isinstance(raw_scenario, Mapping) else {}
    scenario.update(
        {
            "frozen_path": str(artifact.directory),
            "frozen_event_ids": (
                [int(event["event_id"]) for event in artifact.events]
                if event_ids is None
                else list(event_ids)
            ),
            "frozen_event_notice_hours": notice_h,
        }
    )
    scenario.pop("locked_set", None)
    scenario.pop("locked_ood", None)
    scenario.pop("preregistration_manifest", None)
    document["scenario"] = scenario
    dr = _mapping(document.get("dr"), "frozen exhaustion dr")
    dr.update(
        {
            "event_reduction_kw": requested_reduction_kw,
            "event_notice_hours": notice_h,
            "event_start_jitter_hours": 0,
        }
    )
    document["dr"] = dr
    return document


def _minimum_local_service_margin(
    outcome: EventOutcome,
    criteria: FirmFlexibilityCriteria,
) -> float:
    return min(
        outcome.delivery_ratio - criteria.min_delivery_ratio,
        outcome.minimum_interval_delivery_ratio - criteria.min_interval_delivery_ratio,
        criteria.max_rebound_ratio - outcome.rebound_ratio,
        outcome.window_peak_relief_fraction - criteria.min_window_peak_relief_fraction,
    )


def _local_event_decision(
    outcome: EventOutcome,
    criteria: FirmFlexibilityCriteria,
) -> tuple[bool, tuple[str, ...]]:
    """Judge only event-local delivery, rebound and window-relief outcomes."""

    failures: list[str] = []
    if (
        outcome.delivery_ratio + 1e-9 < criteria.min_delivery_ratio
        or outcome.minimum_interval_delivery_ratio + 1e-9
        < criteria.min_interval_delivery_ratio
    ):
        failures.append("delivery")
    if (
        outcome.minimum_interval_delivery_ratio + 1e-9
        < criteria.min_interval_delivery_ratio
    ):
        failures.append("interval_delivery")
    if outcome.rebound_ratio - 1e-9 > criteria.max_rebound_ratio:
        failures.append("rebound")
    if (
        outcome.window_peak_relief_fraction + 1e-9
        < criteria.min_window_peak_relief_fraction
    ):
        failures.append("window_relief")
    return not failures, tuple(failures)


def _rollout_exhaustion_program(
    artifact: FrozenHourlyScenario,
    *,
    capacity_kw: float,
    controller_config: str,
    event_ids: Sequence[int] | None = None,
) -> tuple[pd.DataFrame, list[EventOutcome]]:
    specification = load_robust_mpc_specification(controller_config)
    selected_ids = (
        [int(event["event_id"]) for event in artifact.events]
        if event_ids is None
        else list(event_ids)
    )
    by_id = {int(event["event_id"]): event for event in artifact.events}
    notice_h = int(by_id[selected_ids[0]]["notice_hours"])
    env = HourlyCommunityAIDemandResponseEnv(
        _repeated_environment_document(
            artifact,
            notice_h=notice_h,
            requested_reduction_kw=capacity_kw,
            event_ids=selected_ids,
        )
    )
    controller = make_hourly_controller(
        "robust_mpc",
        robust_mpc_specification=specification,
    )
    frame, _ = rollout_hourly_episode(env, controller, seed=artifact.episode_seed)
    outcomes = derive_event_outcomes(
        frame,
        env.event_manifest,
        recovery_tolerance_gpu_h=(
            env.config.recovery_backlog_tolerance_fraction
            * env.power_model.flexible_capacity_gpu_h
        ),
    )
    return frame, outcomes


def _evaluate_exhaustion_artifact(
    payload: tuple[str, int, int, float, dict[str, float], str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    artifact_path, duration_h, gap_h, capacity_kw, criteria_raw, controller_config = payload
    artifact = load_frozen_hourly_scenario(artifact_path)
    criteria = FirmFlexibilityCriteria(**criteria_raw)
    frame, outcomes = _rollout_exhaustion_program(
        artifact,
        capacity_kw=capacity_kw,
        controller_config=controller_config,
    )
    fresh_by_ordinal: dict[int, tuple[pd.DataFrame, EventOutcome]] = {}
    for ordinal, event in enumerate(artifact.events, start=1):
        fresh_frame, fresh_outcomes = _rollout_exhaustion_program(
            artifact,
            capacity_kw=capacity_kw,
            controller_config=controller_config,
            event_ids=[int(event["event_id"])],
        )
        if len(fresh_outcomes) != 1:
            raise RuntimeError("fresh exhaustion counterfactual must contain one event")
        fresh_by_ordinal[ordinal] = (fresh_frame, fresh_outcomes[0])
    rows: list[dict[str, Any]] = []
    successes: list[bool] = []
    for ordinal, outcome in enumerate(outcomes, start=1):
        success, failures = _local_event_decision(outcome, criteria)
        successes.append(success)
        start_row = frame.loc[frame["hour"] == outcome.start_hour]
        if len(start_row) != 1:
            raise RuntimeError("exhaustion diagnostic could not locate event start")
        fresh_frame, fresh_outcome = fresh_by_ordinal[ordinal]
        fresh_start_row = fresh_frame.loc[fresh_frame["hour"] == fresh_outcome.start_hour]
        if len(fresh_start_row) != 1:
            raise RuntimeError("exhaustion diagnostic could not locate fresh event start")
        delivered_kw = capacity_kw * outcome.delivery_ratio
        fresh_delivered_kw = capacity_kw * fresh_outcome.delivery_ratio
        fresh_success, fresh_failures = _local_event_decision(fresh_outcome, criteria)
        local_margin = _minimum_local_service_margin(outcome, criteria)
        fresh_local_margin = _minimum_local_service_margin(fresh_outcome, criteria)
        rows.append(
            {
                "scenario_id": artifact.scenario_id,
                "scenario_hash": artifact.scenario_hash,
                "episode_seed": artifact.episode_seed,
                "duration_h": duration_h,
                "recovery_gap_h": gap_h,
                "event_ordinal": ordinal,
                "event_start_hour": outcome.start_hour,
                "fixed_capacity_kw": capacity_kw,
                "delivered_reduction_kw": delivered_kw,
                "fresh_delivered_reduction_kw": fresh_delivered_kw,
                "paired_residual_flexibility_ratio": (
                    delivered_kw / fresh_delivered_kw
                    if fresh_delivered_kw > 1e-9
                    else math.nan
                ),
                "delivery_ratio": outcome.delivery_ratio,
                "minimum_interval_delivery_ratio": (
                    outcome.minimum_interval_delivery_ratio
                ),
                "deadline_miss_rate": outcome.deadline_miss_rate,
                "rebound_ratio": outcome.rebound_ratio,
                "window_peak_relief_fraction": outcome.window_peak_relief_fraction,
                "terminal_backlog_fraction": outcome.terminal_backlog_fraction,
                "event_start_backlog_gpu_h": float(
                    start_row["decision_backlog_gpu_h"].iloc[0]
                ),
                "event_start_compute_debt_kwh": float(
                    start_row["decision_compute_debt_kwh"].iloc[0]
                ),
                "fresh_event_start_compute_debt_kwh": float(
                    fresh_start_row["decision_compute_debt_kwh"].iloc[0]
                ),
                "paired_compute_debt_increment_kwh": float(
                    start_row["decision_compute_debt_kwh"].iloc[0]
                    - fresh_start_row["decision_compute_debt_kwh"].iloc[0]
                ),
                "minimum_local_service_margin": local_margin,
                "fresh_minimum_local_service_margin": fresh_local_margin,
                "paired_local_service_margin_delta": local_margin - fresh_local_margin,
                "local_event_success": success,
                "fresh_local_event_success": fresh_success,
                "failure_labels": ",".join(failures),
                "fresh_failure_labels": ",".join(fresh_failures),
            }
        )
    episode_deadline_miss_rate = outcomes[0].deadline_miss_rate
    episode_terminal_backlog_fraction = outcomes[0].terminal_backlog_fraction
    episode_service_feasible = (
        episode_deadline_miss_rate <= criteria.max_deadline_miss_rate + 1e-9
        and episode_terminal_backlog_fraction
        <= criteria.max_terminal_backlog_fraction + 1e-9
    )
    episode = {
        "scenario_id": artifact.scenario_id,
        "scenario_hash": artifact.scenario_hash,
        "episode_seed": artifact.episode_seed,
        "duration_h": duration_h,
        "recovery_gap_h": gap_h,
        "fixed_capacity_kw": capacity_kw,
        "joint_episode_success": all(successes) and episode_service_feasible,
        "episode_service_feasible": episode_service_feasible,
        "episode_deadline_miss_rate": episode_deadline_miss_rate,
        "episode_terminal_backlog_fraction": episode_terminal_backlog_fraction,
        "successful_event_count": sum(successes),
        "event_count": len(successes),
    }
    return rows, episode


@dataclass(frozen=True, slots=True)
class _ExhaustionTask:
    payload: tuple[str, int, int, float, dict[str, float], str]
    scenario_id: str
    scenario_hash: str
    checkpoint_path: Path


def _write_exhaustion_checkpoint(
    task: _ExhaustionTask,
    result: tuple[list[dict[str, Any]], dict[str, Any]],
    *,
    analysis_identity_sha256: str,
) -> None:
    event_rows, episode = result
    body: dict[str, Any] = {
        "schema_version": 1,
        "analysis_identity_sha256": analysis_identity_sha256,
        "scenario_id": task.scenario_id,
        "scenario_hash": task.scenario_hash,
        "duration_h": task.payload[1],
        "recovery_gap_h": task.payload[2],
        "fixed_capacity_kw": task.payload[3],
        "event_rows": event_rows,
        "episode": episode,
    }
    document = {**body, "checkpoint_sha256": _canonical_sha256(body)}
    task.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = task.checkpoint_path.with_name(
        f".{task.checkpoint_path.name}.incomplete"
    )
    if temporary.exists():
        raise FileExistsError(f"incomplete exhaustion checkpoint exists: {temporary}")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(task.checkpoint_path)


def _load_exhaustion_checkpoint(
    task: _ExhaustionTask,
    *,
    analysis_identity_sha256: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw = json.loads(task.checkpoint_path.read_text(encoding="utf-8"))
    document = _mapping(raw, "exhaustion checkpoint")
    expected_fields = {
        "schema_version",
        "analysis_identity_sha256",
        "scenario_id",
        "scenario_hash",
        "duration_h",
        "recovery_gap_h",
        "fixed_capacity_kw",
        "event_rows",
        "episode",
        "checkpoint_sha256",
    }
    _exact_fields(document, expected_fields, "exhaustion checkpoint")
    body = {key: value for key, value in document.items() if key != "checkpoint_sha256"}
    if document["checkpoint_sha256"] != _canonical_sha256(body):
        raise ValueError("exhaustion checkpoint payload SHA-256 mismatch")
    expected_identity = {
        "schema_version": 1,
        "analysis_identity_sha256": analysis_identity_sha256,
        "scenario_id": task.scenario_id,
        "scenario_hash": task.scenario_hash,
        "duration_h": task.payload[1],
        "recovery_gap_h": task.payload[2],
        "fixed_capacity_kw": task.payload[3],
    }
    for key, expected in expected_identity.items():
        if document[key] != expected:
            raise ValueError(f"exhaustion checkpoint identity mismatch: {key}")
    event_rows = document["event_rows"]
    episode = document["episode"]
    if not isinstance(event_rows, list) or not all(
        isinstance(row, Mapping) for row in event_rows
    ):
        raise ValueError("exhaustion checkpoint event_rows must be a list of mappings")
    if not isinstance(episode, Mapping):
        raise ValueError("exhaustion checkpoint episode must be a mapping")
    return (
        [{str(key): value for key, value in row.items()} for row in event_rows],
        {str(key): value for key, value in episode.items()},
    )


def compute_repeated_event_exhaustion_diagnostics(
    scenario_root: str | Path,
    *,
    specification_path: str | Path,
    output_directory: str | Path,
    workers: int = 1,
) -> dict[str, Any]:
    """Evaluate frozen Model A at one fixed commitment over event chains."""

    specification = load_repeated_event_exhaustion_specification(specification_path)
    _validate_v2_provenance_files(specification)
    root = Path(scenario_root)
    index_path = root / _INDEX_NAME
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if index.get("dataset_role") != specification.dataset_role:
        raise ValueError("exhaustion scenario dataset role mismatch")
    if index.get("model_a_git_commit") != specification.model_a_git_commit:
        raise ValueError("exhaustion scenario Model A commit mismatch")
    if index.get("specification_sha256") != specification.sha256:
        raise ValueError("exhaustion scenario specification mismatch")
    if index.get("specification_file_sha256") != sha256_file(Path(specification_path)):
        raise ValueError("exhaustion scenario specification file hash mismatch")
    if specification.expected_seed_range is not None:
        start, end = specification.expected_seed_range
        if index.get("seeds") != list(range(start, end + 1)):
            raise ValueError("exhaustion scenario seed range mismatch")
    capacity_by_duration = _capacity_by_duration(specification)
    controller_specification = load_robust_mpc_specification(
        specification.controller_config
    )
    controller_provenance = _controller_provenance(
        specification.controller_config,
        controller_specification,
    )
    repository_root = Path(__file__).resolve().parents[3]
    analysis_provenance = {
        "git_commit": _git_commit(),
        "source_sha256": {
            path: sha256_file(repository_root / path) for path in _SOURCE_PATHS
        },
    }
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    checkpoints = output / "scenario_checkpoints"
    checkpoints.mkdir(exist_ok=True)
    tasks: list[_ExhaustionTask] = []
    scenario_hashes: list[str] = []
    programs = index.get("programs")
    if not isinstance(programs, list):
        raise ValueError("exhaustion scenario index has no program list")
    for raw_program in programs:
        program = _mapping(raw_program, "exhaustion program")
        duration_h = int(program["duration_h"])
        gap_h = int(program["recovery_gap_h"])
        directory = Path(str(program["directory"]))
        artifacts = [
            load_frozen_hourly_scenario(child)
            for child in sorted(directory.iterdir())
            if child.is_dir() and (child / "metadata.json").is_file()
        ]
        if not artifacts:
            raise ValueError("exhaustion program contains no scenarios")
        expected_hashes = [str(value) for value in program["scenario_hashes"]]
        if [artifact.scenario_hash for artifact in artifacts] != expected_hashes:
            raise ValueError("exhaustion scenario hashes mismatch")
        scenario_hashes.extend(expected_hashes)
        program_checkpoints = checkpoints / f"duration_{duration_h}h_gap_{gap_h}h"
        tasks.extend(
            _ExhaustionTask(
                payload=(
                    str(artifact.directory),
                    duration_h,
                    gap_h,
                    capacity_by_duration[duration_h],
                    specification.criteria.as_dict(),
                    specification.controller_config,
                ),
                scenario_id=artifact.scenario_id,
                scenario_hash=artifact.scenario_hash,
                checkpoint_path=(
                    program_checkpoints / f"{artifact.scenario_hash}.json"
                ),
            )
            for artifact in artifacts
        )
    if workers <= 0:
        raise ValueError("workers must be positive")
    run_state = {
        "schema_version": 1,
        "dataset_role": specification.dataset_role,
        "locked_data_read": False,
        "model_a_git_commit": specification.model_a_git_commit,
        "specification": specification.as_dict(),
        "specification_sha256": specification.sha256,
        "specification_file_sha256": sha256_file(Path(specification_path)),
        "scenario_index_sha256": sha256_file(index_path),
        "scenario_hashes": scenario_hashes,
        "controller_provenance": controller_provenance,
        "analysis_provenance": analysis_provenance,
    }
    run_state_path = output / _RUN_STATE_NAME
    if run_state_path.is_file():
        observed_run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
        if observed_run_state != run_state:
            raise ValueError("exhaustion diagnostics resume state mismatch")
    else:
        run_state_path.write_text(
            json.dumps(run_state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    analysis_identity_sha256 = _canonical_sha256(run_state)
    evaluated_by_checkpoint: dict[
        Path, tuple[list[dict[str, Any]], dict[str, Any]]
    ] = {}
    missing: list[_ExhaustionTask] = []
    for task in tasks:
        if task.checkpoint_path.is_file():
            evaluated_by_checkpoint[task.checkpoint_path] = (
                _load_exhaustion_checkpoint(
                    task,
                    analysis_identity_sha256=analysis_identity_sha256,
                )
            )
        else:
            missing.append(task)
    if workers == 1:
        for task in missing:
            result = _evaluate_exhaustion_artifact(task.payload)
            _write_exhaustion_checkpoint(
                task,
                result,
                analysis_identity_sha256=analysis_identity_sha256,
            )
            evaluated_by_checkpoint[task.checkpoint_path] = result
    elif missing:
        with ProcessPoolExecutor(
            max_workers=min(workers, len(missing)),
            mp_context=multiprocessing.get_context("spawn"),
        ) as executor:
            future_by_task = {
                executor.submit(_evaluate_exhaustion_artifact, task.payload): task
                for task in missing
            }
            for future in as_completed(future_by_task):
                task = future_by_task[future]
                result = future.result()
                _write_exhaustion_checkpoint(
                    task,
                    result,
                    analysis_identity_sha256=analysis_identity_sha256,
                )
                evaluated_by_checkpoint[task.checkpoint_path] = result
    evaluated = [evaluated_by_checkpoint[task.checkpoint_path] for task in tasks]
    events = pd.DataFrame.from_records(
        [row for event_rows, _ in evaluated for row in event_rows]
    )
    events = events.reindex(sorted(events.columns), axis=1).sort_values(
        ["duration_h", "recovery_gap_h", "episode_seed", "event_ordinal"],
        ignore_index=True,
    )
    episodes = pd.DataFrame.from_records(
        [episode for _, episode in evaluated]
    )
    episodes = episodes.reindex(sorted(episodes.columns), axis=1).sort_values(
        ["duration_h", "recovery_gap_h", "episode_seed"],
        ignore_index=True,
    )
    summary_rows: list[dict[str, Any]] = []
    for raw_key, program_frame in events.groupby(
        ["duration_h", "recovery_gap_h"], sort=True
    ):
        duration_h, gap_h = cast(tuple[Any, Any], raw_key)
        first = program_frame.loc[program_frame["event_ordinal"] == 1]
        first_debt = float(first["event_start_compute_debt_kwh"].mean())
        for ordinal, selected in program_frame.groupby("event_ordinal", sort=True):
            delivered = float(selected["delivered_reduction_kw"].quantile(0.05))
            fresh_delivered = float(
                selected["fresh_delivered_reduction_kw"].quantile(0.05)
            )
            ratio = float(selected["paired_residual_flexibility_ratio"].quantile(0.05))
            failure_counts = Counter(
                label
                for labels in selected["failure_labels"].astype(str)
                for label in labels.split(",")
                if label
            )
            summary_rows.append(
                {
                    "duration_h": int(duration_h),
                    "recovery_gap_h": int(gap_h),
                    "event_ordinal": int(str(ordinal)),
                    "scenario_count": int(len(selected)),
                    "fixed_capacity_kw": float(selected["fixed_capacity_kw"].iloc[0]),
                    "local_event_success_fraction": float(
                        selected["local_event_success"].mean()
                    ),
                    "fresh_local_event_success_fraction": float(
                        selected["fresh_local_event_success"].mean()
                    ),
                    "p05_delivered_reduction_kw": delivered,
                    "p05_fresh_delivered_reduction_kw": fresh_delivered,
                    "fixed_commitment_residual_flexibility_ratio": ratio,
                    "fixed_commitment_exhaustion": 1.0 - ratio,
                    "mean_event_start_compute_debt_kwh": float(
                        selected["event_start_compute_debt_kwh"].mean()
                    ),
                    "compute_debt_growth_vs_first_kwh": float(
                        selected["event_start_compute_debt_kwh"].mean() - first_debt
                    ),
                    "mean_paired_compute_debt_increment_kwh": float(
                        selected["paired_compute_debt_increment_kwh"].mean()
                    ),
                    "mean_event_start_backlog_gpu_h": float(
                        selected["event_start_backlog_gpu_h"].mean()
                    ),
                    "p05_minimum_local_service_margin": float(
                        selected["minimum_local_service_margin"].quantile(0.05)
                    ),
                    "p05_paired_local_service_margin_delta": float(
                        selected["paired_local_service_margin_delta"].quantile(0.05)
                    ),
                    "p95_rebound_ratio": float(selected["rebound_ratio"].quantile(0.95)),
                    "failure_counts": json.dumps(
                        dict(sorted(failure_counts.items())), sort_keys=True
                    ),
                }
            )
    summary = pd.DataFrame.from_records(summary_rows)
    joint = (
        episodes.groupby(["duration_h", "recovery_gap_h"], as_index=False)
        .agg(
            scenario_count=("scenario_hash", "size"),
            fixed_capacity_kw=("fixed_capacity_kw", "first"),
            joint_episode_success_fraction=("joint_episode_success", "mean"),
            mean_successful_event_count=("successful_event_count", "mean"),
            event_count=("event_count", "first"),
            episode_service_feasible_fraction=("episode_service_feasible", "mean"),
            mean_episode_deadline_miss_rate=("episode_deadline_miss_rate", "mean"),
            mean_episode_terminal_backlog_fraction=(
                "episode_terminal_backlog_fraction",
                "mean",
            ),
        )
        .sort_values(["duration_h", "recovery_gap_h"], ignore_index=True)
    )
    events_path = output / "repeated_event_outcomes.parquet"
    episodes_path = output / "repeated_episode_outcomes.parquet"
    summary_path = output / "exhaustion_summary.parquet"
    joint_path = output / "joint_episode_summary.parquet"
    manifest_path = output / "exhaustion_diagnostics.json"
    events.to_parquet(events_path, index=False)
    episodes.to_parquet(episodes_path, index=False)
    summary.to_parquet(summary_path, index=False)
    joint.to_parquet(joint_path, index=False)
    manifest_path.write_text(
        json.dumps(
            {
                **run_state,
                "capacity_interpretation": (
                    "paired_fresh_event_fixed_Model_A_commitment_mechanism_diagnostic_"
                    "not_eventwise_certificate"
                ),
                "workers": workers,
                "checkpoint_count": len(tasks),
                "outputs": {
                    "event_outcomes": str(events_path),
                    "episode_outcomes": str(episodes_path),
                    "exhaustion_summary": str(summary_path),
                    "joint_episode_summary": str(joint_path),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "manifest": str(manifest_path),
        "event_outcomes": str(events_path),
        "episode_outcomes": str(episodes_path),
        "exhaustion_summary": str(summary_path),
        "joint_episode_summary": str(joint_path),
        "program_count": len(joint),
        "scenario_program_count": len(tasks),
        "resumed_checkpoint_count": len(tasks) - len(missing),
        "evaluated_checkpoint_count": len(missing),
    }
