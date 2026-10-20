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
def json_and_fences_decode_to_native_values(text: str) -> None:
    assert decode_response(text) == {"choice": "B", "reason": "Cheap"}


@pytest.mark.parametrize(
    "text",
    [
        "```json\n{}",
        "not JSON",
        "[" * 10_000 + "]" * 10_000,
        '{"choice":/*comment*/"B"}',
        '{"choice":"raw\nnewline"}',
        '{"choice":"B",}',
    ],
)
def malformed_candidates_produce_a_null_response(text: str) -> None:
    assert decode_response(text) is None


@pytest.mark.parametrize("safe", [True, False])
def scalar_values_preserve_types_and_escaping(*, safe: bool) -> None:
    fields = {"state": 'quote" \\ \n é', "safe": safe, "empty": "", "count": 5, "ratio": 0.5}
    result = decode_response(json.dumps(fields))
    assert result == fields
    assert isinstance(result, dict)
    assert result["safe"] is safe


def duplicate_keys_keep_the_last_json_value() -> None:
    assert decode_response('{"choice":"A","choice":"B"}') == {"choice": "B"}


def nested_replies_decode_to_lists_and_records() -> None:
    assert decode_response('{"items":[1,null,{"x":[]}]}') == {"items": [1, None, {"x": []}]}


def candidate_text_cannot_execute_code(tmp_path: Path) -> None:
    sentinel = tmp_path / "candidate-ran"
    assert decode_response(f'let () = let c = open_out "{sentinel}" in close_out c') is None
    assert not sentinel.exists()
