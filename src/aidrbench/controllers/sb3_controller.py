"""Stable-Baselines3 policy adapter placeholder for P4."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from aidrbench.controllers.base import BaseController


class SB3Controller(BaseController):
    def act(self, observation: Mapping[str, Any], deterministic: bool = True) -> int:
        del observation, deterministic
        raise NotImplementedError("SB3Controller is implemented in P4 after the environment exists")
