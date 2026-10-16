"""Exercise trusted kernel requests independently of Inspect adapters."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from evals.python._kernel import Verification
from evals.python.catalog import (
    DRIVERS,
    Selection,
    load_cases,
    reference,
    verifier,
)
from evals.python.query import GradeCase
from evals.python.transport import LIBRARY


def _judgment(*, response: str, suite: Selection = "smoke") -> bool:
    return GradeCase(
        case_id="small-decision",
        response=response,
        changed_files=(),
        verification=Verification(status="unchecked"),
        selection=suite,
    )["correctness"]


def kernel_grades_response_and_scope() -> None:
    scores = GradeCase(
        case_id="small-decision",
        response='{"choice":"B","reason":"Lower cost."}',
        changed_files=(),
        verification=Verification(status="unchecked"),
    )
    assert dict(scores) == {"correctness": True, "scope": True}
    with pytest.raises(TypeError):
        scores["scope"] = False  # type: ignore[index]


@pytest.mark.parametrize(
    "response",
    [
        "version-missing",
        '{"version":1,"scores":{"correctness":true,"scope":true}}',
        '{"version":true,"scores":{"correctness":true,"scope":true}}',
        '{"version":3,"scores":{"correctness":1,"scope":true}}',
        '{"version":3,"scores":{"correctness":true,"scope":"true"}}',
        '{"version":3,"scores":{"correctness":true,"scope":true},"extra":1}',
    ],
)
def invalid_kernel_output_is_a_harness_error(response: str) -> None:
    _judgment(response="{}")
    with (
        patch(
            "evals.python.transport.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, stdout=response),
        ),
        pytest.raises(ValidationError),
    ):
        _judgment(response="{}")


def unknown_kernel_score_names_are_rejected() -> None:
    _judgment(response="{}")
    with (
        patch(
            "evals.python.transport.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, stdout='{"version":3,"scores":{}}'),
        ),
        pytest.raises(ValueError, match="score names"),
    ):
        _judgment(response="{}")


def unknown_case_is_a_harness_error() -> None:
    with pytest.raises(subprocess.CalledProcessError):
        GradeCase(
            case_id="unknown",
            response="{}",
            changed_files=(),
            verification=Verification(status="unchecked"),
        )


@pytest.mark.parametrize("error", [TimeoutError("timeout"), subprocess.CalledProcessError(1, [])])
def kernel_process_errors_propagate(error: Exception) -> None:
    _judgment(response="{}")
    with (
        patch("evals.python.transport.subprocess.run", side_effect=error),
        pytest.raises(type(error)),
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
    with patch("evals.python.transport.subprocess.run", wraps=subprocess.run) as process:
        observed = [_judgment(response=response) for response in responses]
        assert observed == [False, True, False]
        assert [call.args[0][1:] for call in process.call_args_list] == [["--grade"]] * 3


@pytest.mark.parametrize("source", [*LIBRARY, *DRIVERS])
def kernel_cache_tracks_every_trusted_source(*, source: Path, tmp_path: Path) -> None:
    copied = tmp_path / source.name
    copied.write_text(source.read_text() + "\n")
    _judgment(response="{}")
    library = tuple({source: copied}.get(path, path) for path in LIBRARY)
    drivers = tuple({source: copied}.get(path, path) for path in DRIVERS)
    with (
        patch("evals.python.transport.LIBRARY", library),
        patch("evals.python.catalog.DRIVERS", drivers),
        patch("evals.python.transport.subprocess.run", wraps=subprocess.run) as process,
    ):
        assert _judgment(response='{"choice":"B","reason":"Cheap"}')
        assert (process.call_count, process.call_args_list[0].args[0][0]) == (3, "ocamlfind")


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
    _judgment(response="{}")
    response = '{"version":3,"scores":{"correctness":true,"scope":false,"new_metric":true}}'
    with patch(
        "evals.python.transport.subprocess.run",
        return_value=subprocess.CompletedProcess([], 0, stdout=response),
    ):
        scores = GradeCase(
            case_id="small-decision",
            response="{}",
            changed_files=(),
            verification=Verification(status="unchecked"),
        )
    assert dict(scores) == {"correctness": True, "scope": False, "new_metric": True}


def reference_channels_export_independently_and_escape(tmp_path: Path) -> None:
    suite = tmp_path / "suite.ml"
    suite.write_text(r"""let fields = Response.of_fields [
      "state", Ast.String "quote\" \\ \n é";
      "safe", Ast.Bool true]
let cases = [Case.make ~id:"reference" ~fixture:Fixture.empty
  ~instruction:{ Ast.skill = "reasoning"; prompt = "fields" }
  ~criterion:(Criterion.answer ~expected:fields ()) ~allowed_files:["result.txt"]
  ~reference:{ Ast.edits = Fixture.of_files ["result.txt", "result"];
    completion = Structured fields }]
""")
    case = load_cases(selection=suite)[0]
    expected = reference(case.id, selection=suite)
    assert verifier(case.id, selection=suite) is None
    assert dict(expected.solution) == {"result.txt": "result"}
    assert json.loads(expected.answer) == {"state": 'quote" \\ \n é', "safe": True}
    assert GradeCase(
        case_id="reference",
        response=expected.answer,
        changed_files=(),
        verification=Verification(status="unchecked"),
        selection=suite,
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
