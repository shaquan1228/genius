import unittest

from receipt import total


class TestTotal(unittest.TestCase):
    def test_multiple_units(self) -> None:
        self.assertEqual(total([(2, 3), (1, 1)]), 7)
