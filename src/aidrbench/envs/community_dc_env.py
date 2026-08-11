"""Placeholder for the P3 Gymnasium environment implementation."""

from __future__ import annotations

try:
    import gymnasium as gym
except ModuleNotFoundError:  # P0 deliberately supports validation before uv sync.
    gym = None  # type: ignore[assignment]


if gym is not None:

    class CommunityAIDemandResponseEnv(gym.Env):  # type: ignore[misc]
        """P3 implementation target; deliberately unavailable during P0."""

        metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 1}

        def __init__(self, *args: object, **kwargs: object) -> None:
            raise NotImplementedError("CommunityAIDemandResponseEnv is implemented in P3")

else:

    class CommunityAIDemandResponseEnv:
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise RuntimeError("Gymnasium is not installed; run uv sync in a network-enabled phase")
