"""Validate schemas and keep the comparison's inputs controlled."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from genius_evals.answers import grade_answer, unfence
from genius_evals.cases import CaseId, load_cases, state_case
from genius_evals.profiles import content_hash, files_for, prompt_for, samples
from tests.scenarios import ANSWERS


def test_manifest_roundtrip() -> None:
    cases = load_cases()
    assert [state_case({"case": case.model_dump()}) for case in cases] == cases


def test_invalid_manifest_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "cases.json"
    path.write_text('[{"id":"unknown"}]')
    with pytest.raises(ValidationError):
        load_cases(path)


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
def test_correct_decision_outputs(case_id: CaseId) -> None:
    assert grade_answer(case_id, ANSWERS[case_id])


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
