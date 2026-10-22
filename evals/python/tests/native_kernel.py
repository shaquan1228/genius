"""Exercise native types and real kernel policy through the installed package."""

from operator import itemgetter

import pytest
from kernel import (
    REQUIRED_SCORES,
    Case,
    Criterion,
    File,
    Instruction,
    Outcome,
    Reference,
    Rubric,
    Task,
    Value,
    Verification,
    Verifier,
)

from evals.python.tests.declarations import _files


def _outcome(
    *, changed_files: list[str], verification: Verification, response: Value | None = None
) -> Outcome:
    return Outcome(
        changed_files=changed_files,
        verification=verification,
        response=response or Value.from_python(value=None),
        facts=[],
    )


def _answer() -> tuple[Task, Value]:
    expected = Value.from_python(value={"choice": "B"})
    case = Task(
        id="native-answer",
        fixture=[File(path="context.txt", contents="Public context")],
        instruction=Instruction(prompt="Choose B"),
        criterion=Criterion.answer(
            rubric=Rubric(expected=[("choice", Value.from_python(value="B"))], text_rule=None)
        ),
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
    outcome = _outcome(changed_files=[], verification=Verification.unchecked(), response=expected)
    scores = case.grade(outcome=outcome)
    assert tuple(map(itemgetter(0), scores)) == REQUIRED_SCORES
    assert dict(scores) == {"correctness": True, "scope": True}
    silent = _outcome(changed_files=[], verification=Verification.unchecked())
    assert not dict(case.grade(outcome=silent))["correctness"]


@pytest.mark.parametrize(
    ("status", "correctness"), [(Verification.passed(), True), (Verification.failed(), False)]
)
def check_code(status: Verification, *, correctness: bool) -> None:
    checks = Verifier(
        inputs=["solution.py"],
        files=[File(path="verify.py", contents="private check")],
        tools=[],
        command=["python3", "verify.py"],
        stdin="private input",
        timeout_seconds=5,
    )
    case = Task(
        id="native-code",
        fixture=[File(path="solution.py", contents="pass")],
        instruction=Instruction(prompt="Fix solution.py"),
        criterion=Criterion.code(verifier=checks),
        allowed_files=["solution.py"],
        reference=Reference(
            edits=[File(path="solution.py", contents="fixed")],
            completion=Value.from_python(value=None),
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
    outside = _outcome(changed_files=["other.py"], verification=Verification.passed())
    assert dict(case.grade(outcome=outside)) == {"correctness": True, "scope": False}
