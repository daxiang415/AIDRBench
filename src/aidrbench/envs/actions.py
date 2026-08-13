"""Canonical codec for the 27 discrete V0 actions."""

from __future__ import annotations

from dataclasses import dataclass

INFERENCE_CAP_RATIOS = (0.84, 0.92, 1.00)
BATCH_GPU_COUNTS = (0, 1, 2)
BATCH_CAP_RATIOS = (0.84, 0.92, 1.00)
ACTION_COUNT = 27


@dataclass(frozen=True, slots=True)
class ActionComponents:
    inference_cap_ratio: float
    batch_gpu_count: int
    batch_cap_ratio: float


def decode_action(action: int) -> ActionComponents:
    """Decode an action ID using the README section 21.1 mapping."""
    if isinstance(action, bool) or not isinstance(action, int):
        raise TypeError("action must be an integer")
    if not 0 <= action < ACTION_COUNT:
        raise ValueError(f"action must be in [0, {ACTION_COUNT - 1}]")

    inference_index, remainder = divmod(action, 9)
    batch_gpu_index, batch_cap_index = divmod(remainder, 3)
    return ActionComponents(
        inference_cap_ratio=INFERENCE_CAP_RATIOS[inference_index],
        batch_gpu_count=BATCH_GPU_COUNTS[batch_gpu_index],
        batch_cap_ratio=BATCH_CAP_RATIOS[batch_cap_index],
    )


def encode_action(components: ActionComponents) -> int:
    """Encode validated components into their stable action ID."""
    try:
        inference_index = INFERENCE_CAP_RATIOS.index(components.inference_cap_ratio)
        batch_gpu_index = BATCH_GPU_COUNTS.index(components.batch_gpu_count)
        batch_cap_index = BATCH_CAP_RATIOS.index(components.batch_cap_ratio)
    except ValueError as exc:
        raise ValueError(f"unsupported action components: {components}") from exc
    return inference_index * 9 + batch_gpu_index * 3 + batch_cap_index


def all_actions() -> tuple[ActionComponents, ...]:
    return tuple(decode_action(action) for action in range(ACTION_COUNT))
