"""Gymnasium registration for V0 hourly environments."""

CONTINUOUS_ENV_ID = "AIDRBench-Continuous-v0"
DISCRETE_ENV_ID = "AIDRBench-Discrete-v0"
ENV_ID = DISCRETE_ENV_ID


def register_environments() -> None:
    try:
        from gymnasium.envs.registration import register
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Install the project dependencies before registering Gymnasium envs"
        ) from exc

    from gymnasium.envs.registration import registry

    registrations = {
        CONTINUOUS_ENV_ID: (
            "aidrbench.envs.community_ai_dr_env:ContinuousCommunityAIDemandResponseEnv"
        ),
        DISCRETE_ENV_ID: (
            "aidrbench.envs.community_ai_dr_env:DiscreteCommunityAIDemandResponseEnv"
        ),
    }
    for env_id, entry_point in registrations.items():
        if env_id not in registry:
            register(id=env_id, entry_point=entry_point)
