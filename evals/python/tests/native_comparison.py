"""Generic assessments explain every check against the observation it saw."""

from typing import cast

import pytest
from kernel import (
    Assessment,
    Criterion,
    GradingError,
    Instruction,
    Outcome,
    Predicate,
    Record,
    Reference,
    Rubric,
    Task,
    TextRule,
    Value,
    Verification,
)
from pydantic import JsonValue

from evals.python import datasets
from evals.python.datasets import Declaration
from evals.python.integrations.inspect import scoring
from evals.python.provenance import plain
from evals.python.tests.native_kernel import _answer


def _reply(*, choice: str = "B", reason: str = "One reason") -> JsonValue:
    return {"choice": choice, "reason": reason}


def _outcome(
    *,
    verification: Verification,
    changed_files: tuple[str, ...] = (),
    response: object = None,
    facts: tuple[tuple[str, JsonValue], ...] = (),
) -> Outcome:
    return Outcome(
        changed_files=changed_files,
        verification=verification,
        response=response,
        facts=facts,
    )


def _observation(response: object) -> Value:
    return _outcome(verification=Verification.Unchecked(), response=response).observation()


@pytest.mark.parametrize(
    ("response", "present", "passed", "observed"),
    [
        (_reply(), True, True, "One reason"),
        (_reply(choice="A"), True, False, "One reason"),
        (_reply(reason="long enough to fail"), True, False, "long enough to fail"),
        (None, False, False, None),
        ({}, True, False, None),
    ],
)
def composed_answer_retains_field_and_text_evidence(
    response: JsonValue, *, present: bool, passed: bool, observed: str | None
) -> None:
    rubric = Rubric(
        expected=[("choice", "B")],
        text_rule=TextRule(field="reason", min_words=1, max_words=3),
    )
    result = Assessment(
        predicate=Criterion.Answer(rubric=rubric).condition(),
        observation=_observation(response),
    )
    details = scoring.assessment_details(result)
    checks = cast(dict[str, dict[str, object]], details["checks"])
    assert (
        result.passed(),
        checks["response"]["observed"] is not None,
        checks["text"]["observed"],
    ) == (passed, present, observed)


def assessment_and_scores_agree() -> None:
    task, expected = _answer()
    outcome = _outcome(
        changed_files=("unexpected.txt",),
        verification=Verification.Unchecked(),
        response=expected,
    )
    result = task.assess(outcome=outcome)
    assert isinstance(result, Assessment.All)
    scope = dict(result.checks)["scope"]
    assert plain(scope.observed()) == ["unexpected.txt"]
    assert (
        dict(result.scores())
        == dict(task.grade(outcome=outcome))
        == {"correctness": True, "scope": False}
    )


def nested_assessments_retain_both_success_and_failure() -> None:
    yes = Predicate.Present(path=["verification"])
    no = Predicate.Present(path=["absent"])
    child = Predicate.All(checks=[("bad", no), ("good", yes)])
    root = Assessment(
        predicate=Predicate.All(checks=[("correctness", child), ("scope", yes)]),
        observation=_observation(None),
    )
    assert isinstance(root, Assessment.All)
    inner = dict(root.checks)["correctness"]
    assert isinstance(inner, Assessment.All)
    assert [name for name, _ in inner.checks] == ["bad", "good"]
    assert dict(root.scores()) == {"correctness": False, "scope": True}


def conjunction_identity_and_single_check_projection() -> None:
    empty = Assessment(predicate=Predicate.All(checks=[]), observation=None)
    single = Assessment(
        predicate=Predicate.Not(check=Predicate.Present(path=["absent"])), observation=None
    )
    assert empty.passed()
    assert empty.scores() == ()
    assert dict(single.scores()) == {"passed": True}
    assert single.observed() is None


@pytest.mark.parametrize("case_id", ["clear-task", "small-decision"])
def harness_failures_are_errors_for_every_criterion(case_id: str) -> None:
    task = datasets.load_dataset(selection="smoke").records[case_id].task
    with pytest.raises(GradingError, match="offline"):
        task.assess(outcome=_outcome(verification=Verification.HarnessError(detail="offline")))


def text_assessment_preserves_wrong_value_type() -> None:
    result = Assessment(
        predicate=Predicate.Words(path=["response", "reason"], min_words=0, max_words=3),
        observation=_observation({"reason": True}),
    )
    assert not result.passed()
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
    outcome = _outcome(verification=Verification.Passed())
    result = Assessment(
        predicate=datasets.load_dataset(selection="smoke")
        .records["clear-task"]
        .task.criterion.condition(),
        observation=outcome.observation(),
    )
    assert scoring.assessment_details(result) == {
        "passed": True,
        "predicate": {"kind": "equals", "path": ["verification"], "expected": "passed"},
        "observed": "passed",
    }


def tool_traces_and_environment_state_are_graded_as_facts() -> None:
    call: dict[str, JsonValue] = {"name": "lookup", "arguments": {"id": 7}}
    criterion = Criterion.State(
        predicate=Predicate.All(
            checks=[
                ("looked-up", Predicate.Contains(path=["trace"], item=call)),
                ("only-lookups", Predicate.Within(path=["trace"], allowed=[call])),
                (
                    "balance",
                    Predicate.Equals(path=["state", "balance"], expected=5),
                ),
                (
                    "no-transfer",
                    Predicate.Not(check=Predicate.Present(path=["state", "transfer"])),
                ),
                ("any", Predicate.Any(checks=[("missing", Predicate.Present(path=["absent"]))])),
            ]
        )
    )
    task = Task(
        id="tool-task",
        fixture=[],
        instruction=Instruction(prompt="Report the balance"),
        criterion=criterion,
        allowed_files=[],
        reference=Reference(edits=[], completion="5"),
    )
    dataset = datasets.compile_dataset(cases=(Declaration(skill="reasoning", task=task),))
    assert (task.checks(), bool(dataset.cases_hash)) == (None, True)
    outcome = _outcome(
        verification=Verification.Unchecked(),
        facts=(("trace", [call]), ("state", {"balance": 5, "ratio": 0.5})),
    )
    result = task.assess(outcome=outcome)
    details = cast(dict[str, dict[str, object]], scoring.assessment_details(result)["checks"])
    checks = cast(dict[str, dict[str, object]], details["correctness"]["checks"])
    assert {name: check["passed"] for name, check in checks.items()} == {
        "looked-up": True,
        "only-lookups": True,
        "balance": True,
        "no-transfer": True,
        "any": False,
    }
    assert {name: checks[name]["predicate"] for name in ("no-transfer", "only-lookups", "any")} == {
        "no-transfer": {"kind": "not", "check": {"kind": "present", "path": ["state", "transfer"]}},
        "only-lookups": {
            "kind": "within",
            "path": ["trace"],
            "allowed": [{"name": "lookup", "arguments": {"id": 7}}],
        },
        "any": {"kind": "any", "checks": [["missing", {"kind": "present", "path": ["absent"]}]]},
    }


def native_values_decode_to_plain_json() -> None:
    witness = Reference(edits=[], completion={"ratio": 0.5, "flag": True, "items": (1, "x")})
    assert plain(witness.completion) == {"ratio": 0.5, "flag": True, "items": [1, "x"]}
    with pytest.raises(TypeError, match="Unsupported"):
        Reference(edits=[], completion=object())


@pytest.mark.parametrize("state", [{"transfer": 2**64}, {"transfer": 5, "time": 2**64}])
def unrepresentable_state_cannot_pass_a_negated_check(state: dict[str, object]) -> None:
    absent = Predicate.Not(check=Predicate.Present(path=["state", "transfer"]))
    outcome = Outcome(
        changed_files=[],
        verification=Verification.Unchecked(),
        response=scoring.observed(None),
        facts=[("state", scoring.observed(state))],
    )
    assert not absent.holds(observation=outcome.observation())


def unrepresentable_extra_field_keeps_the_answer_gradable() -> None:
    task, _ = _answer()
    outcome = _outcome(verification=Verification.Unchecked())
    reply = scoring.observed({"choice": "B", "id": 2**64})
    graded = Outcome(
        changed_files=outcome.changed_files,
        verification=outcome.verification,
        response=reply,
        facts=outcome.facts,
    )
    assert dict(task.grade(outcome=graded))["correctness"]


def _equals(*, expected: object, path: tuple[str, ...] = ("response",)) -> Predicate:
    return Predicate.Equals(path=path, expected=expected)


@pytest.mark.parametrize(
    ("check", "response", "holds"),
    [
        (_equals(expected=1), 1.0, False),
        (_equals(expected=True), 1, False),
        (_equals(expected={"a": 1, "b": 2}), {"b": 2, "a": 1}, True),
        (_equals(expected=[1, 2]), [2, 1], False),
        (
            _equals(expected=1, path=("response", "a")),
            Record(fields=[("a", 1), ("a", 2)]),
            True,
        ),
        (Predicate.Words(path=["response"], min_words=2, max_words=2), "one\u3000two", True),
    ],
    ids=["int-float", "bool-int", "record-order", "list-order", "first-duplicate", "unicode-words"],
)
def grading_rules_genius_depends_on(check: Predicate, *, response: object, holds: bool) -> None:
    assert check.holds(observation=_observation(response)) is holds
