"""Common backend API for emulator and server-in-the-loop execution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any


class Backend(ABC):
    @abstractmethod
    def reset(self, scenario: Mapping[str, Any]) -> None:
        """Prepare a deterministic scenario."""

    @abstractmethod
    def apply_action(self, action: int) -> None:
        """Validate and apply one canonical action ID."""

    @abstractmethod
    def advance(self, dt_seconds: float) -> None:
        """Advance backend state without changing controller policy."""

    @abstractmethod
    def get_state(self) -> Mapping[str, Any]:
        """Return raw backend state."""

    @abstractmethod
    def get_metrics(self) -> Mapping[str, Any]:
        """Return raw KPIs, separate from training reward."""

    @abstractmethod
    def close(self) -> None:
        """Restore safe defaults and release resources."""
