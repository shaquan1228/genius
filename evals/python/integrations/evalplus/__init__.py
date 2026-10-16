"""Declare executable checks using the pinned upstream EvalPlus evaluator."""

import json
from collections.abc import Mapping
from pathlib import Path

from evals.python import query
from kernel import Ast


def checks(*, record: str, manifest: Mapping[str, object]) -> Ast.criterion:
    return Ast.Code(
        Ast.verifier(
            inputs=("solution.py",),
            files=(
                (
                    "verifier.py",
                    Ast.Inline(Path(__file__).with_name("evalplus_verifier.py").read_text()),
                ),
            ),
            tools=(),
            command=("python3", "-I", "verifier.py", "evalplus"),
            stdin=json.dumps({"manifest": dict(manifest), "record": record}),
            timeout_seconds=180,
        )
    )
