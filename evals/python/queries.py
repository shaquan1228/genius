"""Typed public queries adapt the native kernel through immutable dataset snapshots."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, cast

from pydantic import validate_call

from evals.python import datasets
from evals.python.datasets import Dataset, Selection
from evals.python.schema import FROZEN, DatasetInfo, Files
from kernel import Ast, Experiment, Grader, InvalidArgument, Projection, Response

if TYPE_CHECKING:
    from kernel.Experiment import ResolveArgs


def _scalar(value: object) -> Ast.response_value:
    if isinstance(value, bool):
        return Ast.Bool(value)
    if isinstance(value, str):
        return Ast.String(value)
    raise ValueError("Response fields must be strings or booleans")


def _response(fields: object) -> Ast.response:
    if not isinstance(fields, dict):
        raise ValueError("Expected response object")
    return Response.of_fields([(name, _scalar(value)) for name, value in fields.items()])


def _candidate(text: str) -> Ast.response | None:
    text = Grader.trim(text)
    if text.startswith("```json\n") and text.endswith("\n```"):
        text = text[8:-4]
    try:
        return _response(json.loads(text))
    except (ValueError, RecursionError, InvalidArgument):
        return None


__all__ = [
    "Dataset",
    "DatasetInfo",
    "DatasetProvenance",
    "Scores",
    "Selection",
    "compile_dataset",
    "describe_dataset",
    "get_provenance",
    "get_reference",
    "list_cases",
    "load_dataset",
    "resolve_settings",
    "score_case",
]

type Scores = Mapping[str, bool]
_UNCHECKED = Ast.Unchecked()


@dataclass(frozen=True, kw_only=True)
class DatasetProvenance:
    info: DatasetInfo | None
    source_hash: str
    cases_hash: str


@validate_call(config=FROZEN)
def compile_dataset(
    *,
    cases: tuple[Ast.task, ...],
    info: DatasetInfo | None = None,
    resources: Files | None = None,
) -> Dataset:
    return datasets.compile_declarations(
        cases, info=info, resources={} if resources is None else resources
    )


@validate_call(config=FROZEN)
def load_dataset(*, selection: Selection = "smoke") -> Dataset:
    return datasets.load_dataset(selection)


@validate_call(config=FROZEN)
def list_cases(*, selection: Selection = "smoke") -> tuple[Ast.case, ...]:
    return tuple(datasets.load_dataset(selection).cases.values())


@validate_call(config=FROZEN)
def get_reference(*, case_id: str, selection: Selection = "smoke") -> Ast.reference:
    return Projection.reference(datasets.record(case_id, selection=selection))


@validate_call(config=FROZEN)
def resolve_settings(
    *,
    epochs: int | None = None,
    message_limit: int | None = None,
    cost_limit: float | None = None,
    time_limit: int | None = None,
    cache: bool | None = None,
) -> Ast.experiment:
    options = {
        "epochs": epochs,
        "message_limit": message_limit,
        "cost_limit": cost_limit,
        "time_limit": time_limit,
        "cache": cache,
    }
    return Experiment.resolve(
        **cast("ResolveArgs", {name: value for name, value in options.items() if value is not None})
    )


@validate_call(config=FROZEN)
def describe_dataset(*, selection: Selection = "smoke") -> DatasetInfo | None:
    return datasets.dataset_info(selection)


@validate_call(config=FROZEN)
def get_provenance(*, selection: Selection = "smoke") -> DatasetProvenance:
    dataset = datasets.load_dataset(selection)
    return DatasetProvenance(
        info=dataset.info,
        source_hash=datasets.fingerprint(dataset.sources),
        cases_hash=datasets.cases_hash(dataset),
    )


@validate_call(config=FROZEN)
def score_case(
    *,
    case_id: str,
    response: str,
    changed_files: tuple[str, ...],
    verification: Ast.verification = _UNCHECKED,
    selection: Selection = "smoke",
) -> Scores:
    scores = dict(
        Grader.grade(
            datasets.record(case_id, selection=selection),
            response=_candidate(response),
            outcome=Ast.outcome(changed_files=changed_files, verification=verification),
        )
    )
    if not {"correctness", "scope"} <= scores.keys():
        raise ValueError("Kernel omitted required score names")
    return MappingProxyType(scores)
