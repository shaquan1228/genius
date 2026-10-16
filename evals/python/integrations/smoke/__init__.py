"""Declare executable checks for private Python assertions."""

from pathlib import Path

from evals.python import query


def checks(*, inputs: tuple[str, ...], program: str) -> query.CodeCriterion:
    return query.CodeCriterion(
        verifier=query.VerifierDefinition(
            inputs=inputs,
            files={
                "verifier.py": query.Inline(
                    text=Path(__file__).with_name("verifier.py").read_text()
                )
            },
            tools={},
            command=("python3", "-I", "verifier.py", *inputs),
            stdin=program,
            timeout_seconds=30,
        )
    )
