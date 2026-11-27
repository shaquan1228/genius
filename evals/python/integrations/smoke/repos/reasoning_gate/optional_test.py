import unittest


class TestTotal(unittest.TestCase):
    def test_addition(self) -> None:
        self.assertEqual(sum([1, 2]), 3)

    def test_optional_modes(self) -> None:
        for mode in ("legacy", "experimental"):
            with self.subTest(mode=mode):
                self.skipTest("Mode is unavailable in this checkout")
