"""Executable CLI contracts; all writes and SDK calls are isolated or stubbed."""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASH = os.environ.get("BASH_BIN", "bash")
SCRIPTS = (
    "evals/bin/huggingface-run",
    "evals/scripts/huggingface-bootstrap.sh",
)


class BinContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="genius cli ")
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name).resolve()
        self.repo = self.work / "repo with spaces\\literal"
        for folder in ("evals/bin", "evals/lib", "evals/scripts"):
            shutil.copytree(
                ROOT / folder,
                self.repo / folder,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
        self.home = self.work / "home"
        self.home.mkdir()
        self.environment = os.environ | {
            "HOME": str(self.home),
            "CDPATH": str(self.work),
        }
        for name in (
            "HF_NAMESPACE",
            "EVAL_MODEL",
            "EVAL_MODEL_COST",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "INSTALL_DATASET",
        ):
            self.environment.pop(name, None)

    def run_script(self, script, *arguments, env=None):
        return subprocess.run(
            [BASH, str(self.repo / script), *arguments],
            cwd=self.work,
            env=self.environment | (env or {}),
            capture_output=True,
            text=True,
        )

    def fake(self, name, body):
        directory = self.work / "commands"
        directory.mkdir(exist_ok=True)
        executable = directory / name
        executable.write_text("#!/usr/bin/env bash\nset -eu\n" + body)
        executable.chmod(0o755)
        self.environment["PATH"] = str(directory) + os.pathsep + os.environ["PATH"]
        return executable

    def test_public_commands_are_separate_from_non_executable_helpers(self):
        self.assertEqual(
            [path.name for path in (self.repo / "evals/bin").iterdir()],
            ["huggingface-run"],
        )
        helper = self.repo / "evals/lib/shell.sh"
        self.assertFalse(helper.stat().st_mode & 0o111)
        result = subprocess.run(
            [str(self.repo / "evals/bin/huggingface-run"), "--help"],
            cwd=self.work,
            env=self.environment,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("huggingface-run", result.stdout)

    def test_help_takes_precedence_and_has_no_side_effects(self):
        self.environment.pop("HOME")
        for script in SCRIPTS:
            with self.subTest(script=script):
                result = self.run_script(script, "--invalid", "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Usage:", result.stdout)
                self.assertEqual(result.stderr, "")
        self.assertEqual(list(self.home.iterdir()), [])

    def test_bad_arguments_have_usage_status_and_stderr(self):
        for script in SCRIPTS:
            with self.subTest(script=script):
                result = self.run_script(script, "--invalid")
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIn("--help", result.stderr)

    def test_end_of_options_rejects_operands(self):
        for script in SCRIPTS:
            with self.subTest(script=script):
                result = self.run_script(script, "--", "operand")
                self.assertEqual(result.returncode, 2)

    def test_failed_producer_cannot_commit_partial_output(self):
        target = self.work / "file"
        target.write_text("original\n")
        code = 'set -euo pipefail; source "$1"; cli_init; file_update "$2" bash -c "printf partial; exit 7"'
        result = subprocess.run(
            [
                BASH,
                "-c",
                code,
                "test",
                str(self.repo / "evals/lib/shell.sh"),
                str(target),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 7)
        self.assertEqual(target.read_text(), "original\n")
        self.assertEqual(list(self.work.glob(".genius.*")), [])

    def test_host_dry_run_needs_no_auth_or_sdk(self):
        calls = self.work / "calls"
        self.fake("uvx", 'touch "$CALLS"; exit 99\n')
        result = self.run_script(
            "evals/bin/huggingface-run",
            "--dry-run",
            env={
                "HF_NAMESPACE": "team",
                "EVAL_MODEL": "openai/model",
                "CALLS": str(calls),
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Would launch", result.stdout)
        self.assertFalse(calls.exists())

    def test_host_missing_auth_is_reported_before_sdk_calls(self):
        calls = self.work / "calls"
        self.fake("uvx", 'touch "$CALLS"\n')
        result = self.run_script(
            "evals/bin/huggingface-run",
            env={
                "HF_NAMESPACE": "team",
                "EVAL_MODEL": "openai/model",
                "CALLS": str(calls),
            },
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("OPENAI_API_KEY", result.stderr)
        self.assertFalse(calls.exists())

    def test_failed_archive_never_uploads_and_cleans_workspace(self):
        calls = self.work / "calls"
        temporary = self.work / "temp"
        temporary.mkdir()
        self.fake("uvx", 'touch "$CALLS"\n')
        self.fake("git", "exit 7\n")
        result = self.run_script(
            "evals/bin/huggingface-run",
            env={
                "HF_NAMESPACE": "team",
                "EVAL_MODEL": "openai/model",
                "OPENAI_API_KEY": "secret",
                "CALLS": str(calls),
                "TMPDIR": str(temporary),
            },
        )
        self.assertEqual(result.returncode, 7)
        self.assertFalse(calls.exists())
        self.assertEqual(list(temporary.iterdir()), [])
        self.assertNotIn("secret", result.stdout + result.stderr)

    def test_bootstrap_rejects_missing_option_value(self):
        for option in ("--source-dir", "--work-dir", "--results-dir"):
            result = self.run_script("evals/scripts/huggingface-bootstrap.sh", option)
            self.assertEqual(result.returncode, 2)
            self.assertIn("requires a directory", result.stderr)

    def test_bootstrap_preserves_runner_exit_and_arguments(self):
        source = self.work / "source snapshot"
        (source / "evals/scripts").mkdir(parents=True)
        (source / "evals/pyproject.toml").touch()
        log = self.work / "runner.json"
        for tool in ("git", "cc"):
            self.fake(tool, "exit 0\n")
        self.fake(
            "uv",
            '[ "$1" = run ] || exit 0\n'
            'exec "$PYTHON_FOR_TEST" -c \'import json, os, sys; json.dump({"args":sys.argv[1:], "log":os.environ["EVAL_LOG_DIR"]},open(os.environ["RUNNER_LOG"],"w")); sys.exit(7)\' "$@"\n',
        )
        work = self.work / "working copy"
        results = self.work / "result files"
        result = self.run_script(
            "evals/scripts/huggingface-bootstrap.sh",
            "--source-dir",
            str(source),
            "--work-dir",
            str(work),
            "--results-dir",
            str(results),
            env={
                "PYTHON_FOR_TEST": sys.executable,
                "RUNNER_LOG": str(log),
                "EVAL_RUNNER_MODULE": "custom.runner",
            },
        )
        self.assertEqual(result.returncode, 7, result.stderr)
        recorded = json.loads(log.read_text())
        self.assertEqual(recorded["args"][-2:], ["-m", "custom.runner"])
        self.assertEqual(Path(recorded["log"]), (results / "live").resolve())

    def test_signal_cleans_temporary_files(self):
        ready = self.work / "ready"
        code = 'set -euo pipefail; source "$1"; cli_init; cli_temp_dir "$2"; touch "$3"; sleep 30'
        process = subprocess.Popen(
            [
                BASH,
                "-c",
                code,
                "test",
                str(self.repo / "evals/lib/shell.sh"),
                str(self.work),
                str(ready),
            ],
            start_new_session=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            deadline = time.monotonic() + 5
            while not ready.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(ready.exists())
            os.killpg(process.pid, signal.SIGTERM)
            _, error = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 143, error)
            self.assertEqual(list(self.work.glob("genius.*")), [])
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()

    def test_python_entry_point_has_help_and_rejects_bad_options(self):
        script = self.repo / "evals/scripts/check_installation.py"
        help_result = subprocess.run(
            [sys.executable, str(script), "--help"], capture_output=True, text=True
        )
        self.assertEqual(help_result.returncode, 0)
        result = subprocess.run(
            [sys.executable, str(script), "--bad"], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
