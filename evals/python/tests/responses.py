import json
from pathlib import Path

import pytest

from evals.python.integrations.inspect.scoring import decode_response


@pytest.mark.parametrize(
    "text",
    [
        '  {"choice":"B","reason":"Cheap"}  ',
        '```json\n{"choice":"B","reason":"Cheap"}\n```',
        '\u2003{"choice":"B","reason":"Cheap"}\u2003',
    ],
)
def json_and_fences_decode_to_native_fields(text: str) -> None:
    result = decode_response(text)
    assert result is not None
    assert {field.name: field.value.value for field in result.fields} == {
        "choice": "B",
        "reason": "Cheap",
    }


@pytest.mark.parametrize(
    "text",
    [
        '{"":"x"}',
        '{"unused":null}',
        '{"choice":[]}',
        '{"choice":{}}',
        '{"choice":5}',
        "```json\n{}",
        "[]",
        "not JSON",
        "[" * 10_000 + "]" * 10_000,
        '{"choice":/*comment*/"B"}',
        '{"choice":"raw\nnewline"}',
        '{"choice":"B",}',
    ],
)
def malformed_candidates_produce_no_structured_response(text: str) -> None:
    assert decode_response(text) is None


@pytest.mark.parametrize("safe", [True, False])
def scalar_values_preserve_types_and_escaping(*, safe: bool) -> None:
    fields = {"state": 'quote" \\ \n é', "safe": safe, "empty": ""}
    result = decode_response(json.dumps(fields))
    assert result is not None
    assert {field.name: field.value.value for field in result.fields} == fields


def duplicate_keys_keep_the_last_json_value() -> None:
    result = decode_response('{"choice":"A","choice":"B"}')
    assert result is not None
    assert result.fields[0].value.value == "B"


def candidate_text_cannot_execute_code(tmp_path: Path) -> None:
    sentinel = tmp_path / "candidate-ran"
    assert decode_response(f'let () = let c = open_out "{sentinel}" in close_out c') is None
    assert not sentinel.exists()
