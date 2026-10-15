"""Validate schemas and keep the comparison's inputs controlled."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from evals.python.profiles import BASELINE, GENIUS, content_hash
from evals.python.tests.support import ocaml_choice_case, ocaml_timeout_case
from evals.python.transport import case_by_id, decode, load_cases
from evals.python.transport import grade as kernel_grade


def encode(cases: list[dict[str, object]]) -> str:
    return json.dumps(cases)


def test_manifest_roundtrip() -> None:
    cases = load_cases()
    assert decode(encode([case.model_dump() for case in cases])) == cases


def test_invalid_ocaml_suite_is_rejected(
    *, tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "suite.ml"
    path.write_text("this is not valid OCaml")
    with pytest.raises(subprocess.CalledProcessError):
        load_cases(path)
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


def grade(case_id: str, *, text: str) -> bool:
    return kernel_grade(case_id, response=text, changed_files=(), code_passed=False)["correctness"]


def test_profiles_share_fixture_files() -> None:
    case = load_cases()[0]
    baseline = BASELINE.files(case)
    genius = GENIUS.files(case)
    assert {key: genius[key] for key in baseline} == baseline


def test_only_genius_receives_instructions() -> None:
    case = load_cases()[0]
    assert (
        any(key.startswith("instructions/") for key in BASELINE.files(case)),
        any(key.startswith("instructions/") for key in GENIUS.files(case)),
    ) == (False, True)


def test_profile_prompts() -> None:
    case = load_cases()[0]
    assert (
        BASELINE.prompt(case) == case.prompt,
        "../instructions/skills/reasoning/SKILL.md" in GENIUS.prompt(case),
    ) == (True, True)


def test_samples_keep_task_ids_and_metadata() -> None:
    assert [sample.id for sample in GENIUS.samples()] == [case.id for case in load_cases()]


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
    cases = load_cases(suite)
    assert len(cases) == 200
    assert cases[199].solution["config.ml"] == "let timeout_seconds = 229\n"
    assert [path.name for path in tmp_path.iterdir()] == ["suite.ml"]


def test_generated_artifacts_stay_out_of_sample_metadata() -> None:
    for sample in BASELINE.samples():
        assert sample.metadata == {"case_id": sample.id, "profile": "baseline"}
        assert not any("heldout" in path for path in sample.files or {})


def test_duplicate_case_ids_are_rejected(tmp_path: Path) -> None:
    suite = tmp_path / "suite.ml"
    expression = ocaml_choice_case(case_id="duplicate", a=10, b=8)
    suite.write_text(f"let c = {expression}\nlet cases = [c; c]\n")
    with pytest.raises(ValueError, match="unique"):
        load_cases(suite)


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
    assert load_cases(suite)[0].prompt == 'quote" slash\\ newline\n tab\t return\r zero\x00 é'


def test_cases_are_immutable() -> None:
    case = case_by_id("clear-task")
    with pytest.raises(ValidationError):
        case.id = "changed"
    with pytest.raises(TypeError):
        case.files["receipt.ml"] = "changed"  # type: ignore[index]
    with pytest.raises(TypeError):
        case.solution["receipt.ml"] = "changed"  # type: ignore[index]
    assert case.checks is not None
    with pytest.raises(ValidationError):
        case.checks.program = "changed"
    assert isinstance(case.checks.sources, tuple)
    assert case_by_id("clear-task") is case


def test_compilation_cache_invalidates_when_suite_changes(tmp_path: Path) -> None:
    suite = tmp_path / "suite.ml"
    expression = ocaml_choice_case(case_id="cache", a=10, b=8)
    source = f"let cases = [{expression}]\n"
    suite.write_text(source)
    with patch("evals.python.transport.subprocess.run", wraps=subprocess.run) as compiler:
        first = load_cases(suite)
        assert load_cases(suite) == first
        assert compiler.call_count == 2
        changed = ocaml_choice_case(case_id="cache", a=4, b=8)
        suite.write_text(f"let cases = [{changed}]\n")
        assert json.loads(load_cases(suite)[0].answer)["choice"] == "A"
        assert compiler.call_count == 4
