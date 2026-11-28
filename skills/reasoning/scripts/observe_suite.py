"""Observe a unittest discovery suite in the current checkout."""
import contextlib
import sys
import unittest
from pathlib import Path
from uuid import uuid4


class SuiteResult(unittest.TextTestResult):
    any_passed = False

    def addSuccess(self, test):
        super().addSuccess(test)
        self.any_passed = True


def main(directory, pattern):
    root = Path.cwd()
    target = (root / directory).resolve()
    if not target.is_relative_to(root) or not target.is_dir():
        print("test directory must exist inside the checkout", file=sys.stderr)
        return 2
    sys.path.insert(0, str(root))
    with contextlib.redirect_stdout(sys.stderr):
        suite = unittest.defaultTestLoader.discover(str(target), pattern=pattern)
        result = unittest.TextTestRunner(resultclass=SuiteResult).run(suite)
    # Reusing a result keeps its run ID. A fresh run gets a new one.
    print(uuid4().hex)
    return 0 if result.wasSuccessful() and result.any_passed else 1


if __name__ == "__main__":
    try:
        status = main(*sys.argv[1:])
    except (Exception, SystemExit) as error:
        print(f"unittest did not produce a result: {error}", file=sys.stderr)
        status = 2
    sys.exit(status)
