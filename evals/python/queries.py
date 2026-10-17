"""Typed public queries adapt the native kernel through immutable dataset snapshots."""

from typing import TYPE_CHECKING, cast

from pydantic import validate_call

import kernel
from evals.python import datasets, grading, schema
from kernel._operations import experiment as experiment_ops
from kernel._operations import projection as projection_ops

if TYPE_CHECKING:
    from kernel._experiment import ResolveArgs


__all__ = [
    "compile_dataset",
    "describe_dataset",
    "get_provenance",
    "get_reference",
    "list_cases",
    "load_dataset",
    "resolve_settings",
    "score_case",
]


@validate_call(config=schema.FROZEN)
def compile_dataset(
    *,
    cases: tuple[kernel.Task, ...],
    info: schema.DatasetInfo | None = None,
    resources: schema.Files | None = None,
) -> datasets.Dataset:
    return datasets.compile_declarations(
        cases, info=info, resources={} if resources is None else resources
    )


@validate_call(config=schema.FROZEN)
def load_dataset(*, selection: datasets.Selection = "smoke") -> datasets.Dataset:
    return datasets.load_dataset(selection)


@validate_call(config=schema.FROZEN)
def list_cases(*, selection: datasets.Selection = "smoke") -> tuple[kernel.Case, ...]:
    return tuple(datasets.load_dataset(selection).cases.values())


@validate_call(config=schema.FROZEN)
def get_reference(*, case_id: str, selection: datasets.Selection = "smoke") -> kernel.Reference:
    return projection_ops.reference(datasets.record(case_id, selection=selection))


@validate_call(config=schema.FROZEN)
def resolve_settings(
    *,
    epochs: int | None = None,
    message_limit: int | None = None,
    cost_limit: float | None = None,
    time_limit: int | None = None,
    cache: bool | None = None,
) -> kernel.Experiment:
    options = {
        "epochs": epochs,
        "message_limit": message_limit,
        "cost_limit": cost_limit,
        "time_limit": time_limit,
        "cache": cache,
    }
    return experiment_ops.resolve(
        **cast("ResolveArgs", {name: value for name, value in options.items() if value is not None})
    )


@validate_call(config=schema.FROZEN)
def describe_dataset(*, selection: datasets.Selection = "smoke") -> schema.DatasetInfo | None:
    return datasets.dataset_info(selection)


@validate_call(config=schema.FROZEN)
def get_provenance(*, selection: datasets.Selection = "smoke") -> datasets.DatasetProvenance:
    dataset = datasets.load_dataset(selection)
    return datasets.DatasetProvenance(
        info=dataset.info,
        source_hash=datasets.fingerprint(dataset.sources),
        cases_hash=datasets.cases_hash(dataset),
    )


@validate_call(config=schema.FROZEN)
def score_case(
    *,
    case_id: str,
    response: str,
    changed_files: tuple[str, ...],
    verification: kernel.Verification.Value = grading.UNCHECKED,
    selection: datasets.Selection = "smoke",
) -> grading.Scores:
    return grading.score(
        datasets.record(case_id, selection=selection),
        response=response,
        changed_files=changed_files,
        verification=verification,
    )
