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

from evals.python import transport
from evals.python.contracts import GradeRequest, Verification
from evals.python.integrations.datasets.catalog import (
    case as catalog_case,
)
from evals.python.integrations.datasets.catalog import (
    experiment,
    load_cases,
    reference,
    verifier,
)
from evals.python.integrations.datasets.catalog import grade as kernel_grade
from evals.python.integrations.inspect.profiles import (
    REASONING_DOCUMENTS,
    InstructionDelivery,
    content_hash,
    load_profile,
)
from evals.python.integrations.inspect.tasks import TaskRequest, build_task
from evals.python.paths import REPO_ROOT
from evals.python.tests.support import ocaml_choice_case, ocaml_timeout_case
from evals.python.transport import SUITE, decode


def encode(cases: list[dict[str, object]]) -> str:
    return json.dumps({"version": 3, "value": cases})


def test_manifest_roundtrip() -> None:
    cases = load_cases()
    assert decode(encode([case.model_dump() for case in cases])) == cases


def test_invalid_ocaml_suite_is_rejected(
    *, tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
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
def test_generated_paths_are_validated(*, field: str, value: object) -> None:
    data = load_cases()[0].model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        decode(encode([data]))


def grade(case_id: str, *, text: str, suite: Path | None = None) -> bool:
    return kernel_grade(
        request=GradeRequest(
            case_id=case_id,
            response=text,
            changed_files=(),
            verification=Verification(status="unchecked"),
        ),
        selection=SUITE if suite is None else suite,
    )["correctness"]


def test_profiles_share_fixture_files() -> None:
    case = load_cases()[0]
    baseline = load_profile(name="baseline").files(case)
    genius = load_profile(name="genius").files(case)
    assert {key: genius[key] for key in baseline} == baseline


def test_only_genius_receives_instructions() -> None:
    case = load_cases()[0]
    assert (
        any(key.startswith("instructions/") for key in load_profile(name="baseline").files(case)),
        any(key.startswith("instructions/") for key in load_profile(name="genius").files(case)),
    ) == (False, True)


def test_profile_prompts() -> None:
    case = load_cases()[0]
    assert (
        load_profile(name="baseline").prompt(case) == case.prompt,
        "../instructions/skills/reasoning/SKILL.md" in load_profile(name="genius").prompt(case),
    ) == (True, True)


def test_samples_keep_task_ids_and_metadata() -> None:
    assert [sample.id for sample in load_profile(name="genius").samples()] == [
        case.id for case in load_cases()
    ]


def test_hash_tracks_contents_and_ignores_mapping_order(tmp_path: Path) -> None:
    path = tmp_path / "source.txt"
    path.write_text("before")
    before = content_hash({"a": str(path), "b": str(path)})
    assert content_hash({"b": str(path), "a": str(path)}) == before
    path.write_text("after")
    assert content_hash({"a": str(path), "b": str(path)}) != before


@pytest.mark.parametrize(
    "text",
    ['  {"choice":"B","reason":"Cheap"}  ', '```json\n{"choice":"B","reason":"Cheap"}\n```'],
)
def test_json_fences(text: str) -> None:
    assert grade("small-decision", text=text)


def test_200_cases_are_values_in_one_ocaml_suite(tmp_path: Path) -> None:
    suite = tmp_path / "suite.ml"
    expression = ocaml_timeout_case(
        id_expression='Printf.sprintf "timeout-%d" i',
        initial="15",
        requested="30 + i",
    )
    suite.write_text(f"let cases = List.init 200 (fun i -> {expression})\n")
    cases = load_cases(selection=suite)
    assert len(cases) == 200
    assert (
        reference(cases[199].id, selection=suite).solution["config.ml"]
        == "let timeout_seconds = 229\n"
    )
    assert [path.name for path in tmp_path.iterdir()] == ["suite.ml"]


def test_generated_artifacts_stay_out_of_sample_metadata() -> None:
    for sample in load_profile(name="baseline").samples():
        assert sample.metadata == {
            "case_id": sample.id,
            "profile": "baseline",
            "dataset": "smoke",
        }
        assert not any("heldout" in path for path in sample.files or {})


def test_duplicate_case_ids_are_rejected(tmp_path: Path) -> None:
    suite = tmp_path / "suite.ml"
    expression = ocaml_choice_case(case_id="duplicate", a=10, b=8)
    suite.write_text(f"let c = {expression}\nlet cases = [c; c]\n")
    with pytest.raises(subprocess.CalledProcessError):
        load_cases(selection=suite)


def test_exporter_escapes_strings(tmp_path: Path) -> None:
    suite = tmp_path / "suite.ml"
    expression = ocaml_choice_case(case_id="escaped", a=10, b=8)
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


def test_cases_are_immutable() -> None:
    case = catalog_case("clear-task")
    with pytest.raises(ValidationError):
        case.id = "changed"
    with pytest.raises(TypeError):
        case.files["receipt.ml"] = "changed"  # type: ignore[index]
    with pytest.raises(TypeError):
        reference(case.id).solution["receipt.ml"] = "changed"  # type: ignore[index]
    checks = verifier(case.id)
    assert checks is not None
    with pytest.raises(ValidationError):
        checks.stdin = "changed"
    assert isinstance(checks.inputs, tuple)
    assert catalog_case("clear-task") is case


def test_compilation_cache_invalidates_when_suite_changes(tmp_path: Path) -> None:
    suite = tmp_path / "suite.ml"
    expression = ocaml_choice_case(case_id="cache", a=10, b=8)
    source = f"let cases = [{expression}]\n"
    suite.write_text(source)
    with patch("evals.python.transport.subprocess.run", wraps=subprocess.run) as compiler:
        first = load_cases(selection=suite)
        assert load_cases(selection=suite) == first
        assert compiler.call_count == 3
        changed = ocaml_choice_case(case_id="cache", a=4, b=8)
        suite.write_text(f"let cases = [{changed}]\n")
        assert json.loads(reference("cache", selection=suite).answer)["choice"] == "A"
        assert compiler.call_count == 7


def test_generic_python_case_exports_without_language_restriction(tmp_path: Path) -> None:
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


def test_experiment_cache_tracks_native_configuration(tmp_path: Path) -> None:
    before = experiment()
    source = transport.OCAML_ROOT / "experiment.ml"
    copied = tmp_path / source.name
    copied.write_text(
        source.read_text().replace("epochs = 5", "epochs = 7").replace("Apply that", "Follow that")
    )
    library = tuple({source: copied}.get(path, path) for path in transport.LIBRARY)
    with patch("evals.python.transport.LIBRARY", library):
        task = build_task(request=TaskRequest(profile="genius", agent="codex"))
        assert (
            experiment().epochs,
            task.epochs,
            "Follow that" in str(task.dataset[0].input),
            "Follow that" in load_profile(name="genius").preamble,
        ) == (7, 7, True, True)
    assert experiment() == before


@pytest.mark.parametrize("grade_only", [False, True])
def test_record_updates_cannot_bypass_kernel_validation(
    *, grade_only: bool, tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    suite = tmp_path / "suite.ml"
    expression = ocaml_timeout_case(id_expression='"updated"', initial="15", requested="30")
    suite.write_text(f"let c = {expression}\nlet cases = [{{c with fixture = Fixture.empty}}]\n")
    request = GradeRequest(
        case_id="updated",
        response="",
        changed_files=(),
        verification=Verification(status="unchecked"),
    )
    operation: Callable[[], object]
    if grade_only:
        operation = partial(kernel_grade, request=request, selection=suite)
    else:
        operation = partial(load_cases, selection=suite)
    with pytest.raises(subprocess.CalledProcessError):
        operation()
    assert "criteria read files missing from the fixture" in capfd.readouterr().err


@pytest.mark.parametrize("delivery", ["manifest", "inline"])
@pytest.mark.parametrize("name", REASONING_DOCUMENTS)
def test_delivery_preserves_instruction_bytes_and_baseline(delivery: str, *, name: str) -> None:
    mode = cast(InstructionDelivery, delivery)
    case = load_cases()[0]
    root = "/eval/instructions"
    profile = load_profile(name="genius")
    before = profile.files(case)
    prompt = profile.prompt(case, delivery=mode, instruction_root=root)
    assert (
        prompt.endswith(case.prompt),
        profile.files(case),
        load_profile(name="baseline").prompt(case, delivery=mode),
    ) == (True, before, case.prompt)
    assert f"{root}/{name}" in prompt
    assert ((REPO_ROOT / name).read_text() in prompt) == (delivery == "inline")


def test_delivery_rejects_unimplemented_skill_instead_of_silently_changing_it() -> None:
    with pytest.raises(ValueError, match="reasoning only"):
        load_profile(name="genius").prompt(load_cases()[1], delivery="inline")
