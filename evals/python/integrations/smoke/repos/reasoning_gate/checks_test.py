import unittest


class TestTotal(unittest.TestCase):
    def test_addition(self) -> None:
        self.assertEqual(sum([1, 2]), 3)
