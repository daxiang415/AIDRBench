"""Controller contract shared by emulator and HIL evaluation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any


class BaseController(ABC):
    """Minimal algorithm-independent controller interface."""

    def reset(self, scenario_metadata: Mapping[str, Any] | None = None) -> None:
        """Reset episode-local state."""
        return None

    @abstractmethod
    def act(self, observation: Mapping[str, Any], deterministic: bool = True) -> int:
        """Return one canonical V0 action ID."""

    def close(self) -> None:
        """Release controller resources."""
        return None
