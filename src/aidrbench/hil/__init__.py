"""Hardware-in-the-loop interfaces with an explicit mutation boundary."""

from aidrbench.hil.actuator_client import (
    ActuatorError,
    NvidiaSmiPowerBackend,
    PowerActuator,
    PowerActuatorConfig,
)
from aidrbench.hil.backend import Backend

__all__ = [
    "ActuatorError",
    "Backend",
    "NvidiaSmiPowerBackend",
    "PowerActuator",
    "PowerActuatorConfig",
]
