"""Exercise generated types and real kernel policy through an in-process bridge."""

from collections.abc import Callable
from typing import cast

import pytest

import kernel as kernel_types
from kernel import (
    Answer,
    Case,
    Code,
    Experiment,
    Failed,
    Inline,
    Instruction,
    InvalidArgument,
    Outcome,
    Passed,
    Plain,
    Reference,
    Response,
    Rubric,
    String,
    Structured,
    Task,
    Unchecked,
    Verification,
)
from kernel._bridge import native as native_kernel
from kernel._operations import case as case_ops
from kernel._operations import experiment as experiment_ops
from kernel._operations import fixture as fixture_ops
from kernel._operations import grader as grader_ops
from kernel._operations import projection as projection_ops
from kernel._operations import response as response_ops
from kernel._operations import verifier as verifier_ops


def _answer() -> tuple[Task, Response]:
    expected = response_ops.of_fields([("choice", String("B"))])
    fixture = fixture_ops.of_files([("context.txt", "Public context")])
    reference = Reference(edits=fixture_ops.empty, completion=Structured(expected))
    criterion = Answer(Rubric(expected=expected, text_rule=None))
    instruction = Instruction(skill="reasoning", prompt="Choose B")
    case = case_ops.make(
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
    assert isinstance(case, Task)
    public = projection_ops.case(case)
    assert isinstance(public, Case)
    assert (public.id, hasattr(public, "reference"), projection_ops.verifier(case)) == (
        case.id,
        False,
        None,
    )
    assert (
        [(name, text[0]) for name, text in public.files],
        projection_ops.reference(case).completion[0][0][0],
    ) == ([("context.txt", "Public context")], "choice")


def check_answer_grading() -> None:
    assert experiment_ops.resolve(epochs=1).epochs == 1
    case, expected = _answer()
    outcome = Outcome(changed_files=[], verification=Unchecked())
    scores = grader_ops.grade(case, response=expected, outcome=outcome)
    assert dict(scores) == {"correctness": True, "scope": True}
    assert not dict(grader_ops.grade(case, response=None, outcome=outcome))["correctness"]


@pytest.mark.parametrize(("status", "correctness"), [(Passed(), True), (Failed(), False)])
def check_code(status: Verification, *, correctness: bool) -> None:
    checks = verifier_ops.make(
        inputs=["solution.py"],
        files=[("verify.py", Inline("private check"))],
        tools=[],
        command=["python3", "verify.py"],
        stdin="private input",
        timeout_seconds=5,
    )
    case = case_ops.make(
        id="native-code",
        fixture=fixture_ops.of_files([("solution.py", "pass")]),
        instruction=Instruction(skill="reasoning", prompt="Fix solution.py"),
        criterion=Code(checks),
        allowed_files=["solution.py"],
        reference=Reference(
            edits=fixture_ops.of_files([("solution.py", "fixed")]), completion=Plain("")
        ),
    )
    projected = projection_ops.verifier(case)
    assert projected is not None
    public_files = [name for name, _ in projection_ops.case(case).files]
    outcome = Outcome(changed_files=["workspace/solution.py"], verification=status)
    assert dict(grader_ops.grade(case, response=None, outcome=outcome)) == {
        "correctness": correctness,
        "scope": True,
    }
    outside_scope = Outcome(changed_files=["workspace/other.py"], verification=Passed())
    assert (
        projected.stdin,
        public_files,
        dict(grader_ops.grade(case, response=None, outcome=outside_scope))["scope"],
    ) == ("private input", ["solution.py"], False)


def check_rejections() -> None:
    with pytest.raises(InvalidArgument):
        fixture_ops.of_files([("duplicate.txt", "one"), ("duplicate.txt", "two")])
    with pytest.raises(TypeError):
        cast(Callable[..., Experiment], experiment_ops.resolve)(epochs="wrong type")


@pytest.mark.parametrize(
    ("public_name", "native_name"),
    [("Case", "case"), ("Task", "task"), ("Rubric", "answer"), ("Answer", "Answer")],
)
def explicit_types_preserve_native_identity(public_name: str, *, native_name: str) -> None:
    assert getattr(kernel_types, public_name) is getattr(native_kernel, native_name)


def public_kernel_exports_only_capitalized_types_and_constructors() -> None:
    assert all(
        name[0].isupper() and isinstance(getattr(kernel_types, name), type)
        for name in vars(kernel_types)["__all__"]
    )
    assert not {"Ast", "Grader", "Projection", "sources"} & vars(kernel_types).keys()
