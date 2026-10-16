"""Standalone trusted OCaml verifier; only standard-library imports are required."""

import json
import os
import secrets
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from typing import Literal

Status = Literal["passed", "failed", "invalid_submission", "timed_out", "harness_error"]


@dataclass(frozen=True, kw_only=True)
class Result:
    status: Status
    detail: str = ""
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class Invocation:
    sources: tuple[str, ...] = ()


@dataclass(frozen=True, kw_only=True)
class Compilation:
    result: subprocess.CompletedProcess[str]
    marker: str


def compile_ocaml(invocation: Invocation) -> Result:
    if shutil.which("ocamlc") is None:
        return Result(status="harness_error", detail="OCaml compiler is unavailable")
    marker = secrets.token_hex(24)
    program = sys.stdin.read() + '\nlet () = print_endline "\\n' + marker + '"\n'
    result = subprocess.run(
        ["sh", "check.sh", "--stdin", *invocation.sources],
        input=program,
        capture_output=True,
        text=True,
        check=False,
    )
    return Result(
        status=classify(compilation=Compilation(result=result, marker=marker)),
        detail=(result.stdout + result.stderr)[-2000:],
    )


def classify(compilation: Compilation) -> Status:
    result, marker = compilation.result, compilation.marker
    match result.returncode:
        case 65:
            return "invalid_submission"
        case 127:
            return "harness_error"
        case 0:
            return "passed" if marker in result.stdout.splitlines() else "failed"
        case _:
            return "failed"


def main() -> None:
    try:
        match sys.argv[1:]:
            case ["ocaml", *sources]:
                invocation = Invocation(sources=tuple(sources))
            case _:
                raise ValueError("Expected verifier mode: ocaml <sources...>")
        result = compile_ocaml(invocation=invocation)
    except Exception as error:
        result = Result(status="harness_error", detail=str(error))
    print(
        json.dumps({"marker": os.environ["GENIUS_VERIFIER_MARKER"], **asdict(result)}), flush=True
    )


if __name__ == "__main__":
    main()
