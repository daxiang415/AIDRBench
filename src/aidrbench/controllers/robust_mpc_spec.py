"""Validated, hash-stable specification for the Nature robust-MPC reference."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import yaml


def _finite_non_negative(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class RobustMPCSpecification:
    """Every parameter and declared information source used by formal robust MPC."""

    schema_version: Literal[1]
    controller: Literal["robust_mpc"]
    horizon_hours: int
    solver: Literal["HIGHS"]
    solver_threads: int
    warm_start: bool
    deadline_penalty: float
    limit_penalty: float
    backlog_penalty: float
    backlog_normalization_hours: float
    switching_penalty: float
    arrival_history_window_hours: int
    arrival_safety_sigma: float
    minimum_arrival_safety_fraction: float
    service_envelope_enabled: bool
    fallback_controller: Literal["threshold"]
    information_structure: Literal["causal_control_state_plus_6h_environment_forecast"]
    arrival_forecast: Literal["historical_mean_plus_uncertainty_envelope"]
    community_and_limit_forecast: Literal["environment_provided_6h"]
    full_horizon_oracle: Literal[False]

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("robust MPC schema_version must be 1")
        if self.controller != "robust_mpc":
            raise ValueError("controller specification must declare robust_mpc")
        _positive_int(self.horizon_hours, "horizon_hours")
        if self.solver != "HIGHS":
            raise ValueError("formal robust MPC solver must be HIGHS")
        _positive_int(self.solver_threads, "solver_threads")
        if not isinstance(self.warm_start, bool):
            raise ValueError("warm_start must be boolean")
        for name in (
            "deadline_penalty",
            "limit_penalty",
            "backlog_penalty",
            "switching_penalty",
            "arrival_safety_sigma",
            "minimum_arrival_safety_fraction",
        ):
            _finite_non_negative(getattr(self, name), name)
        if _finite_non_negative(
            self.backlog_normalization_hours, "backlog_normalization_hours"
        ) == 0.0:
            raise ValueError("backlog_normalization_hours must be positive")
        _positive_int(self.arrival_history_window_hours, "arrival_history_window_hours")
        if not isinstance(self.service_envelope_enabled, bool):
            raise ValueError("service_envelope_enabled must be boolean")
        if self.fallback_controller != "threshold":
            raise ValueError("formal robust MPC fallback_controller must be threshold")
        if self.information_structure != "causal_control_state_plus_6h_environment_forecast":
            raise ValueError("unexpected robust MPC information_structure")
        if self.arrival_forecast != "historical_mean_plus_uncertainty_envelope":
            raise ValueError("unexpected robust MPC arrival_forecast")
        if self.community_and_limit_forecast != "environment_provided_6h":
            raise ValueError("unexpected robust MPC community_and_limit_forecast")
        if self.full_horizon_oracle is not False:
            raise ValueError("formal robust MPC cannot enable a full-horizon oracle")

    def as_dict(self) -> dict[str, Any]:
        """Return the canonical JSON-compatible specification."""

        return asdict(self)


_REQUIRED_KEYS = frozenset(RobustMPCSpecification.__dataclass_fields__)


def load_robust_mpc_specification(
    source: str | Path | Mapping[str, Any],
) -> RobustMPCSpecification:
    """Load a complete specification and reject omissions or unknown fields."""

    if isinstance(source, str | Path):
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(f"robust MPC controller config does not exist: {path}")
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    else:
        document = dict(source)
    if not isinstance(document, Mapping):
        raise ValueError("robust MPC controller config must be a mapping")
    normalized = {str(key): value for key, value in document.items()}
    missing = sorted(_REQUIRED_KEYS - set(normalized))
    unknown = sorted(set(normalized) - _REQUIRED_KEYS)
    if missing or unknown:
        raise ValueError(
            f"robust MPC controller config fields mismatch; missing={missing}, unknown={unknown}"
        )
    return RobustMPCSpecification(**normalized)


def robust_mpc_specification_sha256(specification: RobustMPCSpecification) -> str:
    """Hash the normalized specification independently of YAML formatting."""

    payload = json.dumps(
        specification.as_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
