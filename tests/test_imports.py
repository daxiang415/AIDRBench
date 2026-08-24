from __future__ import annotations

import importlib
import unittest


class ImportSmokeTests(unittest.TestCase):
    def test_formal_mainline_modules_import(self) -> None:
        modules = (
            "aidrbench",
            "aidrbench.cli",
            "aidrbench.calibration",
            "aidrbench.controllers",
            "aidrbench.data.frozen_scenarios",
            "aidrbench.envs",
            "aidrbench.evaluation",
            "aidrbench.evaluation.frozen_causal_certificate",
            "aidrbench.evaluation.hosting_capacity",
            "aidrbench.telemetry",
            "aidrbench.workloads",
        )
        for module in modules:
            with self.subTest(module=module):
                importlib.import_module(module)


if __name__ == "__main__":
    unittest.main()
