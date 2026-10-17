"""Python dataset loading, resource resolution and immutable native case snapshots."""

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import import_module
from types import MappingProxyType
from typing import Protocol, cast

from pydantic import TypeAdapter

from evals.python.schema import FROZEN, DatasetInfo, FileName
from kernel import Case, Content, Criterion, Fixture, Task, Verifier
from kernel._operations import case as case_ops
from kernel._operations import fixture as fixture_ops
from kernel._operations import projection as projection_ops
from kernel._operations import sources


@dataclass(frozen=True, kw_only=True)
class DatasetProvenance:
    info: DatasetInfo | None
    source_hash: str
    cases_hash: str


@dataclass(frozen=True, kw_only=True)
class Sources:
    modules: tuple[tuple[str, str], ...]
    resources: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "modules", tuple((name, text) for name, text in self.modules))
        object.__setattr__(self, "resources", tuple((name, text) for name, text in self.resources))


_MODULES = sources()


def kernel_sources(*, resources: Mapping[str, str] = MappingProxyType({})) -> Sources:
    return Sources(modules=_MODULES, resources=tuple(sorted(resources.items())))


def fingerprint(value: Sources) -> str:
    return hashlib.sha256(repr((value.modules, value.resources)).encode()).hexdigest()


def _canonical(value: object) -> object:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Fixture):
        return tuple(fixture_ops.files(value))
    return (type(value).__name__, tuple(_canonical(item) for item in cast(Sequence[object], value)))


def value_fingerprint(value: Task) -> str:
    return hashlib.sha256(repr(_canonical(value)).encode()).hexdigest()


@dataclass(frozen=True, kw_only=True)
class Dataset:
    sources: Sources
    cases: Mapping[str, Case] = field(init=False)
    records: Mapping[str, Task]
    info: DatasetInfo | None = None

    def __post_init__(self) -> None:
        records = dict(self.records)
        _validate_snapshot(self.sources, count=len(records), info=self.info)
        normalized = _resolve_records(records, sources=self.sources)
        public = {name: projection_ops.case(record) for name, record in normalized.items()}
        object.__setattr__(self, "cases", MappingProxyType(public))
        object.__setattr__(self, "records", MappingProxyType(normalized))


def _validate_snapshot(sources: Sources, *, count: int, info: DatasetInfo | None) -> None:
    if sources.modules != _MODULES:
        raise ValueError("Kernel sources differ from the loaded native types; restart the process")
    if info is not None and count != info.count:
        raise ValueError("Dataset count mismatch")


class DatasetModule(Protocol):
    info: DatasetInfo | None

    def cases(self) -> tuple[Task, ...]: ...


Selection = str | Dataset


@dataclass(frozen=True)
class _CaseKey:
    value: Task = field(compare=False, hash=False)
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "digest", value_fingerprint(self.value))


def _artifacts(
    values: Sequence[tuple[str, Content.Value]], *, resources: Mapping[str, str]
) -> tuple[tuple[str, Content.Value], ...]:
    return tuple(
        (
            name,
            Content.Inline(resources[content[0]])
            if isinstance(content, Content.Resource)
            else content,
        )
        for name, content in values
    )


def _resolve(case: Task, *, sources: Sources) -> Task:
    case_ops.validate(case)
    if isinstance(case.criterion, Criterion.Answer):
        return case
    checks = case.criterion[0]
    resources = dict(sources.resources)
    verifier = Verifier(
        inputs=checks.inputs,
        files=_artifacts(checks.files, resources=resources),
        tools=_artifacts(checks.tools, resources=resources),
        command=checks.command,
        stdin=checks.stdin,
        timeout_seconds=checks.timeout_seconds,
    )
    return case_ops.make(
        id=case.id,
        fixture=case.fixture,
        instruction=case.instruction,
        criterion=Criterion.Code(verifier),
        allowed_files=case.allowed_files,
        reference=case.reference,
    )


def _resolve_records(records: Mapping[str, Task], *, sources: Sources) -> dict[str, Task]:
    normalized = {}
    for name, record in records.items():
        if name != record.id:
            raise ValueError(f"Dataset record ID differs from its key: {name}")
        normalized[name] = _resolve(record, sources=sources)
    return normalized


@lru_cache(maxsize=8)
def _compile(
    *, sources: Sources, records: tuple[_CaseKey, ...], info: DatasetInfo | None
) -> Dataset:
    private = {}
    for record in records:
        if record.value.id in private:
            raise ValueError("Dataset task IDs must be unique")
        private[record.value.id] = record.value
    return Dataset(sources=sources, records=private, info=info)


def compile_records(
    *, sources: Sources, records: tuple[Task, ...], info: DatasetInfo | None = None
) -> Dataset:
    return _compile(
        sources=sources, records=tuple(_CaseKey(record) for record in records), info=info
    )


def compile_declarations(
    definitions: tuple[Task, ...],
    *,
    info: DatasetInfo | None = None,
    resources: Mapping[str, str] = MappingProxyType({}),
) -> Dataset:
    return compile_records(
        sources=kernel_sources(resources=resources), records=definitions, info=info
    )


def _module(selection: str) -> DatasetModule:
    name = TypeAdapter(FileName).validate_python(selection, strict=True)
    return cast(DatasetModule, import_module(f"evals.python.datasets.{name}"))


def load_dataset(selection: Selection) -> Dataset:
    selection = TypeAdapter(Selection, config=FROZEN).validate_python(selection, strict=True)
    if isinstance(selection, Dataset):
        return selection
    module = _module(selection)
    return compile_declarations(module.cases(), info=module.info)


def record(case_id: str, *, selection: Selection) -> Task:
    return load_dataset(selection).records[case_id]


def dataset_info(selection: Selection) -> DatasetInfo | None:
    return selection.info if isinstance(selection, Dataset) else _module(selection).info


def cases_hash(dataset: Dataset) -> str:
    return fingerprint(
        Sources(
            modules=dataset.sources.modules,
            resources=(
                *dataset.sources.resources,
                *((name, value_fingerprint(value)) for name, value in dataset.records.items()),
                ("dataset-info", dataset.info.model_dump_json() if dataset.info else "null"),
            ),
        )
    )
