"""Candidate response decoding and native boolean score adaptation."""

import json
from collections.abc import Mapping
from contextlib import suppress
from types import MappingProxyType

from pydantic import TypeAdapter, validate_call

from evals.python import datasets
from evals.python.datasets import Selection
from evals.python.schema import FROZEN
from kernel import (
    Completion,
    Outcome,
    Response,
    ResponseField,
    ResponseValue,
    Task,
    TaskGrade,
    Verification,
)

__all__ = ["Scores", "grade_case", "score_case"]

type Scores = Mapping[str, bool]
UNCHECKED = Verification.Unchecked()
_RESPONSE_FIELDS = TypeAdapter(dict[str, str | bool], config=FROZEN)


def _parse_response(text: str) -> Response | None:
    text = Completion.trim(text=text)
    if text.startswith("```json\n") and text.endswith("\n```"):
        text = text[8:-4]
    with suppress(ValueError, RecursionError):
        fields = _RESPONSE_FIELDS.validate_python(json.loads(text))
        return Response.create(
            fields=[
                ResponseField.create(
                    name=name,
                    value=(
                        ResponseValue.create(bool=value)
                        if isinstance(value, bool)
                        else ResponseValue.create(string=value)
                    ),
                )
                for name, value in fields.items()
            ]
        )
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
        response=_parse_response(response),
        outcome=Outcome.create(changed_files=changed_files, verification=verification),
    )
    return MappingProxyType(dict(pairs))


@validate_call(config=FROZEN)
def grade_case(
    *,
    case_id: str,
    response: str,
    changed_files: tuple[str, ...],
    verification: Verification.Value = UNCHECKED,
    selection: Selection = "smoke",
) -> TaskGrade:
    """Return native field-level judgments alongside the canonical boolean scores."""
    return Task.grade_report(
        task=datasets.record(case_id, selection=selection),
        response=_parse_response(response),
        outcome=Outcome.create(changed_files=changed_files, verification=verification),
    )
