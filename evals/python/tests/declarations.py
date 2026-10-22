"""Native declarations retain validation and separate public/private projections."""

import json
from collections.abc import Callable, Sequence

import pytest
from kernel import (
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
from pydantic import ValidationError

from evals.python import datasets
from evals.python.datasets import Case, Declaration
from evals.python.tests.projections import reference as private_reference
from evals.python.tests.projections import verifier


def _override[T](value: T | None, *, original: T) -> T:
    return original if value is None else value


def _copy_case(  # noqa: PLR0913 - Reconstruct the actual native record fields.
    value: Declaration,
    *,
    id: str | None = None,
    fixture: Sequence[File] | None = None,
    instruction: Instruction | None = None,
    criterion: Criterion | None = None,
    allowed_files: Sequence[str] | None = None,
    reference: Reference | None = None,
) -> Declaration:
    task = value.task
    return Declaration(
        skill=value.skill,
        task=Task(
            id=_override(id, original=task.id),
            fixture=_override(fixture, original=task.fixture),
            instruction=_override(instruction, original=task.instruction),
            criterion=_override(criterion, original=task.criterion),
            allowed_files=_override(allowed_files, original=task.allowed_files),
            reference=_override(reference, original=task.reference),
        ),
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


def _declaration(*, code: bool = True) -> Declaration:
    if code:
        criterion = Criterion.code(
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
        criterion = Criterion.answer(
            rubric=Rubric(
                expected=[
                    ("choice", Value.from_python(value="B")),
                    ("safe", Value.from_python(value=True)),
                ],
                text_rule=TextRule(field="reason", min_words=1, max_words=5),
            )
        )
    return Declaration(
        skill="reasoning",
        task=Task(
            id="external",
            fixture=[File(path="main.py", contents="broken")],
            instruction=Instruction(prompt="Fix it: é"),
            criterion=criterion,
            allowed_files=("main.py",),
            reference=Reference(
                edits=[File(path="main.py", contents="fixed")],
                completion=Value.from_python(
                    value="done" if code else {"choice": "B", "safe": True}
                ),
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
    assert completion.kind == "record"
    choice, safe = dict(completion.fields)["choice"], dict(completion.fields)["safe"]
    assert (choice.kind, safe.kind) == ("string", "bool")
    assert (choice.scalar, safe.scalar) == ("B", True)


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
            c, criterion=Criterion.answer(rubric=Rubric(expected=[], text_rule=None))
        ),
        lambda c: _copy_case(
            c,
            criterion=Criterion.answer(
                rubric=Rubric(
                    expected=[("choice", Value.from_python(value="B"))],
                    text_rule=TextRule(field="choice", min_words=0, max_words=2),
                )
            ),
        ),
        lambda c: _copy_case(
            c,
            reference=Reference(
                edits=[File(path="outside.py", contents="unauthorized")],
                completion=Value.from_python(value=None),
            ),
        ),
        lambda c: Declaration(skill="Reasoning", task=c.task),
    ],
)
def kernel_constructors_validate_raw_declarations(
    invalid: Callable[[Declaration], Declaration],
) -> None:
    with pytest.raises((DomainValidationError, ValidationError)):
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
    old = definition.task.checks()
    assert old is not None
    fields = {
        name: getattr(old, name)
        for name in ("inputs", "files", "tools", "command", "stdin", "timeout_seconds")
    }
    with pytest.raises(DomainValidationError):
        _copy_case(
            definition,
            criterion=Criterion.code(
                verifier=Verifier(**{**fields, field: value() if callable(value) else value})
            ),
        )


@pytest.mark.parametrize(("minimum", "maximum"), [(-1, 2), (3, 2)])
def answer_constructor_rules_fail_closed(minimum: int, *, maximum: int) -> None:
    with pytest.raises(DomainValidationError, match="text rule"):
        _copy_case(
            _declaration(code=False),
            criterion=Criterion.answer(
                rubric=Rubric(
                    expected=[],
                    text_rule=TextRule(field="reason", min_words=minimum, max_words=maximum),
                )
            ),
        )


def native_fields_retain_immutable_snapshots() -> None:
    initial = [File(path="main.py", contents="broken")]
    task = _copy_case(_declaration(), fixture=initial).task
    initial[0] = File(path="main.py", contents="changed")
    assert _files(task.fixture) == {"main.py": "broken"}
    with pytest.raises((AttributeError, TypeError)):
        task.fixture = ()  # type: ignore[misc]
    artifacts = [File(path="verify.py", contents="private assertions")]
    original = task.checks()
    assert original is not None
    checks = _copy_verifier(original, files=artifacts)
    artifacts.clear()
    assert _files(checks.files) == {"verify.py": "private assertions"}


@pytest.mark.parametrize(
    "criterion",
    [
        Criterion.answer(
            rubric=Rubric(expected=[("choice", Value.from_python(value="B"))], text_rule=None)
        ),
        Criterion.answer(
            rubric=Rubric(expected=[], text_rule=TextRule(field="reason", min_words=1, max_words=5))
        ),
    ],
)
def answer_construction_supports_each_optional_rule_shape(criterion: Criterion) -> None:
    dataset = datasets.compile_dataset(
        cases=(_copy_case(_declaration(code=False), criterion=criterion),)
    )
    assert datasets.list_cases(selection=dataset)[0].case_id == "external"


def _reference_files(value: Reference) -> dict[str, str]:
    return _files(value.edits)


def _reference_text(value: Reference) -> str:
    from evals.python.integrations.inspect.scoring import plain  # noqa: PLC0415

    completion = value.completion
    if completion.kind == "string":
        return str(completion.scalar)
    return json.dumps(plain(completion))


def _public_snapshot(
    cases: Sequence[Case],
) -> tuple[tuple[str, str, str, dict[str, str]], ...]:
    return tuple((case.case_id, case.skill, case.prompt, _files(case.files)) for case in cases)
