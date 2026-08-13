"""P2 telemetry adapters."""

from aidrbench.telemetry.nvidia_smi import (
    NvidiaSmiError,
    collect_nvidia_smi_telemetry,
    sample_nvidia_smi,
)

__all__ = ["NvidiaSmiError", "collect_nvidia_smi_telemetry", "sample_nvidia_smi"]
