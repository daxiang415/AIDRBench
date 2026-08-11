from __future__ import annotations

import unittest

from aidrbench.hil.backend import Backend


class BackendContractTests(unittest.TestCase):
    def test_incomplete_backend_cannot_be_instantiated(self) -> None:
        class IncompleteBackend(Backend):
            pass

        with self.assertRaises(TypeError):
            IncompleteBackend()


if __name__ == "__main__":
    unittest.main()
