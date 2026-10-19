"""Executable CLI contracts; all writes and SDK calls are isolated or stubbed."""

import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASH = os.environ.get("BASH_BIN", "bash")
SCRIPTS = (
    "bin/setup",
    "bin/teardown",
    "evals/bin/kernel_setup.sh",
    "evals/bin/hf_host.sh",
    "evals/bin/hf_bootstrap.sh",
)


class BinContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="genius cli ")
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name).resolve()
        self.repo = self.work / "repo with spaces\\literal"
        for folder in ("bin", "evals/bin"):
            shutil.copytree(
                ROOT / folder,
                self.repo / folder,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
        (self.repo / "docs").mkdir()
        (self.repo / "docs/identity.md").write_text("An identity.\n")
        self.home = self.work / "home"
        self.home.mkdir()
        self.claude = self.home / ".claude/CLAUDE.md"
        self.cursor = self.repo / ".cursor/rules/genius.mdc"
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
            "KERNEL_JOBS",
            "KERNEL_PYTHON",
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

    def seed(self, content):
        self.claude.parent.mkdir(parents=True, exist_ok=True)
        self.claude.write_text(content)

    def test_help_takes_precedence_and_has_no_side_effects(self):
        self.environment.pop("HOME")
        for script in SCRIPTS:
            with self.subTest(script=script):
                result = self.run_script(script, "--invalid", "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Usage:", result.stdout)
                self.assertEqual(result.stderr, "")
        self.assertFalse(self.cursor.exists())
        self.assertFalse(self.claude.exists())

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

    def test_identity_round_trip_is_idempotent_and_preserves_mode(self):
        self.seed("before\n# BEGIN GENIUS\nold\n# END GENIUS\nafter\n")
        self.claude.chmod(0o640)
        result = self.run_script("bin/setup")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        expected = f"before\n# BEGIN GENIUS\n@{self.repo}/docs/identity.md\n# END GENIUS\nafter\n"
        self.assertEqual(self.claude.read_text(), expected)
        self.assertEqual(stat.S_IMODE(self.claude.stat().st_mode), 0o640)
        first_cursor = self.cursor.read_bytes()
        result = self.run_script("bin/setup", "--quiet")
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
        self.assertEqual(self.claude.read_text(), expected)
        self.assertEqual(self.cursor.read_bytes(), first_cursor)
        preview = self.run_script("bin/teardown")
        self.assertEqual(preview.returncode, 0)
        self.assertIn("Would remove", preview.stdout)
        self.assertEqual(self.claude.read_text(), expected)
        self.assertTrue(self.cursor.exists())
        result = self.run_script("bin/teardown", "--confirm")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.claude.read_text(), "before\nafter\n")
        self.assertFalse(self.cursor.exists())

    def test_dry_run_never_creates_identity_files(self):
        for script, flags in (
            ("bin/setup", ("--dry-run",)),
            ("bin/teardown", ("--yes", "--dry-run")),
        ):
            result = self.run_script(script, *flags)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.claude.parent.exists())
        self.assertFalse(self.cursor.parent.exists())

    def test_malformed_markers_preserve_all_content(self):
        contents = (
            "before\n# BEGIN GENIUS\nafter\n",
            "# END GENIUS\nafter\n",
            "# BEGIN GENIUS\n# BEGIN GENIUS\n# END GENIUS\n",
        )
        for content in contents:
            for script, flags in (("bin/setup", ()), ("bin/teardown", ("--yes",))):
                with self.subTest(content=content, script=script):
                    self.seed(content)
                    result = self.run_script(script, *flags)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(self.claude.read_text(), content)
                    self.assertEqual(list(self.claude.parent.glob(".genius.*")), [])
                    self.assertFalse(self.cursor.exists())

    def test_similar_marker_prefixes_are_not_deleted(self):
        self.seed("# BEGIN GENIUS manual note\nkeep this\n")
        result = self.run_script("bin/teardown", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.claude.read_text(), "# BEGIN GENIUS manual note\nkeep this\n"
        )

    def test_removal_preserves_unmanaged_file_without_final_newline(self):
        self.seed("unrelated text without a newline")
        result = self.run_script("bin/teardown", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.claude.read_bytes(), b"unrelated text without a newline")

    def test_failed_mode_copy_preserves_file_in_guarded_update(self):
        self.seed("keep me\n")
        self.fake("cp", "exit 7\n")
        result = self.run_script("bin/setup")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.claude.read_text(), "keep me\n")
        self.assertEqual(list(self.claude.parent.glob(".genius.*")), [])
        self.assertFalse(self.cursor.exists())

    def test_symbolic_links_are_preserved(self):
        target = self.work / "real instructions"
        target.write_text("keep me\n")
        self.claude.parent.mkdir()
        self.claude.symlink_to(target)
        result = self.run_script("bin/setup")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.claude.is_symlink())
        self.assertEqual(target.read_text(), "keep me\n")
        self.assertFalse(self.cursor.exists())

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
                str(self.repo / "evals/bin/lib/common.bash"),
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
            "evals/bin/hf_host.sh",
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
            "evals/bin/hf_host.sh",
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
            "evals/bin/hf_host.sh",
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

    def test_kernel_rejects_invalid_jobs_before_touching_opam(self):
        calls = self.work / "calls"
        self.fake("opam", 'touch "$CALLS"\n')
        result = self.run_script(
            "evals/bin/kernel_setup.sh", env={"KERNEL_JOBS": "0", "CALLS": str(calls)}
        )
        self.assertEqual(result.returncode, 2)
        self.assertFalse(calls.exists())

    def test_bridge_cache_lock_and_failed_clone(self):
        root = self.work / "opam root"
        root.mkdir()
        (root / "config").touch()
        interpreter = self.work / "python stub"
        interpreter.write_text(
            '#!/usr/bin/env bash\ncase "$2" in\n'
            '  *sys.executable*) printf "%s\\n" "$0" ;;\n'
            '  *hashlib*) printf "patchhash\\n" ;;\nesac\n'
        )
        interpreter.chmod(0o755)
        self.fake(
            "opam",
            'case "$*" in\n'
            '  "var --global root") printf "%s\\n" "$OPAM_TEST_ROOT" ;;\n'
            '  "switch list --short") printf "genius-kernel-414\\n" ;;\n'
            '  *ocaml:version) printf "4.14.2\\n" ;;\n'
            "  *) exit 99 ;;\nesac\n",
        )
        calls = self.work / "git calls"
        self.fake("git", 'touch "$CALLS"; exit 7\n')
        lock = (
            root
            / "genius-kernel-bridge-4bd7956a69f1ee91201f440f3a87fa976dedfc3a-patchhash.lock"
        )
        lock.mkdir()
        environment = {
            "OPAM_TEST_ROOT": str(root),
            "KERNEL_PYTHON": str(interpreter),
            "CALLS": str(calls),
        }
        result = self.run_script("evals/bin/kernel_setup.sh", env=environment)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("cache is busy", result.stderr)
        self.assertTrue(lock.is_dir())
        self.assertFalse(calls.exists())
        lock.rmdir()
        result = self.run_script("evals/bin/kernel_setup.sh", env=environment)
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertTrue(calls.exists())
        self.assertEqual(sorted(path.name for path in root.iterdir()), ["config"])

    def test_bootstrap_rejects_missing_option_value(self):
        for option in ("--source-dir", "--work-dir", "--results-dir"):
            result = self.run_script("evals/bin/hf_bootstrap.sh", option)
            self.assertEqual(result.returncode, 2)
            self.assertIn("requires a directory", result.stderr)

    def test_bootstrap_preserves_runner_exit_and_arguments(self):
        source = self.work / "source snapshot"
        (source / "evals/bin").mkdir(parents=True)
        (source / "evals/pyproject.toml").touch()
        (source / "evals/bin/kernel_setup.sh").write_text(
            '#!/usr/bin/env bash\nprintf "native\\n" >&2\n'
        )
        log = self.work / "runner.json"
        for tool in ("git", "make", "cc", "pkg-config", "rsync"):
            self.fake(tool, "exit 0\n")
        self.fake("uv", "exit 0\n")
        self.fake(
            "opam",
            'exec "$PYTHON_FOR_TEST" -c \'import json, os, sys; json.dump({"args":sys.argv[1:], "log":os.environ["EVAL_LOG_DIR"]},open(os.environ["RUNNER_LOG"],"w")); sys.exit(7)\' "$@"\n',
        )
        work = self.work / "working copy"
        results = self.work / "result files"
        result = self.run_script(
            "evals/bin/hf_bootstrap.sh",
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
                str(self.repo / "evals/bin/lib/common.bash"),
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
        script = self.repo / "evals/bin/check_install.py"
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
