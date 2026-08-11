"""MPC adapter placeholder for the P4 benchmark."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from aidrbench.controllers.base import BaseController


class MPCController(BaseController):
    def act(self, observation: Mapping[str, Any], deterministic: bool = True) -> int:
        del observation, deterministic
        raise NotImplementedError("MPCController is implemented in P4 after surrogate fitting")
