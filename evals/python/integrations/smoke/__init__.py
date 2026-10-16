"""Declare executable checks for private Python assertions."""

from pathlib import Path

from kernel import Code, Criterion, Inline, Verifier


def checks(*, inputs: tuple[str, ...], program: str) -> Criterion:
    return Code(
        Verifier(
            inputs=inputs,
            files=(
                (
                    "verifier.py",
                    Inline(Path(__file__).with_name("verifier.py").read_text()),
                ),
            ),
            tools=(),
            command=("python3", "-I", "verifier.py", *inputs),
            stdin=program,
            timeout_seconds=30,
        )
    )
