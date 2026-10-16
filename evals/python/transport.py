"""Dataset-independent compiler and versioned OCaml protocol boundary."""

import hashlib
import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from itertools import batched, chain
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
from typing import Annotated, Final

from pydantic import AfterValidator, BaseModel, Field

from evals.python._kernel import (
    FROZEN,
    Case,
    CaseDefinition,
    ExecutableChecks,
    Experiment,
    Reference,
    Verification,
)
from evals.python.paths import EVALS_ROOT

VERSION: Final = 3


@dataclass(frozen=True, kw_only=True)
class Sources:
    modules: tuple[tuple[str, str], ...]
    resources: tuple[tuple[str, str], ...]


OCAML_ROOT: Final = EVALS_ROOT / "ocaml"
LIBRARY: Final = tuple(
    OCAML_ROOT / name
    for name in (
        "ast.ml",
        "experiment.mli",
        "experiment.ml",
        "response.mli",
        "response.ml",
        "fixture.mli",
        "fixture.ml",
        "verifier.mli",
        "verifier.ml",
        "criterion.mli",
        "criterion.ml",
        "case.mli",
        "case.ml",
        "reference.mli",
        "reference.ml",
        "grader.mli",
        "grader.ml",
        "projection.mli",
        "projection.ml",
        "codec.ml",
        "declaration.mli",
        "declaration.ml",
    )
)
EXPORTER: Final = OCAML_ROOT / "transport.ml"


class Envelope[T](BaseModel):
    model_config = FROZEN
    version: int = Field(ge=VERSION, le=VERSION)
    value: T


class GradingResult(BaseModel):
    model_config = FROZEN
    version: int = Field(ge=VERSION, le=VERSION)
    scores: Annotated[Mapping[str, bool], AfterValidator(MappingProxyType)]


@dataclass(frozen=True, kw_only=True)
class KernelRequest:
    arguments: tuple[str, ...]
    data: str


@dataclass(frozen=True)
class _Kernel:
    directory: TemporaryDirectory[str]

    def run(self, request: KernelRequest) -> str:
        return subprocess.run(
            [str(Path(self.directory.name) / "kernel"), *request.arguments],
            input=request.data,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
            timeout=30,
        ).stdout


@lru_cache(maxsize=8)
def _kernel(*, sources: Sources) -> _Kernel:
    directory = TemporaryDirectory(prefix="genius-kernel-")
    try:
        for name, contents in sources.modules:
            (Path(directory.name) / name).write_text(contents)
        resources = Path(directory.name) / "resources"
        resources.mkdir()
        for name, contents in sources.resources:
            (resources / name).write_text(contents)
        subprocess.run(
            [
                "ocamlfind",
                "ocamlc",
                "-package",
                "jsonm",
                "-linkpkg",
                "-o",
                "kernel",
                *(name for name, _ in sources.modules),
            ],
            cwd=directory.name,
            check=True,
            timeout=30,
        )
    except BaseException:
        directory.cleanup()
        raise
    return _Kernel(directory)


def sources(*, resources: Mapping[str, str] = MappingProxyType({})) -> Sources:
    return Sources(
        modules=tuple((path.name, path.read_text()) for path in (*LIBRARY, EXPORTER)),
        resources=tuple(sorted(resources.items())),
    )


def fingerprint(sources: Sources) -> str:
    return hashlib.sha256(json.dumps((sources.modules, sources.resources)).encode()).hexdigest()


def invoke(*, sources: Sources, operation: str, payload: object) -> str:
    return _kernel(sources=sources).run(
        request=KernelRequest(arguments=(operation,), data=json.dumps(payload))
    )


def decode(data: str) -> tuple[Case, ...]:
    cases = Envelope[tuple[Case, ...]].model_validate_json(data).value
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("Suite case IDs must be unique")
    return cases


def cases(*, sources: Sources, records: tuple[str, ...] = ()) -> tuple[Case, ...]:
    batches = tuple(batched(records, 16)) or ((),)
    result = tuple(
        chain.from_iterable(
            decode(invoke(sources=sources, operation="--cases", payload=batch)) for batch in batches
        )
    )
    if len({case.id for case in result}) != len(result):
        raise ValueError("Dataset task IDs must be unique")
    return result


def describe(*, sources: Sources) -> DatasetInfo | None:
    return (
        Envelope[DatasetInfo | None]
        .model_validate_json(invoke(sources=sources, operation="--describe", payload={}))
        .value
    )


def experiment(
    *, sources: Sources, overrides: Mapping[str, int | float | bool | None]
) -> Experiment:
    return (
        Envelope[Experiment]
        .model_validate_json(invoke(sources=sources, operation="--experiment", payload=overrides))
        .value
    )


@lru_cache(maxsize=256)
def verifier(*, sources: Sources, case_id: str, record: str) -> ExecutableChecks | None:
    return (
        Envelope[ExecutableChecks | None]
        .model_validate_json(
            invoke(
                sources=sources,
                operation="--verifier",
                payload={"case_id": case_id, "record": record},
            )
        )
        .value
    )


def reference(*, sources: Sources, case_id: str, record: str) -> Reference:
    return (
        Envelope[Reference]
        .model_validate_json(
            invoke(
                sources=sources,
                operation="--reference",
                payload={"case_id": case_id, "record": record},
            )
        )
        .value
    )


def grade(  # noqa: PLR0913 - kernel grading fields and trusted compiler context
    *,
    sources: Sources,
    case_id: str,
    response: str,
    changed_files: tuple[str, ...],
    verification: Verification,
    record: str,
) -> Mapping[str, bool]:
    result = GradingResult.model_validate_json(
        invoke(
            sources=sources,
            operation="--grade",
            payload={
                "record": record,
                "request": {
                    "version": VERSION,
                    "case_id": case_id,
                    "response": response,
                    "changed_files": changed_files,
                    "verification": verification.model_dump(),
                },
            },
        )
    )
    if not {"correctness", "scope"} <= result.scores.keys():
        raise ValueError("Kernel omitted required score names")
    return result.scores


def encode_declarations(definitions: tuple[CaseDefinition, ...]) -> tuple[str, ...]:
    return tuple(definition.model_dump_json() for definition in definitions)
