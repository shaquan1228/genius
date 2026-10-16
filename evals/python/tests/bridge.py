"""Exercise trusted kernel requests independently of Inspect adapters."""

import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from evals.python import datasets, query
from evals.python.datasets import Selection
from evals.python.query import GradeCase
from evals.python.tests.declarations import _declaration, _reference_files, _reference_text
from evals.python.tests.projections import reference, verifier
from kernel import load
from kernel.build import LIBRARY, build


def commands_and_queries_use_in_process_kernel_calls() -> None:
    dataset = query.CompileDataset(cases=(_declaration(code=False),))
    with patch("subprocess.run", side_effect=AssertionError("Kernel calls must stay in process")):
        assert query.ExperimentSettings(epochs=2).epochs == 2
        assert query.Cases(selection=dataset)[0].id == "external"
        assert query.GradeCase(
            case_id="external",
            selection=dataset,
            response='{"choice":"B","safe":true,"reason":"clear"}',
            changed_files=(),
        ) == {"correctness": True, "scope": True}


def _judgment(*, response: str, suite: Selection = "smoke") -> bool:
    return GradeCase(
        case_id="small-decision",
        response=response,
        changed_files=(),
        verification=query.Ast.Unchecked(),
        selection=suite,
    )["correctness"]


def kernel_grades_response_and_scope() -> None:
    scores = GradeCase(
        case_id="small-decision",
        response='{"choice":"B","reason":"Lower cost."}',
        changed_files=(),
        verification=query.Ast.Unchecked(),
    )
    assert dict(scores) == {"correctness": True, "scope": True}
    with pytest.raises(TypeError):
        scores["scope"] = False  # type: ignore[index]


def unknown_kernel_score_names_are_rejected() -> None:
    native = load(datasets.kernel_sources().modules)
    with (
        patch.object(native.Grader, "grade", return_value=[]),
        pytest.raises(ValueError, match="score names"),
    ):
        _judgment(response="{}")


def unknown_case_is_a_harness_error() -> None:
    with pytest.raises(KeyError):
        GradeCase(
            case_id="unknown",
            response="{}",
            changed_files=(),
            verification=query.Ast.Unchecked(),
        )


def native_kernel_errors_propagate() -> None:
    native = load(datasets.kernel_sources().modules)
    with (
        patch.object(native.Grader, "grade", side_effect=RuntimeError("kernel failed")),
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
    native = load(datasets.kernel_sources().modules)
    responses = ("invalid", '{"choice":"B","reason":"Cheap"}', '{"choice":"A","reason":"Cheap"}')
    with (
        patch("kernel.build.subprocess.run", side_effect=AssertionError("Unexpected compilation")),
        patch.object(native.Grader, "grade", wraps=native.Grader.grade) as grade,
    ):
        assert [_judgment(response=response) for response in responses] == [False, True, False]
        assert grade.call_count == 3


@pytest.mark.parametrize("source", LIBRARY)
def kernel_fingerprint_tracks_every_trusted_source(source: Path) -> None:
    original = datasets.kernel_sources()
    changed = datasets.Sources(
        modules=tuple(
            (name, contents + "\n" if name == source.name else contents)
            for name, contents in original.modules
        ),
        resources=original.resources,
    )
    assert datasets.fingerprint(changed) != datasets.fingerprint(original)


def kernel_compilation_failure_cleans_temporary_directory(tmp_path: Path) -> None:
    directory = TemporaryDirectory(dir=tmp_path)
    modules = tuple(
        (name, "this is not OCaml" if name == "criterion.ml" else contents)
        for name, contents in datasets.kernel_sources().modules
    )
    with (
        patch("kernel.build.TemporaryDirectory", return_value=directory),
        pytest.raises(subprocess.CalledProcessError),
    ):
        build(modules)
    assert not Path(directory.name).exists()


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
    native = load(datasets.kernel_sources().modules)
    with patch.object(
        native.Grader,
        "grade",
        return_value=[("correctness", True), ("scope", False), ("new_metric", True)],
    ):
        scores = GradeCase(
            case_id="small-decision",
            response="{}",
            changed_files=(),
            verification=query.Ast.Unchecked(),
        )
    assert dict(scores) == {"correctness": True, "scope": False, "new_metric": True}


def reference_channels_export_independently_and_escape() -> None:
    fields: dict[str, str | bool] = {"state": 'quote" \\ \n é', "safe": True}
    dataset = query.CompileDataset(
        cases=(
            query.Ast.case(
                id="reference",
                fixture=query.Fixture.empty,
                instruction=query.Ast.instruction(skill="reasoning", prompt="fields"),
                criterion=query.Ast.Answer(
                    query.Ast.answer(
                        expected=[
                            (
                                name,
                                query.Ast.Bool(value)
                                if isinstance(value, bool)
                                else query.Ast.String(value),
                            )
                            for name, value in fields.items()
                        ],
                        text_rule=None,
                    )
                ),
                allowed_files=("result.txt",),
                reference=query.Ast.reference(
                    edits=query.Fixture.of_files([("result.txt", "result")]),
                    completion=query.Ast.Structured(
                        [
                            (
                                name,
                                query.Ast.Bool(value)
                                if isinstance(value, bool)
                                else query.Ast.String(value),
                            )
                            for name, value in fields.items()
                        ]
                    ),
                ),
            ),
        )
    )
    case = query.Cases(selection=dataset)[0]
    expected = reference(case.id, selection=dataset)
    assert verifier(case.id, selection=dataset) is None
    assert dict(_reference_files(expected)) == {"result.txt": "result"}
    assert json.loads(_reference_text(expected)) == fields
    assert GradeCase(
        case_id="reference",
        response=_reference_text(expected),
        changed_files=(),
        verification=query.Ast.Unchecked(),
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
