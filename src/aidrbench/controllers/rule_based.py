"""Conservative P0 rule-controller scaffold.

Threshold calibration and forecast-aware behavior belong to P3/P4.  This
implementation only establishes deterministic action selection for smoke tests.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from aidrbench.controllers.base import BaseController
from aidrbench.envs.actions import ActionComponents, encode_action


class RuleBasedController(BaseController):
    def act(self, observation: Mapping[str, Any], deterministic: bool = True) -> int:
        del deterministic
        dr_active = bool(observation.get("dr_active", False))
        urgent_batch = bool(observation.get("urgent_batch", False))

        if not dr_active:
            batch_gpus = 2 if urgent_batch else 1
            return encode_action(ActionComponents(1.00, batch_gpus, 1.00))

        # First shed delay-tolerant work. Keep inference at its default cap in P0.
        return encode_action(ActionComponents(1.00, 0, 0.84))
