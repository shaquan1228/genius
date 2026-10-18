from typing import cast

import pytest

from evals.python import grading
from evals.python.integrations.inspect import scoring
from evals.python.tests.native_kernel import _answer
from kernel import Assessment as NativeAssessment
from kernel import (
    Completion,
    Criterion,
    Fixture,
    GradingError,
    Instruction,
    Outcome,
    Profile,
    Reference,
    Response,
    ResponseField,
    ResponseValue,
    Rubric,
    Task,
    TaskComparison,
    TextRule,
    Verification,
)
from kernel import ValidationError as NativeValidationError


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
    ("response", "present", "passed", "words"),
    [
        (_response(), True, True, 2),
        (_response(choice="A"), True, False, 2),
        (_response(reason="long enough to fail"), True, False, 4),
        (None, False, False, None),
        (Response.empty, True, False, None),
    ],
)
def composed_answer_retains_field_and_text_evidence(
    response: Response | None, *, present: bool, passed: bool, words: int | None
) -> None:
    _, expected = _answer()
    rubric = Rubric.create(
        expected=expected, text_rule=TextRule.create(field="reason", min_words=1, max_words=3)
    )
    result = NativeAssessment.criterion(
        criterion=Criterion.create(answer=rubric),
        response=response,
        verification=Verification.Unchecked(),
    )
    details = scoring.assessment_details(result)
    checks = cast(dict[str, dict[str, object]], details["checks"])
    assert (
        NativeAssessment.passed(assessment=result),
        checks["response"]["response_present"],
        checks["text"]["word_count"],
    ) == (passed, present, words)


def assessment_and_legacy_scores_agree() -> None:
    task, expected = _answer()
    outcome = Outcome.create(
        changed_files=["workspace/unexpected.txt"], verification=Verification.Unchecked()
    )
    result = Task.assess(task=task, response=expected, outcome=outcome)
    assert isinstance(result, NativeAssessment.All)
    assert tuple(NativeAssessment.unexpected_files(assessment=result)) == (
        "workspace/unexpected.txt",
    )
    assert (
        dict(NativeAssessment.scores(assessment=result))
        == dict(Task.grade(task=task, response=expected, outcome=outcome))
        == {"correctness": True, "scope": False}
    )


def nested_assessments_retain_both_success_and_failure() -> None:
    yes = NativeAssessment.present(response=Response.empty)
    no = NativeAssessment.present(response=None)
    child = NativeAssessment.all(checks=[("bad", no), ("good", yes)])
    root = NativeAssessment.all(checks=[("correctness", child), ("scope", yes)])
    assert isinstance(child, NativeAssessment.All)
    assert [name for name, _ in child.checks] == ["bad", "good"]
    assert dict(NativeAssessment.scores(assessment=root)) == {"correctness": False, "scope": True}


def conjunction_identity_and_single_check_projection() -> None:
    empty = NativeAssessment.all(checks=[])
    yes = NativeAssessment.present(response=Response.empty)
    assert NativeAssessment.passed(assessment=empty)
    assert tuple(NativeAssessment.scores(assessment=empty)) == ()
    assert dict(NativeAssessment.scores(assessment=yes)) == {"passed": True}


@pytest.mark.parametrize("names", [("",), ("same", "same")])
def named_composition_rejects_ambiguous_checks(names: tuple[str, ...]) -> None:
    yes = NativeAssessment.present(response=Response.empty)
    with pytest.raises(NativeValidationError, match="unique, nonempty"):
        NativeAssessment.all(checks=[(name, yes) for name in names])


def decoding_boundary_returns_one_native_assessment() -> None:
    response = '{"choice":"A","reason":"Cheap"}'
    changed = ("workspace/unexpected.txt",)
    result = grading.assess_case(case_id="small-decision", response=response, changed_files=changed)
    assert dict(NativeAssessment.scores(assessment=result)) == grading.score_case(
        case_id="small-decision", response=response, changed_files=changed
    )
    assert not NativeAssessment.passed(assessment=result)


@pytest.mark.parametrize("case_id", ["clear-task", "small-decision"])
def harness_failures_are_errors_for_every_criterion(case_id: str) -> None:
    with pytest.raises(GradingError, match="offline"):
        grading.assess_case(
            case_id=case_id,
            response="",
            changed_files=(),
            verification=Verification.HarnessError(detail="offline"),
        )


def text_assessment_preserves_wrong_value_type() -> None:
    value = ResponseValue.create(bool=True)
    result = NativeAssessment.text(
        rule=TextRule.create(field="reason", min_words=0, max_words=3), value=value
    )
    assert not NativeAssessment.passed(assessment=result)
    assert scoring.assessment_details(result) == {
        "passed": False,
        "field": "reason",
        "actual": True,
        "word_count": None,
        "min_words": 0,
        "max_words": 3,
    }


def scope_evidence_is_derived_from_the_same_composition() -> None:
    first = NativeAssessment.scope(allowed_files=[], changed_files=["a", "a"])
    root = NativeAssessment.all(checks=[("first", first), ("second", first)])
    assert tuple(NativeAssessment.unexpected_files(assessment=root)) == ("a",)
    assert scoring.assessment_details(first) == {"passed": False, "unexpected_files": ["a"]}


def code_assessment_serializes_the_verified_outcome() -> None:
    result = NativeAssessment.verified(verification=Verification.Passed())
    assert scoring.assessment_details(result) == {"passed": True, "verification": "passed"}
