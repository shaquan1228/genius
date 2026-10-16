"""Exercise generated types and real kernel policy through an in-process bridge."""

from collections.abc import Callable
from typing import cast

import pytest

from kernel import (
    Ast,
    Case,
    Criterion,
    Experiment,
    Fixture,
    Grader,
    InvalidArgument,
    Projection,
    Response,
    Verifier,
)


def check_answer() -> None:
    assert Experiment.resolve(epochs=1).epochs == 1
    expected = Response.of_fields([("choice", Ast.String("B"))])
    fixture = Fixture.of_files([("context.txt", "Public context")])
    reference = Ast.reference(edits=Fixture.empty, completion=Ast.Structured(expected))
    criterion = Criterion.answer(expected=expected)
    instruction = Ast.instruction(skill="reasoning", prompt="Choose B")
    case = Case.make(
        id="native-answer",
        fixture=fixture,
        instruction=instruction,
        criterion=criterion,
        allowed_files=[],
        reference=reference,
    )
    assert isinstance(case, Ast.case)
    public = Projection.case(case)
    assert isinstance(public, Ast.public_case)
    assert public.id == case.id
    assert [(name, text[0]) for name, text in public.files] == [("context.txt", "Public context")]
    assert not hasattr(public, "reference")
    assert Projection.verifier(case) is None
    assert Projection.reference(case).completion[0][0][0] == "choice"
    outcome = Ast.outcome(changed_files=[], verification=Ast.Unchecked())
    scores = Grader.grade(case, response=expected, outcome=outcome)
    assert dict(scores) == {"correctness": True, "scope": True}
    assert not dict(Grader.grade(case, response=None, outcome=outcome))["correctness"]


def check_code() -> None:
    checks = Verifier.make(
        inputs=["solution.py"],
        files=[("verify.py", Ast.Inline("private check"))],
        tools=[],
        command=["python3", "verify.py"],
        stdin="private input",
        timeout_seconds=5,
    )
    case = Case.make(
        id="native-code",
        fixture=Fixture.of_files([("solution.py", "pass")]),
        instruction=Ast.instruction(skill="reasoning", prompt="Fix solution.py"),
        criterion=Ast.Code(checks),
        allowed_files=["solution.py"],
        reference=Ast.reference(
            edits=Fixture.of_files([("solution.py", "fixed")]), completion=Ast.Plain("")
        ),
    )
    projected = Projection.verifier(case)
    assert projected is not None
    assert projected.stdin == "private input"
    assert [name for name, _ in Projection.case(case).files] == ["solution.py"]
    for status, correctness in ((Ast.Passed(), True), (Ast.Failed(), False)):
        outcome = Ast.outcome(changed_files=["workspace/solution.py"], verification=status)
        assert dict(Grader.grade(case, response=None, outcome=outcome)) == {
            "correctness": correctness,
            "scope": True,
        }
    outside_scope = Ast.outcome(changed_files=["workspace/other.py"], verification=Ast.Passed())
    assert not dict(Grader.grade(case, response=None, outcome=outside_scope))["scope"]


def check_rejections() -> None:
    with pytest.raises(InvalidArgument):
        Fixture.of_files([("duplicate.txt", "one"), ("duplicate.txt", "two")])
    with pytest.raises(TypeError):
        cast(Callable[..., Ast.experiment], Experiment.resolve)(epochs="wrong type")
