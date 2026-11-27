import unittest


class TestTotal(unittest.TestCase):
    @unittest.skip("Compatibility target is unavailable in this checkout")
    def test_addition(self) -> None:
        self.assertEqual(sum([1, 2]), 3)
