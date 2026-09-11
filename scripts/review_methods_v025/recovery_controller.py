"""Causal memory of every observed call; no future event/arrival access."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class ObservedCall:
    event_id: int
    stop_hour: int
    recovery_stop_hour: int
    request_kw: float
    baseline_peak_kw: float = -math.inf


class AllWindowController:
    """Preserve all still-active call constraints around an unchanged proposer.

    Starts and durations are learned only from the current public control state.
    Each baseline peak contains observed hours, including the present decision.
    The constraints are sufficient electrical guards, not deadline guarantees.
    """

    name = "all_window_mpc"
    information_structure = "causal_control_state_and_memory_of_observed_calls"

    def __init__(self, proposer=None):
        self.proposer = proposer
        self.name = "all_window_mpc" if proposer is not None else "all_window_greedy"
        self.reset()

    def reset(self):
        self.hour = 0
        self.calls = {}
        self.audit = []
        if self.proposer is not None:
            self.proposer.reset()

    def act(self, env, info):
        state = info["control_state"]
        t = self.hour
        baseline = float(state["baseline_pcc_power_current_kw"])
        if state["event_active"]:
            eid = int(state["event_id"])
            if eid not in self.calls:
                stop = t + int(state["event_remaining_hours"])
                self.calls[eid] = ObservedCall(
                    eid,
                    stop,
                    stop + env.config.recovery_window_hours,
                    float(state["requested_reduction_kw"]),
                )
        active = [c for c in self.calls.values() if t < c.recovery_stop_hour]
        for call in active:
            call.baseline_peak_kw = max(call.baseline_peak_kw, baseline)
        reward = env.config.reward
        target = math.inf
        if state["event_active"]:
            target = baseline - reward.min_delivery_ratio * float(state["requested_reduction_kw"])
        for call in active:
            # Include event hours too: they can overlap an earlier recovery.
            target = min(
                target,
                call.baseline_peak_kw - reward.min_window_peak_relief_fraction * call.request_kw,
            )
            if t >= call.stop_hour:
                target = min(
                    target,
                    baseline
                    + reward.max_rebound_ratio * reward.min_delivery_ratio * call.request_kw,
                )
        proposed = 1.0 if self.proposer is None else float(self.proposer.act(env, info)[0])
        fixed = float(state["community_power_kw"]) + float(state["rigid_dc_power_kw"])
        dynamic = max(float(state["worst_class_peak_kw"]) - float(state["rigid_dc_power_kw"]), 1e-9)
        limit = (
            1.0
            if not math.isfinite(target)
            else float(np.clip((target - fixed) / dynamic, 0.0, 1.0))
        )
        fraction = min(proposed, limit)
        action = np.float32(fraction)
        if float(action) > fraction:
            action = np.nextafter(action, np.float32(0.0))
        self.audit.append(
            dict(
                hour=t,
                observed_active_windows=len(active),
                target_pcc_kw=None if not math.isfinite(target) else target,
                proposed_fraction=proposed,
                guarded_fraction=float(action),
                additional_cap_active=bool(float(action) < proposed - 1e-8),
                target_below_fixed_power=bool(target < fixed - 1e-8),
            )
        )
        if self.proposer is not None:
            self.proposer._previous_fraction = float(action)
        self.hour += 1
        return np.array([action], dtype=np.float32)
