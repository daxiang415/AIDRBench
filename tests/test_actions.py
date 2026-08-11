from __future__ import annotations

import unittest

from aidrbench.envs.actions import ACTION_COUNT, ActionComponents, all_actions, decode_action, encode_action


class ActionCodecTests(unittest.TestCase):
    def test_all_27_actions_are_unique(self) -> None:
        actions = all_actions()
        self.assertEqual(ACTION_COUNT, 27)
        self.assertEqual(len(actions), ACTION_COUNT)
        self.assertEqual(len(set(actions)), ACTION_COUNT)

    def test_round_trip(self) -> None:
        for action_id in range(ACTION_COUNT):
            with self.subTest(action_id=action_id):
                self.assertEqual(encode_action(decode_action(action_id)), action_id)

    def test_documented_boundaries(self) -> None:
        self.assertEqual(decode_action(0), ActionComponents(0.70, 0, 0.60))
        self.assertEqual(decode_action(26), ActionComponents(1.00, 2, 1.00))

    def test_rejects_invalid_action_ids(self) -> None:
        for value in (-1, 27):
            with self.assertRaises(ValueError):
                decode_action(value)
        with self.assertRaises(TypeError):
            decode_action(True)


if __name__ == "__main__":
    unittest.main()
