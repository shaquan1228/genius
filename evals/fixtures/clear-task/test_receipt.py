import unittest
from receipt import total


class ReceiptTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(total([]), 0)

    def test_single_quantity(self):
        self.assertEqual(total([(3, 1), (4, 1)]), 7)
