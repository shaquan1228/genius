"""Declare executable checks for private Python assertions."""

from pathlib import Path

from kernel import Criterion, File, Verifier


def checks(*, inputs: tuple[str, ...], program: str) -> Criterion.Value:
    return Criterion.Code(
        verifier=Verifier(
            inputs=inputs,
            files=[
                File(
                    path="verifier.py", contents=Path(__file__).with_name("verifier.py").read_text()
                )
            ],
            tools=[],
            command=("python3", "-I", "verifier.py", *inputs),
            stdin=program,
            timeout_seconds=30,
        )
    )
