"""External declarations retain canonical validation and separate projections."""

import json
import subprocess
from collections.abc import Mapping
from typing import cast

import pytest
from pydantic import ValidationError

from evals.python import catalog, query, transport


def declaration(*, code: bool = True) -> query.CaseDefinition:
    criterion: query.CodeCriterion | query.AnswerCriterion
    if code:
        criterion = query.CodeCriterion(
            verifier=query.VerifierDefinition(
                inputs=("main.py",),
                files={"verify.py": query.Inline(text="private assertions")},
                tools={"check.sh": query.Resource(name="verifier.py")},
                command=("python3", "verify.py"),
                stdin="private stdin",
                timeout_seconds=30,
            )
        )
    else:
        criterion = query.AnswerCriterion(
            expected={"choice": "B", "safe": True},
            text_rule=query.TextRule(field="reason", min_words=1, max_words=5),
        )
    return query.CaseDefinition(
        id="external",
        fixture={"main.py": "broken"},
        instruction=query.Instruction(skill="reasoning", prompt="Fix it: é"),
        criterion=criterion,
        allowed_files=("main.py",),
        reference=query.ReferenceDefinition(
            edits={"main.py": "fixed"},
            completion=(
                query.PlainCompletion(text="done")
                if code
                else query.StructuredCompletion(fields={"choice": "B", "safe": True})
            ),
        ),
    )


def sources() -> transport.Sources:
    return transport.sources(
        transport.Program(
            suite=transport.SUITE,
            adapter=transport.OCAML_ROOT / "datasets/declarations.ml",
            resources=catalog.DRIVERS,
        )
    )


@pytest.mark.parametrize("code", [True, False])
def external_declarations_preserve_public_projection_test(*, code: bool) -> None:
    (record,) = transport.encode_declarations((declaration(code=code),))
    (case,) = transport.cases(sources=sources(), records=(record,))
    public_files = {"main.py": "broken"}
    if code:
        public_files["check.sh"] = dict(catalog.sources().resources)["verifier.py"]
    assert case == query.Case(
        id="external", skill="reasoning", prompt="Fix it: é", files=public_files
    )
    assert set(case.model_dump()) == {"id", "skill", "prompt", "files"}


def code_declarations_preserve_private_checks_and_resolve_resources_test() -> None:
    (record,) = transport.encode_declarations((declaration(),))
    checks = transport.verifier(sources=sources(), case_id="external", record=record)
    assert checks is not None
    assert checks.files == {"verify.py": "private assertions"}
    assert checks.tools == {"check.sh": dict(catalog.sources().resources)["verifier.py"]}
    assert (checks.stdin, checks.inputs) == ("private stdin", ("main.py",))


@pytest.mark.parametrize("code", [True, False])
def declarations_preserve_private_references_test(*, code: bool) -> None:
    (record,) = transport.encode_declarations((declaration(code=code),))
    reference = transport.reference(sources=sources(), case_id="external", record=record)
    assert reference.solution == {"main.py": "fixed"}
    if code:
        assert reference.answer == "done"
    else:
        assert json.loads(reference.answer) == {"choice": "B", "safe": True}


def answer_declarations_do_not_supply_executable_checks_test() -> None:
    (record,) = transport.encode_declarations((declaration(code=False),))
    assert transport.verifier(sources=sources(), case_id="external", record=record) is None


@pytest.mark.parametrize("code", [True, False])
def imported_declarations_use_existing_grading_test(*, code: bool) -> None:
    (record,) = transport.encode_declarations((declaration(code=code),))
    scores = transport.grade(
        sources=sources(),
        case_id="external",
        record=record,
        response='{"choice":"B","safe":true,"reason":"clear"}',
        changed_files=("workspace/main.py",),
        verification=query.Verification(status="passed"),
    )
    assert scores == {"correctness": True, "scope": True}


def generic_declarations_do_not_supply_cases_or_download_metadata_test() -> None:
    assert transport.describe(sources=sources()) is None
    assert transport.cases(sources=sources()) == ()


def declaration_inputs_are_frozen_defensive_copies_test() -> None:
    fields = {"choice": "B"}
    criterion = query.AnswerCriterion(expected=fields)
    fields["choice"] = "A"
    assert criterion.expected == {"choice": "B"}
    with pytest.raises(TypeError):
        cast(dict[str, str | bool], criterion.expected)["choice"] = "A"
    with pytest.raises(ValidationError):
        criterion.kind = "answer"
    for fields_value in ({"choice": 1}, {"choice": None}):
        with pytest.raises(ValidationError):
            query.AnswerCriterion.model_validate({"expected": fields_value})
    with pytest.raises(ValidationError):
        query.CaseDefinition.model_validate({**declaration().model_dump(), "allowed_files": []})
    assert transport.encode_declarations(()) == ()


@pytest.mark.parametrize(
    "change",
    [
        {"criterion": {"kind": "answer", "expected": {}, "text_rule": None}},
        {"allowed_files": []},
        {
            "criterion": {
                "kind": "answer",
                "expected": {"choice": "B"},
                "text_rule": {"field": "choice", "min_words": 0, "max_words": 2},
            }
        },
    ],
)
def kernel_constructors_validate_raw_declarations_test(change: Mapping[str, object]) -> None:
    raw = {**declaration().model_dump(), **change}
    with pytest.raises(subprocess.CalledProcessError):
        transport.cases(sources=sources(), records=(json.dumps(raw),))


@pytest.mark.parametrize("raw", ["null", "[]", "{}", '{"id":"a","id":"b"}', '{"unknown":true}'])
def malformed_declarations_fail_closed_test(raw: str) -> None:
    with pytest.raises(subprocess.CalledProcessError):
        transport.cases(sources=sources(), records=(raw,))


@pytest.mark.parametrize(
    ("path", "invalid"),
    [
        (("id",), False),
        (("fixture",), []),
        (("fixture", "main.py"), 3),
        (("instruction", "prompt"), None),
        (("instruction", "unexpected"), "extra"),
        (("criterion", "kind"), "unknown"),
        (("criterion", "verifier", "inputs"), "main.py"),
        (("criterion", "verifier", "inputs"), []),
        (("criterion", "verifier", "inputs"), ["missing.py"]),
        (("criterion", "verifier", "command"), []),
        (("criterion", "verifier", "timeout_seconds"), True),
        (("criterion", "verifier", "timeout_seconds"), 1.5),
        (("criterion", "verifier", "timeout_seconds"), 0),
        (("criterion", "verifier", "timeout_seconds"), 1e30),
        (("criterion", "verifier", "files", "verify.py", "kind"), "unknown"),
        (("criterion", "verifier", "files", "verify.py", "text"), []),
        (("criterion", "verifier", "files", "main.py"), {"kind": "inline", "text": "overlap"}),
        (("criterion", "verifier", "tools", "check.sh", "name"), "../secret"),
        (("reference", "completion", "kind"), "unknown"),
        (("reference", "completion", "text"), False),
        (("reference", "edits", "outside.py"), "unauthorized"),
    ],
)
def nested_wire_shapes_and_constructor_rules_fail_closed_test(
    *, path: tuple[str, ...], invalid: object
) -> None:
    raw = declaration().model_dump()
    parent = raw
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = invalid
    with pytest.raises(subprocess.CalledProcessError):
        transport.cases(sources=sources(), records=(json.dumps(raw),))


@pytest.mark.parametrize(
    "criterion",
    [
        {"kind": "answer", "expected": {"choice": 3}, "text_rule": None},
        {"kind": "answer", "expected": {"choice": None}, "text_rule": None},
        {"kind": "answer", "expected": [], "text_rule": None},
        {
            "kind": "answer",
            "expected": {},
            "text_rule": {"field": "reason", "min_words": -1, "max_words": 2},
        },
        {
            "kind": "answer",
            "expected": {},
            "text_rule": {"field": "reason", "min_words": 1, "max_words": False},
        },
    ],
)
def answer_wire_validation_is_owned_by_kernel_test(criterion: Mapping[str, object]) -> None:
    raw = {**declaration(code=False).model_dump(), "criterion": criterion}
    with pytest.raises(subprocess.CalledProcessError):
        transport.cases(sources=sources(), records=(json.dumps(raw),))


@pytest.mark.parametrize("field", ["id", "main.py", "kind", "choice"])
def nested_duplicate_wire_fields_are_rejected_test(field: str) -> None:
    record = declaration(code=False).model_dump_json()
    marker = json.dumps(field) + ":"
    raw = record.replace(marker, marker + "null," + marker, 1)
    with pytest.raises(subprocess.CalledProcessError):
        transport.cases(sources=sources(), records=(raw,))


def fixture_and_artifact_mappings_retain_immutable_snapshots_test() -> None:
    definition = declaration()
    with pytest.raises(TypeError):
        cast(dict[str, str], definition.fixture)["main.py"] = "changed"
    assert isinstance(definition.criterion, query.CodeCriterion)
    with pytest.raises(TypeError):
        cast(dict[str, query.Inline], definition.criterion.verifier.files)["verify.py"] = (
            query.Inline(text="changed")
        )
    with pytest.raises(TypeError):
        cast(dict[str, str], definition.reference.edits)["main.py"] = "changed"


@pytest.mark.parametrize(
    "criterion",
    [
        query.AnswerCriterion(expected={"choice": "B"}),
        query.AnswerCriterion(
            expected={}, text_rule=query.TextRule(field="reason", min_words=1, max_words=5)
        ),
    ],
)
def answer_construction_supports_each_optional_rule_shape_test(
    criterion: query.AnswerCriterion,
) -> None:
    definition = declaration(code=False).model_copy(update={"criterion": criterion})
    (record,) = transport.encode_declarations((definition,))
    (case,) = transport.cases(sources=sources(), records=(record,))
    assert case.id == "external"
