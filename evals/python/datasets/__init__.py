"""Load declarations and compose canonical task snapshots."""

import json
import re
from collections import OrderedDict
from collections.abc import Callable
from importlib import import_module
from threading import RLock
from typing import Annotated, Protocol, cast

from kernel import Reference
from pydantic import AfterValidator, validate_call

from evals.python import FROZEN
from evals.python.dataset import Case, Dataset, DatasetInfo, Declaration
from evals.python.provenance import fingerprint

__all__ = [
    "Case",
    "Dataset",
    "DatasetInfo",
    "Declaration",
    "Selection",
    "clear_cache",
    "compile_dataset",
    "describe_dataset",
    "get_reference",
    "list_cases",
    "load_dataset",
]

_LOCK = RLock()
_CACHE: OrderedDict[tuple[object, ...], Dataset] = OrderedDict()


def clear_cache() -> None:
    """Release cached snapshots without invalidating callers holding a dataset."""
    with _LOCK:
        _CACHE.clear()


class DatasetModule(Protocol):
    info: DatasetInfo | None

    def cases(self) -> tuple[Declaration, ...]: ...


def _file_name(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", value):
        raise ValueError("Invalid file name")
    return value


Selection = Annotated[str, AfterValidator(_file_name)] | Dataset


@validate_call(config=FROZEN)
def compile_dataset(*, cases: tuple[Declaration, ...], info: DatasetInfo | None = None) -> Dataset:
    records = {record.task.id: record for record in cases}
    if len(records) != len(cases):
        raise ValueError("Dataset task IDs must be unique")
    key = (
        tuple(map(fingerprint, records.values())),
        json.dumps(info.model_dump(mode="json"), sort_keys=True) if info else None,
    )
    return _cached(key, dataset=lambda: Dataset(records=records, info=info))


def _cached(key: tuple[object, ...], *, dataset: Callable[[], Dataset]) -> Dataset:
    """Reuse the snapshot for a key, keeping the eight most recent."""
    with _LOCK:
        if key not in _CACHE:
            _CACHE[key] = dataset()
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
    return load_dataset(selection=selection).records[case_id].task.reference


@validate_call(config=FROZEN)
def describe_dataset(*, selection: Selection = "smoke") -> DatasetInfo | None:
    return selection.info if isinstance(selection, Dataset) else _module(selection).info
