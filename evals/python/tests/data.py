"""Validate schemas and keep the comparison's inputs controlled."""

import json
import subprocess
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from evals.python import commands, query, transport
from evals.python._kernel import Verification
from evals.python.catalog import (
    case as catalog_case,
)
from evals.python.catalog import (
    experiment,
    load_cases,
    reference,
    verifier,
)
from evals.python.integrations.inspect import profiles
from evals.python.integrations.inspect.profiles import (
    REASONING_DOCUMENTS,
    content_hash,
    load_profile,
)
from evals.python.integrations.inspect.tasks import build_task
from evals.python.paths import REPO_ROOT
from evals.python.query import GradeCase
from evals.python.tests.support import (
    choice_case as _choice_case,
)
from evals.python.tests.support import (
    timeout_case as _timeout_case,
)
from evals.python.transport import decode


def _encode(cases: list[dict[str, object]]) -> str:
    return json.dumps({"version": 3, "value": cases})


def manifest_roundtrip() -> None:
    cases = load_cases()
    assert decode(_encode([case.model_dump() for case in cases])) == cases


def native_dataset_paths_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "suite.ml"
    path.write_text("let cases = []")
    operation = cast(Callable[..., query.Dataset], query.LoadDataset)
    with pytest.raises(ValidationError):
        operation(selection=path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("checks", {"sources": ["../outside.ml"], "program": ""}),
        ("files", {"../outside.ml": "bad"}),
        ("solution", {"../outside.ml": "bad"}),
    ],
)
def generated_paths_are_validated(*, field: str, value: object) -> None:
    data = load_cases()[0].model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        decode(_encode([data]))


def _grade(case_id: str, *, text: str) -> bool:
    return GradeCase(
        case_id=case_id,
        response=text,
        changed_files=(),
        verification=Verification(status="unchecked"),
        selection="smoke",
    )["correctness"]


def profiles_share_fixture_files() -> None:
    spec = query.ExperimentSettings()
    assert load_profile("genius", spec=spec) is spec.profiles[1]
    case = load_cases()[0]
    baseline = profiles.files(
        load_profile(name="baseline", spec=query.ExperimentSettings()),
        case=case,
        instructions=profiles.load_instructions(query.ExperimentSettings()),
    )
    genius = profiles.files(
        load_profile(name="genius", spec=query.ExperimentSettings()),
        case=case,
        instructions=profiles.load_instructions(query.ExperimentSettings()),
    )
    assert {key: genius[key] for key in baseline} == baseline


def only_genius_receives_instructions() -> None:
    case = load_cases()[0]
    assert (
        any(
            key.startswith("instructions/")
            for key in profiles.files(
                load_profile(name="baseline", spec=query.ExperimentSettings()),
                case=case,
                instructions=profiles.load_instructions(query.ExperimentSettings()),
            )
        ),
        any(
            key.startswith("instructions/")
            for key in profiles.files(
                load_profile(name="genius", spec=query.ExperimentSettings()),
                case=case,
                instructions=profiles.load_instructions(query.ExperimentSettings()),
            )
        ),
    ) == (False, True)


def profile_prompts() -> None:
    case = load_cases()[0]
    assert (
        profiles.prompt(
            load_profile(name="baseline", spec=query.ExperimentSettings()),
            case=case,
            instructions=profiles.load_instructions(query.ExperimentSettings()),
        )
        == case.prompt,
        "../instructions/skills/reasoning/SKILL.md"
        in profiles.prompt(
            load_profile(name="genius", spec=query.ExperimentSettings()),
            case=case,
            instructions=profiles.load_instructions(query.ExperimentSettings()),
        ),
    ) == (True, True)


def samples_keep_task_ids_and_metadata() -> None:
    assert [
        sample.id
        for sample in profiles.samples(
            load_profile(name="genius", spec=query.ExperimentSettings()),
            cases=query.Cases(),
            instructions=profiles.load_instructions(query.ExperimentSettings()),
        )
    ] == [case.id for case in load_cases()]


def hash_tracks_contents_and_ignores_mapping_order() -> None:
    before = content_hash({"a": b"before", "b": b"before"})
    assert content_hash({"b": b"before", "a": b"before"}) == before
    assert content_hash({"a": b"after", "b": b"before"}) != before


@pytest.mark.parametrize(
    "text",
    ['  {"choice":"B","reason":"Cheap"}  ', '```json\n{"choice":"B","reason":"Cheap"}\n```'],
)
def json_fences(text: str) -> None:
    assert _grade("small-decision", text=text)


def cases_200_cases_are_python_values() -> None:
    dataset = query.CompileDataset(
        cases=tuple(
            _timeout_case(case_id=f"timeout-{i}", initial=15, requested=30 + i) for i in range(200)
        )
    )
    cases = load_cases(selection=dataset)
    assert len(cases) == 200
    assert (
        reference(cases[199].id, selection=dataset).solution["config.py"]
        == "timeout_seconds = 229\n"
    )


def generated_artifacts_stay_out_of_sample_metadata() -> None:
    for sample in profiles.samples(
        load_profile(name="baseline", spec=query.ExperimentSettings()),
        cases=query.Cases(),
        instructions=profiles.load_instructions(query.ExperimentSettings()),
    ):
        assert sample.metadata == {
            "case_id": sample.id,
            "profile": "baseline",
            "dataset": "smoke",
        }
        assert not any("heldout" in path for path in sample.files or {})


def duplicate_case_ids_are_rejected() -> None:
    definition = _choice_case(case_id="duplicate", a=10, b=8)
    with pytest.raises(subprocess.CalledProcessError):
        query.CompileDataset(cases=(definition, definition))


def exporter_escapes_strings() -> None:
    text = 'quote" slash\\ newline\n tab\t return\r zero\x00 é'
    definition = _choice_case(case_id="escaped", a=10, b=8).model_copy(
        update={"instruction": query.Instruction(skill="reasoning", prompt=text)}
    )
    dataset = query.CompileDataset(cases=(definition,))
    assert load_cases(selection=dataset)[0].prompt == text


def cases_are_immutable() -> None:
    case = catalog_case("clear-task")
    with pytest.raises(ValidationError):
        case.id = "changed"
    with pytest.raises(TypeError):
        case.files["receipt.py"] = "changed"  # type: ignore[index]
    with pytest.raises(TypeError):
        reference(case.id).solution["receipt.py"] = "changed"  # type: ignore[index]
    checks = verifier(case.id)
    assert checks is not None
    with pytest.raises(ValidationError):
        checks.stdin = "changed"
    assert isinstance(checks.inputs, tuple)
    assert catalog_case("clear-task") is case


def compilation_cache_invalidates_when_declarations_change() -> None:
    definition = _choice_case(case_id="cache", a=10, b=8)
    first = query.CompileDataset(cases=(definition,))
    with patch("evals.python.transport.subprocess.run", wraps=subprocess.run) as compiler:
        assert query.CompileDataset(cases=(definition,)) is first
        assert compiler.call_count == 0
        changed = query.CompileDataset(cases=(_choice_case(case_id="cache", a=4, b=8),))
        assert json.loads(reference("cache", selection=changed).answer)["choice"] == "A"
        assert compiler.call_count == 2


def generic_python_case_exports_without_language_restriction() -> None:
    definition = query.CaseDefinition(
        id="python-case",
        fixture={"solution.py": "print(42)"},
        instruction=query.Instruction(skill="reasoning", prompt="Return 42"),
        criterion=query.CodeCriterion(
            verifier=query.VerifierDefinition(
                inputs=("solution.py",),
                files={"grader.py": query.Inline(text="trusted")},
                tools={},
                command=("python3", "grader.py"),
                stdin="private",
                timeout_seconds=5,
            )
        ),
        allowed_files=("solution.py",),
        reference=query.ReferenceDefinition(
            edits={}, completion=query.PlainCompletion(text="done")
        ),
    )
    dataset = query.CompileDataset(cases=(definition,))
    case = load_cases(selection=dataset)[0]
    checks = verifier(case.id, selection=dataset)
    assert checks is not None
    assert checks.model_dump() == {
        "inputs": ("solution.py",),
        "files": {"grader.py": "trusted"},
        "tools": {},
        "command": ("python3", "grader.py"),
        "stdin": "private",
        "timeout_seconds": 5,
    }


def experiment_cache_tracks_native_configuration(tmp_path: Path) -> None:
    before = experiment()
    source = transport.OCAML_ROOT / "experiment.ml"
    copied = tmp_path / source.name
    copied.write_text(
        source.read_text().replace("epochs = 5", "epochs = 7").replace("Apply that", "Follow that")
    )
    library = tuple({source: copied}.get(path, path) for path in transport.LIBRARY)
    with patch("evals.python.transport.LIBRARY", library):
        task = build_task(
            profile=profiles.load_profile("genius", spec=query.ExperimentSettings()),
            spec=query.ExperimentSettings(),
            agent="codex",
            catalog=query.LoadDataset(selection="smoke"),
            instructions=profiles.load_instructions(query.ExperimentSettings()),
            provenance=query.Provenance(selection=query.LoadDataset(selection="smoke")),
        )
        assert (
            experiment().epochs,
            task.epochs,
            "Follow that" in str(task.dataset[0].input),
            "Follow that" in load_profile(name="genius", spec=query.ExperimentSettings()).preamble,
        ) == (7, 7, True, True)
    assert experiment() == before


@pytest.mark.parametrize("grade_only", [False, True])
def record_updates_cannot_bypass_kernel_validation(
    *, grade_only: bool, capfd: pytest.CaptureFixture[str]
) -> None:
    definition = _timeout_case(case_id="updated", initial=15, requested=30)
    invalid = definition.model_copy(update={"fixture": {}})
    records = transport.encode_declarations((invalid,))
    operation: Callable[[], object]
    if grade_only:
        operation = partial(
            transport.grade,
            sources=transport.sources(),
            record=records[0],
            case_id="updated",
            response="",
            changed_files=(),
            verification=Verification(status="unchecked"),
        )
    else:
        operation = partial(transport.cases, sources=transport.sources(), records=records)
    with pytest.raises(subprocess.CalledProcessError):
        operation()
    assert "criteria read files missing from the fixture" in capfd.readouterr().err


@pytest.mark.parametrize("delivery", ["manifest", "inline"])
@pytest.mark.parametrize("name", REASONING_DOCUMENTS)
def delivery_preserves_instruction_bytes_and_baseline(delivery: str, *, name: str) -> None:
    mode = cast(commands.InstructionDelivery, delivery)
    case = load_cases()[0]
    root = "/eval/instructions"
    profile = load_profile(name="genius", spec=query.ExperimentSettings())
    before = profiles.files(
        profile, case=case, instructions=profiles.load_instructions(query.ExperimentSettings())
    )
    prompt = profiles.prompt(
        profile,
        case=case,
        delivery=mode,
        instruction_root=root,
        instructions=profiles.load_instructions(query.ExperimentSettings()),
    )
    assert (
        prompt.endswith(case.prompt),
        profiles.files(
            profile, case=case, instructions=profiles.load_instructions(query.ExperimentSettings())
        ),
        profiles.prompt(
            load_profile(name="baseline", spec=query.ExperimentSettings()),
            case=case,
            delivery=mode,
            instructions=profiles.load_instructions(query.ExperimentSettings()),
        ),
    ) == (True, before, case.prompt)
    assert f"{root}/{name}" in prompt
    assert ((REPO_ROOT / name).read_text() in prompt) == (delivery == "inline")


def delivery_rejects_unimplemented_skill_instead_of_silently_changing_it() -> None:
    with pytest.raises(ValueError, match="reasoning only"):
        profiles.prompt(
            load_profile(name="genius", spec=query.ExperimentSettings()),
            case=load_cases()[1],
            delivery="inline",
            instructions=profiles.load_instructions(query.ExperimentSettings()),
        )
