"""Declare executable checks using the pinned upstream EvalPlus evaluator."""

import json
from collections.abc import Mapping
from pathlib import Path

from kernel import Content, Criterion, Verifier


def checks(*, record: str, manifest: Mapping[str, object]) -> Criterion.Value:
    return Criterion.Code(
        Verifier.create(
            inputs=("solution.py",),
            files=(
                (
                    "verifier.py",
                    Content.Inline(Path(__file__).with_name("evalplus_verifier.py").read_text()),
                ),
            ),
            tools=(),
            command=("python3", "-I", "verifier.py", "evalplus"),
            stdin=json.dumps({"manifest": dict(manifest), "record": record}),
            timeout_seconds=180,
        )
    )
