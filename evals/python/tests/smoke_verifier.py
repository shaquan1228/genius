"""The standalone smoke checker reports candidate failures and owns its child."""

import io
import json
import os
import runpy
import signal
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path
from unittest.mock import patch

import pytest

from evals.python.integrations.smoke import verifier

CHECKS = "import runpy\nassert runpy.run_path('receipt.py')['total']([(3, 4)]) == 12\n"
SOLUTION = "def total(items): return sum(price * quantity for price, quantity in items)\n"


@pytest.mark.parametrize(
    ("source", "status"),
    [
        (SOLUTION, "passed"),
        ("def total(items): return 0\n", "failed"),
        ("def total(:", "invalid_submission"),
        ('raise RuntimeError("candidate failed")\n', "failed"),
        ("raise SystemExit(0)\n", "failed"),
        ("import os\nos._exit(0)\n", "failed"),
        ('print("debug", end="")\n' + SOLUTION, "passed"),
        ("import sys\nsys.stdout.buffer.write(b'\\xff\\n')\n" + SOLUTION, "passed"),
    ],
)
def private_checker_classifies_candidate_behavior_test(
    source: str, *, status: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("receipt.py").write_text(source)
    assert verifier.verify(("receipt.py",), checks=CHECKS)["status"] == status


def child_does_not_receive_outer_completion_marker_test(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GENIUS_VERIFIER_MARKER", "outer-private-marker")
    result = verifier.run("import os\nprint('GENIUS_VERIFIER_MARKER' in os.environ)")
    assert (result.returncode, result.stdout) == (0, "False\n")


@pytest.mark.parametrize("failure", [None, RuntimeError("checker failed")])
def main_emits_process_evidence_test(
    failure: Exception | None,
    *,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("GENIUS_VERIFIER_MARKER", "outer")
    monkeypatch.setattr(sys, "argv", ["verifier.py", "receipt.py"])
    monkeypatch.setattr(sys, "stdin", io.StringIO(CHECKS))
    with patch.object(
        verifier, "verify", return_value={"status": "passed", "detail": "done"}, side_effect=failure
    ):
        verifier.main()
    assert json.loads(capsys.readouterr().out) == {
        "marker": "outer",
        "status": "harness_error" if failure else "passed",
        "detail": str(failure) if failure else "done",
    }


def entrypoint_rejects_missing_sources_test(
    monkeypatch: pytest.MonkeyPatch, *, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("GENIUS_VERIFIER_MARKER", "outer")
    monkeypatch.setattr(sys, "argv", ["verifier.py"])
    runpy.run_path(verifier.__file__, run_name="__main__")
    assert json.loads(capsys.readouterr().out) == {
        "marker": "outer",
        "status": "harness_error",
        "detail": "Expected candidate source paths",
    }


def wait_for_pid(path: Path) -> int:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if path.exists():
            return int(path.read_text())
        time.sleep(0.01)
    raise TimeoutError("candidate did not start")


def candidate_startup_wait_is_bounded_test(tmp_path: Path) -> None:
    with (
        patch.object(time, "monotonic", side_effect=[0, 6]),
        pytest.raises(TimeoutError, match="candidate did not start"),
    ):
        wait_for_pid(tmp_path / "missing.pid")


def terminating_checker_reaps_candidate_child_test(tmp_path: Path) -> None:
    candidate = tmp_path / "receipt.py"
    candidate.write_text(SOLUTION)
    pidfile = tmp_path / "candidate.pid"
    checks = (
        "import os, time\nfrom pathlib import Path\ntime.sleep(0.2)\n"
        f"Path({str(pidfile) + '.tmp'!r}).write_text(str(os.getpid()))\n"
        f"os.replace({str(pidfile) + '.tmp'!r}, {str(pidfile)!r})\n"
        "time.sleep(30)\n"
    )
    with subprocess.Popen(
        [sys.executable, "-I", verifier.__file__, str(candidate)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "GENIUS_VERIFIER_MARKER": "outer"},
    ) as process:
        with pytest.raises(subprocess.TimeoutExpired):
            process.communicate(input=checks, timeout=0.1)
        child_pid = wait_for_pid(pidfile)
        try:
            process.terminate()
            process.wait(timeout=5)
            with pytest.raises(ProcessLookupError):
                os.kill(child_pid, 0)
        finally:
            process.kill()
            with suppress(ProcessLookupError):
                os.kill(child_pid, signal.SIGKILL)
