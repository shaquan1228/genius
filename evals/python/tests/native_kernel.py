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


def _answer() -> tuple[Ast.task, Ast.response]:
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
    return case, expected


def check_answer_projection() -> None:
    case, _ = _answer()
    assert isinstance(case, Ast.task)
    public = Projection.case(case)
    assert isinstance(public, Ast.case)
    assert (public.id, hasattr(public, "reference"), Projection.verifier(case)) == (
        case.id,
        False,
        None,
    )
    assert (
        [(name, text[0]) for name, text in public.files],
        Projection.reference(case).completion[0][0][0],
    ) == ([("context.txt", "Public context")], "choice")


def check_answer_grading() -> None:
    assert Experiment.resolve(epochs=1).epochs == 1
    case, expected = _answer()
    outcome = Ast.outcome(changed_files=[], verification=Ast.Unchecked())
    scores = Grader.grade(case, response=expected, outcome=outcome)
    assert dict(scores) == {"correctness": True, "scope": True}
    assert not dict(Grader.grade(case, response=None, outcome=outcome))["correctness"]


@pytest.mark.parametrize(("status", "correctness"), [(Ast.Passed(), True), (Ast.Failed(), False)])
def check_code(status: Ast.verification, *, correctness: bool) -> None:
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
    public_files = [name for name, _ in Projection.case(case).files]
    outcome = Ast.outcome(changed_files=["workspace/solution.py"], verification=status)
    assert dict(Grader.grade(case, response=None, outcome=outcome)) == {
        "correctness": correctness,
        "scope": True,
    }
    outside_scope = Ast.outcome(changed_files=["workspace/other.py"], verification=Ast.Passed())
    assert (
        projected.stdin,
        public_files,
        dict(Grader.grade(case, response=None, outcome=outside_scope))["scope"],
    ) == ("private input", ["solution.py"], False)


def check_rejections() -> None:
    with pytest.raises(InvalidArgument):
        Fixture.of_files([("duplicate.txt", "one"), ("duplicate.txt", "two")])
    with pytest.raises(TypeError):
        cast(Callable[..., Ast.experiment], Experiment.resolve)(epochs="wrong type")
