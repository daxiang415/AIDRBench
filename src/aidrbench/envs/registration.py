"""Gymnasium registration hook kept import-safe before dependencies exist."""

ENV_ID = "AIDRBench-v0"


def register_environments() -> None:
    try:
        from gymnasium.envs.registration import register
    except ModuleNotFoundError as exc:
        raise RuntimeError("Install the project dependencies before registering Gymnasium envs") from exc

    register(id=ENV_ID, entry_point="aidrbench.envs.community_dc_env:CommunityAIDemandResponseEnv")
