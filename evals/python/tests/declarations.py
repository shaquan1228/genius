"""Native declarations retain validation and separate public/private projections."""
# Native boolean variants have a single positional payload.
# ruff: noqa: FBT003

import json
from collections.abc import Callable, Sequence

import pytest

from evals.python import queries
from evals.python.tests.projections import reference as private_reference
from evals.python.tests.projections import verifier
from kernel import Ast, Fixture, InvalidArgument


def _override[T](value: T | None, *, original: T) -> T:
    return original if value is None else value


def _copy_case(  # noqa: PLR0913 - Reconstruct the actual native record fields.
    value: Ast.task,
    *,
    id: str | None = None,
    fixture: Ast.fixture | None = None,
    instruction: Ast.instruction | None = None,
    criterion: Ast.criterion | None = None,
    allowed_files: Sequence[str] | None = None,
    reference: Ast.reference | None = None,
) -> Ast.task:
    return Ast.task(
        id=_override(id, original=value.id),
        fixture=_override(fixture, original=value.fixture),
        instruction=_override(instruction, original=value.instruction),
        criterion=_override(criterion, original=value.criterion),
        allowed_files=_override(allowed_files, original=value.allowed_files),
        reference=_override(reference, original=value.reference),
    )


def _copy_verifier(  # noqa: PLR0913 - Reconstruct the actual native record fields.
    value: Ast.verifier,
    *,
    inputs: Sequence[str] | None = None,
    files: Sequence[tuple[str, Ast.content]] | None = None,
    tools: Sequence[tuple[str, Ast.content]] | None = None,
    command: Sequence[str] | None = None,
    stdin: str | None = None,
    timeout_seconds: int | None = None,
) -> Ast.verifier:
    return Ast.verifier(
        inputs=_override(inputs, original=value.inputs),
        files=_override(files, original=value.files),
        tools=_override(tools, original=value.tools),
        command=_override(command, original=value.command),
        stdin=_override(stdin, original=value.stdin),
        timeout_seconds=_override(timeout_seconds, original=value.timeout_seconds),
    )


def _files(value: Sequence[tuple[str, Ast.content]]) -> dict[str, str]:
    result = {}
    for name, content in value:
        assert isinstance(content, Ast.Inline)
        result[name] = content[0]
    return result


def _declaration(*, code: bool = True) -> Ast.task:
    criterion: Ast.criterion
    if code:
        criterion = Ast.Code(
            Ast.verifier(
                inputs=("main.py",),
                files=[("verify.py", Ast.Inline("private assertions"))],
                tools=[("check.sh", Ast.Inline("visible helper"))],
                command=("python3", "verify.py"),
                stdin="private stdin",
                timeout_seconds=30,
            )
        )
    else:
        criterion = Ast.Answer(
            Ast.answer(
                expected=[("choice", Ast.String("B")), ("safe", Ast.Bool(True))],
                text_rule=Ast.text_rule(field="reason", min_words=1, max_words=5),
            )
        )
    return Ast.task(
        id="external",
        fixture=Fixture.of_files([("main.py", "broken")]),
        instruction=Ast.instruction(skill="reasoning", prompt="Fix it: é"),
        criterion=criterion,
        allowed_files=("main.py",),
        reference=Ast.reference(
            edits=Fixture.of_files([("main.py", "fixed")]),
            completion=Ast.Plain("done")
            if code
            else Ast.Structured([("choice", Ast.String("B")), ("safe", Ast.Bool(True))]),
        ),
    )


@pytest.mark.parametrize("code", [True, False])
def external_declarations_preserve_public_projection(*, code: bool) -> None:
    dataset = queries.compile_dataset(cases=(_declaration(code=code),))
    (case,) = queries.list_cases(selection=dataset)
    assert isinstance(case, Ast.case)
    assert (case.id, case.skill, case.prompt) == ("external", "reasoning", "Fix it: é")
    assert _files(case.files) == (
        {"main.py": "broken", "check.sh": "visible helper"} if code else {"main.py": "broken"}
    )
    assert (hasattr(case, "criterion"), hasattr(case, "reference")) == (False, False)


def code_declarations_preserve_private_checks_and_resolve_resources() -> None:
    dataset = queries.compile_dataset(cases=(_declaration(),))
    checks = verifier("external", selection=dataset)
    assert checks is not None
    assert _files(checks.files) == {"verify.py": "private assertions"}
    assert _files(checks.tools) == {"check.sh": "visible helper"}
    assert (checks.stdin, tuple(checks.inputs)) == ("private stdin", ("main.py",))


def missing_private_resource_fails_at_resolution() -> None:
    definition = _declaration()
    assert isinstance(definition.criterion, Ast.Code)
    checks = _copy_verifier(
        definition.criterion[0], files=[("verify.py", Ast.Resource("missing.py"))]
    )
    definition = _copy_case(definition, criterion=Ast.Code(checks))
    with pytest.raises(KeyError, match=r"missing\.py"):
        queries.compile_dataset(cases=(definition,))


@pytest.mark.parametrize("code", [True, False])
def declarations_preserve_private_reference_edits(*, code: bool) -> None:
    dataset = queries.compile_dataset(cases=(_declaration(code=code),))
    reference = private_reference("external", selection=dataset)
    assert dict(Fixture.files(reference.edits)) == {"main.py": "fixed"}


def code_declarations_preserve_plain_completion() -> None:
    dataset = queries.compile_dataset(cases=(_declaration(),))
    completion = private_reference("external", selection=dataset).completion
    assert isinstance(completion, Ast.Plain)
    assert completion[0] == "done"


def answer_declarations_preserve_typed_completion_fields() -> None:
    dataset = queries.compile_dataset(cases=(_declaration(code=False),))
    completion = private_reference("external", selection=dataset).completion
    assert isinstance(completion, Ast.Structured)
    fields = dict(completion[0])
    assert (isinstance(fields["choice"], Ast.String), fields["choice"][0]) == (True, "B")
    assert (isinstance(fields["safe"], Ast.Bool), fields["safe"][0]) == (True, True)


def answer_declarations_do_not_supply_executable_checks() -> None:
    dataset = queries.compile_dataset(cases=(_declaration(code=False),))
    assert verifier("external", selection=dataset) is None


@pytest.mark.parametrize("code", [True, False])
def imported_declarations_use_existing_grading(*, code: bool) -> None:
    dataset = queries.compile_dataset(cases=(_declaration(code=code),))
    assert queries.score_case(
        selection=dataset,
        case_id="external",
        response='{"choice":"B","safe":true,"reason":"clear"}',
        changed_files=("workspace/main.py",),
        verification=Ast.Passed(),
    ) == {"correctness": True, "scope": True}


def generic_declarations_do_not_supply_cases_or_download_metadata() -> None:
    assert queries.list_cases(selection=queries.compile_dataset(cases=())) == ()


@pytest.mark.parametrize(
    "invalid",
    [
        lambda c: _copy_case(c, allowed_files=()),
        lambda c: _copy_case(c, fixture=Fixture.empty),
        lambda c: _copy_case(c, criterion=Ast.Answer(Ast.answer(expected=[], text_rule=None))),
        lambda c: _copy_case(
            c,
            criterion=Ast.Answer(
                Ast.answer(
                    expected=[("choice", Ast.String("B"))],
                    text_rule=Ast.text_rule(field="choice", min_words=0, max_words=2),
                )
            ),
        ),
        lambda c: _copy_case(
            c,
            reference=Ast.reference(
                edits=Fixture.of_files([("outside.py", "unauthorized")]),
                completion=Ast.Plain(""),
            ),
        ),
    ],
)
def kernel_constructors_validate_raw_declarations(
    invalid: Callable[[Ast.task], Ast.task],
) -> None:
    with pytest.raises(InvalidArgument):
        queries.compile_dataset(cases=(invalid(_declaration()),))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("inputs", ()),
        ("inputs", ("missing.py",)),
        ("command", ()),
        ("timeout_seconds", 0),
        ("files", [("main.py", Ast.Inline("overlap"))]),
        ("tools", [("../secret", Ast.Inline("bad"))]),
    ],
)
def nested_constructor_rules_fail_closed(field: str, *, value: object) -> None:
    definition = _declaration()
    assert isinstance(definition.criterion, Ast.Code)
    old = definition.criterion[0]
    fields = {
        name: getattr(old, name)
        for name in ("inputs", "files", "tools", "command", "stdin", "timeout_seconds")
    }
    fields[field] = value
    checks = Ast.verifier(**fields)
    with pytest.raises(InvalidArgument):
        queries.compile_dataset(cases=(_copy_case(definition, criterion=Ast.Code(checks)),))


@pytest.mark.parametrize(("minimum", "maximum"), [(-1, 2), (3, 2)])
def answer_constructor_rules_fail_closed(minimum: int, *, maximum: int) -> None:
    criterion = Ast.Answer(
        Ast.answer(
            expected=[],
            text_rule=Ast.text_rule(field="reason", min_words=minimum, max_words=maximum),
        )
    )
    with pytest.raises(InvalidArgument):
        queries.compile_dataset(cases=(_copy_case(_declaration(code=False), criterion=criterion),))


def native_fields_retain_immutable_snapshots() -> None:
    fields = [("choice", Ast.String("B"))]
    answer = Ast.answer(expected=fields, text_rule=None)
    fields.clear()
    assert len(answer.expected) == 1
    with pytest.raises((AttributeError, TypeError)):
        answer.expected = []  # type: ignore[misc]
    initial = [("main.py", "broken")]
    fixture = Fixture.of_files(initial)
    initial[0] = ("main.py", "changed")
    assert dict(Fixture.files(fixture)) == {"main.py": "broken"}
    artifacts = [("verify.py", Ast.Inline("private assertions"))]
    definition = _declaration()
    assert isinstance(definition.criterion, Ast.Code)
    checks = _copy_verifier(definition.criterion[0], files=artifacts)
    artifacts.clear()
    assert _files(checks.files) == {"verify.py": "private assertions"}


@pytest.mark.parametrize(
    "criterion",
    [
        Ast.Answer(Ast.answer(expected=[("choice", Ast.String("B"))], text_rule=None)),
        Ast.Answer(
            Ast.answer(
                expected=[], text_rule=Ast.text_rule(field="reason", min_words=1, max_words=5)
            )
        ),
    ],
)
def answer_construction_supports_each_optional_rule_shape(criterion: Ast.criterion) -> None:
    dataset = queries.compile_dataset(
        cases=(_copy_case(_declaration(code=False), criterion=criterion),)
    )
    assert queries.list_cases(selection=dataset)[0].id == "external"


def _reference_files(value: Ast.reference) -> dict[str, str]:
    return dict(Fixture.files(value.edits))


def _reference_text(value: Ast.reference) -> str:
    completion = value.completion
    if isinstance(completion, Ast.Plain):
        return completion[0]
    assert isinstance(completion, Ast.Structured)
    return json.dumps({name: scalar[0] for name, scalar in completion[0]})


def _public_snapshot(
    cases: Sequence[Ast.case],
) -> tuple[tuple[str, str, str, dict[str, str]], ...]:
    return tuple((case.id, case.skill, case.prompt, _files(case.files)) for case in cases)
