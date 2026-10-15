"""Validate schemas and keep the comparison's inputs controlled."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from evals.answers import grade_answer, unfence
from evals.cases import Case, case_by_id, load_cases
from evals.profiles import content_hash, files_for, prompt_for, samples
from evals.tests.support import ocaml_choice_case, ocaml_timeout_case


def test_manifest_roundtrip() -> None:
    cases = load_cases()
    assert [Case.model_validate(case.model_dump()) for case in cases] == cases


def test_invalid_ocaml_suite_is_rejected(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "suite.ml"
    path.write_text("this is not valid OCaml")
    with pytest.raises(subprocess.CalledProcessError):
        load_cases(path)
    assert 'File "suite.ml"' in capfd.readouterr().err


@pytest.mark.parametrize(
    "field,value",
    [
        ("sources", ["../outside.ml"]),
        ("files", {"../outside.ml": "bad"}),
        ("solution", {"../outside.ml": "bad"}),
        ("allowed_files", ["../outside.ml"]),
    ],
)
def test_generated_paths_are_validated(field: str, value: object) -> None:
    data = load_cases()[0].model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        Case.model_validate(data)


def grade(case_id: str, text: str) -> bool:
    case = case_by_id(case_id)
    return grade_answer(case.grading, text, expected=case.expected)


def test_profiles_share_fixture_files() -> None:
    case = load_cases()[0]
    baseline = files_for(case, "baseline")
    genius = files_for(case, "genius")
    assert {key: genius[key] for key in baseline} == baseline


def test_only_genius_receives_instructions() -> None:
    case = load_cases()[0]
    assert (
        any(key.startswith("instructions/") for key in files_for(case, "baseline")),
        any(key.startswith("instructions/") for key in files_for(case, "genius")),
    ) == (False, True)


def test_profile_prompts() -> None:
    case = load_cases()[0]
    assert (
        prompt_for(case, "baseline") == case.prompt,
        "../instructions/skills/reasoning/SKILL.md" in prompt_for(case, "genius"),
    ) == (True, True)


def test_samples_keep_task_ids_and_metadata() -> None:
    assert [sample.id for sample in samples("genius")] == [case.id for case in load_cases()]


def test_hash_tracks_contents_and_ignores_mapping_order(tmp_path: Path) -> None:
    path = tmp_path / "source.txt"
    path.write_text("before")
    before = content_hash({"a": str(path), "b": str(path)})
    assert content_hash({"b": str(path), "a": str(path)}) == before
    path.write_text("after")
    assert content_hash({"a": str(path), "b": str(path)}) != before


@pytest.mark.parametrize(
    "case_id,text",
    [
        ("small-decision", '{"choice":"B","reason":"B costs less for identical service."}'),
        (
            "decision-review",
            '{"decision_was_supported":true,"change_rule":false,'
            '"reason":"One loss did not change the known odds."}',
        ),
    ],
)
def test_correct_decision_outputs(case_id: str, text: str) -> None:
    assert grade(case_id, text)


@pytest.mark.parametrize(
    "text",
    [
        "{}",
        "[]",
        "not JSON",
        '{"choice":"A","reason":"Cheaper"}',
        '{"choice":"B","reason":5}',
        '{"choice":"B","reason":""}',
        json.dumps({"choice": "B", "reason": "word " * 41}),
        '{"choice":"B","reason":"Cheap","extra":true}',
    ],
)
def test_invalid_decisions_fail(text: str) -> None:
    assert not grade("small-decision", text)


@pytest.mark.parametrize(
    "supported,changed", [(False, False), (False, True), (True, True), (1, 0), ("true", "false")]
)
def test_wrong_review_verdicts_fail(supported: object, changed: object) -> None:
    text = json.dumps(
        {"decision_was_supported": supported, "change_rule": changed, "reason": "One loss."}
    )
    assert not grade("decision-review", text)


@pytest.mark.parametrize(
    "text,expected",
    [("  plain  ", "plain"), ("```json\n{}\n```", "{}"), ("```json\n{}", "```json\n{}")],
)
def test_json_fences(text: str, expected: str) -> None:
    assert unfence(text) == expected


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
    for sample in samples("baseline"):
        assert sample.metadata == {"case_id": sample.id, "profile": "baseline"}
        assert not any("heldout" in path for path in sample.files or {})


def test_duplicate_case_ids_are_rejected(tmp_path: Path) -> None:
    suite = tmp_path / "suite.ml"
    expression = ocaml_choice_case(case_id="duplicate", a=10, b=8)
    suite.write_text(f"let c = {expression}\nlet cases = [c; c]\n")
    with pytest.raises(ValueError, match="unique"):
        load_cases(suite)


@pytest.mark.parametrize(
    "fixture,allowed_files,message",
    [
        (
            "Fixtures.Preflight.fixture ~timeout:15",
            '["receipt.ml"]',
            "checks read files missing from the fixture: receipt.ml",
        ),
        (
            "Fixtures.Receipt.fixture ~bug:Ignore_quantity",
            '["config.ml"]',
            "reference edits files outside allowed_files: receipt.ml",
        ),
    ],
)
def test_case_parts_must_agree_on_files(
    fixture: str,
    allowed_files: str,
    message: str,
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    suite = tmp_path / "suite.ml"
    suite.write_text(
        f"""let cases = [Eval.case ~id:"mismatch" ~fixture:({fixture})
  ~task:Task.Receipt.fix_total ~checks:Check.Receipt.(totals [ expect ~items:[] ~total:0.0 ])
  ~allowed_files:{allowed_files} ~reference:Reference.receipt]
"""
    )
    with pytest.raises(subprocess.CalledProcessError):
        load_cases(suite)
    assert f"Case mismatch: {message}" in capfd.readouterr().err


def test_prompts_name_their_scope_and_answer_fields() -> None:
    for case in load_cases():
        assert all(name in case.prompt for name in [*case.allowed_files, *case.expected]), case.id


def test_new_decision_ids_and_reversed_costs_need_no_registry_entry(tmp_path: Path) -> None:
    suite = tmp_path / "suite.ml"
    expression = ocaml_choice_case(case_id="new-choice", a=4, b=8)
    suite.write_text(f"let cases = [{expression}]\n")
    case = load_cases(suite)[0]
    assert grade_answer(case.grading, case.answer, expected=case.expected)
    assert not grade_answer(
        case.grading, '{"choice":"B","reason":"Cheaper."}', expected=case.expected
    )


def test_exporter_escapes_strings(tmp_path: Path) -> None:
    suite = tmp_path / "suite.ml"
    expression = ocaml_choice_case(case_id="escaped", a=10, b=8)
    suite.write_text(
        f"let c = {expression}\n"
        + r"""
let text = "quote\" slash\\ newline\n tab\t return\r zero\000 é"
let cases = [{ c with task = { c.task with prompt = text } }]
"""
    )
    assert load_cases(suite)[0].prompt == 'quote" slash\\ newline\n tab\t return\r zero\x00 é'


def test_cached_cases_do_not_share_mutable_contents() -> None:
    original = case_by_id("clear-task")
    changed = case_by_id("clear-task")
    changed.files.clear()
    changed.solution.clear()
    assert case_by_id("clear-task") == original


def test_compilation_cache_invalidates_when_suite_changes(tmp_path: Path) -> None:
    suite = tmp_path / "suite.ml"
    expression = ocaml_choice_case(case_id="cache", a=10, b=8)
    source = f"let cases = [{expression}]\n"
    suite.write_text(source)
    with patch("evals.cases.subprocess.run", wraps=subprocess.run) as compiler:
        first = load_cases(suite)
        assert load_cases(suite) == first
        assert compiler.call_count == 1
        changed = ocaml_choice_case(case_id="cache", a=4, b=8)
        suite.write_text(f"let cases = [{changed}]\n")
        assert load_cases(suite)[0].expected == {"choice": "A"}
        assert compiler.call_count == 2
