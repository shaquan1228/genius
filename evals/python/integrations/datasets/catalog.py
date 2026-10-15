"""Dataset composition: choose an adapter, fetch pinned records, retain trusted inputs."""

from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Annotated

from pydantic import AfterValidator, BaseModel, TypeAdapter

from evals.python import transport
from evals.python.contracts import (
    FROZEN,
    Attributes,
    Case,
    DatasetInfo,
    ExecutableChecks,
    Experiment,
    FileName,
    GradeRequest,
    Program,
    Reference,
    RunOverrides,
    Sources,
)
from evals.python.integrations.datasets.download import Download, cache_path, download
from evals.python.paths import EVALS_ROOT

Selection = str | Path

ADAPTER_ROOT = EVALS_ROOT / "ocaml/datasets"
RUNNER = EVALS_ROOT / "ocaml/check.sh"
DRIVER = EVALS_ROOT / "python/integrations/verifiers/verifier.py"


class Catalog(BaseModel):
    model_config = FROZEN
    sources: Sources
    cases: Annotated[Mapping[str, Case], AfterValidator(MappingProxyType)]
    records: Attributes


def sources(selection: Selection = "smoke") -> Sources:
    selection = TypeAdapter(Selection).validate_python(selection, strict=True)
    if isinstance(selection, Path):
        suite, adapter = selection, ADAPTER_ROOT / "smoke.ml"
    else:
        name = TypeAdapter(FileName).validate_python(selection, strict=True)
        suite, adapter = transport.SUITE, ADAPTER_ROOT / f"{name}.ml"
    return transport.sources(Program(suite=suite, adapter=adapter, resources=(RUNNER, DRIVER)))


def compile_records(*, sources: Sources, records: tuple[str, ...]) -> Catalog:
    cases = transport.cases(sources=sources, records=records)
    return Catalog(
        sources=sources,
        cases={case.id: case for case in cases},
        records=dict(zip((case.id for case in cases), records, strict=bool(records))),
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


def _selected(selection: Selection) -> Catalog:
    return _catalog(sources(selection))


def load_cases(*, selection: Selection = "smoke") -> tuple[Case, ...]:
    return tuple(_selected(selection).cases.values())


def case(case_id: str, *, selection: Selection = "smoke") -> Case:
    return _selected(selection).cases[case_id]


def verifier(case_id: str, *, selection: Selection = "smoke") -> ExecutableChecks | None:
    catalog = _selected(selection)
    return transport.verifier(
        sources=catalog.sources, case_id=case_id, record=catalog.records.get(case_id)
    )


def reference(case_id: str, *, selection: Selection = "smoke") -> Reference:
    catalog = _selected(selection)
    return transport.reference(
        sources=catalog.sources, case_id=case_id, record=catalog.records.get(case_id)
    )


def grade(*, request: GradeRequest, selection: Selection = "smoke") -> Mapping[str, bool]:
    catalog = _selected(selection)
    return transport.grade(
        sources=catalog.sources, request=request, record=catalog.records.get(request.case_id)
    )


def dataset_info(selection: Selection) -> DatasetInfo | None:
    return transport.describe(sources=sources(selection))


def benchmark_metadata(dataset: Selection) -> dict[str, object]:
    info = dataset_info(dataset)
    return {} if info is None else info.model_dump()


def experiment(overrides: RunOverrides | None = None) -> Experiment:
    return transport.experiment(sources=sources(), overrides=overrides)


def cases_hash(dataset: Selection) -> str:
    catalog = _selected(dataset)
    # Includes trusted adapter, verifier code, and private dataset records, not just public inputs.
    material = Sources(
        modules=catalog.sources.modules,
        resources=(*catalog.sources.resources, *catalog.records.items()),
    )
    return transport.fingerprint(material)
