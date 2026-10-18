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
    Assessment,
    Completion,
    Outcome,
    Response,
    ResponseField,
    ResponseValue,
    Task,
    Verification,
)

__all__ = ["Scores", "assess_case", "score_case"]

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
    assessment = assess_case(
        case_id=case_id,
        response=response,
        changed_files=changed_files,
        verification=verification,
        selection=selection,
    )
    return MappingProxyType(dict(Assessment.scores(assessment=assessment)))


@validate_call(config=FROZEN)
def assess_case(
    *,
    case_id: str,
    response: str,
    changed_files: tuple[str, ...],
    verification: Verification.Value = UNCHECKED,
    selection: Selection = "smoke",
) -> Assessment.Value:
    """Bind decoded candidate evidence to the native assessment composition."""
    return Task.assess(
        task=datasets.record(case_id, selection=selection),
        response=_parse_response(response),
        outcome=Outcome.create(changed_files=changed_files, verification=verification),
    )
