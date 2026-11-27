import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BEND = os.environ.get("BEND_BIN") or shutil.which("bend")
RUNNER = ROOT / "skills/reasoning/scripts/prove.sh"


@unittest.skipUnless(BEND, "Bend 2 is required for executable checks")
class ProofRunner(unittest.TestCase):
    def test_runner_checks_named_suite(self):
        fixture = ROOT / "evals/python/integrations/smoke/repos/reasoning_gate"
        cases = (
            (".", "checks_test.py", 0, "supported"),
            (".", "optional_test.py", 0, "supported"),
            (".", "integration_test.py", 1, "contradicted"),
            (".", "compatibility_test.py", 1, "contradicted"),
            (".", "setup_test.py", 1, "contradicted"),
            ("missing", "test*.py", 2, "unavailable"),
        )
        for directory, pattern, exit_code, decision in cases:
            with self.subTest(directory=directory, pattern=pattern):
                result = subprocess.run(
                    ["bash", RUNNER, "gns-004", "unittest", directory, pattern],
                    cwd=fixture,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                    env=dict(os.environ, BEND_BIN=BEND, BEND_NO_TELEMETRY="1"),
                )
                self.assertEqual(result.returncode, exit_code, result.stderr)
                self.assertEqual(result.stdout.strip(), decision)

    def test_one_committed_observation_checks_two_predictions(self):
        def git(*args):
            return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()

        def check(proof, path, expected, code, verdict, revision=None):
            result = subprocess.run(
                ["bash", RUNNER, proof, "git-blob", revision or commit, path, *expected],
                cwd=repo, text=True, capture_output=True, timeout=30,
                env=dict(os.environ, BEND_BIN=BEND),
            )
            self.assertEqual((result.returncode, result.stdout.strip()), (code, verdict), result.stderr)

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git("init", "-q")
            path = "recorded result.txt"
            (repo / path).write_text("InvalidInput\n")
            (repo / "--verdict").write_text("a different finding\n")
            (repo / "docs").mkdir()
            (repo / "docs" / "file").touch()
            git("add", "--", path, "--verdict", "docs")
            git("-c", "user.name=Fixture", "-c", "user.email=test@example.org", "commit", "-qm", "record")
            commit = git("rev-parse", "HEAD")
            recorded = git("rev-parse", f"HEAD:{path}")
            other = git("rev-parse", "HEAD:--verdict")
            (repo / path).write_text("The working copy now says otherwise.\n")

            check("postulate-001", path, [], 0, "observed")
            check("gns-004", path, [recorded], 0, "supported")
            check("gns-004", path, [other], 1, "contradicted")
            check("gns-004", "--verdict", [other], 0, "supported")
            for non_blob in ("docs", "missing"):
                check("postulate-001", non_blob, [], 0, "observed")
                check("gns-004", non_blob, [recorded], 1, "contradicted")
            unknown = "0" * len(commit)
            check("postulate-001", path, [], 2, "undecided", unknown)
            check("gns-004", path, [recorded], 2, "undecided", unknown)
            check("gns-004", path, [other, other], 2, "")
