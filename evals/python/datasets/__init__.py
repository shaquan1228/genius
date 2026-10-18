"""Load declarations and compose canonical task snapshots."""

import json
from collections import OrderedDict
from collections.abc import Mapping
from importlib import import_module
from threading import RLock
from typing import Annotated, Protocol, cast

from pydantic import AfterValidator, validate_call

from evals.python import FROZEN
from evals.python.dataset import Dataset, DatasetInfo
from evals.python.provenance import value_fingerprint
from kernel import Case, File, Reference, ResourceBinding, Task

__all__ = [
    "Dataset",
    "DatasetInfo",
    "Selection",
    "compile_dataset",
    "describe_dataset",
    "get_reference",
    "list_cases",
    "load_dataset",
]

_LOCK = RLock()
_CACHE: OrderedDict[tuple[object, ...], Dataset] = OrderedDict()


class DatasetModule(Protocol):
    info: DatasetInfo | None

    def cases(self) -> tuple[Task, ...]: ...


def _file_name(value: str) -> str:
    if not File.valid_path(path=value):
        raise ValueError("Invalid file name")
    return value


Selection = Annotated[str, AfterValidator(_file_name)] | Dataset


@validate_call(config=FROZEN)
def compile_dataset(
    *,
    cases: tuple[Task, ...],
    info: DatasetInfo | None = None,
    resources: Mapping[Annotated[str, AfterValidator(_file_name)], str] | None = None,
) -> Dataset:
    records = {task.id: task for task in cases}
    if len(records) != len(cases):
        raise ValueError("Dataset task IDs must be unique")
    bindings = tuple(sorted((resources or {}).items()))
    return _compiled(records, info=info, bindings=bindings)


def _compiled(
    records: Mapping[str, Task], *, info: DatasetInfo | None, bindings: tuple[tuple[str, str], ...]
) -> Dataset:
    key = (
        tuple(map(value_fingerprint, records.values())),
        bindings,
        json.dumps(info.model_dump(mode="json"), sort_keys=True) if info else None,
    )
    with _LOCK:
        if key not in _CACHE:
            _CACHE[key] = Dataset(
                records=records,
                info=info,
                resources=tuple(
                    ResourceBinding.create(key=name, contents=text) for name, text in bindings
                ),
            )
        _CACHE.move_to_end(key)
        if len(_CACHE) > 8:
            _CACHE.popitem(last=False)
        return _CACHE[key]


def _module(selection: str) -> DatasetModule:
    return cast(DatasetModule, import_module(f"evals.python.datasets.{selection}"))


@validate_call(config=FROZEN)
def load_dataset(*, selection: Selection = "smoke") -> Dataset:
    if isinstance(selection, Dataset):
        return selection
    module = _module(selection)
    return compile_dataset(cases=module.cases(), info=module.info)


@validate_call(config=FROZEN)
def list_cases(*, selection: Selection = "smoke") -> tuple[Case, ...]:
    return tuple(load_dataset(selection=selection).cases.values())


@validate_call(config=FROZEN)
def get_reference(*, case_id: str, selection: Selection = "smoke") -> Reference:
    return load_dataset(selection=selection).records[case_id].reference


@validate_call(config=FROZEN)
def describe_dataset(*, selection: Selection = "smoke") -> DatasetInfo | None:
    return selection.info if isinstance(selection, Dataset) else _module(selection).info
