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
    native_choice_case as _native_choice_case,
)
from evals.python.tests.support import (
    native_timeout_case as _native_timeout_case,
)
from evals.python.transport import decode


def _encode(cases: list[dict[str, object]]) -> str:
    return json.dumps({"version": 3, "value": cases})


def manifest_roundtrip() -> None:
    cases = load_cases()
    assert decode(_encode([case.model_dump() for case in cases])) == cases


def invalid_ocaml_suite_is_rejected(*, tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "suite.ml"
    path.write_text("this is not valid OCaml")
    with pytest.raises(subprocess.CalledProcessError):
        load_cases(selection=path)
    assert 'File "suite.ml"' in capfd.readouterr().err


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


def _grade(case_id: str, *, text: str, suite: Path | None = None) -> bool:
    return GradeCase(
        case_id=case_id,
        response=text,
        changed_files=(),
        verification=Verification(status="unchecked"),
        selection="smoke" if suite is None else suite,
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


def cases_200_cases_are_values_in_one_ocaml_suite(tmp_path: Path) -> None:
    suite = tmp_path / "suite.ml"
    expression = _native_timeout_case(
        id_expression='Printf.sprintf "timeout-%d" i',
        initial="15",
        requested="30 + i",
    )
    suite.write_text(f"let cases = List.init 200 (fun i -> {expression})\n")
    cases = load_cases(selection=suite)
    assert len(cases) == 200
    assert (
        reference(cases[199].id, selection=suite).solution["config.py"] == "timeout_seconds = 229\n"
    )
    assert [path.name for path in tmp_path.iterdir()] == ["suite.ml"]


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


def duplicate_case_ids_are_rejected(tmp_path: Path) -> None:
    suite = tmp_path / "suite.ml"
    expression = _native_choice_case(case_id="duplicate", a=10, b=8)
    suite.write_text(f"let c = {expression}\nlet cases = [c; c]\n")
    with pytest.raises(subprocess.CalledProcessError):
        load_cases(selection=suite)


def exporter_escapes_strings(tmp_path: Path) -> None:
    suite = tmp_path / "suite.ml"
    expression = _native_choice_case(case_id="escaped", a=10, b=8)
    suite.write_text(
        f"let c = {expression}\n"
        + r"""
let text = "quote\" slash\\ newline\n tab\t return\r zero\000 é"
let cases = [{ c with instruction = { c.instruction with prompt = text } }]
"""
    )
    assert (
        load_cases(selection=suite)[0].prompt
        == 'quote" slash\\ newline\n tab\t return\r zero\x00 é'
    )


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


def compilation_cache_invalidates_when_suite_changes(tmp_path: Path) -> None:
    suite = tmp_path / "suite.ml"
    expression = _native_choice_case(case_id="cache", a=10, b=8)
    source = f"let cases = [{expression}]\n"
    suite.write_text(source)
    with patch("evals.python.transport.subprocess.run", wraps=subprocess.run) as compiler:
        first = load_cases(selection=suite)
        assert load_cases(selection=suite) == first
        assert compiler.call_count == 3
        changed = _native_choice_case(case_id="cache", a=4, b=8)
        suite.write_text(f"let cases = [{changed}]\n")
        assert json.loads(reference("cache", selection=suite).answer)["choice"] == "A"
        assert compiler.call_count == 7


def generic_python_case_exports_without_language_restriction(tmp_path: Path) -> None:
    suite = tmp_path / "suite.ml"
    suite.write_text("""let cases = [Case.make ~id:"python-case"
      ~fixture:(Fixture.of_files ["solution.py", "print(42)"])
      ~instruction:{ Ast.skill = "reasoning"; prompt = "Return 42" }
      ~criterion:(Ast.Code (Verifier.make ~inputs:["solution.py"]
        ~files:["grader.py", Inline "trusted"] ~tools:[]
        ~command:["python3"; "grader.py"] ~stdin:"private" ~timeout_seconds:5))
      ~allowed_files:["solution.py"]
      ~reference:{ Ast.edits = Fixture.empty; completion = Plain "done" }]
""")
    case = load_cases(selection=suite)[0]
    checks = verifier(case.id, selection=suite)
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
    *, grade_only: bool, tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    suite = tmp_path / "suite.ml"
    expression = _native_timeout_case(id_expression='"updated"', initial="15", requested="30")
    suite.write_text(f"let c = {expression}\nlet cases = [{{c with fixture = Fixture.empty}}]\n")
    operation: Callable[[], object]
    if grade_only:
        operation = partial(
            GradeCase, case_id="updated", response="", changed_files=(), selection=suite
        )
    else:
        operation = partial(load_cases, selection=suite)
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
