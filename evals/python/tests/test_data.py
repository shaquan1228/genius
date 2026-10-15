"""Validate schemas and keep the comparison's inputs controlled."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from evals.python.profiles import BASELINE, GENIUS, content_hash
from evals.python.tests.support import ocaml_choice_case, ocaml_timeout_case
from evals.python.transport import AnswerChecks, case_by_id, decode, load_cases
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
        ("checks", {"kind": "code", "sources": ["../outside.ml"], "program": ""}),
        ("checks", {"kind": "unknown"}),
        ("files", {"../outside.ml": "bad"}),
        ("solution", {"../outside.ml": "bad"}),
        ("allowed_files", ["../outside.ml"]),
    ],
)
def test_generated_paths_are_validated(*, field: str, value: object) -> None:
    data = load_cases()[0].model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        decode(encode([data]))


def grade(case_id: str, *, text: str, suite: Path | None = None) -> bool:
    arguments = {} if suite is None else {"suite": suite}
    return kernel_grade(case_id, response=text, changed_files=(), code_passed=False, **arguments)[
        "correctness"
    ]


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
    ("case_id", "text"),
    [
        ("small-decision", '{"choice":"B","reason":"B costs less for identical service."}'),
        (
            "decision-review",
            '{"decision_was_supported":true,"change_rule":false,'
            '"reason":"One loss did not change the known odds."}',
        ),
    ],
)
def test_correct_decision_outputs(*, case_id: str, text: str) -> None:
    assert grade(case_id, text=text)


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
    assert not grade("small-decision", text=text)


@pytest.mark.parametrize(
    ("supported", "changed"),
    [(False, False), (False, True), (True, True), (1, 0), ("true", "false")],
)
def test_wrong_review_verdicts_fail(*, supported: object, changed: object) -> None:
    text = json.dumps(
        {"decision_was_supported": supported, "change_rule": changed, "reason": "One loss."}
    )
    assert not grade("decision-review", text=text)


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


@pytest.mark.parametrize(
    ("fixture", "allowed_files", "message"),
    [
        (
            "Fixtures.Preflight.fixture ~timeout:15",
            '["receipt.ml"]',
            "criteria read files missing from the fixture: receipt.ml",
        ),
        (
            "Fixtures.Receipt.fixture ~bug:Ignore_quantity",
            '["config.ml"]',
            "reference edits files outside allowed_files: receipt.ml",
        ),
    ],
)
def test_case_parts_must_agree_on_files(
    *,
    fixture: str,
    allowed_files: str,
    message: str,
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    suite = tmp_path / "suite.ml"
    suite.write_text(
        f"""let cases = [Case.make ~id:"mismatch" ~fixture:({fixture})
  ~instruction:Scenarios.Receipt.fix_total
  ~criterion:Scenarios.Receipt.(totals [ expect ~items:[] ~total:0.0 ])
  ~allowed_files:{allowed_files} ~reference:Scenarios.Receipt.reference]
"""
    )
    with pytest.raises(subprocess.CalledProcessError):
        load_cases(suite)
    assert f"Case mismatch: {message}" in capfd.readouterr().err


def test_prompts_name_their_scope_and_answer_fields() -> None:
    for case in load_cases():
        fields = json.loads(case.answer) if isinstance(case.checks, AnswerChecks) else {}
        assert all(name in case.prompt for name in [*case.allowed_files, *fields]), case.id


def test_new_decision_ids_and_reversed_costs_need_no_registry_entry(tmp_path: Path) -> None:
    suite = tmp_path / "suite.ml"
    expression = ocaml_choice_case(case_id="new-choice", a=4, b=8)
    suite.write_text(f"let cases = [{expression}]\n")
    case = load_cases(suite)[0]
    assert grade(case.id, text=case.answer, suite=suite)
    assert not grade(case.id, text='{"choice":"B","reason":"Cheaper."}', suite=suite)


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
    with pytest.raises(ValidationError):
        case.checks.kind = "answer"
    assert isinstance(case.allowed_files, tuple)
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
