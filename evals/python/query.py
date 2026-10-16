"""Typed public queries adapt the native kernel through immutable dataset snapshots."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Literal, assert_never, cast

from pydantic import validate_call

from evals.python import datasets
from evals.python.datasets import Dataset, Selection
from evals.python.schema import FROZEN, DatasetInfo, Files
from evals.python.verification import Runtime
from kernel import Ast, Experiment, Fixture, Grader, Response

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
    except (ValueError, RecursionError):
        return None


__all__ = [
    "Ast",
    "Cases",
    "CompileDataset",
    "Dataset",
    "DatasetInfo",
    "DatasetProvenance",
    "DescribeDataset",
    "ExecutionRuntime",
    "ExperimentSettings",
    "Fixture",
    "GradeCase",
    "LoadDataset",
    "Provenance",
    "Runtime",
    "Scores",
    "Selection",
]

type Scores = Mapping[str, bool]
_UNCHECKED = Ast.Unchecked()


@dataclass(frozen=True, kw_only=True)
class DatasetProvenance:
    info: DatasetInfo | None
    source_hash: str
    cases_hash: str


@validate_call(config=FROZEN)
def CompileDataset(
    *,
    cases: tuple[Ast.case, ...],
    info: DatasetInfo | None = None,
    resources: Files | None = None,
) -> Dataset:
    return datasets.compile_declarations(
        cases, info=info, resources={} if resources is None else resources
    )


@validate_call(config=FROZEN)
def LoadDataset(*, selection: Selection = "smoke") -> Dataset:
    return datasets.load_dataset(selection)


@validate_call(config=FROZEN)
def Cases(*, selection: Selection = "smoke") -> tuple[Ast.public_case, ...]:
    return tuple(datasets.load_dataset(selection).cases.values())


@validate_call(config=FROZEN)
def ExperimentSettings(
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
def DescribeDataset(*, selection: Selection = "smoke") -> DatasetInfo | None:
    return datasets.dataset_info(selection)


@validate_call(config=FROZEN)
def Provenance(*, selection: Selection = "smoke") -> DatasetProvenance:
    dataset = datasets.load_dataset(selection)
    return DatasetProvenance(
        info=dataset.info,
        source_hash=datasets.fingerprint(dataset.sources),
        cases_hash=datasets.cases_hash(dataset),
    )


@validate_call(config=FROZEN)
def GradeCase(
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


@validate_call(config=FROZEN)
def ExecutionRuntime(*, provider: Literal["local", "hf"] = "local") -> Runtime:
    match provider:
        case "local":
            from evals.python.integrations.inspect import environments  # noqa: PLC0415 - lazy local SDK composition

            return environments.runtime()
        case "hf":
            from evals.python.integrations.hugging_face import sandbox  # noqa: PLC0415 - lazy HF SDK composition

            return sandbox.runtime()
        case _ as unreachable:
            assert_never(unreachable)
