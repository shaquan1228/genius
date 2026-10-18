"""Native declarations retain validation and separate public/private projections."""

import json
from collections.abc import Callable, Sequence

import pytest

from evals.python import datasets
from evals.python.tests.projections import reference as private_reference
from evals.python.tests.projections import verifier
from kernel import (
    Artifact,
    Case,
    Completion,
    Content,
    Criterion,
    File,
    Fixture,
    Instruction,
    Reference,
    Response,
    ResponseField,
    ResponseValue,
    Rubric,
    Task,
    TextRule,
    Verifier,
)
from kernel import (
    ValidationError as DomainValidationError,
)


def _override[T](value: T | None, *, original: T) -> T:
    return original if value is None else value


def _copy_case(  # noqa: PLR0913 - Reconstruct the actual native record fields.
    value: Task,
    *,
    id: str | None = None,
    fixture: Fixture | None = None,
    instruction: Instruction | None = None,
    criterion: Criterion.Value | None = None,
    allowed_files: Sequence[str] | None = None,
    reference: Reference | None = None,
) -> Task:
    return Task.create(
        id=_override(id, original=value.id),
        fixture=_override(fixture, original=value.fixture),
        instruction=_override(instruction, original=value.instruction),
        criterion=_override(criterion, original=value.criterion),
        allowed_files=_override(allowed_files, original=value.allowed_files),
        reference=_override(reference, original=value.reference),
    )


def _copy_verifier(  # noqa: PLR0913 - Reconstruct the actual native record fields.
    value: Verifier,
    *,
    inputs: Sequence[str] | None = None,
    files: Sequence[Artifact] | None = None,
    tools: Sequence[Artifact] | None = None,
    command: Sequence[str] | None = None,
    stdin: str | None = None,
    timeout_seconds: int | None = None,
) -> Verifier:
    return Verifier.create(
        inputs=_override(inputs, original=value.inputs),
        files=_override(files, original=value.files),
        tools=_override(tools, original=value.tools),
        command=_override(command, original=value.command),
        stdin=_override(stdin, original=value.stdin),
        timeout_seconds=_override(timeout_seconds, original=value.timeout_seconds),
    )


def _files(value: Sequence[Artifact]) -> dict[str, str]:
    result = {}
    for artifact in value:
        assert isinstance(artifact.content, Content.Inline)
        result[artifact.path] = artifact.content.text
    return result


def _declaration(*, code: bool = True) -> Task:
    criterion: Criterion.Value
    if code:
        criterion = Criterion.create(
            code=Verifier.create(
                inputs=("main.py",),
                files=[
                    Artifact.create(
                        path="verify.py", content=Content.create(inline="private assertions")
                    )
                ],
                tools=[
                    Artifact.create(
                        path="check.sh", content=Content.create(inline="visible helper")
                    )
                ],
                command=("python3", "verify.py"),
                stdin="private stdin",
                timeout_seconds=30,
            )
        )
    else:
        criterion = Criterion.create(
            answer=Rubric.create(
                expected=Response.create(
                    fields=[
                        ResponseField.create(name="choice", value=ResponseValue.create(string="B")),
                        ResponseField.create(name="safe", value=ResponseValue.create(bool=True)),
                    ]
                ),
                text_rule=TextRule.create(field="reason", min_words=1, max_words=5),
            )
        )
    return Task.create(
        id="external",
        fixture=Fixture.create(files=[File.create(path="main.py", contents="broken")]),
        instruction=Instruction.create(skill="reasoning", prompt="Fix it: é"),
        criterion=criterion,
        allowed_files=("main.py",),
        reference=Reference.create(
            edits=Fixture.create(files=[File.create(path="main.py", contents="fixed")]),
            completion=Completion.create(plain="done")
            if code
            else Completion.create(
                structured=Response.create(
                    fields=[
                        ResponseField.create(name="choice", value=ResponseValue.create(string="B")),
                        ResponseField.create(name="safe", value=ResponseValue.create(bool=True)),
                    ]
                )
            ),
        ),
    )


@pytest.mark.parametrize("code", [True, False])
def external_declarations_preserve_public_projection(*, code: bool) -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(code=code),))
    (case,) = datasets.list_cases(selection=dataset)
    assert isinstance(case, Case)
    assert (case.id, case.skill, case.prompt) == ("external", "reasoning", "Fix it: é")
    assert _files(case.files) == (
        {"main.py": "broken", "check.sh": "visible helper"} if code else {"main.py": "broken"}
    )
    assert (hasattr(case, "criterion"), hasattr(case, "reference")) == (False, False)


def code_declarations_preserve_private_checks_and_resolve_resources() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(),))
    checks = verifier("external", selection=dataset)
    assert checks is not None
    assert _files(checks.files) == {"verify.py": "private assertions"}
    assert _files(checks.tools) == {"check.sh": "visible helper"}
    assert (checks.stdin, tuple(checks.inputs)) == ("private stdin", ("main.py",))


def missing_private_resource_fails_at_resolution() -> None:
    definition = _declaration()
    assert isinstance(definition.criterion, Criterion.Code)
    checks = _copy_verifier(
        definition.criterion.verifier,
        files=[Artifact.create(path="verify.py", content=Content.create(resource="missing.py"))],
    )
    definition = _copy_case(definition, criterion=Criterion.create(code=checks))
    with pytest.raises(DomainValidationError, match=r"missing\.py"):
        datasets.compile_dataset(cases=(definition,))


@pytest.mark.parametrize("code", [True, False])
def declarations_preserve_private_reference_edits(*, code: bool) -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(code=code),))
    reference = private_reference("external", selection=dataset)
    assert {file.path: file.contents for file in Fixture.files(fixture=reference.edits)} == {
        "main.py": "fixed"
    }


def code_declarations_preserve_plain_completion() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(),))
    completion = private_reference("external", selection=dataset).completion
    assert isinstance(completion, Completion.Plain)
    assert completion.text == "done"


def answer_declarations_preserve_typed_completion_fields() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(code=False),))
    completion = private_reference("external", selection=dataset).completion
    assert isinstance(completion, Completion.Structured)
    fields = {field.name: field.value for field in completion.response.fields}
    assert (isinstance(fields["choice"], ResponseValue.String), fields["choice"].value) == (
        True,
        "B",
    )
    assert (isinstance(fields["safe"], ResponseValue.Bool), fields["safe"].value) == (True, True)


def answer_declarations_do_not_supply_executable_checks() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(code=False),))
    assert verifier("external", selection=dataset) is None


def generic_declarations_do_not_supply_cases_or_download_metadata() -> None:
    assert datasets.list_cases(selection=datasets.compile_dataset(cases=())) == ()


@pytest.mark.parametrize(
    "invalid",
    [
        lambda c: _copy_case(c, allowed_files=()),
        lambda c: _copy_case(c, fixture=Fixture.create(files=[])),
        lambda c: _copy_case(
            c,
            criterion=Criterion.create(
                answer=Rubric.create(expected=Response.create(fields=[]), text_rule=None)
            ),
        ),
        lambda c: _copy_case(
            c,
            criterion=Criterion.create(
                answer=Rubric.create(
                    expected=Response.create(
                        fields=[
                            ResponseField.create(
                                name="choice", value=ResponseValue.create(string="B")
                            )
                        ]
                    ),
                    text_rule=TextRule.create(field="choice", min_words=0, max_words=2),
                )
            ),
        ),
        lambda c: _copy_case(
            c,
            reference=Reference.create(
                edits=Fixture.create(
                    files=[File.create(path="outside.py", contents="unauthorized")]
                ),
                completion=Completion.create(plain=""),
            ),
        ),
    ],
)
def kernel_constructors_validate_raw_declarations(
    invalid: Callable[[Task], Task],
) -> None:
    with pytest.raises(DomainValidationError):
        datasets.compile_dataset(cases=(invalid(_declaration()),))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("inputs", ()),
        ("inputs", ("missing.py",)),
        ("command", ()),
        ("timeout_seconds", 0),
        (
            "files",
            lambda: [Artifact.create(path="main.py", content=Content.create(inline="overlap"))],
        ),
        (
            "tools",
            lambda: [Artifact.create(path="../secret", content=Content.create(inline="bad"))],
        ),
    ],
)
def nested_constructor_rules_fail_closed(field: str, *, value: object) -> None:
    definition = _declaration()
    assert isinstance(definition.criterion, Criterion.Code)
    old = definition.criterion.verifier
    fields = {
        name: getattr(old, name)
        for name in ("inputs", "files", "tools", "command", "stdin", "timeout_seconds")
    }
    with pytest.raises(DomainValidationError):
        _copy_case(
            definition,
            criterion=Criterion.create(
                code=Verifier.create(**{**fields, field: value() if callable(value) else value})
            ),
        )


@pytest.mark.parametrize(("minimum", "maximum"), [(-1, 2), (3, 2)])
def answer_constructor_rules_fail_closed(minimum: int, *, maximum: int) -> None:
    with pytest.raises(DomainValidationError):
        TextRule.create(field="reason", min_words=minimum, max_words=maximum)


def native_fields_retain_immutable_snapshots() -> None:
    fields = [ResponseField.create(name="choice", value=ResponseValue.create(string="B"))]
    answer = Rubric.create(expected=Response.create(fields=fields), text_rule=None)
    fields.clear()
    assert len(answer.expected.fields) == 1
    with pytest.raises((AttributeError, TypeError)):
        answer.expected = []  # type: ignore[misc, assignment]
    initial = [File.create(path="main.py", contents="broken")]
    fixture = Fixture.create(files=initial)
    initial[0] = File.create(path="main.py", contents="changed")
    assert {file.path: file.contents for file in Fixture.files(fixture=fixture)} == {
        "main.py": "broken"
    }
    artifacts = [
        Artifact.create(path="verify.py", content=Content.create(inline="private assertions"))
    ]
    definition = _declaration()
    assert isinstance(definition.criterion, Criterion.Code)
    checks = _copy_verifier(definition.criterion.verifier, files=artifacts)
    artifacts.clear()
    assert _files(checks.files) == {"verify.py": "private assertions"}


@pytest.mark.parametrize(
    "criterion",
    [
        Criterion.create(
            answer=Rubric.create(
                expected=Response.create(
                    fields=[
                        ResponseField.create(name="choice", value=ResponseValue.create(string="B"))
                    ]
                ),
                text_rule=None,
            )
        ),
        Criterion.create(
            answer=Rubric.create(
                expected=Response.create(fields=[]),
                text_rule=TextRule.create(field="reason", min_words=1, max_words=5),
            )
        ),
    ],
)
def answer_construction_supports_each_optional_rule_shape(criterion: Criterion.Value) -> None:
    dataset = datasets.compile_dataset(
        cases=(_copy_case(_declaration(code=False), criterion=criterion),)
    )
    assert datasets.list_cases(selection=dataset)[0].id == "external"


def _reference_files(value: Reference) -> dict[str, str]:
    return {file.path: file.contents for file in Fixture.files(fixture=value.edits)}


def _reference_text(value: Reference) -> str:
    completion = value.completion
    if isinstance(completion, Completion.Plain):
        return completion.text
    assert isinstance(completion, Completion.Structured)
    return json.dumps({field.name: field.value.value for field in completion.response.fields})


def _public_snapshot(
    cases: Sequence[Case],
) -> tuple[tuple[str, str, str, dict[str, str]], ...]:
    return tuple((case.id, case.skill, case.prompt, _files(case.files)) for case in cases)
