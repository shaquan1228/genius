"""Compile Python declarations and retain private dataset snapshots."""

from collections.abc import Mapping
from functools import lru_cache
from importlib import import_module
from types import MappingProxyType
from typing import Annotated, Protocol, cast

from pydantic import AfterValidator, BaseModel, TypeAdapter

from evals.python import transport
from evals.python._kernel import (
    FROZEN,
    Attributes,
    Case,
    CaseDefinition,
    DatasetInfo,
    ExecutableChecks,
    Experiment,
    FileName,
    Reference,
    Verification,
)
from evals.python.transport import Sources


class Catalog(BaseModel):
    model_config = FROZEN
    sources: Sources
    cases: Annotated[Mapping[str, Case], AfterValidator(MappingProxyType)]
    records: Attributes
    info: DatasetInfo | None = None


class DatasetModule(Protocol):
    info: DatasetInfo | None

    def cases(self) -> tuple[CaseDefinition, ...]: ...


Selection = str | Catalog


@lru_cache(maxsize=8)
def compile_records(
    *, sources: Sources, records: tuple[str, ...], info_json: str | None = None
) -> Catalog:
    cases = transport.cases(sources=sources, records=records)
    return Catalog(
        sources=sources,
        cases={case.id: case for case in cases},
        records=dict(zip((case.id for case in cases), records, strict=True)),
        info=DatasetInfo.model_validate_json(info_json) if info_json is not None else None,
    )


def compile_declarations(
    definitions: tuple[CaseDefinition, ...],
    *,
    info: DatasetInfo | None = None,
    resources: Mapping[str, str] = MappingProxyType({}),
) -> Catalog:
    if info is not None and len(definitions) != info.count:
        raise ValueError("Dataset count mismatch")
    return compile_records(
        sources=transport.sources(resources=resources),
        records=transport.encode_declarations(definitions),
        info_json=info.model_dump_json() if info is not None else None,
    )


def _module(selection: str) -> DatasetModule:
    name = TypeAdapter(FileName).validate_python(selection, strict=True)
    return cast(DatasetModule, import_module(f"evals.python.datasets.{name}"))


def load_dataset(selection: Selection) -> Catalog:
    selection = TypeAdapter(Selection).validate_python(selection, strict=True)
    if isinstance(selection, Catalog):
        return selection
    dataset = _module(selection)
    return compile_declarations(dataset.cases(), info=dataset.info)


def sources(selection: Selection = "smoke") -> Sources:
    return load_dataset(selection).sources


def load_cases(*, selection: Selection = "smoke") -> tuple[Case, ...]:
    return tuple(load_dataset(selection).cases.values())


def case(case_id: str, *, selection: Selection = "smoke") -> Case:
    return load_dataset(selection).cases[case_id]


def verifier(case_id: str, *, selection: Selection = "smoke") -> ExecutableChecks | None:
    catalog = load_dataset(selection)
    return transport.verifier(
        sources=catalog.sources, case_id=case_id, record=catalog.records[case_id]
    )


def reference(case_id: str, *, selection: Selection = "smoke") -> Reference:
    catalog = load_dataset(selection)
    return transport.reference(
        sources=catalog.sources, case_id=case_id, record=catalog.records[case_id]
    )


def grade(
    *,
    case_id: str,
    response: str,
    changed_files: tuple[str, ...],
    verification: Verification,
    selection: Selection = "smoke",
) -> Mapping[str, bool]:
    catalog = load_dataset(selection)
    return transport.grade(
        sources=catalog.sources,
        case_id=case_id,
        response=response,
        changed_files=changed_files,
        verification=verification,
        record=catalog.records[case_id],
    )


def dataset_info(selection: Selection) -> DatasetInfo | None:
    return selection.info if isinstance(selection, Catalog) else _module(selection).info


def experiment(
    *,
    epochs: int | None = None,
    message_limit: int | None = None,
    cost_limit: float | None = None,
    time_limit: int | None = None,
    cache: bool | None = None,
) -> Experiment:
    return transport.experiment(
        sources=transport.sources(),
        overrides={
            "epochs": epochs,
            "message_limit": message_limit,
            "cost_limit": cost_limit,
            "time_limit": time_limit,
            "cache": cache,
        },
    )


def cases_hash(dataset: Selection) -> str:
    catalog = load_dataset(dataset)
    material = Sources(
        modules=catalog.sources.modules,
        resources=(
            *catalog.sources.resources,
            *catalog.records.items(),
            ("dataset-info", catalog.info.model_dump_json() if catalog.info else "null"),
        ),
    )
    return transport.fingerprint(material)


def source_hash(dataset: Selection) -> str:
    return transport.fingerprint(sources(dataset))
