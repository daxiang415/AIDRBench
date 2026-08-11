"""Counterfactual no-control baseline."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from aidrbench.controllers.base import BaseController
from aidrbench.envs.actions import ActionComponents, encode_action


NO_CONTROL_ACTION = encode_action(ActionComponents(1.00, 2, 1.00))


class NoControlController(BaseController):
    def act(self, observation: Mapping[str, Any], deterministic: bool = True) -> int:
        del observation, deterministic
        return NO_CONTROL_ACTION
