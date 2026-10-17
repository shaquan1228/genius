"""Exercise trusted kernel requests independently of Inspect adapters."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from evals.python import datasets, evaluation, grading
from evals.python.datasets import Selection, Sources
from evals.python.grading import score_case
from evals.python.tests.declarations import _declaration, _reference_files, _reference_text
from evals.python.tests.projections import reference, verifier
from kernel import (
    Completion,
    Criterion,
    File,
    Fixture,
    Instruction,
    Reference,
    Response,
    ResponseField,
    ResponseValue,
    Rubric,
    Task,
    Verification,
    sources,
)
from kernel import grader as grader_ops


def commands_and_queries_use_in_process_kernel_calls() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(code=False),))
    with patch("subprocess.run", side_effect=AssertionError("Kernel calls must stay in process")):
        assert evaluation.resolve_settings(epochs=2).epochs == 2
        assert datasets.list_cases(selection=dataset)[0].id == "external"
        assert grading.score_case(
            case_id="external",
            selection=dataset,
            response='{"choice":"B","safe":true,"reason":"clear"}',
            changed_files=(),
        ) == {"correctness": True, "scope": True}


def _judgment(*, response: str, suite: Selection = "smoke") -> bool:
    return score_case(
        case_id="small-decision",
        response=response,
        changed_files=(),
        verification=Verification.Unchecked(),
        selection=suite,
    )["correctness"]


def kernel_grades_response_and_scope() -> None:
    scores = score_case(
        case_id="small-decision",
        response='{"choice":"B","reason":"Lower cost."}',
        changed_files=(),
        verification=Verification.Unchecked(),
    )
    assert dict(scores) == {"correctness": True, "scope": True}
    with pytest.raises(TypeError):
        scores["scope"] = False  # type: ignore[index]


def unknown_case_is_a_harness_error() -> None:
    with pytest.raises(KeyError):
        score_case(
            case_id="unknown",
            response="{}",
            changed_files=(),
            verification=Verification.Unchecked(),
        )


def native_kernel_errors_propagate() -> None:
    with (
        patch.object(grader_ops, "grade", side_effect=RuntimeError("kernel failed")),
        pytest.raises(RuntimeError, match="kernel failed"),
    ):
        _judgment(response="{}")


def candidate_response_cannot_execute_code(tmp_path: Path) -> None:
    sentinel = tmp_path / "candidate-ran"
    candidate = f'let () = let c = open_out "{sentinel}" in close_out c'
    assert not _judgment(response=candidate)
    assert not sentinel.exists()


def grading_does_not_recompile_or_cache_results() -> None:
    _judgment(response="{}")
    responses = ("invalid", '{"choice":"B","reason":"Cheap"}', '{"choice":"A","reason":"Cheap"}')
    with (
        patch("subprocess.run", side_effect=AssertionError("Unexpected compilation")),
        patch.object(grader_ops, "grade", wraps=grader_ops.grade) as grade,
    ):
        assert [_judgment(response=response) for response in responses] == [False, True, False]
        assert grade.call_count == 3


@pytest.mark.parametrize("source", [name for name, _ in sources()])
def kernel_fingerprint_tracks_every_trusted_source(source: str) -> None:
    original = datasets.kernel_sources()
    changed = Sources(
        modules=tuple(
            (name, contents + "\n" if name == source else contents)
            for name, contents in original.modules
        ),
        resources=original.resources,
    )
    assert datasets.fingerprint(changed) != datasets.fingerprint(original)


@pytest.mark.parametrize(
    "response",
    [
        '{"choice":"B","reason":"ok","unused":null}',
        '{"choice":[],"reason":"ok"}',
        '{"choice":{},"reason":"ok"}',
        "```json\n{}",
        "[]",
        "not JSON",
        '{"choice":"B","reason":5}',
        "[" * 10_000 + "]" * 10_000,
    ],
)
def invalid_candidate_values_fail_without_harness_error(response: str) -> None:
    assert not _judgment(response=response)


def candidate_duplicate_keys_keep_last_value() -> None:
    assert _judgment(response='{"choice":"A","choice":"B","reason":"Cheap"}')


def additional_named_scores_cross_bridge_without_decoder_changes() -> None:
    with patch.object(
        grader_ops,
        "grade",
        return_value=[("correctness", True), ("scope", False), ("new_metric", True)],
    ):
        scores = score_case(
            case_id="small-decision",
            response="{}",
            changed_files=(),
            verification=Verification.Unchecked(),
        )
    assert dict(scores) == {"correctness": True, "scope": False, "new_metric": True}


def reference_channels_export_independently_and_escape() -> None:
    state = 'quote" \\ \n é'
    fields: dict[str, str | bool] = {"state": state, "safe": True}
    safe = True
    expected_fields = Response.create(
        fields=[
            ResponseField.create(name="state", value=ResponseValue.create(string=state)),
            ResponseField.create(name="safe", value=ResponseValue.create(bool=safe)),
        ]
    )
    dataset = datasets.compile_dataset(
        cases=(
            Task.create(
                id="reference",
                fixture=Fixture.create(files=[]),
                instruction=Instruction.create(skill="reasoning", prompt="fields"),
                criterion=Criterion.create(
                    answer=Rubric.create(expected=expected_fields, text_rule=None)
                ),
                allowed_files=("result.txt",),
                reference=Reference.create(
                    edits=Fixture.create(files=[File.create(path="result.txt", contents="result")]),
                    completion=Completion.create(structured=expected_fields),
                ),
            ),
        )
    )
    case = datasets.list_cases(selection=dataset)[0]
    expected = reference(case.id, selection=dataset)
    assert verifier(case.id, selection=dataset) is None
    assert dict(_reference_files(expected)) == {"result.txt": "result"}
    assert json.loads(_reference_text(expected)) == fields
    assert score_case(
        case_id="reference",
        response=_reference_text(expected),
        changed_files=(),
        verification=Verification.Unchecked(),
        selection=dataset,
    )["correctness"]


@pytest.mark.parametrize(
    "response",
    [
        '{"choice":/*comment*/"B","reason":"ok"}',
        '{"choice":"B","reason":"raw\nnewline"}',
        '{"choice":"B","reason":"ok",}',
    ],
)
def nonstandard_json_is_an_incorrect_candidate(response: str) -> None:
    assert not _judgment(response=response)
