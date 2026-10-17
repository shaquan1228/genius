"""Candidate response decoding and native boolean score adaptation."""

import json
from collections.abc import Mapping
from operator import itemgetter
from types import MappingProxyType

from pydantic import validate_call

from evals.python import datasets
from evals.python.datasets import Selection
from evals.python.schema import FROZEN
from kernel import InvalidArgument, Outcome, Response, ResponseValue, Task, Verification
from kernel._operations import grader as grader_ops
from kernel._operations import response as response_ops

__all__ = ["Scores", "score_case"]

type Scores = Mapping[str, bool]
UNCHECKED = Verification.Unchecked()


def _scalar(value: object) -> ResponseValue.Value:
    if isinstance(value, bool):
        return ResponseValue.Bool(value)
    if isinstance(value, str):
        return ResponseValue.String(value)
    raise ValueError("Response fields must be strings or booleans")


def _response(fields: object) -> Response:
    if not isinstance(fields, dict):
        raise ValueError("Expected response object")
    return response_ops.of_fields([(name, _scalar(value)) for name, value in fields.items()])


def _candidate(text: str) -> Response | None:
    text = grader_ops.trim(text)
    if text.startswith("```json\n") and text.endswith("\n```"):
        text = text[8:-4]
    try:
        return _response(json.loads(text))
    except (ValueError, RecursionError, InvalidArgument):
        return None


def score(
    case: Task, *, response: str, changed_files: tuple[str, ...], verification: Verification.Value
) -> Scores:
    pairs = grader_ops.grade(
        case,
        response=_candidate(response),
        outcome=Outcome(changed_files=changed_files, verification=verification),
    )
    names = tuple(map(itemgetter(0), pairs))
    if len(set(names)) != len(names):
        raise ValueError("Kernel returned duplicate score names")
    if not all(isinstance(value, bool) for _, value in pairs):
        raise ValueError("Kernel returned non-boolean scores")
    if not set(grader_ops.required_names) <= set(names):
        raise ValueError("Kernel omitted required score names")
    return MappingProxyType(dict(pairs))


@validate_call(config=FROZEN)
def score_case(
    *,
    case_id: str,
    response: str,
    changed_files: tuple[str, ...],
    verification: Verification.Value = UNCHECKED,
    selection: Selection = "smoke",
) -> Scores:
    return score(
        datasets.record(case_id, selection=selection),
        response=response,
        changed_files=changed_files,
        verification=verification,
    )
