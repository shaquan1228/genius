import pytest

from evals.python import grading
from evals.python.integrations.inspect import scoring
from evals.python.tests.native_kernel import _answer
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
    TaskGrade,
    TextRule,
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
def detailed_answer_grade_retains_field_and_text_judgments(
    response: Response | None, *, present: bool, passed: bool, words: int | None
) -> None:
    _, expected = _answer()
    rubric = Rubric.create(
        expected=expected,
        text_rule=TextRule.create(field="reason", min_words=1, max_words=3),
    )
    grade = Criterion.grade(
        criterion=Criterion.create(answer=rubric),
        response=response,
        verification=Verification.Unchecked(),
    )
    assert grade.answer is not None
    assert grade.answer.text_rule is not None
    assert (
        grade.passed,
        grade.answer.response_present,
        grade.answer.text_rule.word_count,
        grade.answer.fields.fields[0].name,
    ) == (passed, present, words, "choice")


def detailed_grade_and_legacy_scores_agree() -> None:
    task, expected = _answer()
    outcome = Outcome.create(
        changed_files=["workspace/unexpected.txt"], verification=Verification.Unchecked()
    )
    report = Task.grade_report(task=task, response=expected, outcome=outcome)
    assert isinstance(report, TaskGrade)
    assert (
        tuple(report.scope.unexpected_files),
        dict(report.scores),
        dict(Task.grade(task=task, response=expected, outcome=outcome)),
    ) == (
        ("workspace/unexpected.txt",),
        {"correctness": True, "scope": False},
        {"correctness": True, "scope": False},
    )
    assert scoring.grade_details(report) == {
        "correctness": True,
        "unexpected_files": ["workspace/unexpected.txt"],
        "answer": {
            "response_present": True,
            "fields": [{"name": "choice", "passed": True}],
            "text_rule": None,
        },
    }


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


def grade_case_returns_native_report_for_decoded_candidate() -> None:
    report = grading.grade_case(
        case_id="small-decision",
        response='{"choice":"A","reason":"Cheap"}',
        changed_files=("workspace/unexpected.txt",),
    )
    assert report.correctness.answer is not None
    assert not report.correctness.passed
    assert not report.scope.passed
    assert dict(report.scores) == grading.score_case(
        case_id="small-decision",
        response='{"choice":"A","reason":"Cheap"}',
        changed_files=("workspace/unexpected.txt",),
    )


def detailed_code_grade_preserves_harness_failure() -> None:
    with pytest.raises(GradingError, match="offline"):
        grading.grade_case(
            case_id="clear-task",
            response="",
            changed_files=(),
            verification=Verification.HarnessError(detail="offline"),
        )


def grade_metadata_retains_code_and_absent_reports() -> None:
    report = grading.grade_case(
        case_id="clear-task", response="", changed_files=(), verification=Verification.Passed()
    )
    assert scoring.grade_details(report) == {
        "correctness": True,
        "unexpected_files": [],
        "answer": None,
    }
    assert scoring.grade_details(None) is None
