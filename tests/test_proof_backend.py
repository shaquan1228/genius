import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "skills/reasoning/scripts/prove.sh"
FIXTURE = ROOT / "evals/python/integrations/smoke/repos/basic"


class MarkdownBackend(unittest.TestCase):
    def run_proof(self, *arguments, **environment):
        env = dict(os.environ, BEND_BIN="/missing/bend")
        env.pop("GENIUS_PROOF_BACKEND", None)
        return subprocess.run(
            ["bash", RUNNER, *arguments], cwd=FIXTURE, text=True, capture_output=True,
            env=env | environment, timeout=30,
        )

    def test_default_reads_the_rule_and_observes_the_requested_suite(self):
        rule = (ROOT / "docs/proofs/004-INDEPENDENT-PREMISE-VALIDATION.md").read_text()
        for pattern, code in (("checks_test.py", 0), ("integration_test.py", 1)):
            with self.subTest(pattern=pattern):
                result = self.run_proof("gns-004", "unittest", ".", pattern)
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertTrue(result.stdout.startswith(rule))
                self.assertRegex(result.stdout.splitlines()[-1], r"^[a-f0-9]{32}$")
                self.assertIn("Ran 1 test", result.stderr)

    def test_markdown_git_result_comes_from_the_requested_commit(self):
        def git(*args):
            return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

        commit = git("rev-parse", "HEAD")
        blob = git("rev-parse", "HEAD:README.md")
        result = self.run_proof("postulate-001", "git-blob", commit, "README.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("The Loop Is Epistemology", result.stdout)
        self.assertEqual(result.stdout.splitlines()[-1], f"blob {blob}")
        wrong = "0" * len(blob)
        result = self.run_proof("gns-004", "git-blob", commit, "README.md", wrong)
        self.assertEqual(result.stdout.splitlines()[-1], f"blob {blob}")

    def test_pilot_launcher_respects_the_backend_and_keeps_its_statuses(self):
        launcher = RUNNER.with_name("check-tests.sh")
        for directory, pattern, code, status in (
            (".", "checks_test.py", 0, "confirmed"),
            (".", "integration_test.py", 1, "needs_evidence"),
            ("missing", "checks_test.py", 2, "unavailable"),
        ):
            with self.subTest(directory=directory, pattern=pattern):
                result = subprocess.run(
                    ["sh", launcher, directory, pattern], cwd=FIXTURE,
                    text=True, capture_output=True, timeout=30,
                    env=dict(os.environ, GENIUS_PROOF_BACKEND="markdown", BEND_BIN="/missing/bend"),
                )
                self.assertEqual((result.returncode, result.stdout.strip()), (code, status))

    def test_unknown_backend_fails_before_running_an_observer(self):
        result = self.run_proof("gns-004", "unittest", ".", GENIUS_PROOF_BACKEND="unknown")
        self.assertEqual((result.returncode, result.stdout), (2, ""))
        self.assertIn("Expected proof backend", result.stderr)
