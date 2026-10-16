"""Native declarations retain validation and separate public/private projections."""
# Native boolean variants have a single positional payload.
# ruff: noqa: FBT003

import json
from collections.abc import Callable, Sequence

import pytest

from evals.python import query
from evals.python.tests.projections import reference as private_reference
from evals.python.tests.projections import verifier
from kernel import InvalidArgument


def _copy_case(  # noqa: PLR0913 - Reconstruct the actual native record fields.
    value: query.Ast.case,
    *,
    id: str | None = None,
    fixture: query.Ast.fixture | None = None,
    instruction: query.Ast.instruction | None = None,
    criterion: query.Ast.criterion | None = None,
    allowed_files: Sequence[str] | None = None,
    reference: query.Ast.reference | None = None,
) -> query.Ast.case:
    return query.Ast.case(
        id=value.id if id is None else id,
        fixture=value.fixture if fixture is None else fixture,
        instruction=value.instruction if instruction is None else instruction,
        criterion=value.criterion if criterion is None else criterion,
        allowed_files=value.allowed_files if allowed_files is None else allowed_files,
        reference=value.reference if reference is None else reference,
    )


def _copy_verifier(  # noqa: PLR0913 - Reconstruct the actual native record fields.
    value: query.Ast.verifier,
    *,
    inputs: Sequence[str] | None = None,
    files: Sequence[tuple[str, query.Ast.content]] | None = None,
    tools: Sequence[tuple[str, query.Ast.content]] | None = None,
    command: Sequence[str] | None = None,
    stdin: str | None = None,
    timeout_seconds: int | None = None,
) -> query.Ast.verifier:
    return query.Ast.verifier(
        inputs=value.inputs if inputs is None else inputs,
        files=value.files if files is None else files,
        tools=value.tools if tools is None else tools,
        command=value.command if command is None else command,
        stdin=value.stdin if stdin is None else stdin,
        timeout_seconds=value.timeout_seconds if timeout_seconds is None else timeout_seconds,
    )


def _files(value: Sequence[tuple[str, query.Ast.content]]) -> dict[str, str]:
    result = {}
    for name, content in value:
        assert isinstance(content, query.Ast.Inline)
        result[name] = content[0]
    return result


def _declaration(*, code: bool = True) -> query.Ast.case:
    criterion: query.Ast.criterion
    if code:
        criterion = query.Ast.Code(
            query.Ast.verifier(
                inputs=("main.py",),
                files=[("verify.py", query.Ast.Inline("private assertions"))],
                tools=[("check.sh", query.Ast.Inline("visible helper"))],
                command=("python3", "verify.py"),
                stdin="private stdin",
                timeout_seconds=30,
            )
        )
    else:
        criterion = query.Ast.Answer(
            query.Ast.answer(
                expected=[("choice", query.Ast.String("B")), ("safe", query.Ast.Bool(True))],
                text_rule=query.Ast.text_rule(field="reason", min_words=1, max_words=5),
            )
        )
    return query.Ast.case(
        id="external",
        fixture=query.Fixture.of_files([("main.py", "broken")]),
        instruction=query.Ast.instruction(skill="reasoning", prompt="Fix it: é"),
        criterion=criterion,
        allowed_files=("main.py",),
        reference=query.Ast.reference(
            edits=query.Fixture.of_files([("main.py", "fixed")]),
            completion=query.Ast.Plain("done")
            if code
            else query.Ast.Structured(
                [("choice", query.Ast.String("B")), ("safe", query.Ast.Bool(True))]
            ),
        ),
    )


@pytest.mark.parametrize("code", [True, False])
def external_declarations_preserve_public_projection(*, code: bool) -> None:
    dataset = query.CompileDataset(cases=(_declaration(code=code),))
    (case,) = query.Cases(selection=dataset)
    assert isinstance(case, query.Ast.public_case)
    assert (case.id, case.skill, case.prompt) == ("external", "reasoning", "Fix it: é")
    assert _files(case.files) == (
        {"main.py": "broken", "check.sh": "visible helper"} if code else {"main.py": "broken"}
    )
    assert not hasattr(case, "criterion")
    assert not hasattr(case, "reference")


def code_declarations_preserve_private_checks_and_resolve_resources() -> None:
    dataset = query.CompileDataset(cases=(_declaration(),))
    checks = verifier("external", selection=dataset)
    assert checks is not None
    assert _files(checks.files) == {"verify.py": "private assertions"}
    assert _files(checks.tools) == {"check.sh": "visible helper"}
    assert (checks.stdin, tuple(checks.inputs)) == ("private stdin", ("main.py",))


def missing_private_resource_fails_at_resolution() -> None:
    definition = _declaration()
    assert isinstance(definition.criterion, query.Ast.Code)
    checks = _copy_verifier(
        definition.criterion[0], files=[("verify.py", query.Ast.Resource("missing.py"))]
    )
    definition = _copy_case(definition, criterion=query.Ast.Code(checks))
    with pytest.raises(KeyError, match=r"missing\.py"):
        query.CompileDataset(cases=(definition,))


@pytest.mark.parametrize("code", [True, False])
def declarations_preserve_private_references(*, code: bool) -> None:
    dataset = query.CompileDataset(cases=(_declaration(code=code),))
    reference = private_reference("external", selection=dataset)
    assert dict(query.Fixture.files(reference.edits)) == {"main.py": "fixed"}
    if code:
        assert isinstance(reference.completion, query.Ast.Plain)
        assert reference.completion[0] == "done"
    else:
        assert isinstance(reference.completion, query.Ast.Structured)
        fields = dict(reference.completion[0])
        assert isinstance(fields["choice"], query.Ast.String)
        assert fields["choice"][0] == "B"
        assert isinstance(fields["safe"], query.Ast.Bool)
        assert fields["safe"][0] is True


def answer_declarations_do_not_supply_executable_checks() -> None:
    dataset = query.CompileDataset(cases=(_declaration(code=False),))
    assert verifier("external", selection=dataset) is None


@pytest.mark.parametrize("code", [True, False])
def imported_declarations_use_existing_grading(*, code: bool) -> None:
    dataset = query.CompileDataset(cases=(_declaration(code=code),))
    assert query.GradeCase(
        selection=dataset,
        case_id="external",
        response='{"choice":"B","safe":true,"reason":"clear"}',
        changed_files=("workspace/main.py",),
        verification=query.Ast.Passed(),
    ) == {"correctness": True, "scope": True}


def generic_declarations_do_not_supply_cases_or_download_metadata() -> None:
    assert query.Cases(selection=query.CompileDataset(cases=())) == ()


@pytest.mark.parametrize(
    "invalid",
    [
        lambda c: _copy_case(c, allowed_files=()),
        lambda c: _copy_case(c, fixture=query.Fixture.empty),
        lambda c: _copy_case(
            c, criterion=query.Ast.Answer(query.Ast.answer(expected=[], text_rule=None))
        ),
        lambda c: _copy_case(
            c,
            criterion=query.Ast.Answer(
                query.Ast.answer(
                    expected=[("choice", query.Ast.String("B"))],
                    text_rule=query.Ast.text_rule(field="choice", min_words=0, max_words=2),
                )
            ),
        ),
        lambda c: _copy_case(
            c,
            reference=query.Ast.reference(
                edits=query.Fixture.of_files([("outside.py", "unauthorized")]),
                completion=query.Ast.Plain(""),
            ),
        ),
    ],
)
def kernel_constructors_validate_raw_declarations(
    invalid: Callable[[query.Ast.case], query.Ast.case],
) -> None:
    with pytest.raises(InvalidArgument):
        query.CompileDataset(cases=(invalid(_declaration()),))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("inputs", ()),
        ("inputs", ("missing.py",)),
        ("command", ()),
        ("timeout_seconds", 0),
        ("files", [("main.py", query.Ast.Inline("overlap"))]),
        ("tools", [("../secret", query.Ast.Inline("bad"))]),
    ],
)
def nested_constructor_rules_fail_closed(field: str, *, value: object) -> None:
    definition = _declaration()
    assert isinstance(definition.criterion, query.Ast.Code)
    old = definition.criterion[0]
    fields = {
        name: getattr(old, name)
        for name in ("inputs", "files", "tools", "command", "stdin", "timeout_seconds")
    }
    fields[field] = value
    checks = query.Ast.verifier(**fields)
    with pytest.raises(InvalidArgument):
        query.CompileDataset(cases=(_copy_case(definition, criterion=query.Ast.Code(checks)),))


@pytest.mark.parametrize(("minimum", "maximum"), [(-1, 2), (3, 2)])
def answer_constructor_rules_fail_closed(minimum: int, *, maximum: int) -> None:
    criterion = query.Ast.Answer(
        query.Ast.answer(
            expected=[],
            text_rule=query.Ast.text_rule(field="reason", min_words=minimum, max_words=maximum),
        )
    )
    with pytest.raises(InvalidArgument):
        query.CompileDataset(cases=(_copy_case(_declaration(code=False), criterion=criterion),))


def native_fields_retain_immutable_snapshots() -> None:
    fields = [("choice", query.Ast.String("B"))]
    answer = query.Ast.answer(expected=fields, text_rule=None)
    fields.clear()
    assert len(answer.expected) == 1
    with pytest.raises((AttributeError, TypeError)):
        answer.expected = []  # type: ignore[misc]
    initial = [("main.py", "broken")]
    fixture = query.Fixture.of_files(initial)
    initial[0] = ("main.py", "changed")
    assert dict(query.Fixture.files(fixture)) == {"main.py": "broken"}
    artifacts = [("verify.py", query.Ast.Inline("private assertions"))]
    definition = _declaration()
    assert isinstance(definition.criterion, query.Ast.Code)
    checks = _copy_verifier(definition.criterion[0], files=artifacts)
    artifacts.clear()
    assert _files(checks.files) == {"verify.py": "private assertions"}


@pytest.mark.parametrize(
    "criterion",
    [
        query.Ast.Answer(
            query.Ast.answer(expected=[("choice", query.Ast.String("B"))], text_rule=None)
        ),
        query.Ast.Answer(
            query.Ast.answer(
                expected=[], text_rule=query.Ast.text_rule(field="reason", min_words=1, max_words=5)
            )
        ),
    ],
)
def answer_construction_supports_each_optional_rule_shape(criterion: query.Ast.criterion) -> None:
    dataset = query.CompileDataset(
        cases=(_copy_case(_declaration(code=False), criterion=criterion),)
    )
    assert query.Cases(selection=dataset)[0].id == "external"


def _reference_files(value: query.Ast.reference) -> dict[str, str]:
    return dict(query.Fixture.files(value.edits))


def _reference_text(value: query.Ast.reference) -> str:
    completion = value.completion
    if isinstance(completion, query.Ast.Plain):
        return completion[0]
    assert isinstance(completion, query.Ast.Structured)
    return json.dumps({name: scalar[0] for name, scalar in completion[0]})


def _public_snapshot(
    cases: Sequence[query.Ast.public_case],
) -> tuple[tuple[str, str, str, dict[str, str]], ...]:
    return tuple((case.id, case.skill, case.prompt, _files(case.files)) for case in cases)
