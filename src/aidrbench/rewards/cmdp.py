"""Primal-dual reward adapter for service-feasible firm-flexibility learning.

The hourly environment remains the source of physical transitions and all
certification metrics.  This module only changes the scalar signal presented
to Stable-Baselines3 during an explicitly configured training run.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Final

import gymnasium as gym

CMDP_CONSTRAINT_NAMES: Final[tuple[str, ...]] = (
    "delivery",
    "feasibility",
    "deadline",
    "rebound",
    "window_relief",
    "terminal_backlog",
)


def _finite_non_negative(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


def _finite_positive(value: object, name: str) -> float:
    result = _finite_non_negative(value, name)
    if result <= 0.0:
        raise ValueError(f"{name} must be positive")
    return result


@dataclass(frozen=True, slots=True)
class FirmCMDPRewardConfig:
    """Configuration of an experimental firm CMDP training signal."""

    version: str = "firm_cmdp_v1"
    useful_compute_weight: float = 1.0
    potential_shaping_weight: float = 0.25
    switching_weight: float = 0.001
    dual_learning_rate: float = 0.005
    dual_tolerance: float = 0.01
    initial_multiplier: float = 1.0
    maximum_multiplier: float = 20.0
    cost_clip: float = 10.0

    def __post_init__(self) -> None:
        if self.version not in {
            "firm_cmdp_v1",
            "firm_cmdp_v2",
            "firm_cmdp_v3",
            "firm_cmdp_v4",
            "firm_cmdp_v5",
        }:
            raise ValueError(
                "reward_adapter.version must be one of: firm_cmdp_v1, "
                "firm_cmdp_v2, firm_cmdp_v3, firm_cmdp_v4, firm_cmdp_v5"
            )
        for name in (
            "useful_compute_weight",
            "potential_shaping_weight",
            "switching_weight",
            "dual_learning_rate",
            "dual_tolerance",
            "initial_multiplier",
        ):
            _finite_non_negative(getattr(self, name), f"reward_adapter.{name}")
        _finite_positive(self.maximum_multiplier, "reward_adapter.maximum_multiplier")
        _finite_positive(self.cost_clip, "reward_adapter.cost_clip")
        if self.initial_multiplier > self.maximum_multiplier:
            raise ValueError(
                "reward_adapter.initial_multiplier must not exceed maximum_multiplier"
            )

    @classmethod
    def from_mapping(cls, value: object) -> FirmCMDPRewardConfig:
        if not isinstance(value, Mapping):
            raise ValueError("reward_adapter must be a mapping")
        raw = {str(key): item for key, item in value.items()}
        return cls(
            version=str(raw.get("version", "")),
            useful_compute_weight=_finite_non_negative(
                raw.get("useful_compute_weight", 1.0),
                "reward_adapter.useful_compute_weight",
            ),
            potential_shaping_weight=_finite_non_negative(
                raw.get("potential_shaping_weight", 0.25),
                "reward_adapter.potential_shaping_weight",
            ),
            switching_weight=_finite_non_negative(
                raw.get("switching_weight", 0.001),
                "reward_adapter.switching_weight",
            ),
            dual_learning_rate=_finite_non_negative(
                raw.get("dual_learning_rate", 0.005),
                "reward_adapter.dual_learning_rate",
            ),
            dual_tolerance=_finite_non_negative(
                raw.get("dual_tolerance", 0.01),
                "reward_adapter.dual_tolerance",
            ),
            initial_multiplier=_finite_non_negative(
                raw.get("initial_multiplier", 1.0),
                "reward_adapter.initial_multiplier",
            ),
            maximum_multiplier=_finite_positive(
                raw.get("maximum_multiplier", 20.0),
                "reward_adapter.maximum_multiplier",
            ),
            cost_clip=_finite_positive(
                raw.get("cost_clip", 10.0),
                "reward_adapter.cost_clip",
            ),
        )

    def as_dict(self) -> dict[str, float | str]:
        return {
            "version": self.version,
            "useful_compute_weight": self.useful_compute_weight,
            "potential_shaping_weight": self.potential_shaping_weight,
            "switching_weight": self.switching_weight,
            "dual_learning_rate": self.dual_learning_rate,
            "dual_tolerance": self.dual_tolerance,
            "initial_multiplier": self.initial_multiplier,
            "maximum_multiplier": self.maximum_multiplier,
            "cost_clip": self.cost_clip,
        }


@dataclass(slots=True)
class CMDPDualState:
    """Shared deterministic Lagrange multipliers for one vectorized run."""

    multipliers: dict[str, float]
    updates: int = 0

    @classmethod
    def initialize(cls, config: FirmCMDPRewardConfig) -> CMDPDualState:
        return cls(
            multipliers={
                name: config.initial_multiplier for name in CMDP_CONSTRAINT_NAMES
            }
        )

    @classmethod
    def from_dict(
        cls,
        value: object,
        config: FirmCMDPRewardConfig,
    ) -> CMDPDualState:
        if not isinstance(value, Mapping):
            raise ValueError("saved CMDP dual state must be a mapping")
        raw_multipliers = value.get("multipliers")
        if not isinstance(raw_multipliers, Mapping):
            raise ValueError("saved CMDP dual state is missing multipliers")
        multipliers: dict[str, float] = {}
        for name in CMDP_CONSTRAINT_NAMES:
            if name not in raw_multipliers:
                raise ValueError(f"saved CMDP dual state is missing multiplier: {name}")
            multiplier = _finite_non_negative(
                raw_multipliers[name], f"saved CMDP multiplier {name}"
            )
            if multiplier > config.maximum_multiplier:
                raise ValueError(f"saved CMDP multiplier {name} exceeds configured maximum")
            multipliers[name] = multiplier
        raw_updates = value.get("updates", 0)
        if isinstance(raw_updates, bool) or not isinstance(raw_updates, int) or raw_updates < 0:
            raise ValueError("saved CMDP dual updates must be a non-negative integer")
        return cls(multipliers=multipliers, updates=raw_updates)

    def update(
        self,
        peak_costs: Mapping[str, float],
        observed: Mapping[str, bool],
        config: FirmCMDPRewardConfig,
    ) -> None:
        """Apply one projected dual-ascent update after an episode."""

        for name in CMDP_CONSTRAINT_NAMES:
            if not observed.get(name, False):
                continue
            violation = min(max(float(peak_costs[name]), 0.0), config.cost_clip)
            updated = self.multipliers[name] + config.dual_learning_rate * (
                violation - config.dual_tolerance
            )
            self.multipliers[name] = float(
                min(max(updated, 0.0), config.maximum_multiplier)
            )
        self.updates += 1

    def as_dict(self) -> dict[str, object]:
        return {"multipliers": dict(self.multipliers), "updates": self.updates}


@dataclass(slots=True)
class _EpisodeConstraintState:
    peak_costs: dict[str, float] = field(
        default_factory=lambda: {name: 0.0 for name in CMDP_CONSTRAINT_NAMES}
    )
    observed: dict[str, bool] = field(
        default_factory=lambda: {name: False for name in CMDP_CONSTRAINT_NAMES}
    )

    def record(self, costs: Mapping[str, float], observed: Mapping[str, bool]) -> None:
        for name in CMDP_CONSTRAINT_NAMES:
            if observed[name]:
                self.observed[name] = True
                self.peak_costs[name] = max(self.peak_costs[name], costs[name])


def _float_info(info: Mapping[str, Any], name: str) -> float:
    value = info.get(name, 0.0)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"environment info {name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"environment info {name} must be finite and non-negative")
    return result


def _constraint_costs(info: Mapping[str, Any], *, episode_done: bool) -> tuple[
    dict[str, float], dict[str, bool]
]:
    completed_recovery = int(_float_info(info, "completed_recovery_event_count"))
    requested_reduction = _float_info(info, "requested_reduction_kw")
    costs = {
        "delivery": _float_info(info, "delivery_violation_cost"),
        "feasibility": _float_info(info, "deadline_feasibility_violation_cost"),
        "deadline": _float_info(info, "deadline_violation_cost"),
        "rebound": _float_info(info, "rebound_violation_cost"),
        "window_relief": _float_info(info, "window_relief_violation_cost"),
        "terminal_backlog": _float_info(info, "terminal_backlog_violation_cost"),
    }
    observed = {
        "delivery": requested_reduction > 0.0,
        "feasibility": True,
        "deadline": episode_done,
        "rebound": completed_recovery > 0,
        "window_relief": completed_recovery > 0,
        "terminal_backlog": episode_done,
    }
    return costs, observed


class FirmCMDPRewardWrapper(gym.Wrapper[Any, Any, Any, Any]):
    """Replace only the training scalar reward with an explicit firm-CMDP version."""

    def __init__(
        self,
        env: gym.Env[Any, Any],
        config: FirmCMDPRewardConfig,
        dual_state: CMDPDualState,
        *,
        gamma: float,
    ) -> None:
        super().__init__(env)
        self.cmdp_config = config
        self.dual_state = dual_state
        self.gamma = _finite_positive(gamma, "CMDP gamma")
        if self.gamma > 1.0:
            raise ValueError("CMDP gamma must not exceed one")
        self._previous_potential_cost = 0.0
        self._episode_step = 0
        self._previous_running_constraint_costs = {"rebound": 0.0, "window_relief": 0.0}
        self._episode = _EpisodeConstraintState()

    def _potential_costs(self, info: Mapping[str, Any]) -> tuple[float, float]:
        service_cost = _float_info(info, "excess_backlog_shaping_cost") + _float_info(
            info, "deadline_feasibility_violation_cost"
        )
        recovery_cost = 0.0
        if self.cmdp_config.version in {"firm_cmdp_v2", "firm_cmdp_v3"}:
            recovery_cost = _float_info(
                info, "running_rebound_violation_cost"
            ) + _float_info(info, "running_window_relief_violation_cost")
        return service_cost, recovery_cost

    @staticmethod
    def _capacity_gpu_h(info: Mapping[str, Any]) -> float:
        raw_state = info.get("control_state")
        if not isinstance(raw_state, Mapping):
            raise ValueError("CMDP reward requires control_state in environment info")
        return _finite_positive(
            raw_state.get("flexible_capacity_gpu_h"),
            "control_state.flexible_capacity_gpu_h",
        )

    def _training_constraint_costs(
        self,
        physical_costs: Mapping[str, float],
        info: Mapping[str, Any],
    ) -> dict[str, float]:
        costs = dict(physical_costs)
        if self.cmdp_config.version == "firm_cmdp_v5":
            window_active = info.get("event_window_active")
            if not isinstance(window_active, bool):
                raise ValueError("CMDP reward requires boolean event_window_active in info")
            costs["rebound"] = (
                _float_info(info, "running_rebound_violation_cost")
                if window_active
                else 0.0
            )
            costs["window_relief"] = (
                _float_info(info, "running_window_relief_violation_cost")
                if window_active
                else 0.0
            )
            return costs
        if self.cmdp_config.version != "firm_cmdp_v4":
            return costs
        window_active = info.get("event_window_active")
        if not isinstance(window_active, bool):
            raise ValueError("CMDP reward requires boolean event_window_active in info")
        if not window_active:
            self._previous_running_constraint_costs = {
                "rebound": 0.0,
                "window_relief": 0.0,
            }
            costs["rebound"] = 0.0
            costs["window_relief"] = 0.0
            return costs
        current = {
            "rebound": _float_info(info, "running_rebound_violation_cost"),
            "window_relief": _float_info(info, "running_window_relief_violation_cost"),
        }
        for name, value in current.items():
            costs[name] = value - self._previous_running_constraint_costs[name]
        self._previous_running_constraint_costs = current
        return costs

    def reset(self, **kwargs: Any) -> tuple[Any, dict[str, Any]]:
        observation, info = self.env.reset(**kwargs)
        self._previous_potential_cost = 0.0
        self._episode_step = 0
        self._previous_running_constraint_costs = {"rebound": 0.0, "window_relief": 0.0}
        self._episode = _EpisodeConstraintState()
        enriched = dict(info)
        enriched["training_reward_version"] = self.cmdp_config.version
        enriched["cmdp_multipliers"] = dict(self.dual_state.multipliers)
        return observation, enriched

    def step(self, action: Any) -> tuple[Any, float, bool, bool, dict[str, Any]]:
        observation, environment_reward, terminated, truncated, raw_info = self.env.step(action)
        info = dict(raw_info)
        episode_done = bool(terminated or truncated)
        capacity = self._capacity_gpu_h(info)
        useful_compute = _float_info(info, "executed_gpu_h") / capacity
        service_potential_cost, recovery_potential_cost = self._potential_costs(info)
        current_potential = service_potential_cost + recovery_potential_cost
        potential_shaping = self.cmdp_config.potential_shaping_weight * (
            self._previous_potential_cost - self.gamma * current_potential
        )
        self._previous_potential_cost = current_potential
        switching_penalty = self.cmdp_config.switching_weight * _float_info(
            info, "switching_cost"
        )
        physical_costs, observed = _constraint_costs(info, episode_done=episode_done)
        self._episode.record(physical_costs, observed)
        training_costs = self._training_constraint_costs(physical_costs, info)
        weighted_costs = {
            name: self.dual_state.multipliers[name]
            * min(
                max(training_costs[name], -self.cmdp_config.cost_clip),
                self.cmdp_config.cost_clip,
            )
            for name in CMDP_CONSTRAINT_NAMES
        }
        constraint_penalty = sum(weighted_costs.values())
        base_reward = self.cmdp_config.useful_compute_weight * useful_compute
        discount_correction = (
            self.gamma ** (-self._episode_step)
            if self.cmdp_config.version == "firm_cmdp_v3"
            else 1.0
        )
        time_neutral_reward = discount_correction * (
            base_reward - switching_penalty - constraint_penalty
        )
        training_reward = time_neutral_reward + potential_shaping
        info.update(
            {
                "environment_reward": float(environment_reward),
                "training_reward_version": self.cmdp_config.version,
                "training_useful_compute_reward": base_reward,
                "training_potential_shaping_reward": potential_shaping,
                "training_service_potential_cost": service_potential_cost,
                "training_recovery_potential_cost": recovery_potential_cost,
                "training_potential_cost": current_potential,
                "training_switching_penalty": switching_penalty,
                "training_constraint_penalty": constraint_penalty,
                "training_discount_correction": discount_correction,
                "training_time_neutral_reward": time_neutral_reward,
                **{f"cmdp_{name}_cost": value for name, value in training_costs.items()},
                **{
                    f"cmdp_physical_{name}_cost": value
                    for name, value in physical_costs.items()
                },
                **{
                    f"cmdp_{name}_multiplier": value
                    for name, value in self.dual_state.multipliers.items()
                },
            }
        )
        self._episode_step += 1
        if episode_done:
            self.dual_state.update(
                self._episode.peak_costs,
                self._episode.observed,
                self.cmdp_config,
            )
            info["cmdp_dual_updated"] = True
            info["cmdp_episode_peak_costs"] = dict(self._episode.peak_costs)
            info["cmdp_multipliers_after_update"] = dict(self.dual_state.multipliers)
        return observation, float(training_reward), terminated, truncated, info
