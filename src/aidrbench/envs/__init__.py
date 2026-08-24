"""Hourly community--AI data-centre environment interfaces."""

from aidrbench.envs.community_ai_dr_env import (
    ContinuousCommunityAIDemandResponseEnv,
    DiscreteCommunityAIDemandResponseEnv,
    HourlyCommunityAIDemandResponseEnv,
)
from aidrbench.envs.registration import register_environments

register_environments()

__all__ = [
    "ContinuousCommunityAIDemandResponseEnv",
    "DiscreteCommunityAIDemandResponseEnv",
    "HourlyCommunityAIDemandResponseEnv",
]
