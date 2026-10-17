"""Declare executable checks using the pinned upstream EvalPlus evaluator."""

import json
from collections.abc import Mapping
from pathlib import Path

from kernel import Artifact, Content, Criterion, Verifier


def checks(*, record: str, manifest: Mapping[str, object]) -> Criterion.Value:
    return Criterion.Code(
        verifier=Verifier.create(
            inputs=("solution.py",),
            files=[
                Artifact.create(
                    path="verifier.py",
                    content=Content.Inline(
                        text=Path(__file__).with_name("evalplus_verifier.py").read_text()
                    ),
                )
            ],
            tools=[],
            command=("python3", "-I", "verifier.py", "evalplus"),
            stdin=json.dumps({"manifest": dict(manifest), "record": record}),
            timeout_seconds=180,
        )
    )
