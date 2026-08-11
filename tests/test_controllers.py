from __future__ import annotations

import unittest

from aidrbench.controllers.no_control import NO_CONTROL_ACTION, NoControlController
from aidrbench.controllers.rule_based import RuleBasedController
from aidrbench.envs.actions import ActionComponents, decode_action


class ControllerSmokeTests(unittest.TestCase):
    def test_no_control_is_full_service_action(self) -> None:
        action = NoControlController().act({})
        self.assertEqual(action, NO_CONTROL_ACTION)
        self.assertEqual(decode_action(action), ActionComponents(1.00, 2, 1.00))

    def test_rule_based_sheds_batch_during_dr(self) -> None:
        action = RuleBasedController().act({"dr_active": True})
        self.assertEqual(decode_action(action), ActionComponents(1.00, 0, 0.60))

    def test_rule_based_uses_batch_capacity_without_dr(self) -> None:
        normal = decode_action(RuleBasedController().act({"dr_active": False}))
        urgent = decode_action(
            RuleBasedController().act({"dr_active": False, "urgent_batch": True})
        )
        self.assertEqual(normal.batch_gpu_count, 1)
        self.assertEqual(urgent.batch_gpu_count, 2)


if __name__ == "__main__":
    unittest.main()
