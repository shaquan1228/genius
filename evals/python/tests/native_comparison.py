"""Generic assessments explain every check against the observation it saw."""

from collections.abc import Sequence
from typing import cast

import pytest
from pydantic import JsonValue

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
    return Value.Record(fields=[("choice", choice), ("reason", reason)])


def _observation(response: JsonValue | Value.Value) -> Value.Value:
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
        (None, False, False, None),
        (Value.Record(fields=[]), True, False, None),
    ],
)
def composed_answer_retains_field_and_text_evidence(
    response: Value.Value, *, present: bool, passed: bool, observed: str | None
) -> None:
    rubric = Rubric(
        expected=[("choice", "B")],
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
        observation=_observation(None),
    )
    assert isinstance(root, Assessment.All)
    inner = dict(root.checks)["correctness"]
    assert isinstance(inner, Assessment.All)
    assert [name for name, _ in inner.checks] == ["bad", "good"]
    assert dict(Assessment.scores(assessment=root)) == {"correctness": False, "scope": True}


def conjunction_identity_and_single_check_projection() -> None:
    empty = Assessment.create(predicate=Predicate.All(checks=[]), observation=None)
    single = Assessment.create(
        predicate=Predicate.Not(check=Predicate.Present(path=["absent"])), observation=None
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
        observation=_observation(Value.Record(fields=[("reason", True)])),
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


def _state_details(
    checks: Sequence[tuple[str, Predicate.Value]], *, facts: dict[str, JsonValue]
) -> dict[str, object]:
    task = Task.create(
        id="tool-task",
        fixture=[],
        instruction=Instruction(skill="reasoning", prompt="Report the balance"),
        criterion=Criterion.State(predicate=Predicate.All(checks=checks)),
        allowed_files=[],
        reference=Reference(edits=[], completion="5"),
    )
    outcome = Outcome.create(changed_files=[], verification=Verification.Unchecked(), facts=facts)
    result = Task.assess(task=task, outcome=outcome)
    assert Task.checks(task=task) is None
    return cast(dict[str, object], scoring.assessment_details(result)["checks"])


def tool_trace_facts_are_graded() -> None:
    call: dict[str, JsonValue] = {"name": "lookup", "arguments": {"id": 7}}
    checks: list[tuple[str, Predicate.Value]] = [
        ("looked-up", Predicate.Contains(path=["trace"], item=call)),
        ("only-lookups", Predicate.Within(path=["trace"], allowed=[call])),
    ]
    details = cast(dict[str, dict[str, object]], _state_details(checks, facts={"trace": [call]}))
    graded = details["correctness"]["checks"]
    assert isinstance(graded, dict)
    assert {name: item["passed"] for name, item in graded.items()} == {
        "looked-up": True,
        "only-lookups": True,
    }
    assert graded["only-lookups"]["predicate"] == {
        "kind": "within",
        "path": ["trace"],
        "allowed": [{"name": "lookup", "arguments": {"id": 7}}],
    }


def environment_state_facts_are_graded() -> None:
    checks: list[tuple[str, Predicate.Value]] = [
        ("balance", Predicate.Equals(path=["state", "balance"], expected=5)),
        ("no-transfer", Predicate.Not(check=Predicate.Present(path=["state", "transfer"]))),
    ]
    details = cast(
        dict[str, dict[str, object]],
        _state_details(checks, facts={"state": {"balance": 5, "ratio": 0.5}}),
    )
    graded = details["correctness"]["checks"]
    assert isinstance(graded, dict)
    assert {name: item["passed"] for name, item in graded.items()} == {
        "balance": True,
        "no-transfer": True,
    }
    assert graded["no-transfer"]["predicate"] == {
        "kind": "not",
        "check": {"kind": "present", "path": ["state", "transfer"]},
    }


def any_predicate_records_missing_checks() -> None:
    checks = [("any", Predicate.Any(checks=[("missing", Predicate.Present(path=["absent"]))]))]
    details = cast(dict[str, dict[str, object]], _state_details(checks, facts={}))
    graded = details["correctness"]["checks"]
    assert isinstance(graded, dict)
    assert graded["any"]["passed"] is False
    assert graded["any"]["predicate"] == {"kind": "any", "checks": ["missing"]}


def plain_reference_values_project_to_json() -> None:
    witness = Reference(edits=[], completion={"ratio": 0.5, "flag": True, "items": (1, "x")})
    assert scoring.plain(witness.completion) == {"ratio": 0.5, "flag": True, "items": [1, "x"]}
    assert str(
        scoring.plain(Reference(edits=[], completion=cast(JsonValue, object())).completion)
    ).startswith("<object")


def compiled_dataset_keeps_its_case_hash() -> None:
    task, _ = _answer()
    assert datasets.compile_dataset(cases=(task,)).cases_hash
