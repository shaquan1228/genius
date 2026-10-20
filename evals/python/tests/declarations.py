"""Native declarations retain validation and separate public/private projections."""

import json
from collections.abc import Callable, Sequence

import pytest

from evals.python import datasets
from evals.python.tests.projections import reference as private_reference
from evals.python.tests.projections import verifier
from kernel import (
    Case,
    Criterion,
    File,
    Instruction,
    Reference,
    Rubric,
    Task,
    TextRule,
    Value,
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
    fixture: Sequence[File] | None = None,
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
    files: Sequence[File] | None = None,
    tools: Sequence[File] | None = None,
    command: Sequence[str] | None = None,
    stdin: str | None = None,
    timeout_seconds: int | None = None,
) -> Verifier:
    return Verifier(
        inputs=_override(inputs, original=value.inputs),
        files=_override(files, original=value.files),
        tools=_override(tools, original=value.tools),
        command=_override(command, original=value.command),
        stdin=_override(stdin, original=value.stdin),
        timeout_seconds=_override(timeout_seconds, original=value.timeout_seconds),
    )


def _files(value: Sequence[File]) -> dict[str, str]:
    return {file.path: file.contents for file in value}


def _declaration(*, code: bool = True) -> Task:
    criterion: Criterion.Value
    if code:
        criterion = Criterion.Code(
            verifier=Verifier(
                inputs=("main.py",),
                files=[File(path="verify.py", contents="private assertions")],
                tools=[File(path="check.sh", contents="visible helper")],
                command=("python3", "verify.py"),
                stdin="private stdin",
                timeout_seconds=30,
            )
        )
    else:
        criterion = Criterion.Answer(
            rubric=Rubric(
                expected=[("choice", Value.String(value="B")), ("safe", Value.Bool(value=True))],
                text_rule=TextRule(field="reason", min_words=1, max_words=5),
            )
        )
    return Task.create(
        id="external",
        fixture=[File(path="main.py", contents="broken")],
        instruction=Instruction(skill="reasoning", prompt="Fix it: é"),
        criterion=criterion,
        allowed_files=("main.py",),
        reference=Reference(
            edits=[File(path="main.py", contents="fixed")],
            completion=Value.String(value="done")
            if code
            else Value.Record(
                fields=[("choice", Value.String(value="B")), ("safe", Value.Bool(value=True))]
            ),
        ),
    )


@pytest.mark.parametrize("code", [True, False])
def external_declarations_preserve_public_projection(*, code: bool) -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(code=code),))
    (case,) = datasets.list_cases(selection=dataset)
    assert isinstance(case, Case)
    assert (case.case_id, case.skill, case.prompt) == ("external", "reasoning", "Fix it: é")
    assert _files(case.files) == (
        {"main.py": "broken", "check.sh": "visible helper"} if code else {"main.py": "broken"}
    )
    assert (hasattr(case, "criterion"), hasattr(case, "reference")) == (False, False)


def code_declarations_preserve_private_checks() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(),))
    checks = verifier("external", selection=dataset)
    assert checks is not None
    assert _files(checks.files) == {"verify.py": "private assertions"}
    assert _files(checks.tools) == {"check.sh": "visible helper"}
    assert (checks.stdin, tuple(checks.inputs)) == ("private stdin", ("main.py",))


@pytest.mark.parametrize("code", [True, False])
def declarations_preserve_private_reference_edits(*, code: bool) -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(code=code),))
    reference = private_reference("external", selection=dataset)
    assert _files(reference.edits) == {"main.py": "fixed"}


def answer_declarations_preserve_typed_completion_fields() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(code=False),))
    completion = private_reference("external", selection=dataset).completion
    assert isinstance(completion, Value.Record)
    choice, safe = dict(completion.fields)["choice"], dict(completion.fields)["safe"]
    assert isinstance(choice, Value.String)
    assert isinstance(safe, Value.Bool)
    assert (choice.value, safe.value) == ("B", True)


def answer_declarations_do_not_supply_executable_checks() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(code=False),))
    assert verifier("external", selection=dataset) is None


def generic_declarations_do_not_supply_cases_or_download_metadata() -> None:
    assert datasets.list_cases(selection=datasets.compile_dataset(cases=())) == ()


@pytest.mark.parametrize(
    "invalid",
    [
        lambda c: _copy_case(c, allowed_files=()),
        lambda c: _copy_case(c, fixture=[]),
        lambda c: _copy_case(
            c, criterion=Criterion.Answer(rubric=Rubric(expected=[], text_rule=None))
        ),
        lambda c: _copy_case(
            c,
            criterion=Criterion.Answer(
                rubric=Rubric(
                    expected=[("choice", Value.String(value="B"))],
                    text_rule=TextRule(field="choice", min_words=0, max_words=2),
                )
            ),
        ),
        lambda c: _copy_case(
            c,
            reference=Reference(
                edits=[File(path="outside.py", contents="unauthorized")],
                completion=Value.Null(),
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
        ("files", lambda: [File(path="main.py", contents="overlap")]),
        ("tools", lambda: [File(path="../secret", contents="bad")]),
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
            criterion=Criterion.Code(
                verifier=Verifier(**{**fields, field: value() if callable(value) else value})
            ),
        )


@pytest.mark.parametrize(("minimum", "maximum"), [(-1, 2), (3, 2)])
def answer_constructor_rules_fail_closed(minimum: int, *, maximum: int) -> None:
    with pytest.raises(DomainValidationError, match="text rule"):
        _copy_case(
            _declaration(code=False),
            criterion=Criterion.Answer(
                rubric=Rubric(
                    expected=[],
                    text_rule=TextRule(field="reason", min_words=minimum, max_words=maximum),
                )
            ),
        )


def native_fields_retain_immutable_snapshots() -> None:
    initial = [File(path="main.py", contents="broken")]
    task = _copy_case(_declaration(), fixture=initial)
    initial[0] = File(path="main.py", contents="changed")
    assert _files(task.fixture) == {"main.py": "broken"}
    with pytest.raises((AttributeError, TypeError)):
        task.fixture = []  # type: ignore[misc]
    artifacts = [File(path="verify.py", contents="private assertions")]
    assert isinstance(task.criterion, Criterion.Code)
    checks = _copy_verifier(task.criterion.verifier, files=artifacts)
    artifacts.clear()
    assert _files(checks.files) == {"verify.py": "private assertions"}


@pytest.mark.parametrize(
    "criterion",
    [
        Criterion.Answer(
            rubric=Rubric(expected=[("choice", Value.String(value="B"))], text_rule=None)
        ),
        Criterion.Answer(
            rubric=Rubric(expected=[], text_rule=TextRule(field="reason", min_words=1, max_words=5))
        ),
    ],
)
def answer_construction_supports_each_optional_rule_shape(criterion: Criterion.Value) -> None:
    dataset = datasets.compile_dataset(
        cases=(_copy_case(_declaration(code=False), criterion=criterion),)
    )
    assert datasets.list_cases(selection=dataset)[0].case_id == "external"


def _reference_files(value: Reference) -> dict[str, str]:
    return _files(value.edits)


def _reference_text(value: Reference) -> str:
    from evals.python.integrations.inspect.scoring import plain  # noqa: PLC0415

    completion = value.completion
    if isinstance(completion, Value.String):
        return completion.value
    return json.dumps(plain(completion))


def _public_snapshot(
    cases: Sequence[Case],
) -> tuple[tuple[str, str, str, dict[str, str]], ...]:
    return tuple((case.case_id, case.skill, case.prompt, _files(case.files)) for case in cases)
