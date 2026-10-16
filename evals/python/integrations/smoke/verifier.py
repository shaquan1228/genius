"""Run private smoke assertions against candidate Python in a child process."""

import json
import os
import secrets
import signal
import subprocess
import sys
from contextlib import suppress
from pathlib import Path


def run(checks: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment.pop("GENIUS_VERIFIER_MARKER", None)
    with subprocess.Popen(
        [sys.executable, "-I", "-B", "-c", checks],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        start_new_session=True,
    ) as process:
        previous = signal.signal(signal.SIGTERM, lambda number, _frame: sys.exit(128 + number))
        try:
            stdout, stderr = process.communicate()
        finally:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            signal.signal(signal.SIGTERM, previous)
    return subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)


def verify(sources: tuple[str, ...], *, checks: str) -> dict[str, str]:
    try:
        for name in sources:
            compile(Path(name).read_bytes(), name, "exec")
    except SyntaxError as error:
        return {"status": "invalid_submission", "detail": str(error)}
    marker = secrets.token_hex(24)
    result = run(checks + "\nprint(" + repr("\n" + marker) + ")\n")
    return {
        "status": "passed"
        if result.returncode == 0 and marker in result.stdout.splitlines()
        else "failed",
        "detail": (result.stdout + result.stderr)[-2000:],
    }


def main() -> None:
    try:
        if len(sys.argv) == 1:
            raise ValueError("Expected candidate source paths")
        result = verify(tuple(sys.argv[1:]), checks=sys.stdin.read())
    except Exception as error:
        result = {"status": "harness_error", "detail": str(error)}
    print(json.dumps({"marker": os.environ["GENIUS_VERIFIER_MARKER"], **result}), flush=True)


if __name__ == "__main__":
    main()
