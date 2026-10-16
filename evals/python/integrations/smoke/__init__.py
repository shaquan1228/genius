"""Declare executable checks for private Python assertions."""

from pathlib import Path

from evals.python import query
from kernel import Ast


def checks(*, inputs: tuple[str, ...], program: str) -> Ast.criterion:
    return Ast.Code(
        Ast.verifier(
            inputs=inputs,
            files=(
                (
                    "verifier.py",
                    Ast.Inline(Path(__file__).with_name("verifier.py").read_text()),
                ),
            ),
            tools=(),
            command=("python3", "-I", "verifier.py", *inputs),
            stdin=program,
            timeout_seconds=30,
        )
    )
