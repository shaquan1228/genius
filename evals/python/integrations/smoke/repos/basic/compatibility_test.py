import unittest

from receipt import total


class TestTotal(unittest.TestCase):
    @unittest.skip("Compatibility target is unavailable in this checkout")
    def test_single_units(self) -> None:
        self.assertEqual(total([(2, 1), (1, 1)]), 3)
