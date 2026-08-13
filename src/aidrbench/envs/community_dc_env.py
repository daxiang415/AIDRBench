"""Backward-compatible import for the hourly discrete V0 environment."""

from aidrbench.envs.community_ai_dr_env import (
    DiscreteCommunityAIDemandResponseEnv as CommunityAIDemandResponseEnv,
)

__all__ = ["CommunityAIDemandResponseEnv"]
