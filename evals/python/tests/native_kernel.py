"""Exercise generated types and real kernel policy through an in-process bridge."""

from collections.abc import Callable
from operator import itemgetter
from typing import cast

import pytest

import kernel as kernel_types
from evals.python.tests.declarations import _files
from kernel import (
    Artifact,
    Case,
    Completion,
    Content,
    Criterion,
    Experiment,
    File,
    Fixture,
    Instruction,
    Outcome,
    Reference,
    Response,
    ResponseField,
    ResponseValue,
    Rubric,
    Task,
    Verification,
    Verifier,
)
from kernel import (
    ValidationError as DomainValidationError,
)
from kernel._bridge import native as native_kernel
from kernel._operations import experiment as experiment_ops
from kernel._operations import grader as grader_ops
from kernel._operations import projection as projection_ops


def _answer() -> tuple[Task, Response]:
    expected = Response.create(
        fields=[ResponseField.create(name="choice", value=ResponseValue.String(value="B"))]
    )
    fixture = Fixture.create(files=[File.create(path="context.txt", contents="Public context")])
    reference = Reference(
        edits=Fixture.create(files=[]), completion=Completion.Structured(response=expected)
    )
    criterion = Criterion.Answer(rubric=Rubric.create(expected=expected, text_rule=None))
    instruction = Instruction.create(skill="reasoning", prompt="Choose B")
    case = Task.create(
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
    public = projection_ops.case(task=case)
    assert isinstance(public, Case)
    assert (public.id, hasattr(public, "reference"), projection_ops.verifier(task=case)) == (
        case.id,
        False,
        None,
    )
    assert (
        list(_files(public.files).items()),
        cast(Completion.Structured, projection_ops.reference(task=case).completion)
        .response.fields[0]
        .name,
    ) == ([("context.txt", "Public context")], "choice")


def check_answer_grading() -> None:
    assert experiment_ops.resolve(epochs=1).epochs == 1
    case, expected = _answer()
    outcome = Outcome(changed_files=[], verification=Verification.Unchecked())
    scores = grader_ops.grade(task=case, response=expected, outcome=outcome)
    assert tuple(map(itemgetter(0), scores)) == tuple(grader_ops.required_names)
    assert dict(scores) == {"correctness": True, "scope": True}
    assert not dict(grader_ops.grade(task=case, response=None, outcome=outcome))["correctness"]


@pytest.mark.parametrize(
    ("status", "correctness"), [(Verification.Passed(), True), (Verification.Failed(), False)]
)
def check_code(status: Verification.Value, *, correctness: bool) -> None:
    checks = Verifier.create(
        inputs=["solution.py"],
        files=[Artifact.create(path="verify.py", content=Content.Inline(text="private check"))],
        tools=[],
        command=["python3", "verify.py"],
        stdin="private input",
        timeout_seconds=5,
    )
    case = Task.create(
        id="native-code",
        fixture=Fixture.create(files=[File.create(path="solution.py", contents="pass")]),
        instruction=Instruction.create(skill="reasoning", prompt="Fix solution.py"),
        criterion=Criterion.Code(verifier=checks),
        allowed_files=["solution.py"],
        reference=Reference(
            edits=Fixture.create(files=[File.create(path="solution.py", contents="fixed")]),
            completion=Completion.Plain(text=""),
        ),
    )
    projected = projection_ops.verifier(task=case)
    assert projected is not None
    public_files = [artifact.path for artifact in projection_ops.case(task=case).files]
    outcome = Outcome(changed_files=["workspace/solution.py"], verification=status)
    scores = grader_ops.grade(task=case, response=None, outcome=outcome)
    assert (tuple(map(itemgetter(0), scores)), dict(scores)) == (
        tuple(grader_ops.required_names),
        {"correctness": correctness, "scope": True},
    )
    outside_scope = Outcome(
        changed_files=["workspace/other.py"], verification=Verification.Passed()
    )
    assert (
        projected.stdin,
        public_files,
        dict(grader_ops.grade(task=case, response=None, outcome=outside_scope))["scope"],
    ) == ("private input", ["solution.py"], False)


def check_rejections() -> None:
    with pytest.raises(DomainValidationError):
        Fixture.create(
            files=[
                File.create(path="duplicate.txt", contents="one"),
                File.create(path="duplicate.txt", contents="two"),
            ]
        )
    with pytest.raises(TypeError):
        cast(Callable[..., Experiment], experiment_ops.resolve)(epochs="wrong type")


@pytest.mark.parametrize(
    ("public_name", "native_name"),
    [("Case", "case"), ("Task", "task"), ("Rubric", "rubric")],
)
def explicit_types_preserve_native_identity(public_name: str, *, native_name: str) -> None:
    assert getattr(kernel_types, public_name) is getattr(native_kernel, native_name)


@pytest.mark.parametrize(
    ("owner", "alternative", "native_name"),
    [
        ("Criterion", "Answer", "Answer"),
        ("Content", "Inline", "Inline"),
        ("Completion", "Plain", "Plain"),
        ("ResponseValue", "String", "String"),
        ("Verification", "HarnessError", "Harness_error"),
    ],
)
def owned_alternatives_preserve_native_identity(
    owner: str, *, alternative: str, native_name: str
) -> None:
    assert getattr(getattr(kernel_types, owner), alternative) is getattr(native_kernel, native_name)


def public_kernel_exports_only_domain_types() -> None:
    assert all(
        name[0].isupper() and isinstance(getattr(kernel_types, name), type)
        for name in vars(kernel_types)["__all__"]
    )
    assert (
        not {
            "Ast",
            "Grader",
            "Projection",
            "sources",
            "Answer",
            "Code",
            "Inline",
            "Plain",
            "String",
            "HarnessError",
        }
        & vars(kernel_types).keys()
    )
