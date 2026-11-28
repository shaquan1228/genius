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
    def run_proof(self, *arguments, cwd=None, **environment):
        return subprocess.run(
            ["bash", RUNNER, *arguments], cwd=cwd, text=True, capture_output=True, timeout=30,
            env=dict(os.environ, GENIUS_PROOF_BACKEND="bend", BEND_BIN=BEND, BEND_NO_TELEMETRY="1") | environment,
        )

    def test_runner_checks_named_suite(self):
        fixture = ROOT / "evals/python/integrations/smoke/repos/basic"
        cases = (
            (".", "checks_test.py", 0, "supported"),
            (".", "optional_test.py", 0, "supported"),
            (".", "integration_test.py", 1, "contradicted"),
            (".", "compatibility_test.py", 1, "contradicted"),
            (".", "setup_test.py", 1, "contradicted"),
            (".", "zero_matches.py", 1, "contradicted"),
            ("missing", "test*.py", 2, "unavailable"),
        )
        for directory, pattern, exit_code, decision in cases:
            with self.subTest(directory=directory, pattern=pattern):
                result = self.run_proof("gns-004", "unittest", directory, pattern, cwd=fixture)
                self.assertEqual(result.returncode, exit_code, result.stderr)
                self.assertEqual(result.stdout.strip(), decision)

    def test_predictions_about_literal_parser_inputs(self):
        cases = (
            ("[1,]", "rejected", 0, "supported"),
            ("[1,]", "accepted", 1, "contradicted"),
            ("[1]", "accepted", 0, "supported"),
            ("", "rejected", 0, "supported"),
            ("9" * 5000, "rejected", 0, "supported"),
            ('"line\r\nbreak"', "rejected", 0, "supported"),
        )
        for text, prediction, code, verdict in cases:
            with self.subTest(text=text, prediction=prediction):
                result = self.run_proof("gns-004", "json-parse", text, prediction)
                self.assertEqual((result.returncode, result.stdout.strip()), (code, verdict), result.stderr)

    def test_poker_call_amount_checks_the_observed_wager(self):
        cases = (
            ("58", "16", "42", 0, "supported"),
            ("58", "16", "41", 1, "contradicted"),
            ("7.5", "2.25", "5.25", 0, "supported"),
            ("2.50", "2.5", "0", 0, "supported"),
            ("5", "6", "0", 2, "unavailable"),
        )
        for wager, committed, expected, code, verdict in cases:
            with self.subTest(wager=wager, committed=committed, expected=expected):
                result = self.run_proof("gns-004", "poker-to-call", wager, committed, expected)
                self.assertEqual((result.returncode, result.stdout.strip()), (code, verdict), result.stderr)

    def test_poker_call_amount_rejects_malformed_observations(self):
        for wager in ("-2", "3.001", "nan", "1e2", '{"action":"call"}'):
            with self.subTest(wager=wager):
                result = self.run_proof("gns-004", "poker-to-call", wager, "0", "0")
                self.assertEqual((result.returncode, result.stdout), (2, ""))
                self.assertIn("Usage:", result.stderr)

    def test_parser_version_is_matched_against_the_runner(self):
        args = ("gns-004", "json-parse", "[1,]", "rejected")
        observed = self.run_proof(*args)
        version = observed.stderr.strip()
        self.assertIn("json.loads", version)
        for pin, code, verdict in ((version, 0, "supported"), ("another version", 2, "undecided")):
            with self.subTest(pin=pin):
                result = self.run_proof(*args, pin)
                self.assertEqual((result.returncode, result.stdout.strip()), (code, verdict), result.stderr)

    def test_failed_or_incomplete_parser_observer_cannot_support_a_prediction(self):
        cases = (
            ("echo observer-failed >&2; exit 2", "observer-failed"),
            ("echo version-only", "version and outcome"),
            ("printf 'version\nunknown\n'", "unknown outcome"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            observer = Path(temporary) / "python3"
            for command, detail in cases:
                with self.subTest(command=command):
                    observer.write_text("#!/bin/sh\n" + command + "\n")
                    observer.chmod(0o755)
                    result = self.run_proof(
                        "gns-004", "json-parse", "[1,]", "rejected",
                        PATH=temporary + os.pathsep + os.environ["PATH"],
                    )
                    self.assertEqual((result.returncode, result.stdout.strip()), (2, "unavailable"))
                    self.assertIn(detail, result.stderr)

    def test_one_committed_observation_checks_two_predictions(self):
        def git(*args):
            return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()

        def check(proof, path, expected, code, verdict, revision=None):
            result = self.run_proof(proof, "git-blob", revision or commit, path, *expected, cwd=repo)
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
