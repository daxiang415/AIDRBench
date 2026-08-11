from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from aidrbench.project_check import check_project


class ProjectCheckTests(unittest.TestCase):
    def test_current_repository_has_required_skeleton(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertTrue(check_project(root).ok)

    def test_missing_files_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = check_project(directory)
        self.assertFalse(report.ok)
        self.assertIn("README.md", report.missing)


if __name__ == "__main__":
    unittest.main()
