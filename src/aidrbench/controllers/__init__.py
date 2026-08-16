"""Controller interfaces and baseline adapters."""

from aidrbench.controllers.base import BaseController
from aidrbench.controllers.hourly import (
    HourlyEDFValleyController,
    HourlyMPCController,
    HourlyNoControlController,
    HourlyThresholdController,
    make_hourly_controller,
)
from aidrbench.controllers.hourly_oracle import HourlyFullHorizonOracleController
from aidrbench.controllers.no_control import NoControlController
from aidrbench.controllers.rule_based import RuleBasedController

__all__ = [
    "BaseController",
    "HourlyEDFValleyController",
    "HourlyFullHorizonOracleController",
    "HourlyMPCController",
    "HourlyNoControlController",
    "HourlyThresholdController",
    "NoControlController",
    "RuleBasedController",
    "make_hourly_controller",
]
