"""Typed public queries adapt the native kernel through immutable dataset snapshots."""

from typing import TYPE_CHECKING, cast

from pydantic import validate_call

from evals.python import datasets, grading
from evals.python.datasets import Dataset, DatasetProvenance, Selection
from evals.python.grading import UNCHECKED, Scores
from evals.python.schema import FROZEN, DatasetInfo, Files
from kernel import Case, Experiment, Reference, Task, Verification
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


@validate_call(config=FROZEN)
def compile_dataset(
    *,
    cases: tuple[Task, ...],
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
def list_cases(*, selection: Selection = "smoke") -> tuple[Case, ...]:
    return tuple(datasets.load_dataset(selection).cases.values())


@validate_call(config=FROZEN)
def get_reference(*, case_id: str, selection: Selection = "smoke") -> Reference:
    return projection_ops.reference(datasets.record(case_id, selection=selection))


@validate_call(config=FROZEN)
def resolve_settings(
    *,
    epochs: int | None = None,
    message_limit: int | None = None,
    cost_limit: float | None = None,
    time_limit: int | None = None,
    cache: bool | None = None,
) -> Experiment:
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
    verification: Verification.Value = UNCHECKED,
    selection: Selection = "smoke",
) -> Scores:
    return grading.score(
        datasets.record(case_id, selection=selection),
        response=response,
        changed_files=changed_files,
        verification=verification,
    )
