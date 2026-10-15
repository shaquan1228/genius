import json
import os
import secrets
import shutil
import subprocess
import sys


def execute() -> tuple[str, str]:
    if shutil.which("ocamlc") is None:
        return "harness_error", "OCaml compiler is unavailable"
    marker = secrets.token_hex(24)
    program = sys.stdin.read() + '\nlet () = print_endline "\\n' + marker + '"\n'
    result = subprocess.run(
        ["sh", "check.sh", "--stdin", *sys.argv[1:]],
        input=program,
        capture_output=True,
        text=True,
        check=False,
    )
    return classify(result, marker=marker), (result.stdout + result.stderr)[-2000:]


def classify(result: subprocess.CompletedProcess[str], *, marker: str) -> str:
    if result.returncode == 65:
        return "invalid_submission"
    if result.returncode == 127:
        return "harness_error"
    if result.returncode != 0:
        return "failed"
    if marker in result.stdout.splitlines():
        return "passed"
    return "failed"


def main() -> None:
    try:
        status, detail = execute()
    except Exception as error:
        status, detail = "harness_error", str(error)
    print(
        json.dumps(
            {"marker": os.environ["GENIUS_VERIFIER_MARKER"], "status": status, "detail": detail}
        )
    )


if __name__ == "__main__":
    main()
