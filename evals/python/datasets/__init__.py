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
from kernel import Ast, Case, Fixture, Projection
from kernel.build import LIBRARY


@dataclass(frozen=True, kw_only=True)
class Sources:
    modules: tuple[tuple[str, str], ...]
    resources: tuple[tuple[str, str], ...]


_MODULES = tuple((path.name, path.read_text()) for path in LIBRARY)


def kernel_sources(*, resources: Mapping[str, str] = MappingProxyType({})) -> Sources:
    return Sources(modules=_MODULES, resources=tuple(sorted(resources.items())))


def fingerprint(value: Sources) -> str:
    return hashlib.sha256(repr((value.modules, value.resources)).encode()).hexdigest()


def _canonical(value: object) -> object:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Ast.fixture):
        return tuple(Fixture.files(value))
    return (type(value).__name__, tuple(_canonical(item) for item in cast(Sequence[object], value)))


def value_fingerprint(value: Ast.task) -> str:
    return hashlib.sha256(repr(_canonical(value)).encode()).hexdigest()


@dataclass(frozen=True, kw_only=True)
class Dataset:
    sources: Sources
    cases: Mapping[str, Ast.case]
    records: Mapping[str, Ast.task]
    info: DatasetInfo | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "cases", MappingProxyType(dict(self.cases)))
        object.__setattr__(self, "records", MappingProxyType(dict(self.records)))


class DatasetModule(Protocol):
    info: DatasetInfo | None

    def cases(self) -> tuple[Ast.task, ...]: ...


Selection = str | Dataset


@dataclass(frozen=True)
class _CaseKey:
    value: Ast.task = field(compare=False, hash=False)
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "digest", value_fingerprint(self.value))


def _artifacts(
    values: Sequence[tuple[str, Ast.content]], *, resources: Mapping[str, str]
) -> tuple[tuple[str, Ast.content], ...]:
    return tuple(
        (name, Ast.Inline(resources[content[0]]) if isinstance(content, Ast.Resource) else content)
        for name, content in values
    )


def _resolve(case: Ast.task, *, sources: Sources) -> Ast.task:
    Case.validate(case)
    if sources.modules != _MODULES:
        raise ValueError("Kernel sources differ from the loaded native types; restart the process")
    if isinstance(case.criterion, Ast.Answer):
        return case
    checks = case.criterion[0]
    resources = dict(sources.resources)
    verifier = Ast.verifier(
        inputs=checks.inputs,
        files=_artifacts(checks.files, resources=resources),
        tools=_artifacts(checks.tools, resources=resources),
        command=checks.command,
        stdin=checks.stdin,
        timeout_seconds=checks.timeout_seconds,
    )
    return Case.make(
        id=case.id,
        fixture=case.fixture,
        instruction=case.instruction,
        criterion=Ast.Code(verifier),
        allowed_files=case.allowed_files,
        reference=case.reference,
    )


@lru_cache(maxsize=8)
def _compile(
    *, sources: Sources, records: tuple[_CaseKey, ...], info: DatasetInfo | None
) -> Dataset:
    public = {}
    private = {}
    for record in records:
        case = Projection.case(record.value)
        if case.id in public:
            raise ValueError("Dataset task IDs must be unique")
        public[case.id] = case
        private[case.id] = record.value
    return Dataset(
        sources=sources,
        cases=public,
        records=private,
        info=info,
    )


def compile_records(
    *, sources: Sources, records: tuple[Ast.task, ...], info: DatasetInfo | None = None
) -> Dataset:
    normalized = tuple(_CaseKey(_resolve(record, sources=sources)) for record in records)
    return _compile(sources=sources, records=normalized, info=info)


def compile_declarations(
    definitions: tuple[Ast.task, ...],
    *,
    info: DatasetInfo | None = None,
    resources: Mapping[str, str] = MappingProxyType({}),
) -> Dataset:
    if info is not None and len(definitions) != info.count:
        raise ValueError("Dataset count mismatch")
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


def record(case_id: str, *, selection: Selection) -> Ast.task:
    value = load_dataset(selection).records[case_id]
    if value.id != case_id:
        raise ValueError(f"Unknown case: {case_id}")
    return value


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
