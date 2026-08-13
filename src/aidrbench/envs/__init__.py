"""Environment interfaces and action definitions."""

from aidrbench.envs.actions import ACTION_COUNT, ActionComponents, decode_action, encode_action
from aidrbench.envs.community_ai_dr_env import (
    ContinuousCommunityAIDemandResponseEnv,
    DiscreteCommunityAIDemandResponseEnv,
    HourlyCommunityAIDemandResponseEnv,
)
from aidrbench.envs.registration import register_environments

register_environments()

__all__ = [
    "ACTION_COUNT",
    "ActionComponents",
    "ContinuousCommunityAIDemandResponseEnv",
    "DiscreteCommunityAIDemandResponseEnv",
    "HourlyCommunityAIDemandResponseEnv",
    "decode_action",
    "encode_action",
]
