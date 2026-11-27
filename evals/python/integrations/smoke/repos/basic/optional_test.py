import unittest

from receipt import total


class TestTotal(unittest.TestCase):
    def test_single_units(self) -> None:
        self.assertEqual(total([(2, 1), (1, 1)]), 3)

    def test_optional_modes(self) -> None:
        for mode in ("legacy", "experimental"):
            with self.subTest(mode=mode):
                self.skipTest("Mode is unavailable in this checkout")
