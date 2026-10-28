"""Exercise native types and real kernel policy through the installed package."""

from operator import itemgetter

import pytest
from kernel import (
    REQUIRED_SCORES,
    Case,
    Criterion,
    Instruction,
    Outcome,
    Reference,
    Rubric,
    SourceFile,
    Task,
    Value,
    Verification,
    Verifier,
)
from pydantic import JsonValue

from evals.python.tests.declarations import _files


def _outcome(
    *, changed_files: list[str], verification: Verification, response: JsonValue = None
) -> Outcome:
    return Outcome(
        changed_files=changed_files,
        verification=verification,
        response=response,
        facts=[],
    )


def _answer() -> tuple[Task, JsonValue]:
    expected: JsonValue = {"choice": "B"}
    case = Task(
        id="native-answer",
        fixture=[SourceFile(path="context.txt", contents="Public context")],
        instruction=Instruction(prompt="Choose B"),
        criterion=Criterion.Answer(rubric=Rubric(expected=[("choice", "B")], text_rule=None)),
        allowed_files=[],
        reference=Reference(edits=[], completion=expected),
    )
    return case, expected


def check_answer_projection() -> None:
    case, _ = _answer()
    public = case.project()
    assert all(
        isinstance(item, kind)
        for item, kind in ((case, Task), (public, Case), (case.reference.completion, Value))
    )
    assert (public.case_id, hasattr(public, "reference"), case.checks()) == (case.id, False, None)
    assert list(_files(public.files).items()) == [("context.txt", "Public context")]


def check_answer_grading() -> None:
    case, expected = _answer()
    outcome = _outcome(changed_files=[], verification=Verification.Unchecked(), response=expected)
    scores = case.grade(outcome=outcome)
    assert tuple(map(itemgetter(0), scores)) == REQUIRED_SCORES
    assert dict(scores) == {"correctness": True, "scope": True}
    silent = _outcome(changed_files=[], verification=Verification.Unchecked())
    assert not dict(case.grade(outcome=silent))["correctness"]


@pytest.mark.parametrize(
    ("status", "correctness"), [(Verification.Passed(), True), (Verification.Failed(), False)]
)
def check_code(status: Verification, *, correctness: bool) -> None:
    checks = Verifier(
        inputs=["solution.py"],
        files=[SourceFile(path="verify.py", contents="private check")],
        tools=[],
        command=["python3", "verify.py"],
        stdin="private input",
        timeout_seconds=5,
    )
    case = Task(
        id="native-code",
        fixture=[SourceFile(path="solution.py", contents="pass")],
        instruction=Instruction(prompt="Fix solution.py"),
        criterion=Criterion.Code(verifier=checks),
        allowed_files=["solution.py"],
        reference=Reference(
            edits=[SourceFile(path="solution.py", contents="fixed")],
            completion=None,
        ),
    )
    assert case.checks() is not None
    assert [file.path for file in case.project().files] == ["solution.py"]
    outcome = _outcome(changed_files=["solution.py"], verification=status)
    scores = case.grade(outcome=outcome)
    assert (tuple(map(itemgetter(0), scores)), dict(scores)) == (
        REQUIRED_SCORES,
        {"correctness": correctness, "scope": True},
    )
    outside = _outcome(changed_files=["other.py"], verification=Verification.Passed())
    assert dict(case.grade(outcome=outside)) == {"correctness": True, "scope": False}
