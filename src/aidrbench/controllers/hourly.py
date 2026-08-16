"""Baselines defined for the V0 hourly workload-shifting environment."""

from __future__ import annotations

from typing import Any

import numpy as np

from aidrbench.controllers.hourly_oracle import HourlyFullHorizonOracleController
from aidrbench.envs.community_ai_dr_env import DISCRETE_ACTION_FRACTIONS


def _is_discrete(env: Any) -> bool:
    return getattr(env.config, "action_mode", None) == "discrete"


def fraction_to_action(env: Any, fraction: float) -> np.ndarray | int:
    """Encode a physical execution fraction in an environment action space."""

    bounded = float(np.clip(fraction, 0.0, 1.0))
    if _is_discrete(env):
        return int(np.argmin(np.abs(DISCRETE_ACTION_FRACTIONS - bounded)))
    return np.asarray((bounded,), dtype=np.float32)


class HourlyNoControlController:
    """Execute all available flexible capacity every hour."""

    name = "no_control"
    information_structure = "causal_control_state"

    def act(self, env: Any, info: dict[str, Any]) -> np.ndarray | int:
        del info
        return fraction_to_action(env, 1.0)


class HourlyThresholdController:
    """Use the instantaneous PCC headroom rule from README section 18.2."""

    name = "threshold"
    information_structure = "causal_control_state"

    def act(self, env: Any, info: dict[str, Any]) -> np.ndarray | int:
        state = info["control_state"]
        return fraction_to_action(env, threshold_fraction(state))


def threshold_fraction(state: dict[str, Any]) -> float:
    """Return the threshold-RBC execution fraction from a control state."""

    available_budget_kw = (
        float(state["pcc_limit_kw"])
        - float(state["community_power_kw"])
        - float(state["rigid_dc_power_kw"])
    )
    dynamic_pool_kw = float(state["flexible_pool_peak_power_kw"])
    if available_budget_kw <= 0.0 or dynamic_pool_kw <= 0.0:
        return 0.0
    return float(np.clip(available_budget_kw / dynamic_pool_kw, 0.0, 1.0))


class HourlyEDFValleyController:
    """Serve urgent buckets, otherwise shift flexible work into load valleys."""

    name = "edf_valley"
    information_structure = "causal_control_state_plus_environment_forecast"

    def __init__(
        self, *, valley_percentile: float = 0.40, high_load_fraction: float = 0.25
    ) -> None:
        if not 0.0 < valley_percentile < 1.0:
            raise ValueError("valley_percentile must be in (0, 1)")
        if not 0.0 <= high_load_fraction <= 1.0:
            raise ValueError("high_load_fraction must be in [0, 1]")
        self.valley_percentile = valley_percentile
        self.high_load_fraction = high_load_fraction

    def act(self, env: Any, info: dict[str, Any]) -> np.ndarray | int:
        state = info["control_state"]
        forecast = np.asarray(state["community_forecast_kw"], dtype="float64")
        valley_threshold_kw = float(np.quantile(forecast, self.valley_percentile))
        current_community_kw = float(state["community_power_kw"])
        valley_fraction = (
            1.0 if current_community_kw <= valley_threshold_kw else self.high_load_fraction
        )
        capacity_gpu_h = float(state["flexible_capacity_gpu_h"])
        urgent_fraction = (
            float(state["urgent_gpu_h"]) / capacity_gpu_h if capacity_gpu_h > 0.0 else 0.0
        )
        safe_fraction = min(threshold_fraction(state), valley_fraction)
        # Deadlines are a hard service constraint, so urgency can override
        # peak avoidance in this rule baseline.
        return fraction_to_action(env, max(safe_fraction, urgent_fraction))


class HourlyMPCController:
    """Rolling LP workload scheduler with deadline, PCC and capacity constraints.

    This online baseline receives only the environment's short load/limit
    forecast and uses a historical-mean arrival forecast. It is not an oracle.
    """

    name = "mpc"
    forecast_assumption = "6h_environment_load_limit_forecast+historical_mean_arrivals"
    information_structure = "causal_control_state_plus_6h_environment_forecast"

    def __init__(
        self,
        *,
        horizon_hours: int = 6,
        deadline_penalty: float = 1_000.0,
        limit_penalty: float = 20.0,
        backlog_penalty: float = 0.2,
        switching_penalty: float = 0.02,
    ) -> None:
        if horizon_hours <= 0:
            raise ValueError("horizon_hours must be positive")
        if min(deadline_penalty, limit_penalty, backlog_penalty, switching_penalty) < 0.0:
            raise ValueError("MPC penalties must be non-negative")
        self.horizon_hours = horizon_hours
        self.deadline_penalty = deadline_penalty
        self.limit_penalty = limit_penalty
        self.backlog_penalty = backlog_penalty
        self.switching_penalty = switching_penalty
        self._arrival_history_gpu_h: list[float] = []
        self._previous_fraction = 1.0

    def reset(self) -> None:
        """Clear previous-arrival estimates between evaluation episodes."""

        self._arrival_history_gpu_h.clear()
        self._previous_fraction = 1.0

    def _forecast_arrivals(self, env: Any, horizon: int) -> np.ndarray:
        """Forecast arrivals strictly after the already released current hour."""

        if self._arrival_history_gpu_h:
            mean_arrival = float(np.mean(self._arrival_history_gpu_h[-24:]))
        else:
            mean_arrival = (
                env.power_model.data_center.total_gpu_count
                * env.config.target_total_utilization
                * env.config.workload_mix.flexible_share
            )
        forecast = np.full(horizon, mean_arrival, dtype="float64")
        # At action time the environment has already placed this hour's jobs
        # in ``state['backlog_gpu_h']``.  A causal MPC cannot execute an
        # estimate of the next release in the current interval.
        forecast[0] = 0.0
        return forecast

    @staticmethod
    def _deadline_requirements(
        remaining_gpu_h: np.ndarray,
        arrival_forecast_gpu_h: np.ndarray,
        env: Any,
    ) -> np.ndarray:
        """Cumulative work that must finish by each future interval."""

        horizon = len(arrival_forecast_gpu_h)
        current_due = np.cumsum(remaining_gpu_h[:horizon])
        if len(current_due) < horizon:
            current_due = np.pad(current_due, (0, horizon - len(current_due)), mode="edge")
        requirements = current_due[:horizon]
        flexible_share = env.config.workload_mix.flexible_share
        if flexible_share <= 0.0:
            return requirements
        for job_class in ("training", "offline_inference"):
            class_share = env.config.workload_mix.flexible_class_share(job_class)
            if class_share <= 0.0:
                continue
            relative_share = class_share / flexible_share
            slack = env.config.deadline_policy.for_class(job_class).minimum_slack_h
            for arrival_hour, arrival_gpu_h in enumerate(arrival_forecast_gpu_h):
                deadline_hour = arrival_hour + slack - 1
                if deadline_hour < horizon:
                    requirements[deadline_hour:] += arrival_gpu_h * relative_share
        return requirements

    def act(self, env: Any, info: dict[str, Any]) -> np.ndarray | int:
        if "arrival_gpu_h" in info:
            self._arrival_history_gpu_h.append(float(info["arrival_gpu_h"]))
        state = info["control_state"]
        community_forecast = np.asarray(state["community_forecast_kw"], dtype="float64")
        pcc_limit_forecast = np.asarray(state["pcc_limit_forecast_kw"], dtype="float64")
        horizon = min(self.horizon_hours, len(community_forecast), len(pcc_limit_forecast))
        if horizon <= 0:
            return fraction_to_action(env, threshold_fraction(state))
        capacity_gpu_h = float(state["flexible_capacity_gpu_h"])
        dynamic_pool_kw = float(state["flexible_pool_peak_power_kw"])
        if capacity_gpu_h <= 0.0 or dynamic_pool_kw <= 0.0:
            return fraction_to_action(env, 0.0)
        arrivals = self._forecast_arrivals(env, horizon)
        remaining = np.asarray(state["remaining_by_deadline_gpu_h"], dtype="float64")
        deadline_requirements = self._deadline_requirements(remaining, arrivals, env)
        available_work = float(state["backlog_gpu_h"]) + np.cumsum(arrivals)
        fixed_pcc_kw = community_forecast[:horizon] + float(state["rigid_dc_power_kw"])
        dynamic_kw_per_gpu_h = dynamic_pool_kw / capacity_gpu_h
        try:
            import cvxpy as cp

            execution = cp.Variable(horizon, nonneg=True)
            violation = cp.Variable(horizon, nonneg=True)
            deadline_shortfall = cp.Variable(horizon, nonneg=True)
            switching = cp.Variable(horizon, nonneg=True)
            cumulative_execution = cp.cumsum(execution)  # type: ignore[attr-defined]
            backlog = available_work - cumulative_execution
            constraints = [
                execution <= capacity_gpu_h,
                cumulative_execution <= available_work,
                cumulative_execution + deadline_shortfall >= deadline_requirements,
                violation
                >= fixed_pcc_kw + dynamic_kw_per_gpu_h * execution - pcc_limit_forecast[:horizon],
                switching[0] >= execution[0] / capacity_gpu_h - self._previous_fraction,
                switching[0] >= self._previous_fraction - execution[0] / capacity_gpu_h,
            ]
            if horizon > 1:
                constraints.extend(
                    [
                        switching[1:]
                        >= execution[1:] / capacity_gpu_h - execution[:-1] / capacity_gpu_h,
                        switching[1:]
                        >= execution[:-1] / capacity_gpu_h - execution[1:] / capacity_gpu_h,
                    ]
                )
            objective = cp.Minimize(
                self.deadline_penalty * cp.sum(deadline_shortfall)  # type: ignore[attr-defined]
                + self.limit_penalty * cp.sum(violation)  # type: ignore[attr-defined]
                + self.backlog_penalty
                * cp.sum(backlog)  # type: ignore[attr-defined]
                / max(capacity_gpu_h * 48.0, 1.0)
                + self.switching_penalty * cp.sum(switching)  # type: ignore[attr-defined]
            )
            problem = cp.Problem(objective, constraints)
            problem.solve(solver="HIGHS", warm_start=True)  # type: ignore[no-untyped-call]
            if execution.value is None or problem.status not in {"optimal", "optimal_inaccurate"}:
                return fraction_to_action(env, threshold_fraction(state))
            fraction = float(np.clip(execution.value[0] / capacity_gpu_h, 0.0, 1.0))
        except (ImportError, ValueError):
            return fraction_to_action(env, threshold_fraction(state))
        self._previous_fraction = fraction
        return fraction_to_action(env, fraction)


class HourlyRobustMPCController(HourlyMPCController):
    """Causal MPC with an upper envelope for unreleased future arrivals."""

    name = "robust_mpc"
    forecast_assumption = (
        "6h_environment_load_limit_forecast+historical_mean_plus_arrival_uncertainty_envelope"
    )
    information_structure = "causal_control_state_plus_6h_environment_forecast"

    def __init__(
        self,
        *,
        arrival_safety_sigma: float = 1.0,
        minimum_arrival_safety_fraction: float = 0.15,
        **kwargs: Any,
    ) -> None:
        if arrival_safety_sigma < 0.0:
            raise ValueError("arrival_safety_sigma must be non-negative")
        if minimum_arrival_safety_fraction < 0.0:
            raise ValueError("minimum_arrival_safety_fraction must be non-negative")
        super().__init__(**kwargs)
        self.arrival_safety_sigma = arrival_safety_sigma
        self.minimum_arrival_safety_fraction = minimum_arrival_safety_fraction

    def _forecast_arrivals(self, env: Any, horizon: int) -> np.ndarray:
        forecast = super()._forecast_arrivals(env, horizon)
        baseline = float(forecast[1] if horizon > 1 else 0.0)
        history = np.asarray(self._arrival_history_gpu_h[-24:], dtype="float64")
        spread = float(history.std(ddof=1)) if len(history) > 1 else 0.0
        safety_margin = max(
            self.arrival_safety_sigma * spread,
            self.minimum_arrival_safety_fraction * baseline,
        )
        if horizon > 1:
            forecast[1:] += safety_margin
        return forecast


def make_hourly_controller(
    name: str,
) -> (
    HourlyNoControlController
    | HourlyThresholdController
    | HourlyEDFValleyController
    | HourlyMPCController
    | HourlyRobustMPCController
    | HourlyFullHorizonOracleController
):
    """Build one of the P1 baselines by CLI-safe controller name."""

    if name == "no_control":
        return HourlyNoControlController()
    if name == "threshold":
        return HourlyThresholdController()
    if name == "edf_valley":
        return HourlyEDFValleyController()
    if name == "mpc":
        return HourlyMPCController()
    if name == "robust_mpc":
        return HourlyRobustMPCController()
    if name == "oracle":
        return HourlyFullHorizonOracleController()
    raise ValueError(f"unsupported hourly controller: {name}")
