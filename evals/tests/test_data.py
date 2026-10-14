"""Validate schemas and keep the comparison's inputs controlled."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from evals.answers import grade_answer, unfence
from evals.cases import Case, load_cases
from evals.profiles import content_hash, files_for, prompt_for, samples
from evals.tests.scenarios import SOLUTIONS


def test_manifest_roundtrip() -> None:
    cases = load_cases()
    assert [Case.model_validate(case.model_dump()) for case in cases] == cases


def test_invalid_manifest_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "cases.json"
    path.write_text('[{"id":"unknown"}]')
    with pytest.raises(ValidationError):
        load_cases(path)


def test_new_code_case_needs_no_registry_entry() -> None:
    case = Case(
        id="new-case",
        skill="reasoning",
        fixtures=["ocaml", "new-case"],
        allowed_files=["answer.ml"],
        prompt="Fix answer.ml",
        heldout_test="answer.ml",
    )
    assert (case.id, case.heldout_test) == ("new-case", "answer.ml")


@pytest.mark.parametrize(
    "field,value",
    [
        ("heldout_test", "../outside.ml"),
        ("sources", ["../outside.ml"]),
        ("fixtures", ["../outside"]),
        ("fixtures", []),
        ("heldout_test", "old.py"),
    ],
)
def test_fixture_paths_are_validated(field: str, value: object) -> None:
    data = {
        "id": "new-case",
        "skill": "reasoning",
        "fixtures": ["ocaml", "new-case"],
        "allowed_files": [],
        "prompt": "Fix it",
        field: value,
    }
    with pytest.raises(ValidationError):
        Case.model_validate(data)


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


@pytest.mark.parametrize("case_id", ["small-decision", "decision-review"])
def test_correct_decision_outputs(case_id: str) -> None:
    assert grade_answer(case_id, (SOLUTIONS / case_id / "answer.txt").read_text())


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
    assert not grade_answer("small-decision", text)


@pytest.mark.parametrize(
    "supported,changed", [(False, False), (True, True), (1, 0), ("true", "false")]
)
def test_wrong_review_verdicts_fail(supported: object, changed: object) -> None:
    text = json.dumps(
        {"decision_was_supported": supported, "change_rule": changed, "reason": "One loss."}
    )
    assert not grade_answer("decision-review", text)


@pytest.mark.parametrize(
    "text,expected",
    [("  plain  ", "plain"), ("```json\n{}\n```", "{}"), ("```json\n{}", "```json\n{}")],
)
def test_json_fences(text: str, expected: str) -> None:
    assert unfence(text) == expected


def test_fixture_layers_compose_in_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from evals import profiles

    for layer in ("shared", "specific"):
        directory = tmp_path / "fixtures" / layer
        directory.mkdir(parents=True)
        (directory / "config.ml").write_text(layer)
    (tmp_path / "fixtures/shared/check.sh").write_text("shared runner")
    monkeypatch.setattr(profiles, "EVALS_ROOT", tmp_path)
    case = Case(
        id="composed",
        skill="reasoning",
        fixtures=["shared", "specific"],
        allowed_files=[],
        prompt="Check the fixture",
    )
    files = files_for(case, "baseline")
    assert Path(files["workspace/config.ml"]).read_text() == "specific"
    assert Path(files["workspace/check.sh"]).read_text() == "shared runner"
