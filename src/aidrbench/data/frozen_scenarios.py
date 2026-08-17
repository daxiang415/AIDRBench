"""Immutable, hash-verified hourly exogenous scenario artifacts.

The artifact captures a single realization of community demand, PV, workload
arrivals, event anchors and the no-DR baseline.  It is deliberately separate
from any controller output: a duration frontier can therefore change only the
event duration while retaining the same exogenous trajectory.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd
import yaml

from aidrbench.data.hourly import (
    HOURLY_COMMUNITY_COLUMNS,
    load_hourly_arrivals,
)

if TYPE_CHECKING:
    from aidrbench.models.power import HourlyDataCenterPowerModel


FROZEN_SCENARIO_SCHEMA_VERSION = 1
_METADATA_NAME = "metadata.json"
_COMMUNITY_NAME = "community.parquet"
_ARRIVALS_NAME = "arrivals.parquet"
_BASELINE_NAME = "baseline.parquet"
_CONFIG_NAME = "environment_config.yaml"


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1_048_576), b""):
            digest.update(block)
    return digest.hexdigest()


def _finite_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def power_model_fingerprint(model: HourlyDataCenterPowerModel) -> str:
    """Return a stable identifier for all model parameters affecting power."""

    return _sha256_bytes(_canonical_json(asdict(model)).encode("utf-8"))


@dataclass(frozen=True, slots=True)
class FrozenHourlyScenario:
    """Loaded immutable scenario inputs, with all on-disk hashes verified."""

    directory: Path
    metadata: dict[str, Any]
    community: pd.DataFrame
    arrivals: pd.DataFrame
    baseline: pd.DataFrame
    config_document: dict[str, Any]

    @property
    def scenario_id(self) -> str:
        return str(self.metadata["scenario_id"])

    @property
    def scenario_hash(self) -> str:
        return str(self.metadata["scenario_hash"])

    @property
    def episode_seed(self) -> int:
        return int(self.metadata["episode_seed"])

    @property
    def events(self) -> tuple[dict[str, Any], ...]:
        raw_events = self.metadata["events"]
        if not isinstance(raw_events, list):
            raise RuntimeError("validated frozen scenario has malformed events")
        return tuple(dict(event) for event in raw_events)

    def assert_compatible(
        self,
        *,
        total_hours: int,
        forecast_horizon_hours: int,
        pcc_capacity_kw: float,
        power_model_sha256: str,
    ) -> None:
        """Reject a replay that silently changes its physical interpretation."""

        horizon = self.metadata.get("horizon")
        if not isinstance(horizon, Mapping):
            raise RuntimeError("validated frozen scenario has malformed horizon metadata")
        if int(horizon.get("total_hours", -1)) != total_hours:
            raise ValueError("frozen scenario total_hours does not match the environment")
        if int(horizon.get("forecast_horizon_hours", -1)) != forecast_horizon_hours:
            raise ValueError(
                "frozen scenario forecast_horizon_hours does not match the environment"
            )
        bases = self.metadata.get("scenario_bases")
        if not isinstance(bases, Mapping):
            raise RuntimeError("validated frozen scenario has malformed scenario bases")
        frozen_pcc = _finite_float(bases.get("pcc_capacity_kw"), "scenario_bases.pcc_capacity_kw")
        if not math.isclose(frozen_pcc, pcc_capacity_kw, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("frozen scenario PCC capacity does not match the environment")
        power_model = self.metadata.get("power_model")
        if not isinstance(power_model, Mapping):
            raise RuntimeError("validated frozen scenario has malformed power-model metadata")
        if power_model.get("sha256") != power_model_sha256:
            raise ValueError("frozen scenario power-model hash does not match the environment")


def _validate_community(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(HOURLY_COMMUNITY_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"frozen community is missing required columns: {missing}")
    normalized = frame.loc[:, HOURLY_COMMUNITY_COLUMNS].copy()
    normalized["timestamp"] = pd.to_datetime(normalized["timestamp"], utc=True, errors="coerce")
    for column in ("community_load_kw", "pv_generation_kw", "net_community_load_kw"):
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
    required_columns = [
        "timestamp",
        "community_load_kw",
        "pv_generation_kw",
        "net_community_load_kw",
    ]
    if normalized[required_columns].isna().any().any():
        raise ValueError("frozen community contains invalid timestamps or power values")
    if (
        (normalized["community_load_kw"] < 0.0).any()
        or (normalized["pv_generation_kw"] < 0.0).any()
    ):
        raise ValueError("frozen community gross load and PV generation must be non-negative")
    expected_net = normalized["community_load_kw"] - normalized["pv_generation_kw"]
    if not (expected_net - normalized["net_community_load_kw"]).abs().le(1e-8).all():
        raise ValueError("frozen community net load does not equal gross load minus PV")
    if not normalized["timestamp"].is_monotonic_increasing:
        raise ValueError("frozen community timestamps must be monotone")
    return normalized


def _validate_events(raw_events: object, *, main_hours: int) -> list[dict[str, Any]]:
    if not isinstance(raw_events, list) or not raw_events:
        raise ValueError("frozen scenario events must be a non-empty list")
    events: list[dict[str, Any]] = []
    starts: set[int] = set()
    for index, raw in enumerate(raw_events):
        if not isinstance(raw, Mapping):
            raise ValueError("frozen scenario event must be a mapping")
        start = raw.get("start_hour")
        stop = raw.get("stop_hour")
        if (
            isinstance(start, bool)
            or isinstance(stop, bool)
            or not isinstance(start, int)
            or not isinstance(stop, int)
        ):
            raise ValueError("frozen scenario event bounds must be integers")
        if not 0 <= start < stop <= main_hours or start in starts:
            raise ValueError("frozen scenario event bounds are invalid or duplicated")
        starts.add(start)
        requested = _finite_float(raw.get("requested_reduction_kw"), "event.requested_reduction_kw")
        notice = _finite_float(raw.get("notice_hours"), "event.notice_hours")
        if requested < 0.0 or notice < 0.0:
            raise ValueError("frozen scenario event request and notice must be non-negative")
        events.append(
            {
                "event_id": int(raw.get("event_id", index)),
                "source_event_id": str(raw.get("source_event_id", f"frozen_{index}")),
                "start_hour": start,
                "stop_hour": stop,
                "requested_reduction_kw": requested,
                "notice_hours": notice,
            }
        )
    return events


def _validate_metadata(directory: Path, metadata: object) -> dict[str, Any]:
    if not isinstance(metadata, Mapping):
        raise ValueError("frozen scenario metadata must be a mapping")
    normalized = dict(metadata)
    if normalized.get("schema_version") != FROZEN_SCENARIO_SCHEMA_VERSION:
        raise ValueError("unsupported frozen scenario schema version")
    scenario_id = normalized.get("scenario_id")
    scenario_hash = normalized.get("scenario_hash")
    if not isinstance(scenario_id, str) or not scenario_id:
        raise ValueError("frozen scenario metadata is missing scenario_id")
    if not isinstance(scenario_hash, str) or len(scenario_hash) != 64:
        raise ValueError("frozen scenario metadata is missing scenario_hash")
    check = dict(normalized)
    check.pop("scenario_hash")
    observed_hash = _sha256_bytes(_canonical_json(check).encode("utf-8"))
    if observed_hash != scenario_hash:
        raise ValueError("frozen scenario metadata hash does not match its contents")
    files = normalized.get("files")
    if not isinstance(files, Mapping):
        raise ValueError("frozen scenario metadata is missing file hashes")
    required_files = {_COMMUNITY_NAME, _ARRIVALS_NAME, _BASELINE_NAME, _CONFIG_NAME}
    if set(files) != required_files:
        raise ValueError("frozen scenario metadata has an unexpected file set")
    for name, expected_hash in files.items():
        if not isinstance(name, str) or not isinstance(expected_hash, str):
            raise ValueError("frozen scenario file hashes must be strings")
        path = directory / name
        if not path.is_file() or _sha256_file(path) != expected_hash:
            raise ValueError(f"frozen scenario file hash does not match: {path}")
    return normalized


def load_frozen_hourly_scenario(directory: str | Path) -> FrozenHourlyScenario:
    """Read one scenario artifact and verify its metadata and payload hashes."""

    root = Path(directory)
    metadata_path = root / _METADATA_NAME
    if not metadata_path.is_file():
        raise FileNotFoundError(f"frozen scenario metadata does not exist: {metadata_path}")
    metadata = _validate_metadata(root, json.loads(metadata_path.read_text(encoding="utf-8")))
    horizon = metadata.get("horizon")
    if not isinstance(horizon, Mapping):
        raise ValueError("frozen scenario metadata is missing horizon")
    main_hours = horizon.get("main_hours")
    total_hours = horizon.get("total_hours")
    forecast_hours = horizon.get("forecast_horizon_hours")
    if (
        isinstance(main_hours, bool)
        or isinstance(total_hours, bool)
        or isinstance(forecast_hours, bool)
        or not isinstance(main_hours, int)
        or not isinstance(total_hours, int)
        or not isinstance(forecast_hours, int)
        or main_hours <= 0
        or total_hours < main_hours
        or forecast_hours < 0
    ):
        raise ValueError("frozen scenario has invalid horizon metadata")
    community = _validate_community(pd.read_parquet(root / _COMMUNITY_NAME))
    if len(community) < total_hours + forecast_hours:
        raise ValueError("frozen scenario community horizon is shorter than required")
    arrivals = load_hourly_arrivals(root / _ARRIVALS_NAME)
    if (arrivals["timestamp_index"] >= main_hours).any():
        raise ValueError("frozen scenario arrivals extend beyond the main horizon")
    baseline = pd.read_parquet(root / _BASELINE_NAME)
    required_baseline = {"hour", "baseline_execution_gpu_h", "baseline_pcc_power_kw"}
    if set(baseline.columns) != required_baseline or len(baseline) != total_hours:
        raise ValueError("frozen scenario baseline has an invalid schema or horizon")
    _validate_events(metadata.get("events"), main_hours=main_hours)
    config_document = yaml.safe_load((root / _CONFIG_NAME).read_text(encoding="utf-8"))
    if not isinstance(config_document, Mapping):
        raise ValueError("frozen scenario environment config must be a mapping")
    return FrozenHourlyScenario(
        directory=root,
        metadata=metadata,
        community=community,
        arrivals=arrivals,
        baseline=baseline,
        config_document=copy.deepcopy(dict(config_document)),
    )


def _config_document(config: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(config, str | Path):
        raw = yaml.safe_load(Path(config).read_text(encoding="utf-8"))
    else:
        raw = config
    if not isinstance(raw, Mapping):
        raise ValueError("hourly environment config must be a mapping")
    document = copy.deepcopy(dict(raw))
    raw_scenario = document.get("scenario")
    if isinstance(raw_scenario, Mapping):
        scenario = dict(raw_scenario)
        scenario.pop("frozen_path", None)
        scenario.pop("frozen_event_ids", None)
        scenario.pop("frozen_event_notice_hours", None)
        if scenario:
            document["scenario"] = scenario
        else:
            document.pop("scenario", None)
    return document


def freeze_hourly_scenario(
    config: str | Path | Mapping[str, Any],
    *,
    seed: int,
    output_directory: str | Path,
) -> dict[str, str | int | float]:
    """Generate one immutable, self-verifying hourly scenario artifact.

    The environment is used only to materialize exogenous inputs and the
    no-DR baseline.  No controller or learned policy is evaluated here.
    """

    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("scenario seed must be a non-negative integer")
    from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv

    env = HourlyCommunityAIDemandResponseEnv(config)
    _, reset_info = env.reset(seed=seed)
    snapshot = env.full_horizon_planning_snapshot()
    output_root = Path(output_directory)
    scenario_id = f"hourly_seed_{snapshot.episode_seed}"
    target = output_root / scenario_id
    if target.exists():
        raise FileExistsError(f"refusing to overwrite existing frozen scenario: {target}")
    output_root.mkdir(parents=True, exist_ok=True)
    temporary = output_root / f".{scenario_id}.incomplete"
    if temporary.exists():
        raise FileExistsError(f"incomplete frozen scenario already exists: {temporary}")
    temporary.mkdir()

    community = env._community.copy()  # Exposed immutably by the written artifact.
    arrivals = env._arrivals.copy()
    baseline = pd.DataFrame(
        {
            "hour": range(snapshot.total_hours),
            "baseline_execution_gpu_h": snapshot.baseline_execution_gpu_h,
            "baseline_pcc_power_kw": snapshot.baseline_pcc_power_kw,
        }
    )
    community_path = temporary / _COMMUNITY_NAME
    arrivals_path = temporary / _ARRIVALS_NAME
    baseline_path = temporary / _BASELINE_NAME
    config_path = temporary / _CONFIG_NAME
    community.to_parquet(community_path, index=False)
    arrivals.to_parquet(arrivals_path, index=False)
    baseline.to_parquet(baseline_path, index=False)
    config_path.write_text(
        yaml.safe_dump(_config_document(config), sort_keys=False), encoding="utf-8"
    )
    events = [
        {
            "event_id": event.event_id,
            "source_event_id": event.source_event_id,
            "start_hour": event.start_hour,
            "stop_hour": event.stop_hour,
            "requested_reduction_kw": event.requested_reduction_kw,
            "notice_hours": event.notice_hours,
        }
        for event in env.event_manifest
    ]
    metadata: dict[str, Any] = {
        "schema_version": FROZEN_SCENARIO_SCHEMA_VERSION,
        "scenario_id": scenario_id,
        "episode_seed": snapshot.episode_seed,
        "horizon": {
            "main_hours": snapshot.main_hours,
            "total_hours": snapshot.total_hours,
            "forecast_horizon_hours": env.config.forecast_horizon_hours,
        },
        "scenario_bases": {
            "background_community_peak_kw": env.config.background_community_peak_kw,
            "pcc_capacity_kw": env.config.pcc_capacity_kw,
            "target_dc_peak_kw": env.config.target_dc_peak_kw,
            "reference_mix_operating_peak_kw": (
                env.power_model.reference_mix_operating_peak_kw
            ),
            "worst_class_peak_kw": env.power_model.worst_class_peak_kw,
            # Historical alias retained for schema-v1 readers.
            "actual_dc_peak_kw": env._full_dc_power_kw,
        },
        "power_model": {
            "sha256": power_model_fingerprint(env.power_model),
            "parameters": asdict(env.power_model),
            "calibration_power_case": env.config.calibration_power_case,
            "calibration_artifact_sha256": (
                env.config.calibration_artifact.artifact_sha256
                if env.config.calibration_artifact is not None
                else ""
            ),
        },
        "exogenous_random_stream_seeds": dict(env.random_stream_seeds),
        "events": events,
        "initial_bess_soc_fraction": None,
        "no_dr_baseline": {
            "deadline_miss_gpu_h": snapshot.baseline_deadline_miss_gpu_h,
            "terminal_backlog_gpu_h": snapshot.baseline_terminal_backlog_gpu_h,
        },
        "files": {
            _COMMUNITY_NAME: _sha256_file(community_path),
            _ARRIVALS_NAME: _sha256_file(arrivals_path),
            _BASELINE_NAME: _sha256_file(baseline_path),
            _CONFIG_NAME: _sha256_file(config_path),
        },
    }
    metadata["scenario_hash"] = _sha256_bytes(_canonical_json(metadata).encode("utf-8"))
    (temporary / _METADATA_NAME).write_text(
        json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)
    return {
        "scenario_id": scenario_id,
        "episode_seed": snapshot.episode_seed,
        "scenario_hash": str(metadata["scenario_hash"]),
        "output": str(target),
        "actual_dc_peak_kw": env._full_dc_power_kw,
        "reference_mix_operating_peak_kw": (
            env.power_model.reference_mix_operating_peak_kw
        ),
        "worst_class_peak_kw": env.power_model.worst_class_peak_kw,
    }


def freeze_hourly_scenarios(
    config: str | Path | Mapping[str, Any],
    *,
    seeds: Sequence[int],
    output_directory: str | Path,
) -> list[dict[str, str | int | float]]:
    """Freeze unique scenario seeds without overwriting any existing artifact."""

    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("frozen scenario seeds must be a non-empty unique sequence")
    return [
        freeze_hourly_scenario(config, seed=seed, output_directory=output_directory)
        for seed in seeds
    ]
