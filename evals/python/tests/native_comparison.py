"""Generic assessments explain every check against the observation it saw."""

from typing import cast

import pytest

from evals.python import datasets
from evals.python.integrations.inspect import scoring
from evals.python.tests.native_kernel import _answer
from kernel import (
    Assessment,
    Criterion,
    GradingError,
    Instruction,
    Outcome,
    Predicate,
    Reference,
    Rubric,
    Task,
    TextRule,
    Value,
    Verification,
)


def _reply(*, choice: str = "B", reason: str = "One reason") -> Value.Value:
    return Value.Record(
        fields=[("choice", Value.String(value=choice)), ("reason", Value.String(value=reason))]
    )


def _observation(response: Value.Value) -> Value.Value:
    outcome = Outcome.create(
        changed_files=[], verification=Verification.Unchecked(), response=response
    )
    return Outcome.observation(outcome=outcome)


@pytest.mark.parametrize(
    ("response", "present", "passed", "observed"),
    [
        (_reply(), True, True, "One reason"),
        (_reply(choice="A"), True, False, "One reason"),
        (_reply(reason="long enough to fail"), True, False, "long enough to fail"),
        (Value.Null(), False, False, None),
        (Value.Record(fields=[]), True, False, None),
    ],
)
def composed_answer_retains_field_and_text_evidence(
    response: Value.Value, *, present: bool, passed: bool, observed: str | None
) -> None:
    rubric = Rubric(
        expected=[("choice", Value.String(value="B"))],
        text_rule=TextRule(field="reason", min_words=1, max_words=3),
    )
    result = Assessment.create(
        predicate=Task.condition(criterion=Criterion.Answer(rubric=rubric)),
        observation=_observation(response),
    )
    details = scoring.assessment_details(result)
    checks = cast(dict[str, dict[str, object]], details["checks"])
    assert (
        Assessment.passed(assessment=result),
        checks["response"]["observed"] is not None,
        checks["text"]["observed"],
    ) == (passed, present, observed)


def assessment_and_scores_agree() -> None:
    task, expected = _answer()
    outcome = Outcome.create(
        changed_files=["unexpected.txt"], verification=Verification.Unchecked(), response=expected
    )
    result = Task.assess(task=task, outcome=outcome)
    assert isinstance(result, Assessment.All)
    scope = dict(result.checks)["scope"]
    assert scoring.plain(cast(Value.Value, Assessment.observed(assessment=scope))) == [
        "unexpected.txt"
    ]
    assert (
        dict(Assessment.scores(assessment=result))
        == dict(Task.grade(task=task, outcome=outcome))
        == {"correctness": True, "scope": False}
    )


def nested_assessments_retain_both_success_and_failure() -> None:
    yes = Predicate.Present(path=["verification"])
    no = Predicate.Present(path=["absent"])
    child = Predicate.All(checks=[("bad", no), ("good", yes)])
    root = Assessment.create(
        predicate=Predicate.All(checks=[("correctness", child), ("scope", yes)]),
        observation=_observation(Value.Null()),
    )
    assert isinstance(root, Assessment.All)
    inner = dict(root.checks)["correctness"]
    assert isinstance(inner, Assessment.All)
    assert [name for name, _ in inner.checks] == ["bad", "good"]
    assert dict(Assessment.scores(assessment=root)) == {"correctness": False, "scope": True}


def conjunction_identity_and_single_check_projection() -> None:
    empty = Assessment.create(predicate=Predicate.All(checks=[]), observation=Value.Null())
    single = Assessment.create(
        predicate=Predicate.Not(check=Predicate.Present(path=["absent"])), observation=Value.Null()
    )
    assert Assessment.passed(assessment=empty)
    assert tuple(Assessment.scores(assessment=empty)) == ()
    assert dict(Assessment.scores(assessment=single)) == {"passed": True}
    assert Assessment.observed(assessment=single) is None


@pytest.mark.parametrize("case_id", ["clear-task", "small-decision"])
def harness_failures_are_errors_for_every_criterion(case_id: str) -> None:
    with pytest.raises(GradingError, match="offline"):
        Task.assess(
            task=datasets.load_dataset(selection="smoke").records[case_id],
            outcome=Outcome.create(
                changed_files=(), verification=Verification.HarnessError(detail="offline")
            ),
        )


def text_assessment_preserves_wrong_value_type() -> None:
    result = Assessment.create(
        predicate=Predicate.Words(path=["response", "reason"], min_words=0, max_words=3),
        observation=_observation(Value.Record(fields=[("reason", Value.Bool(value=True))])),
    )
    assert not Assessment.passed(assessment=result)
    assert scoring.assessment_details(result) == {
        "passed": False,
        "predicate": {
            "kind": "words",
            "path": ["response", "reason"],
            "min_words": 0,
            "max_words": 3,
        },
        "observed": True,
    }


def code_assessment_serializes_the_verified_outcome() -> None:
    outcome = Outcome.create(changed_files=[], verification=Verification.Passed())
    result = Assessment.create(
        predicate=Task.condition(
            criterion=datasets.load_dataset(selection="smoke").records["clear-task"].criterion
        ),
        observation=Outcome.observation(outcome=outcome),
    )
    assert scoring.assessment_details(result) == {
        "passed": True,
        "predicate": {"kind": "equals", "path": ["verification"], "expected": "passed"},
        "observed": "passed",
    }


def tool_traces_and_environment_state_are_graded_as_facts() -> None:
    call = scoring.value({"name": "lookup", "arguments": {"id": 7}})
    criterion = Criterion.State(
        predicate=Predicate.All(
            checks=[
                ("looked-up", Predicate.Contains(path=["trace"], item=call)),
                ("only-lookups", Predicate.Within(path=["trace"], allowed=[call])),
                (
                    "balance",
                    Predicate.Equals(path=["state", "balance"], expected=Value.Int(value=5)),
                ),
                ("no-transfer", Predicate.Not(check=Predicate.Present(path=["state", "transfer"]))),
                ("any", Predicate.Any(checks=[("missing", Predicate.Present(path=["absent"]))])),
            ]
        )
    )
    task = Task.create(
        id="tool-task",
        fixture=[],
        instruction=Instruction(skill="reasoning", prompt="Report the balance"),
        criterion=criterion,
        allowed_files=[],
        reference=Reference(edits=[], completion=Value.String(value="5")),
    )
    assert Task.checks(task=task) is None
    facts = [("trace", scoring.value([{"name": "lookup", "arguments": {"id": 7}}]))]
    facts.append(("state", scoring.value({"balance": 5, "ratio": 0.5, "note": None})))
    outcome = Outcome.create(changed_files=[], verification=Verification.Unchecked(), facts=facts)
    result = Task.assess(task=task, outcome=outcome)
    details = cast(dict[str, dict[str, object]], scoring.assessment_details(result)["checks"])
    checks = cast(dict[str, dict[str, object]], details["correctness"]["checks"])
    assert {name: check["passed"] for name, check in checks.items()} == {
        "looked-up": True,
        "only-lookups": True,
        "balance": True,
        "no-transfer": True,
        "any": False,
    }
    assert checks["no-transfer"]["predicate"] == {
        "kind": "not",
        "check": {"kind": "present", "path": ["state", "transfer"]},
    }
    assert checks["only-lookups"]["predicate"] == {
        "kind": "within",
        "path": ["trace"],
        "allowed": [{"name": "lookup", "arguments": {"id": 7}}],
    }
    assert checks["any"]["predicate"] == {"kind": "any", "checks": ["missing"]}
    assert scoring.plain(scoring.value({"ratio": 0.5, "flag": True, "items": (1, "x")})) == {
        "ratio": 0.5,
        "flag": True,
        "items": [1, "x"],
    }
    assert str(scoring.plain(scoring.value(object()))).startswith("<object")
    assert datasets.compile_dataset(cases=(task,)).cases_hash
