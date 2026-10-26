"""Declare executable checks using the pinned upstream EvalPlus evaluator."""

import json
from collections.abc import Mapping
from pathlib import Path

from kernel import Criterion, SourceFile, Verifier


def checks(*, record: str, manifest: Mapping[str, object]) -> Criterion:
    return Criterion.code(
        verifier=Verifier(
            inputs=("solution.py",),
            files=[
                SourceFile(
                    path="verifier.py", contents=Path(__file__).with_name("verifier.py").read_text()
                )
            ],
            tools=[],
            command=("python3", "-I", "verifier.py", "evalplus"),
            stdin=json.dumps({"manifest": dict(manifest), "record": record}),
            timeout_seconds=180,
        )
    )
