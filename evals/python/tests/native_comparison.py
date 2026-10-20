from typing import cast

import pytest

from evals.python import datasets
from evals.python.integrations.inspect import scoring
from evals.python.tests.native_kernel import _answer
from kernel import (
    Assessment,
    Completion,
    Criterion,
    Fixture,
    GradingError,
    Instruction,
    Outcome,
    Predicate,
    Profile,
    Reference,
    Response,
    ResponseField,
    ResponseValue,
    Rubric,
    Task,
    TaskComparison,
    TextRule,
    ValidationError,
    Value,
    Verification,
)


def _response(*, choice: str = "B", reason: str = "One reason") -> Response:
    return Response.create(
        fields=[
            ResponseField.create(name="choice", value=ResponseValue.create(string=choice)),
            ResponseField.create(name="reason", value=ResponseValue.create(string=reason)),
        ]
    )


def native_task_comparison_composes_component_results() -> None:
    before, _ = _answer()
    after = Task.create(
        id="changed-answer",
        fixture=before.fixture,
        instruction=Instruction.create(skill="reasoning", prompt="Choose A"),
        criterion=before.criterion,
        allowed_files=["context.txt"],
        reference=before.reference,
    )
    difference = Task.compare(before=before, after=after)
    assert isinstance(difference, TaskComparison)
    assert not difference.equal
    assert (
        tuple(difference.id.changed_fields),
        tuple(difference.instruction.changed_fields),
        tuple(difference.allowed_files.changed_fields),
        difference.fixture.equal,
        difference.criterion.equal,
        difference.reference.equal,
    ) == (("id",), ("prompt",), ("allowed_files",), True, True, True)
    assert Task.compare(before=before, after=before).equal


def response_comparison_is_keyed_and_preserves_native_values() -> None:
    before = _response()
    reordered = Response.create(fields=list(reversed(before.fields)))
    assert Response.compare(before=before, after=reordered).equal
    after = Response.create(
        fields=[
            ResponseField.create(name="choice", value=ResponseValue.create(bool=True)),
            ResponseField.create(name="extra", value=ResponseValue.create(string="added")),
        ]
    )
    comparison = Response.compare(before=before, after=after)
    fields = {field.name: field for field in comparison.fields}
    assert not comparison.equal
    assert (
        isinstance(fields["choice"].before, ResponseValue.String),
        isinstance(fields["choice"].after, ResponseValue.Bool),
        fields["extra"].before,
        fields["reason"].after,
    ) == (True, True, None, None)


def profile_and_reference_comparison_follow_component_semantics() -> None:
    before = Profile.create(name="a", preamble="read", instructions=["docs", "skills"])
    after = Profile.create(name="a", preamble="read", instructions=["skills", "docs"])
    assert Profile.compare(before=before, after=after).equal
    reference = Reference.create(edits=Fixture.empty, completion=Completion.create(plain="one"))
    changed = Reference.create(edits=Fixture.empty, completion=Completion.create(plain="two"))
    assert tuple(Reference.compare(before=reference, after=changed).changed_fields) == (
        "completion",
    )


@pytest.mark.parametrize(
    ("before", "after", "field"),
    [
        (Completion.create(plain="one"), Completion.create(plain="two"), "text"),
        (
            Completion.create(structured=_response()),
            Completion.create(structured=_response(choice="A")),
            "response",
        ),
        (Completion.create(plain="one"), Completion.create(structured=_response()), "kind"),
    ],
)
def completion_comparison_names_the_changed_dimension(
    before: Completion.Value, *, after: Completion.Value, field: str
) -> None:
    assert tuple(Completion.compare(before=before, after=after).changed_fields) == (field,)


@pytest.mark.parametrize(
    ("response", "present", "passed", "observed"),
    [
        (_response(), True, True, "One reason"),
        (_response(choice="A"), True, False, "One reason"),
        (_response(reason="long enough to fail"), True, False, "long enough to fail"),
        (None, False, False, None),
        (Response.empty, True, False, None),
    ],
)
def composed_answer_retains_field_and_text_evidence(
    response: Response | None, *, present: bool, passed: bool, observed: str | None
) -> None:
    _, expected = _answer()
    rubric = Rubric.create(
        expected=expected, text_rule=TextRule.create(field="reason", min_words=1, max_words=3)
    )
    outcome = Outcome.create(changed_files=[], verification=Verification.Unchecked())
    result = Assessment.create(
        predicate=Criterion.condition(criterion=Criterion.create(answer=rubric)),
        observation=Outcome.observation(outcome=outcome, response=response),
    )
    details = scoring.assessment_details(result)
    checks = cast(dict[str, dict[str, object]], details["checks"])
    assert (
        Assessment.passed(assessment=result),
        checks["response"]["observed"] is not None,
        checks["text"]["observed"],
    ) == (passed, present, observed)


def assessment_and_legacy_scores_agree() -> None:
    task, expected = _answer()
    outcome = Outcome.create(
        changed_files=["unexpected.txt"], verification=Verification.Unchecked()
    )
    result = Task.assess(task=task, response=expected, outcome=outcome)
    assert isinstance(result, Assessment.All)
    scope = dict(result.checks)["scope"]
    assert scoring.plain(cast(Value.Value, Assessment.observed(assessment=scope))) == [
        "unexpected.txt"
    ]
    assert (
        dict(Assessment.scores(assessment=result))
        == dict(Task.grade(task=task, response=expected, outcome=outcome))
        == {"correctness": True, "scope": False}
    )


def nested_assessments_retain_both_success_and_failure() -> None:
    yes = Predicate.present(path=["verification"])
    no = Predicate.present(path=["absent"])
    child = Predicate.all(checks=[("bad", no), ("good", yes)])
    root = Assessment.create(
        predicate=Predicate.all(checks=[("correctness", child), ("scope", yes)]),
        observation=Outcome.observation(
            outcome=Outcome.create(changed_files=[], verification=Verification.Unchecked()),
            response=None,
        ),
    )
    assert isinstance(root, Assessment.All)
    inner = dict(root.checks)["correctness"]
    assert isinstance(inner, Assessment.All)
    assert [name for name, _ in inner.checks] == ["bad", "good"]
    assert dict(Assessment.scores(assessment=root)) == {"correctness": False, "scope": True}


def conjunction_identity_and_single_check_projection() -> None:
    empty = Assessment.create(predicate=Predicate.all(checks=[]), observation=Value.Null())
    yes = Assessment.create(predicate=Predicate.all(checks=[]), observation=Value.Null())
    single = Assessment.create(
        predicate=Predicate.not_(check=Predicate.present(path=["absent"])), observation=Value.Null()
    )
    assert Assessment.passed(assessment=empty)
    assert tuple(Assessment.scores(assessment=yes)) == ()
    assert dict(Assessment.scores(assessment=single)) == {"passed": True}
    assert Assessment.observed(assessment=single) is None


@pytest.mark.parametrize("names", [("",), ("same", "same")])
def named_composition_rejects_ambiguous_checks(names: tuple[str, ...]) -> None:
    yes = Predicate.present(path=["verification"])
    with pytest.raises(ValidationError, match="unique, nonempty"):
        Predicate.all(checks=[(name, yes) for name in names])


@pytest.mark.parametrize("case_id", ["clear-task", "small-decision"])
def harness_failures_are_errors_for_every_criterion(case_id: str) -> None:
    with pytest.raises(GradingError, match="offline"):
        Task.assess(
            task=datasets.load_dataset(selection="smoke").records[case_id],
            response=None,
            outcome=Outcome.create(
                changed_files=(), verification=Verification.HarnessError(detail="offline")
            ),
        )


def text_assessment_preserves_wrong_value_type() -> None:
    result = Assessment.create(
        predicate=Predicate.words(path=["response", "reason"], min_words=0, max_words=3),
        observation=Outcome.observation(
            outcome=Outcome.create(changed_files=[], verification=Verification.Unchecked()),
            response=Response.create(
                fields=[ResponseField.create(name="reason", value=ResponseValue.create(bool=True))]
            ),
        ),
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
        predicate=Criterion.condition(
            criterion=datasets.load_dataset(selection="smoke").records["clear-task"].criterion
        ),
        observation=Outcome.observation(outcome=outcome, response=None),
    )
    assert scoring.assessment_details(result) == {
        "passed": True,
        "predicate": {"kind": "equals", "path": ["verification"], "expected": "passed"},
        "observed": "passed",
    }


def tool_traces_and_environment_state_are_graded_as_facts() -> None:
    call = scoring.value({"name": "lookup", "arguments": {"id": 7}})
    criterion = Criterion.create(
        state=Predicate.all(
            checks=[
                ("looked-up", Predicate.contains(path=["trace"], item=call)),
                ("only-lookups", Predicate.within(path=["trace"], allowed=[call])),
                (
                    "balance",
                    Predicate.equals(path=["state", "balance"], expected=Value.Int(value=5)),
                ),
                (
                    "no-transfer",
                    Predicate.not_(check=Predicate.present(path=["state", "transfer"])),
                ),
                ("any", Predicate.any(checks=[("missing", Predicate.present(path=["absent"]))])),
            ]
        )
    )
    task = Task.create(
        id="tool-task",
        fixture=Fixture.empty,
        instruction=Instruction.create(skill="reasoning", prompt="Report the balance"),
        criterion=criterion,
        allowed_files=[],
        reference=Reference.create(edits=Fixture.empty, completion=Completion.create(plain="5")),
    )
    assert Task.verifier(task=task) is None
    facts = [("trace", scoring.value([{"name": "lookup", "arguments": {"id": 7}}]))]
    facts.append(("state", scoring.value({"balance": 5, "ratio": 0.5, "note": None})))
    outcome = Outcome.create(changed_files=[], verification=Verification.Unchecked(), facts=facts)
    result = Task.assess(task=task, response=None, outcome=outcome)
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
    assert scoring.plain(scoring.value(object())).startswith("<object")  # type: ignore[union-attr]
    assert datasets.compile_dataset(cases=(task,)).cases_hash
