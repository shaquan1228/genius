import json
from pathlib import Path

import pytest
from kernel import Outcome, Verification
from pydantic import JsonValue

from evals.python.integrations.inspect.scoring import (
    decode_response,
    observed,
    representable,
    unrepresentable,
)


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
    reply = decode_response('{"items":[1,null,{"x":[]}]}')
    assert reply == {"items": [1, None, {"x": []}]}
    assert observed(reply) is reply


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (2**63, {"unrepresentable": "int"}),
        ({"count": -(2**64), "kept": 1}, {"count": {"unrepresentable": "int"}, "kept": 1}),
        ({1: "key"}, {"1": "key"}),
        ((1, 2**64), [1, {"unrepresentable": "int"}]),
        (object(), {"unrepresentable": "object"}),
    ],
)
def unrepresentable_parts_become_records_naming_their_type(
    data: object, *, expected: JsonValue
) -> None:
    assert observed(data) == expected


def _nested(depth: int, *, leaf: object) -> object:
    data = leaf
    for _ in range(depth):
        data = [data]
    return data


def _held(data: object) -> bool:
    try:
        Outcome(changed_files=[], verification=Verification.unchecked(), response=data, facts=[])
    except (TypeError, ValueError, OverflowError):
        return False
    return True


@pytest.mark.parametrize(
    "data",
    [
        _nested(255, leaf=1),
        _nested(255, leaf=[]),
        _nested(254, leaf={"a": 1}),
        _nested(254, leaf={"a": []}),
        _nested(300, leaf=None),
        -(2**63),
        2**63 - 1,
        2**63,
        float("nan"),
        {1: "key"},
        b"bytes",
        {"set": {1}},
    ],
)
def representability_matches_the_kernel(data: object) -> None:
    assert representable(data) is _held(data)
    assert _held(observed(data))


def unrepresentable_names_the_channels_the_kernel_cannot_hold() -> None:
    channels = {"response": {"id": 2**64}, "trace": [], "state": {1: "key"}}
    assert unrepresentable(channels) == ["response", "state"]


def candidate_text_cannot_execute_code(tmp_path: Path) -> None:
    sentinel = tmp_path / "candidate-ran"
    assert decode_response(f'let () = let c = open_out "{sentinel}" in close_out c') is None
    assert not sentinel.exists()
