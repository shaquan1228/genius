"""Dataset composition: choose an adapter, fetch pinned records, retain trusted inputs."""

from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Annotated

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
from evals.python.integrations.datasets.download import Download, cache_path, download
from evals.python.paths import EVALS_ROOT
from evals.python.transport import Program, Sources

ADAPTER_ROOT = EVALS_ROOT / "ocaml/datasets"
DRIVERS = (
    EVALS_ROOT / "python/integrations/evalplus/evalplus_verifier.py",
    EVALS_ROOT / "python/integrations/smoke/verifier.py",
)


class Catalog(BaseModel):
    model_config = FROZEN
    sources: Sources
    cases: Annotated[Mapping[str, Case], AfterValidator(MappingProxyType)]
    records: Attributes


Selection = str | Path | Catalog


def sources(selection: Selection = "smoke") -> Sources:
    selection = TypeAdapter(Selection).validate_python(selection, strict=True)
    if isinstance(selection, Catalog):
        return selection.sources
    if isinstance(selection, Path):
        suite, adapter = selection, ADAPTER_ROOT / "suite.ml"
    else:
        name = TypeAdapter(FileName).validate_python(selection, strict=True)
        name = "declarations" if name == "smoke" else name
        suite, adapter = transport.SUITE, ADAPTER_ROOT / f"{name}.ml"
    return transport.sources(Program(suite=suite, adapter=adapter, resources=DRIVERS))


@lru_cache(maxsize=8)
def compile_records(*, sources: Sources, records: tuple[str, ...]) -> Catalog:
    cases = transport.cases(sources=sources, records=records)
    return Catalog(
        sources=sources,
        cases={case.id: case for case in cases},
        records=dict(zip((case.id for case in cases), records, strict=bool(records))),
    )


def compile_declarations(definitions: tuple[CaseDefinition, ...]) -> Catalog:
    return compile_records(
        sources=sources("declarations"), records=transport.encode_declarations(definitions)
    )


@lru_cache(maxsize=8)
def _catalog(sources: Sources) -> Catalog:
    info = transport.describe(sources=sources)
    records = (
        ()
        if info is None
        else tuple(
            download(
                request=Download(
                    source=info.source,
                    sha256=info.sha256,
                    destination=cache_path(info.sha256),
                )
            )
            .decode()
            .splitlines()
        )
    )
    catalog = compile_records(sources=sources, records=records)
    if info is not None and len(catalog.cases) != info.count:
        raise ValueError("Dataset count mismatch")
    return catalog


def load_dataset(selection: Selection) -> Catalog:
    match selection:
        case Catalog():
            return selection
        case "smoke":
            from evals.python.integrations.smoke import declarations  # noqa: PLC0415 - resolve dataset ownership at acquisition

            return compile_declarations(declarations.cases())
        case _:
            return _catalog(sources(selection))


def load_cases(*, selection: Selection = "smoke") -> tuple[Case, ...]:
    return tuple(load_dataset(selection).cases.values())


def case(case_id: str, *, selection: Selection = "smoke") -> Case:
    return load_dataset(selection).cases[case_id]


def verifier(case_id: str, *, selection: Selection = "smoke") -> ExecutableChecks | None:
    catalog = load_dataset(selection)
    return transport.verifier(
        sources=catalog.sources, case_id=case_id, record=catalog.records.get(case_id)
    )


def reference(case_id: str, *, selection: Selection = "smoke") -> Reference:
    catalog = load_dataset(selection)
    return transport.reference(
        sources=catalog.sources, case_id=case_id, record=catalog.records.get(case_id)
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
        record=catalog.records.get(case_id),
    )


def dataset_info(selection: Selection) -> DatasetInfo | None:
    return transport.describe(sources=sources(selection))


def experiment(
    *,
    epochs: int | None = None,
    message_limit: int | None = None,
    token_limit: int | None = None,
    time_limit: int | None = None,
    cache: bool | None = None,
) -> Experiment:
    return transport.experiment(
        sources=sources(),
        overrides={
            "epochs": epochs,
            "message_limit": message_limit,
            "token_limit": token_limit,
            "time_limit": time_limit,
            "cache": cache,
        },
    )


def cases_hash(dataset: Selection) -> str:
    catalog = load_dataset(dataset)
    # Includes trusted adapter, verifier code, and private dataset records, not just public inputs.
    material = Sources(
        modules=catalog.sources.modules,
        resources=(*catalog.sources.resources, *catalog.records.items()),
    )
    return transport.fingerprint(material)


def source_hash(dataset: Selection) -> str:
    return transport.fingerprint(sources(dataset))
