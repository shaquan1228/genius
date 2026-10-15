"""Exercise trusted kernel requests independently of Inspect adapters."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from evals.python.transport import LIBRARY, RUNNER, SUITE, grade, load_cases


def judgment(*, response: str, suite: Path = SUITE) -> bool:
    return grade(
        "small-decision", response=response, changed_files=(), code_passed=False, suite=suite
    )["correctness"]


def test_kernel_grades_response_and_scope() -> None:
    scores = grade(
        "small-decision",
        response='{"choice":"B","reason":"Lower cost."}',
        changed_files=(),
        code_passed=False,
    )
    assert dict(scores) == {"correctness": True, "scope": True}
    with pytest.raises(TypeError):
        scores["scope"] = False  # type: ignore[index]


@pytest.mark.parametrize(
    "response",
    [
        "version-missing",
        '{"version":2,"scores":{"correctness":true,"scope":true}}',
        '{"version":true,"scores":{"correctness":true,"scope":true}}',
        '{"version":1,"scores":{"correctness":1,"scope":true}}',
        '{"version":1,"scores":{"correctness":true,"scope":"true"}}',
        '{"version":1,"scores":{"correctness":true,"scope":true},"extra":1}',
    ],
)
def test_invalid_kernel_output_is_a_harness_error(response: str) -> None:
    judgment(response="{}")
    with (
        patch(
            "evals.python.transport.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, stdout=response),
        ),
        pytest.raises(ValidationError),
    ):
        judgment(response="{}")


def test_unknown_kernel_score_names_are_rejected() -> None:
    judgment(response="{}")
    with (
        patch(
            "evals.python.transport.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, stdout='{"version":1,"scores":{}}'),
        ),
        pytest.raises(ValueError, match="score names"),
    ):
        judgment(response="{}")


def test_unknown_case_is_a_harness_error() -> None:
    with pytest.raises(subprocess.CalledProcessError):
        grade("unknown", response="{}", changed_files=(), code_passed=False)


@pytest.mark.parametrize("error", [TimeoutError("timeout"), subprocess.CalledProcessError(1, [])])
def test_kernel_process_errors_propagate(error: Exception) -> None:
    judgment(response="{}")
    with (
        patch("evals.python.transport.subprocess.run", side_effect=error),
        pytest.raises(type(error)),
    ):
        judgment(response="{}")


def test_candidate_response_cannot_execute_code(tmp_path: Path) -> None:
    sentinel = tmp_path / "candidate-ran"
    candidate = f'let () = let c = open_out "{sentinel}" in close_out c'
    assert not judgment(response=candidate)
    assert not sentinel.exists()


def test_grading_does_not_recompile_or_cache_results() -> None:
    judgment(response="{}")
    responses = ("invalid", '{"choice":"B","reason":"Cheap"}', '{"choice":"A","reason":"Cheap"}')
    with patch("evals.python.transport.subprocess.run", wraps=subprocess.run) as process:
        observed = [judgment(response=response) for response in responses]
        assert observed == [False, True, False]
        assert [call.args[0][1:] for call in process.call_args_list] == [["--grade"]] * 3


@pytest.mark.parametrize("source", [*LIBRARY, RUNNER])
def test_kernel_cache_tracks_every_trusted_source(*, source: Path, tmp_path: Path) -> None:
    copied = tmp_path / source.name
    copied.write_text(source.read_text() + "\n")
    judgment(response="{}")
    library = tuple({source: copied}.get(path, path) for path in LIBRARY)
    runner = {source: copied}.get(RUNNER, RUNNER)
    with (
        patch("evals.python.transport.LIBRARY", library),
        patch("evals.python.transport.RUNNER", runner),
        patch("evals.python.transport.subprocess.run", wraps=subprocess.run) as process,
    ):
        assert judgment(response='{"choice":"B","reason":"Cheap"}')
        assert process.call_count == 2
        assert process.call_args_list[0].args[0][0] == "ocamlfind"


@pytest.mark.parametrize(
    "changed",
    [(), ("workspace/receipt.ml",), ("workspace/extra.ml",), ("instructions/SKILL.md",)],
)
def test_scope_and_code_result_are_kernel_policy(changed: tuple[str, ...]) -> None:
    for passed in (False, True):
        scores = grade("clear-task", response="", changed_files=changed, code_passed=passed)
        assert dict(scores) == {
            "correctness": passed,
            "scope": changed in ((), ("workspace/receipt.ml",)),
        }


def generic_suite(tmp_path: Path, *, expected: str, text_rule: str = "") -> Path:
    suite = tmp_path / "suite.ml"
    suite.write_text(f"""let cases = [Case.make ~id:"small-decision" ~fixture:Fixture.empty
      ~instruction:(Instruction.make ~skill:"reasoning" ~prompt:"Custom answer")
      ~criterion:(Criterion.answer {text_rule} ~expected:(Response.of_fields [{expected}]) ())
      ~allowed_files:[] ~reference:(Reference.make (Plain "reference"))]
""")
    return suite


@pytest.mark.parametrize(
    ("response", "passed"),
    [
        ('{"status":"ready","safe":true,"explanation":"All good"}', True),
        ('{"status":"ready","safe":true,"explanation":"All is good"}', True),
        ('{"status":"ready","safe":1,"explanation":"All good"}', False),
        ('{"status":"ready","safe":true,"explanation":"Good"}', False),
        ('{"status":"ready","safe":true,"explanation":"All is very good"}', False),
    ],
)
def test_unrelated_answer_shape_requires_only_suite_data(
    *, response: str, passed: bool, tmp_path: Path
) -> None:
    suite = generic_suite(
        tmp_path,
        expected='"status", Response.String "ready"; "safe", Response.Bool true',
        text_rule='~text_rule:(Criterion.text_rule ~field:"explanation" ~min_words:2 ~max_words:3)',
    )
    assert load_cases(suite)[0].checks.model_dump() == {"kind": "answer"}
    assert judgment(response=response, suite=suite) == passed


@pytest.mark.parametrize(
    "expected", ['"status", Response.String "ready"', '"reason", Response.String "exact"']
)
def test_exact_fields_have_no_implicit_reason_policy(*, expected: str, tmp_path: Path) -> None:
    suite = generic_suite(tmp_path, expected=expected)
    fields = {"reason": "exact"} if expected.startswith('"reason"') else {"status": "ready"}
    assert judgment(response=json.dumps(fields), suite=suite)
    assert not judgment(response=json.dumps({**fields, "extra": "value"}), suite=suite)


def test_zero_word_text_rule_can_be_the_only_criterion(tmp_path: Path) -> None:
    suite = generic_suite(
        tmp_path,
        expected="",
        text_rule='~text_rule:(Criterion.text_rule ~field:"note" ~min_words:0 ~max_words:0)',
    )
    assert judgment(response='{"note":""}', suite=suite)
    for response in ("{}", '{"note":true}', '{"note":"word"}'):
        assert not judgment(response=response, suite=suite)


@pytest.mark.parametrize("words", [0, 1, 40, 41])
@pytest.mark.parametrize("case_id", ["small-decision", "decision-review"])
def test_existing_reason_bounds_include_unicode_whitespace(*, words: int, case_id: str) -> None:
    fields: dict[str, str | bool] = (
        {"choice": "B"}
        if case_id == "small-decision"
        else {"decision_was_supported": True, "change_rule": False}
    )
    scores = grade(
        case_id,
        response=json.dumps({**fields, "reason": "\u2003".join(["word"] * words)}),
        changed_files=(),
        code_passed=False,
    )
    assert scores["correctness"] == (1 <= words <= 40)


@pytest.mark.parametrize(
    "response",
    [
        '{"choice":"B","reason":"ok","unused":null}',
        '{"choice":[],"reason":"ok"}',
        '{"choice":{},"reason":"ok"}',
        "```json\n{}",
        "[" * 10_000 + "]" * 10_000,
    ],
)
def test_invalid_candidate_values_fail_without_harness_error(response: str) -> None:
    assert not judgment(response=response)


def test_candidate_duplicate_keys_keep_last_value() -> None:
    assert judgment(response='{"choice":"A","choice":"B","reason":"Cheap"}')


def test_additional_named_scores_cross_bridge_without_decoder_changes() -> None:
    judgment(response="{}")
    response = '{"version":1,"scores":{"correctness":true,"scope":false,"new_metric":true}}'
    with patch(
        "evals.python.transport.subprocess.run",
        return_value=subprocess.CompletedProcess([], 0, stdout=response),
    ):
        scores = grade("small-decision", response="{}", changed_files=(), code_passed=False)
    assert dict(scores) == {"correctness": True, "scope": False, "new_metric": True}


@pytest.mark.parametrize(
    "codepoint",
    [
        *range(9, 14),
        *range(28, 33),
        133,
        160,
        5760,
        *range(8192, 8203),
        8232,
        8233,
        8239,
        8287,
        12288,
        8203,
    ],
)
def test_kernel_word_splitting_matches_python(*, codepoint: int, tmp_path: Path) -> None:
    suite = generic_suite(
        tmp_path,
        expected="",
        text_rule='~text_rule:(Criterion.text_rule ~field:"note" ~min_words:2 ~max_words:2)',
    )
    text = f"first{chr(codepoint)}second"
    assert judgment(response=json.dumps({"note": text}), suite=suite) == (len(text.split()) == 2)


def test_reference_channels_export_independently_and_escape(tmp_path: Path) -> None:
    suite = tmp_path / "suite.ml"
    suite.write_text(r"""let fields = Response.of_fields [
      "state", Response.String "quote\" \\ \n é";
      "safe", Response.Bool true]
let cases = [Case.make ~id:"reference" ~fixture:Fixture.empty
  ~instruction:(Instruction.make ~skill:"reasoning" ~prompt:"fields")
  ~criterion:(Criterion.answer ~expected:fields ()) ~allowed_files:["result.txt"]
  ~reference:(Reference.make ~edits:(Fixture.of_files ["result.txt", "result"])
    (Structured fields))]
""")
    case = load_cases(suite)[0]
    assert dict(case.solution) == {"result.txt": "result"}
    assert json.loads(case.answer) == {"state": 'quote" \\ \n é', "safe": True}
    assert grade(
        "reference", response=case.answer, changed_files=(), code_passed=False, suite=suite
    )["correctness"]


@pytest.mark.parametrize(
    "response",
    [
        '{"choice":/*comment*/"B","reason":"ok"}',
        '{"choice":"B","reason":"raw\nnewline"}',
        '{"choice":"B","reason":"ok",}',
    ],
)
def test_nonstandard_json_is_an_incorrect_candidate(response: str) -> None:
    assert not judgment(response=response)
