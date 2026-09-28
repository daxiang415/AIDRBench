"""Export an auditable SI mapping from event-end compute debt to recovery power.

This module deliberately stops before capital-cost accounting.  The reported
GPU count is a recovery-throughput equivalent under declared recovery-time and
execution-efficiency assumptions; it is neither a firm-capacity certificate nor
an estimate of hardware that a real operator must purchase.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
import pandas as pd
import yaml

from aidrbench.calibration.artifact import (
    HardwareCalibrationArtifact,
    PowerParameterEstimate,
    load_hardware_calibration_artifact,
)
from aidrbench.data.splits import sha256_file

_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_VERSION = "aidrbench.economic_reserve_mapping.v1"
_MANIFEST_SCHEMA_VERSION = "aidrbench.economic_reserve_mapping_manifest.v1"
_ANALYSIS_ROLE = "supplementary_diagnostic_physical_mapping"
_GPU_COUNT_TERM = "recovery-throughput-equivalent reserved GPU count"
_EVENT_DEBT_DEFINITION = (
    "max(controlled_backlog_gpu_h - no_dr_backlog_gpu_h, 0) at relative_hour=H-1"
)
_TOP_LEVEL_FIELDS = {
    "schema_version",
    "analysis_id",
    "analysis_role",
    "inputs",
    "selection",
    "mapping",
    "interpretation",
}
_INPUT_FIELDS = {
    "ledger_directory",
    "ledger_manifest_sha256",
    "episode_ledger_sha256",
    "interval_ledger_sha256",
    "calibration_artifact",
    "calibration_file_sha256",
    "calibration_artifact_sha256",
    "expected_ledger_analysis_id",
    "expected_ledger_analysis_role",
}
_SELECTION_FIELDS = {
    "duration_hours",
    "notice_hours",
    "offer_fraction_of_technical_ceiling",
    "event_id",
    "expected_scenarios_per_duration",
}
_MAPPING_FIELDS = {
    "debt_quantiles",
    "quantile_method",
    "recovery_target_hours",
    "recovery_execution_efficiencies",
    "gpus_per_node",
    "pue",
    "pue_parameter_status",
    "node_overhead_cases",
    "active_power_cases",
}
_INTERPRETATION_FIELDS = {
    "gpu_count_term",
    "capital_cost_evaluation",
    "prohibited_claims",
}
_NODE_CASE_FIELDS = {"case_id", "artifact_statistic", "parameter_status"}
_ACTIVE_CASE_FIELDS = {"case_id", "class_weights", "parameter_status"}
_EPISODE_REQUIRED_COLUMNS = {
    "scenario_id",
    "scenario_hash",
    "episode_seed",
    "event_id",
    "event_start_hour",
    "event_stop_hour",
    "duration_h",
    "notice_h",
    "technical_capacity_ceiling_kw",
    "offer_fraction_of_technical_ceiling",
    "candidate_reduction_kw",
    "technical_success",
}
_INTERVAL_REQUIRED_COLUMNS = {
    "scenario_id",
    "scenario_hash",
    "episode_seed",
    "event_id",
    "duration_h",
    "notice_h",
    "candidate_reduction_kw",
    "hour",
    "relative_hour",
    "event_active",
    "backlog_delta_gpu_h",
}


def _mapping(value: object, *, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _exact_fields(document: Mapping[str, Any], expected: set[str], *, name: str) -> None:
    observed = set(document)
    if observed != expected:
        raise ValueError(
            f"{name} fields mismatch; missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )


def _nonempty_text(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _finite_float(value: object, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _positive_int(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _digest(value: object, *, name: str) -> str:
    text = _nonempty_text(value, name=name)
    if len(text) != 64:
        raise ValueError(f"{name} must be a SHA-256 digest")
    try:
        int(text, 16)
    except ValueError as error:
        raise ValueError(f"{name} must be a SHA-256 digest") from error
    return text.lower()


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _resolve_path(value: object, *, config_directory: Path) -> Path:
    declared = Path(_nonempty_text(value, name="input path"))
    if declared.is_absolute():
        return declared
    repository_candidate = _ROOT / declared
    if repository_candidate.exists():
        return repository_candidate
    return config_directory / declared


@dataclass(frozen=True, slots=True)
class ReserveMappingInputs:
    ledger_directory: Path
    ledger_manifest_sha256: str
    episode_ledger_sha256: str
    interval_ledger_sha256: str
    calibration_artifact: Path
    calibration_file_sha256: str
    calibration_artifact_sha256: str
    expected_ledger_analysis_id: str
    expected_ledger_analysis_role: str


@dataclass(frozen=True, slots=True)
class ReserveMappingSelection:
    duration_hours: tuple[int, ...]
    notice_hours: int
    offer_fraction_of_technical_ceiling: float
    event_id: int
    expected_scenarios_per_duration: int


@dataclass(frozen=True, slots=True)
class NodeOverheadCase:
    case_id: str
    artifact_statistic: Literal["lower_bound", "nominal", "upper_bound"]
    parameter_status: str


@dataclass(frozen=True, slots=True)
class ActivePowerCase:
    case_id: str
    class_weights: tuple[tuple[str, float], ...]
    parameter_status: str


@dataclass(frozen=True, slots=True)
class ReserveMappingParameters:
    debt_quantiles: tuple[float, ...]
    quantile_method: Literal["linear"]
    recovery_target_hours: tuple[int, ...]
    recovery_execution_efficiencies: tuple[float, ...]
    gpus_per_node: int
    pue: float
    pue_parameter_status: str
    node_overhead_cases: tuple[NodeOverheadCase, ...]
    active_power_cases: tuple[ActivePowerCase, ...]


@dataclass(frozen=True, slots=True)
class ReserveMappingSpecification:
    path: Path
    analysis_id: str
    inputs: ReserveMappingInputs
    selection: ReserveMappingSelection
    mapping: ReserveMappingParameters
    normalized_document: dict[str, Any]
    file_sha256: str

    @property
    def normalized_sha256(self) -> str:
        return _canonical_sha256(self.normalized_document)


def _strict_increasing(values: object, *, name: str, integer: bool) -> tuple[float, ...]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{name} must be a non-empty list")
    parsed: list[float] = []
    for index, value in enumerate(values):
        if integer:
            parsed.append(float(_positive_int(value, name=f"{name}[{index}]")))
        else:
            parsed.append(_finite_float(value, name=f"{name}[{index}]"))
    result = tuple(parsed)
    if tuple(sorted(set(result))) != result:
        raise ValueError(f"{name} must be unique and strictly increasing")
    return result


def _load_node_cases(value: object) -> tuple[NodeOverheadCase, ...]:
    if not isinstance(value, list):
        raise ValueError("mapping.node_overhead_cases must be a list")
    cases: list[NodeOverheadCase] = []
    for index, raw in enumerate(value):
        document = _mapping(raw, name=f"mapping.node_overhead_cases[{index}]")
        _exact_fields(document, _NODE_CASE_FIELDS, name="node-overhead case")
        statistic = _nonempty_text(
            document["artifact_statistic"], name="artifact_statistic"
        )
        if statistic not in {"lower_bound", "nominal", "upper_bound"}:
            raise ValueError("artifact_statistic must be lower_bound, nominal, or upper_bound")
        cases.append(
            NodeOverheadCase(
                case_id=_nonempty_text(document["case_id"], name="case_id"),
                artifact_statistic=cast(
                    Literal["lower_bound", "nominal", "upper_bound"], statistic
                ),
                parameter_status=_nonempty_text(
                    document["parameter_status"], name="parameter_status"
                ),
            )
        )
    expected = {"lower_bound", "nominal", "upper_bound"}
    if {case.case_id for case in cases} != expected or len(cases) != len(expected):
        raise ValueError(
            "node_overhead_cases must declare lower_bound, nominal, and upper_bound once"
        )
    return tuple(cases)


def _load_active_cases(value: object) -> tuple[ActivePowerCase, ...]:
    if not isinstance(value, list):
        raise ValueError("mapping.active_power_cases must be a list")
    cases: list[ActivePowerCase] = []
    for index, raw in enumerate(value):
        document = _mapping(raw, name=f"mapping.active_power_cases[{index}]")
        _exact_fields(document, _ACTIVE_CASE_FIELDS, name="active-power case")
        raw_weights = _mapping(document["class_weights"], name="class_weights")
        if not raw_weights:
            raise ValueError("class_weights must not be empty")
        weights = tuple(
            sorted(
                (
                    name,
                    _finite_float(weight, name=f"class_weights.{name}"),
                )
                for name, weight in raw_weights.items()
            )
        )
        if any(weight < 0.0 for _, weight in weights) or not math.isclose(
            sum(weight for _, weight in weights), 1.0, abs_tol=1e-12
        ):
            raise ValueError("class_weights must be non-negative and sum to one")
        cases.append(
            ActivePowerCase(
                case_id=_nonempty_text(document["case_id"], name="case_id"),
                class_weights=weights,
                parameter_status=_nonempty_text(
                    document["parameter_status"], name="parameter_status"
                ),
            )
        )
    expected = {"training", "declared_flexible_mix", "offline_inference"}
    if {case.case_id for case in cases} != expected or len(cases) != len(expected):
        raise ValueError(
            "active_power_cases must declare training, declared_flexible_mix, and "
            "offline_inference once"
        )
    return tuple(cases)


def load_reserve_mapping_specification(path: str | Path) -> ReserveMappingSpecification:
    """Load the exact, closed-schema SI mapping contract."""

    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    document = _mapping(raw, name="reserve-mapping specification")
    _exact_fields(document, _TOP_LEVEL_FIELDS, name="reserve-mapping specification")
    if document["schema_version"] != _SCHEMA_VERSION:
        raise ValueError("unsupported reserve-mapping schema_version")
    if document["analysis_role"] != _ANALYSIS_ROLE:
        raise ValueError(f"analysis_role must be {_ANALYSIS_ROLE}")

    inputs = _mapping(document["inputs"], name="inputs")
    selection = _mapping(document["selection"], name="selection")
    parameters = _mapping(document["mapping"], name="mapping")
    interpretation = _mapping(document["interpretation"], name="interpretation")
    _exact_fields(inputs, _INPUT_FIELDS, name="inputs")
    _exact_fields(selection, _SELECTION_FIELDS, name="selection")
    _exact_fields(parameters, _MAPPING_FIELDS, name="mapping")
    _exact_fields(interpretation, _INTERPRETATION_FIELDS, name="interpretation")
    if interpretation["gpu_count_term"] != _GPU_COUNT_TERM:
        raise ValueError(f"interpretation.gpu_count_term must be {_GPU_COUNT_TERM!r}")
    if interpretation["capital_cost_evaluation"] != "disabled":
        raise ValueError("capital_cost_evaluation must remain disabled in v1")
    prohibited = interpretation["prohibited_claims"]
    if not isinstance(prohibited, list) or set(prohibited) != {
        "firm_gpu_count",
        "required_gpu_count",
        "hardware_purchase_requirement",
    }:
        raise ValueError("interpretation.prohibited_claims is incomplete")

    durations = _strict_increasing(
        selection["duration_hours"], name="selection.duration_hours", integer=True
    )
    notice = selection["notice_hours"]
    event_id = selection["event_id"]
    if isinstance(notice, bool) or not isinstance(notice, int) or notice < 0:
        raise ValueError("selection.notice_hours must be a non-negative integer")
    if isinstance(event_id, bool) or not isinstance(event_id, int) or event_id < 0:
        raise ValueError("selection.event_id must be a non-negative integer")
    offer_fraction = _finite_float(
        selection["offer_fraction_of_technical_ceiling"],
        name="selection.offer_fraction_of_technical_ceiling",
    )
    if not 0.0 < offer_fraction <= 1.0:
        raise ValueError("offer fraction must lie in (0, 1]")

    quantiles = _strict_increasing(
        parameters["debt_quantiles"], name="mapping.debt_quantiles", integer=False
    )
    if quantiles != (0.5, 0.95):
        raise ValueError("mapping.debt_quantiles must be the predeclared [0.5, 0.95]")
    recovery_targets = _strict_increasing(
        parameters["recovery_target_hours"],
        name="mapping.recovery_target_hours",
        integer=True,
    )
    if tuple(int(value) for value in recovery_targets) != (2, 4, 8, 12, 24):
        raise ValueError("recovery_target_hours must be [2, 4, 8, 12, 24]")
    efficiencies = _strict_increasing(
        parameters["recovery_execution_efficiencies"],
        name="mapping.recovery_execution_efficiencies",
        integer=False,
    )
    if efficiencies != (0.7, 0.85, 1.0):
        raise ValueError("recovery_execution_efficiencies must be [0.7, 0.85, 1.0]")
    if parameters["quantile_method"] != "linear":
        raise ValueError("mapping.quantile_method must be linear")
    pue = _finite_float(parameters["pue"], name="mapping.pue")
    if pue < 1.0:
        raise ValueError("mapping.pue must be at least one")

    return ReserveMappingSpecification(
        path=source.resolve(),
        analysis_id=_nonempty_text(document["analysis_id"], name="analysis_id"),
        inputs=ReserveMappingInputs(
            ledger_directory=_resolve_path(
                inputs["ledger_directory"], config_directory=source.parent
            ),
            ledger_manifest_sha256=_digest(
                inputs["ledger_manifest_sha256"], name="inputs.ledger_manifest_sha256"
            ),
            episode_ledger_sha256=_digest(
                inputs["episode_ledger_sha256"], name="inputs.episode_ledger_sha256"
            ),
            interval_ledger_sha256=_digest(
                inputs["interval_ledger_sha256"], name="inputs.interval_ledger_sha256"
            ),
            calibration_artifact=_resolve_path(
                inputs["calibration_artifact"], config_directory=source.parent
            ),
            calibration_file_sha256=_digest(
                inputs["calibration_file_sha256"], name="inputs.calibration_file_sha256"
            ),
            calibration_artifact_sha256=_digest(
                inputs["calibration_artifact_sha256"],
                name="inputs.calibration_artifact_sha256",
            ),
            expected_ledger_analysis_id=_nonempty_text(
                inputs["expected_ledger_analysis_id"], name="expected_ledger_analysis_id"
            ),
            expected_ledger_analysis_role=_nonempty_text(
                inputs["expected_ledger_analysis_role"], name="expected_ledger_analysis_role"
            ),
        ),
        selection=ReserveMappingSelection(
            duration_hours=tuple(int(value) for value in durations),
            notice_hours=int(notice),
            offer_fraction_of_technical_ceiling=offer_fraction,
            event_id=int(event_id),
            expected_scenarios_per_duration=_positive_int(
                selection["expected_scenarios_per_duration"],
                name="selection.expected_scenarios_per_duration",
            ),
        ),
        mapping=ReserveMappingParameters(
            debt_quantiles=quantiles,
            quantile_method="linear",
            recovery_target_hours=tuple(int(value) for value in recovery_targets),
            recovery_execution_efficiencies=efficiencies,
            gpus_per_node=_positive_int(
                parameters["gpus_per_node"], name="mapping.gpus_per_node"
            ),
            pue=pue,
            pue_parameter_status=_nonempty_text(
                parameters["pue_parameter_status"], name="mapping.pue_parameter_status"
            ),
            node_overhead_cases=_load_node_cases(parameters["node_overhead_cases"]),
            active_power_cases=_load_active_cases(parameters["active_power_cases"]),
        ),
        normalized_document=document,
        file_sha256=sha256_file(source),
    )


def _read_json_mapping(path: Path, *, name: str) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{name} is not valid JSON: {path}") from error
    return _mapping(raw, name=name)


def _verify_hash(path: Path, expected: str, *, name: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{name} does not exist: {path}")
    observed = sha256_file(path)
    if observed != expected:
        raise ValueError(f"{name} SHA-256 mismatch: expected {expected}, observed {observed}")


def _load_verified_inputs(
    specification: ReserveMappingSpecification,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, HardwareCalibrationArtifact]:
    inputs = specification.inputs
    ledger_manifest_path = inputs.ledger_directory / "ledger_manifest.json"
    event_path = inputs.ledger_directory / "episode_ledger.parquet"
    interval_path = inputs.ledger_directory / "interval_ledger.parquet"
    _verify_hash(
        ledger_manifest_path,
        inputs.ledger_manifest_sha256,
        name="ledger manifest",
    )
    _verify_hash(event_path, inputs.episode_ledger_sha256, name="episode ledger")
    _verify_hash(interval_path, inputs.interval_ledger_sha256, name="interval ledger")
    _verify_hash(
        inputs.calibration_artifact,
        inputs.calibration_file_sha256,
        name="calibration artifact file",
    )
    manifest = _read_json_mapping(ledger_manifest_path, name="ledger manifest")
    if manifest.get("analysis_id") != inputs.expected_ledger_analysis_id:
        raise ValueError("ledger manifest analysis_id does not match the mapping contract")
    if manifest.get("analysis_role") != inputs.expected_ledger_analysis_role:
        raise ValueError("ledger manifest analysis_role does not match the mapping contract")
    if manifest.get("event_ledger_sha256") != inputs.episode_ledger_sha256:
        raise ValueError("ledger manifest does not bind the declared episode ledger")
    if manifest.get("interval_ledger_sha256") != inputs.interval_ledger_sha256:
        raise ValueError("ledger manifest does not bind the declared interval ledger")

    calibration = load_hardware_calibration_artifact(inputs.calibration_artifact)
    if calibration.artifact_sha256 != inputs.calibration_artifact_sha256:
        raise ValueError("calibration artifact identity differs from the mapping contract")
    technical_provenance = _mapping(
        manifest.get("technical_provenance"), name="ledger technical_provenance"
    )
    if (
        technical_provenance.get("calibration_artifact_sha256")
        != calibration.artifact_sha256
    ):
        raise ValueError("ledger and reserve mapping use different calibration artifacts")

    events = pd.read_parquet(event_path)
    intervals = pd.read_parquet(interval_path)
    for name, frame, required in (
        ("episode ledger", events, _EPISODE_REQUIRED_COLUMNS),
        ("interval ledger", intervals, _INTERVAL_REQUIRED_COLUMNS),
    ):
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(f"{name} is missing columns: {', '.join(missing)}")
    if int(manifest.get("event_row_count", -1)) != len(events):
        raise ValueError("episode ledger row count differs from its manifest")
    if int(manifest.get("interval_row_count", -1)) != len(intervals):
        raise ValueError("interval ledger row count differs from its manifest")
    return manifest, events, intervals, calibration


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_numeric(frame[column], errors="raise")
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError(f"{column} contains non-finite values")
    return values


def _selected_event_end_debt(
    events: pd.DataFrame,
    intervals: pd.DataFrame,
    selection: ReserveMappingSelection,
) -> pd.DataFrame:
    event_mask = (
        events["duration_h"].isin(selection.duration_hours)
        & (events["notice_h"] == selection.notice_hours)
        & (events["event_id"] == selection.event_id)
        & np.isclose(
            _numeric(events, "offer_fraction_of_technical_ceiling"),
            selection.offer_fraction_of_technical_ceiling,
            rtol=0.0,
            atol=1e-12,
        )
    )
    selected_events = events.loc[event_mask].copy()
    if len(selected_events) != (
        len(selection.duration_hours) * selection.expected_scenarios_per_duration
    ):
        raise ValueError("selected episode-ledger row count does not match the contract")

    keys = ["scenario_id", "scenario_hash", "episode_seed", "event_id", "duration_h", "notice_h"]
    if selected_events.duplicated(keys).any():
        raise ValueError("selected episode ledger has duplicate scenario/event keys")
    for duration in selection.duration_hours:
        group = selected_events[selected_events["duration_h"] == duration]
        if len(group) != selection.expected_scenarios_per_duration:
            raise ValueError(f"duration {duration} does not have the expected scenario count")
        if group["scenario_hash"].nunique() != selection.expected_scenarios_per_duration:
            raise ValueError(f"duration {duration} contains duplicate scenario hashes")
    scenario_identities = [
        set(
            selected_events.loc[
                selected_events["duration_h"] == duration,
                ["scenario_id", "scenario_hash", "episode_seed"],
            ].itertuples(index=False, name=None)
        )
        for duration in selection.duration_hours
    ]
    if any(identities != scenario_identities[0] for identities in scenario_identities[1:]):
        raise ValueError("duration groups do not contain the same paired scenario set")

    interval_mask = (
        intervals["duration_h"].isin(selection.duration_hours)
        & (intervals["notice_h"] == selection.notice_hours)
        & (intervals["event_id"] == selection.event_id)
        & intervals["event_active"].astype(bool)
        & (
            _numeric(intervals, "relative_hour")
            == _numeric(intervals, "duration_h") - 1
        )
    )
    event_end = intervals.loc[interval_mask].copy()
    if event_end.duplicated(keys).any():
        raise ValueError("interval ledger has duplicate event-end rows")
    merged = selected_events.merge(
        event_end[keys + ["hour", "candidate_reduction_kw", "backlog_delta_gpu_h"]],
        on=keys,
        how="left",
        validate="one_to_one",
        suffixes=("_event", "_interval"),
    )
    if merged[["hour", "backlog_delta_gpu_h"]].isna().any().any():
        raise ValueError("one or more selected events has no event-end interval")
    if not np.array_equal(
        _numeric(merged, "hour").to_numpy(dtype=int),
        _numeric(merged, "event_stop_hour").to_numpy(dtype=int) - 1,
    ):
        raise ValueError("event-end interval hour is inconsistent with event_stop_hour")
    if not np.allclose(
        _numeric(merged, "candidate_reduction_kw_event"),
        _numeric(merged, "candidate_reduction_kw_interval"),
        rtol=0.0,
        atol=1e-9,
    ):
        raise ValueError("event and interval ledgers disagree on candidate reduction")
    merged["event_end_paired_backlog_debt_gpu_h"] = np.maximum(
        _numeric(merged, "backlog_delta_gpu_h"), 0.0
    )
    return merged


def _weighted_power_parameter(
    case: ActivePowerCase,
    calibration: HardwareCalibrationArtifact,
) -> tuple[float, float, float, str]:
    parameters = dict(calibration.active_power_parameters_by_class)
    missing = sorted(set(dict(case.class_weights)).difference(parameters))
    if missing:
        raise ValueError(
            f"active-power case {case.case_id} references absent calibration classes: "
            f"{', '.join(missing)}"
        )
    estimate = 0.0
    lower = 0.0
    upper = 0.0
    for name, weight in case.class_weights:
        parameter = parameters[name]
        estimate += weight * parameter.estimate_w
        lower += weight * parameter.uncertainty_interval_w[0]
        upper += weight * parameter.uncertainty_interval_w[1]
    weights_json = json.dumps(
        dict(case.class_weights), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return estimate, lower, upper, weights_json


def _node_overhead(
    case: NodeOverheadCase, parameter: PowerParameterEstimate
) -> float:
    if case.artifact_statistic == "lower_bound":
        return parameter.uncertainty_interval_w[0]
    if case.artifact_statistic == "upper_bound":
        return parameter.uncertainty_interval_w[1]
    return parameter.estimate_w


def _summary_rows(
    selected: pd.DataFrame,
    specification: ReserveMappingSpecification,
    calibration: HardwareCalibrationArtifact,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    idle = calibration.idle_power
    for duration in specification.selection.duration_hours:
        group = selected[selected["duration_h"] == duration].copy()
        debt = _numeric(group, "event_end_paired_backlog_debt_gpu_h").to_numpy(dtype=float)
        ceilings = np.unique(
            np.round(_numeric(group, "technical_capacity_ceiling_kw").to_numpy(), 12)
        )
        candidates = np.unique(
            np.round(_numeric(group, "candidate_reduction_kw_event").to_numpy(), 12)
        )
        if len(ceilings) != 1 or len(candidates) != 1:
            raise ValueError("each duration must map one technical ceiling and one candidate")
        success = group["technical_success"]
        if not success.isin([True, False]).all():
            raise ValueError("technical_success must be boolean")
        for quantile in specification.mapping.debt_quantiles:
            debt_quantile = float(
                np.quantile(debt, quantile, method=specification.mapping.quantile_method)
            )
            for target_h in specification.mapping.recovery_target_hours:
                for efficiency in specification.mapping.recovery_execution_efficiencies:
                    continuous_gpu = debt_quantile / (efficiency * target_h)
                    node_count = math.ceil(continuous_gpu / specification.mapping.gpus_per_node)
                    rounded_gpu = node_count * specification.mapping.gpus_per_node
                    for active_case in specification.mapping.active_power_cases:
                        active_w, active_lower_w, active_upper_w, weights_json = (
                            _weighted_power_parameter(active_case, calibration)
                        )
                        for node_case in specification.mapping.node_overhead_cases:
                            overhead_w = _node_overhead(node_case, calibration.node_fixed_overhead)
                            installed_it_kw = (
                                rounded_gpu * active_w + node_count * overhead_w
                            ) / 1000.0
                            installed_it_lower_kw = (
                                rounded_gpu * active_lower_w + node_count * overhead_w
                            ) / 1000.0
                            installed_it_upper_kw = (
                                rounded_gpu * active_upper_w + node_count * overhead_w
                            ) / 1000.0
                            dynamic_facility_kw = (
                                specification.mapping.pue
                                * rounded_gpu
                                * (active_w - idle.estimate_w)
                                / 1000.0
                            )
                            dynamic_lower_kw = (
                                specification.mapping.pue
                                * rounded_gpu
                                * max(active_lower_w - idle.uncertainty_interval_w[1], 0.0)
                                / 1000.0
                            )
                            dynamic_upper_kw = (
                                specification.mapping.pue
                                * rounded_gpu
                                * max(active_upper_w - idle.uncertainty_interval_w[0], 0.0)
                                / 1000.0
                            )
                            rows.append(
                                {
                                    "analysis_id": specification.analysis_id,
                                    "analysis_role": _ANALYSIS_ROLE,
                                    "duration_h": duration,
                                    "notice_h": specification.selection.notice_hours,
                                    "offer_fraction_of_technical_ceiling": (
                                        specification.selection.offer_fraction_of_technical_ceiling
                                    ),
                                    "technical_capacity_ceiling_kw": float(ceilings[0]),
                                    "candidate_reduction_kw": float(candidates[0]),
                                    "event_sample_count": int(len(group)),
                                    "technical_success_count": int(success.astype(bool).sum()),
                                    "technical_success_rate": float(success.astype(bool).mean()),
                                    "event_debt_quantile": quantile,
                                    "event_debt_quantile_label": f"q{int(round(100 * quantile))}",
                                    "event_end_paired_backlog_debt_gpu_h": debt_quantile,
                                    "event_debt_definition": _EVENT_DEBT_DEFINITION,
                                    "recovery_target_h": target_h,
                                    "recovery_execution_efficiency": efficiency,
                                    "continuous_recovery_throughput_equivalent_gpu_count": (
                                        continuous_gpu
                                    ),
                                    "recovery_throughput_equivalent_gpu_count_node_rounded": (
                                        rounded_gpu
                                    ),
                                    "recovery_throughput_equivalent_node_count": node_count,
                                    "gpus_per_node": specification.mapping.gpus_per_node,
                                    "gpu_count_interpretation": _GPU_COUNT_TERM,
                                    "active_power_case": active_case.case_id,
                                    "active_power_class_weights_json": weights_json,
                                    "active_board_power_w_per_gpu": active_w,
                                    "active_board_power_lower_w_per_gpu": active_lower_w,
                                    "active_board_power_upper_w_per_gpu": active_upper_w,
                                    "active_board_power_parameter_status": (
                                        active_case.parameter_status
                                    ),
                                    "idle_board_power_w_per_gpu": idle.estimate_w,
                                    "idle_board_power_lower_w_per_gpu": (
                                        idle.uncertainty_interval_w[0]
                                    ),
                                    "idle_board_power_upper_w_per_gpu": (
                                        idle.uncertainty_interval_w[1]
                                    ),
                                    "idle_board_power_parameter_status": (
                                        "single_node_board_power_observation_range"
                                    ),
                                    "node_overhead_case": node_case.case_id,
                                    "node_overhead_w_per_node": overhead_w,
                                    "node_overhead_parameter_status": node_case.parameter_status,
                                    "pue": specification.mapping.pue,
                                    "pue_parameter_status": (
                                        specification.mapping.pue_parameter_status
                                    ),
                                    "installed_it_power_kw": installed_it_kw,
                                    "installed_it_power_lower_kw": installed_it_lower_kw,
                                    "installed_it_power_upper_kw": installed_it_upper_kw,
                                    "installed_facility_power_kw": (
                                        specification.mapping.pue * installed_it_kw
                                    ),
                                    "installed_facility_power_lower_kw": (
                                        specification.mapping.pue * installed_it_lower_kw
                                    ),
                                    "installed_facility_power_upper_kw": (
                                        specification.mapping.pue * installed_it_upper_kw
                                    ),
                                    "recovery_dynamic_facility_power_kw": dynamic_facility_kw,
                                    "recovery_dynamic_facility_power_lower_kw": dynamic_lower_kw,
                                    "recovery_dynamic_facility_power_upper_kw": dynamic_upper_kw,
                                    "power_uncertainty_interpretation": (
                                        "componentwise_calibration_intervals_not_joint_confidence_interval"
                                    ),
                                    "capital_cost_evaluation": "disabled",
                                    "capital_cost": None,
                                    "hardware_identifier": calibration.hardware_identifier,
                                    "topology_identifier": calibration.topology_identifier,
                                    "calibration_artifact_id": calibration.artifact_id,
                                    "calibration_artifact_sha256": calibration.artifact_sha256,
                                    "calibration_evidence_class": calibration.evidence_class.value,
                                }
                            )
    result = pd.DataFrame(rows)
    sort_columns = [
        "duration_h",
        "event_debt_quantile",
        "recovery_target_h",
        "recovery_execution_efficiency",
        "active_power_case",
        "node_overhead_case",
    ]
    return result.sort_values(sort_columns, kind="stable").reset_index(drop=True)


def _git_state() -> dict[str, object]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "working_tree_dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
    }


def export_reserve_mapping_sensitivity(
    configuration: str | Path, output_directory: str | Path
) -> dict[str, object]:
    """Verify inputs and atomically publish the SI physical-mapping table."""

    specification = load_reserve_mapping_specification(configuration)
    manifest, events, intervals, calibration = _load_verified_inputs(specification)
    selected = _selected_event_end_debt(events, intervals, specification.selection)
    summary = _summary_rows(selected, specification, calibration)
    git = _git_state()

    destination = Path(output_directory).resolve()
    if destination.exists():
        raise FileExistsError(
            f"reserve-mapping output already exists; use a new directory: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.",
            suffix=".reserve-mapping.tmp",
            dir=destination.parent,
        )
    )
    output_name = "reserve_mapping_summary.csv"
    try:
        output_path = staging / output_name
        summary.to_csv(output_path, index=False, float_format="%.12g")
        output_sha256 = sha256_file(output_path)
        manifest_document: dict[str, object] = {
            "schema_version": _MANIFEST_SCHEMA_VERSION,
            "analysis_id": specification.analysis_id,
            "analysis_role": _ANALYSIS_ROLE,
            "configuration": {
                "path": str(specification.path),
                "file_sha256": specification.file_sha256,
                "normalized_sha256": specification.normalized_sha256,
            },
            "input_sha256": {
                "ledger_manifest": specification.inputs.ledger_manifest_sha256,
                "episode_ledger": specification.inputs.episode_ledger_sha256,
                "interval_ledger": specification.inputs.interval_ledger_sha256,
                "calibration_file": specification.inputs.calibration_file_sha256,
                "calibration_artifact": calibration.artifact_sha256,
            },
            "ledger_identity": {
                "analysis_id": manifest["analysis_id"],
                "analysis_role": manifest["analysis_role"],
                "event_row_count": int(manifest["event_row_count"]),
                "interval_row_count": int(manifest["interval_row_count"]),
            },
            "calibration": calibration.summary(),
            "mapping_definition": {
                "event_end_debt_gpu_h": _EVENT_DEBT_DEFINITION,
                "quantile_population": (
                    "all declared scenarios at each duration; technical failures are retained"
                ),
                "continuous_gpu_count": "debt_quantile_gpu_h / (eta * recovery_target_h)",
                "node_rounding": "gpus_per_node * ceil(continuous_gpu_count / gpus_per_node)",
                "installed_it_power_kw": (
                    "(node_rounded_gpu_count * active_board_power_w_per_gpu + "
                    "node_count * node_overhead_w_per_node) / 1000"
                ),
                "installed_facility_power_kw": "pue * installed_it_power_kw",
                "recovery_dynamic_facility_power_kw": (
                    "pue * node_rounded_gpu_count * "
                    "(active_board_power_w_per_gpu - idle_board_power_w_per_gpu) / 1000"
                ),
                "node_overhead_dynamic_treatment": (
                    "node overhead is included in installed power and treated as standby; "
                    "it is not added again to recovery dynamic power"
                ),
            },
            "parameter_evidence": {
                "active_and_idle_board_power": (
                    "calibration artifact; declared mix is a weighted combination of "
                    "calibrated class estimates"
                ),
                "node_overhead": "engineering assumption range; no node meter",
                "pue": specification.mapping.pue_parameter_status,
                "capital_cost": "not evaluated; null by design",
            },
            "output": {
                "path": output_name,
                "sha256": output_sha256,
                "row_count": int(len(summary)),
                "columns": list(summary.columns),
            },
            "software": {
                "git": git,
                "source_sha256": {
                    "economic_reserve_mapping.py": sha256_file(Path(__file__))
                },
            },
            "claim_boundaries": [
                "The GPU quantity is a recovery-throughput equivalent, not a firm or "
                "required GPU count.",
                "The mapping is a supplementary sensitivity based on isolated-event "
                "development ledgers, not a repeated-event capacity certificate.",
                "No H100/H200 or other hardware extrapolation is performed.",
                "Node overhead and PUE are engineering assumptions; board-power inputs "
                "retain their calibration evidence labels.",
                "Capital cost and purchase requirements are not evaluated.",
            ],
            "final_publish": "atomic_directory_rename",
        }
        manifest_path = staging / "reserve_mapping_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest_document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(staging, destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    return {
        "output": str(destination / output_name),
        "manifest": str(destination / "reserve_mapping_manifest.json"),
        "row_count": int(len(summary)),
        "final_publish": "atomic_directory_rename",
    }
