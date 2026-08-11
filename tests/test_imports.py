from __future__ import annotations

import importlib
import unittest


class ImportSmokeTests(unittest.TestCase):
    def test_p0_modules_import_without_third_party_packages(self) -> None:
        modules = (
            "aidrbench",
            "aidrbench.cli",
            "aidrbench.controllers",
            "aidrbench.datacenter",
            "aidrbench.envs.actions",
            "aidrbench.evaluation",
            "aidrbench.hil",
            "aidrbench.telemetry",
            "aidrbench.workloads",
        )
        for module in modules:
            with self.subTest(module=module):
                importlib.import_module(module)


if __name__ == "__main__":
    unittest.main()
