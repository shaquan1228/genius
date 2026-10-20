"""Exercise generated types and real kernel policy through an in-process bridge."""

from operator import itemgetter

import pytest

from evals.python.tests.declarations import _files
from kernel import (
    Case,
    Criterion,
    Experiment,
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


def _answer() -> tuple[Task, Value.Value]:
    expected = Value.Record(fields=[("choice", "B")])
    case = Task.create(
        id="native-answer",
        fixture=[File(path="context.txt", contents="Public context")],
        instruction=Instruction(skill="reasoning", prompt="Choose B"),
        criterion=Criterion.Answer(rubric=Rubric(expected=[("choice", "B")], text_rule=None)),
        allowed_files=[],
        reference=Reference(edits=[], completion=expected),
    )
    return case, expected


def check_answer_projection() -> None:
    case, _ = _answer()
    assert isinstance(case, Task)
    public = Task.project(task=case)
    assert isinstance(public, Case)
    assert (public.case_id, hasattr(public, "reference"), Task.checks(task=case)) == (
        case.id,
        False,
        None,
    )
    assert list(_files(public.files).items()) == [("context.txt", "Public context")]
    assert isinstance(case.reference.completion, Value.Record)


def check_answer_grading() -> None:
    assert Experiment.resolve(epochs=1).epochs == 1
    case, expected = _answer()
    outcome = Outcome.create(
        changed_files=[], verification=Verification.Unchecked(), response=expected
    )
    scores = Task.grade(task=case, outcome=outcome)
    assert tuple(map(itemgetter(0), scores)) == tuple(Task.required_scores)
    assert dict(scores) == {"correctness": True, "scope": True}
    silent = Outcome.create(changed_files=[], verification=Verification.Unchecked())
    assert not dict(Task.grade(task=case, outcome=silent))["correctness"]


@pytest.mark.parametrize(
    ("status", "correctness"), [(Verification.Passed(), True), (Verification.Failed(), False)]
)
def check_code(status: Verification.Value, *, correctness: bool) -> None:
    checks = Verifier(
        inputs=["solution.py"],
        files=[File(path="verify.py", contents="private check")],
        tools=[],
        command=["python3", "verify.py"],
        stdin="private input",
        timeout_seconds=5,
    )
    case = Task.create(
        id="native-code",
        fixture=[File(path="solution.py", contents="pass")],
        instruction=Instruction(skill="reasoning", prompt="Fix solution.py"),
        criterion=Criterion.Code(verifier=checks),
        allowed_files=["solution.py"],
        reference=Reference(edits=[File(path="solution.py", contents="fixed")], completion=None),
    )
    assert Task.checks(task=case) is not None
    assert [file.path for file in Task.project(task=case).files] == ["solution.py"]
    outcome = Outcome.create(changed_files=["solution.py"], verification=status)
    scores = Task.grade(task=case, outcome=outcome)
    assert (tuple(map(itemgetter(0), scores)), dict(scores)) == (
        tuple(Task.required_scores),
        {"correctness": correctness, "scope": True},
    )
    outside = Outcome.create(changed_files=["other.py"], verification=Verification.Passed())
    assert dict(Task.grade(task=case, outcome=outside)) == {"correctness": True, "scope": False}
