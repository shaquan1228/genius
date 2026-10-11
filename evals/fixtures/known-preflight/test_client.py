import unittest
import config
from client import timeout


class ClientTests(unittest.TestCase):
    def test_default_matches_config(self):
        self.assertEqual(timeout(), config.TIMEOUT_SECONDS)

    def test_override(self):
        self.assertEqual(timeout(5), 5)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            timeout(0)
