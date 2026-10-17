"""Candidate response decoding and native boolean score adaptation."""

import json
from collections.abc import Mapping
from types import MappingProxyType

from pydantic import validate_call

from evals.python import datasets
from evals.python.datasets import Selection
from evals.python.schema import FROZEN
from kernel import Completion, Outcome, Response, ResponseField, ResponseValue, Task, Verification

__all__ = ["Scores", "score_case"]

type Scores = Mapping[str, bool]
UNCHECKED = Verification.Unchecked()


def _scalar(value: object) -> ResponseValue.Value:
    if isinstance(value, bool):
        return ResponseValue.create(bool=value)
    if isinstance(value, str):
        return ResponseValue.create(string=value)
    raise ValueError("Response fields must be strings or booleans")


def _response(fields: object) -> Response:
    if not isinstance(fields, dict):
        raise ValueError("Expected response object")
    return Response.create(
        fields=[
            ResponseField.create(name=name, value=_scalar(value)) for name, value in fields.items()
        ]
    )


def _candidate(text: str) -> Response | None:
    text = Completion.trim(text=text)
    if text.startswith("```json\n") and text.endswith("\n```"):
        text = text[8:-4]
    try:
        return _response(json.loads(text))
    except (ValueError, RecursionError):
        return None


@validate_call(config=FROZEN)
def score_case(
    *,
    case_id: str,
    response: str,
    changed_files: tuple[str, ...],
    verification: Verification.Value = UNCHECKED,
    selection: Selection = "smoke",
) -> Scores:
    pairs = Task.grade(
        task=datasets.record(case_id, selection=selection),
        response=_candidate(response),
        outcome=Outcome.create(changed_files=changed_files, verification=verification),
    )
    return MappingProxyType(dict(pairs))
