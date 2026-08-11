"""Placeholder for the P3 Gymnasium environment implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import gymnasium as gym

    _EnvBase = gym.Env[object, int]
    _GYM_AVAILABLE = True
else:
    try:
        import gymnasium as gym
    except ModuleNotFoundError:  # P0 deliberately supports validation before dependency sync.
        _EnvBase = object
        _GYM_AVAILABLE = False
    else:
        _EnvBase = gym.Env
        _GYM_AVAILABLE = True


class CommunityAIDemandResponseEnv(_EnvBase):
    """P3 implementation target; deliberately unavailable during P0."""

    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 1}

    def __init__(self, *args: object, **kwargs: object) -> None:
        if not _GYM_AVAILABLE:
            raise RuntimeError(
                "Gymnasium is not installed; create and activate the Conda environment"
            )
        raise NotImplementedError("CommunityAIDemandResponseEnv is implemented in P3")
