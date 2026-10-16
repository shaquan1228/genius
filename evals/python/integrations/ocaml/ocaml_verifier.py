"""Standalone trusted OCaml verifier; only standard-library imports are required."""

import json
import os
import secrets
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import TypedDict


class WireResult(TypedDict):
    """JSON process envelope; decoded to canonical verification by the host."""

    status: str
    detail: str
    metadata: dict[str, object]


def wire_result(
    *, status: str, detail: str = "", metadata: dict[str, object] | None = None
) -> WireResult:
    return {"status": status, "detail": detail, "metadata": metadata or {}}


@dataclass(frozen=True, kw_only=True)
class Invocation:
    sources: tuple[str, ...] = ()


@dataclass(frozen=True, kw_only=True)
class Compilation:
    result: subprocess.CompletedProcess[str]
    marker: str


def compile_ocaml(invocation: Invocation) -> WireResult:
    if shutil.which("ocamlc") is None:
        return wire_result(status="harness_error", detail="OCaml compiler is unavailable")
    marker = secrets.token_hex(24)
    program = sys.stdin.read() + '\nlet () = print_endline "\\n' + marker + '"\n'
    result = subprocess.run(
        ["sh", "check.sh", "--stdin", *invocation.sources],
        input=program,
        capture_output=True,
        text=True,
        check=False,
    )
    return wire_result(
        status=classify(compilation=Compilation(result=result, marker=marker)),
        detail=(result.stdout + result.stderr)[-2000:],
    )


def classify(compilation: Compilation) -> str:
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
        result = wire_result(status="harness_error", detail=str(error))
    print(json.dumps({"marker": os.environ["GENIUS_VERIFIER_MARKER"], **result}), flush=True)


if __name__ == "__main__":
    main()
