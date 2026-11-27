import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

GATE = Path(__file__).resolve().parents[3] / "docs/proofs/reasoning/check-tests.bend"
UNAVAILABLE = 2
TEST_TIMEOUT = 120
BEND_TIMEOUT = 30
WORKER = """
import contextlib
import json
from pathlib import Path
import sys
import unittest

class CountingResult(unittest.TextTestResult):
    tests_passed = 0

    def addSuccess(self, test):
        super().addSuccess(test)
        self.tests_passed += 1

sys.path.insert(0, str(Path.cwd()))
with contextlib.redirect_stdout(sys.stderr):
    suite = unittest.defaultTestLoader.discover(sys.argv[1])
    result = unittest.TextTestRunner(stream=sys.stderr, resultclass=CountingResult).run(suite)
print(json.dumps({
    'tests_run': result.testsRun,
    'tests_passed': result.tests_passed,
    'successful': result.wasSuccessful(),
}))
"""


def test_observation(directory):
    run = subprocess.run(
        [sys.executable, "-I", "-B", "-c", WORKER, directory],
        stdout=subprocess.PIPE,
        text=True,
        check=True,
        timeout=TEST_TIMEOUT,
    )
    report = json.loads(run.stdout)
    passed = report["successful"] and report["tests_passed"] > 0
    return ("passed" if passed else "unconfirmed"), report["tests_run"]


def bend_decision(bend, *, observation):
    run = subprocess.run(
        [bend, str(GATE), observation],
        stdout=subprocess.PIPE,
        text=True,
        check=True,
        env={**os.environ, "BEND_NO_TELEMETRY": "1"},
        timeout=BEND_TIMEOUT,
    )
    decision = run.stdout.strip()
    if decision not in {"confirmed", "needs_evidence"}:
        raise ValueError("Bend returned an invalid gate result")
    return decision


def main():
    parser = argparse.ArgumentParser(description="Verify a claim about a Python unittest suite")
    parser.add_argument("--start-directory", default="tests")
    args = parser.parse_args()
    checkout = Path.cwd().resolve()
    directory = (checkout / args.start_directory).resolve()
    report = {"checkout": str(checkout), "suite": args.start_directory}
    if not directory.is_relative_to(checkout) or not directory.is_dir():
        report.update(
            decision="unavailable", reason="test directory must exist inside the checkout"
        )
        print(json.dumps(report))
        return UNAVAILABLE

    directory_name = directory.relative_to(checkout).as_posix()
    report["suite"] = directory_name
    try:
        observation, report["tests_run"] = test_observation(directory_name)
        bend = os.environ.get("BEND_BIN") or shutil.which("bend")
        if bend is None:
            raise FileNotFoundError("Bend is unavailable")
        report["decision"] = bend_decision(bend, observation=observation)
    except (subprocess.SubprocessError, OSError, ValueError) as error:
        report.update(decision="unavailable", reason=str(error))
    print(json.dumps(report))
    return {"confirmed": 0, "needs_evidence": 1, "unavailable": UNAVAILABLE}[report["decision"]]


if __name__ == "__main__":
    sys.exit(main())
