import unittest

from receipt import total


class TestTotal(unittest.TestCase):
    def test_single_units(self) -> None:
        self.assertEqual(total([(2, 1), (1, 1)]), 3)
