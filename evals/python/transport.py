"""The only bridge between the OCaml suite and the Python harness.

It compiles the OCaml modules, decodes their export into immutable cases, and
builds the OCaml runner inputs that grade a workspace. No other Python module
reads OCaml sources or writes OCaml code.
"""

import gzip
import hashlib
import json
import os
import subprocess
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from types import MappingProxyType
from typing import Annotated, Final, Literal, assert_never

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    TypeAdapter,
    model_validator,
)

from evals.python.paths import EVALS_ROOT

OCAML_ROOT: Final = EVALS_ROOT / "ocaml"
LIBRARY: Final = tuple(
    OCAML_ROOT / name
    for name in (
        "response.mli",
        "response.ml",
        "fixture.mli",
        "fixture.ml",
        "instruction.ml",
        "verifier.mli",
        "verifier.ml",
        "criterion.ml",
        "reference.ml",
        "case.ml",
        "outcome.ml",
        "score.mli",
        "score.ml",
        "grader.ml",
        "fixtures.ml",
        "scenarios.ml",
        "humaneval.ml",
    )
)
SUITE: Final = OCAML_ROOT / "suite.ml"
EXPORTER: Final = OCAML_ROOT / "transport.ml"
RUNNER: Final = OCAML_ROOT / "check.sh"

FROZEN: Final = ConfigDict(strict=True, extra="forbid", frozen=True)
FileName = Annotated[str, Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_.-]*$")]
Files = Annotated[Mapping[FileName, str], AfterValidator(MappingProxyType), PlainSerializer(dict)]


class ExecutableChecks(BaseModel):
    model_config = FROZEN

    inputs: tuple[FileName, ...] = Field(min_length=1)
    files: Files
    tools: Files
    command: tuple[str, ...] = Field(min_length=1)
    stdin: str
    timeout_seconds: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_specification(self) -> "ExecutableChecks":
        names = (*self.inputs, *self.files, *self.tools)
        if len(set(names)) != len(names):
            raise ValueError("Verifier paths must be unique and disjoint")
        if any(not argument for argument in self.command):
            raise ValueError("Verifier command arguments cannot be empty")
        return self

    def validate_fixture(self, files: Files) -> None:
        if not set(self.inputs) <= files.keys():
            raise ValueError("Verifier inputs missing from fixture")
        if (self.files.keys() | self.tools.keys()) & files.keys():
            raise ValueError("Verifier artifacts overlap fixture")


class Case(BaseModel):
    """One exported case. Every field is read-only, so cached cases are safe to share.

    Answer cases have no checks: the kernel grades their replies.
    """

    model_config = FROZEN

    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    skill: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    prompt: str
    files: Files
    checks: ExecutableChecks | None
    solution: Files
    answer: str

    @model_validator(mode="after")
    def validate_files(self) -> "Case":
        match self.checks:
            case ExecutableChecks() as checks:
                checks.validate_fixture(files=self.files)
            case None:
                pass
            case _ as unreachable:
                assert_never(unreachable)
        return self


def decode(data: str) -> tuple[Case, ...]:
    cases = TypeAdapter(tuple[Case, ...]).validate_json(data)
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("Suite case IDs must be unique")
    return cases


Dataset = Literal["smoke", "humanevalplus"]


Selection = Dataset | Path
SELECTION_ADAPTER = TypeAdapter(Selection)


class CaseQuery(BaseModel):
    model_config = FROZEN

    case_id: str
    selection: Selection = "smoke"


@dataclass(frozen=True, kw_only=True)
class Sources:
    modules: tuple[tuple[str, str], ...]
    resources: tuple[tuple[str, str], ...]


@dataclass(frozen=True, kw_only=True)
class KernelRequest:
    arguments: tuple[str, ...] = ()
    data: str | None = None


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

    def import_records(self, records: tuple[str, ...]) -> tuple[Case, ...]:
        cases = tuple(
            case
            for start in range(0, len(records), 16)
            for case in decode(
                data=self.run(
                    request=KernelRequest(
                        arguments=("--import-humaneval",),
                        data=json.dumps(records[start : start + 16]),
                    )
                )
            )
        )
        if len({case.id for case in cases}) != len(cases):
            raise ValueError("Dataset task IDs must be unique")
        return cases

    def import_benchmark(self) -> "Catalog":
        info = BenchmarkInfo.model_validate_json(
            self.run(request=KernelRequest(arguments=("--humaneval-info",)))
        )
        records = tuple(
            download(
                request=Download(
                    source=info.source,
                    sha256=info.sha256,
                    destination=cache_path(sha256=info.sha256),
                )
            )
            .decode()
            .splitlines()
        )
        cases = self.import_records(records=records)
        if len(cases) != info.count:
            raise ValueError("Dataset count mismatch")
        return Catalog(
            cases=MappingProxyType({case.id: case for case in cases}),
            records=MappingProxyType(dict(zip((case.id for case in cases), records, strict=True))),
        )


@lru_cache(maxsize=1)
def _kernel(*, sources: Sources) -> _Kernel:
    directory = TemporaryDirectory(prefix="genius-kernel-")
    try:
        for name, contents in (*sources.modules, *sources.resources):
            (Path(directory.name) / name).write_text(contents)
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


def _sources(selection: Selection = "smoke") -> Sources:
    selection = SELECTION_ADAPTER.validate_python(selection, strict=True)
    match selection:
        case Path() as suite:
            pass
        case "smoke" | "humanevalplus":
            suite = SUITE
        case _ as unreachable:
            assert_never(unreachable)
    return Sources(
        modules=(
            *((path.name, path.read_text()) for path in LIBRARY),
            (SUITE.name, suite.read_text()),
            (EXPORTER.name, EXPORTER.read_text()),
        ),
        resources=_resources(),
    )


def _resources() -> tuple[tuple[str, str], ...]:
    return tuple(
        (path.name, path.read_text()) for path in (RUNNER, EVALS_ROOT / "python/verifier.py")
    )


class BenchmarkInfo(BaseModel):
    model_config = FROZEN

    source: str
    revision: str
    sha256: str
    count: int
    evaluator_commit: str
    numpy_version: str
    psutil_version: str


def benchmark_info() -> BenchmarkInfo:
    kernel = _kernel(sources=_sources())
    return BenchmarkInfo.model_validate_json(
        kernel.run(request=KernelRequest(arguments=("--humaneval-info",)))
    )


def benchmark_metadata(dataset: Dataset) -> dict[str, object]:
    match dataset:
        case "smoke":
            return {}
        case "humanevalplus":
            return benchmark_info().model_dump()
        case _ as unreachable:
            assert_never(unreachable)


@dataclass(frozen=True, kw_only=True)
class Download:
    source: str
    sha256: str
    destination: Path


def cache_path(sha256: str) -> Path:
    root = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    return root / "genius-evals" / f"{sha256}.jsonl"


def download(*, request: Download) -> bytes:
    if request.destination.exists():
        data = request.destination.read_bytes()
    else:
        with urllib.request.urlopen(request.source, timeout=60) as response:
            data = gzip.decompress(response.read())
    if hashlib.sha256(data).hexdigest() != request.sha256:
        raise ValueError("Dataset checksum mismatch")
    if not request.destination.exists():
        request.destination.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=request.destination.parent, delete=False) as stream:
            temporary = Path(stream.name)
            try:
                stream.write(data)
                stream.close()
                temporary.replace(request.destination)
            finally:
                temporary.unlink(missing_ok=True)
    return data


def import_records(records: tuple[str, ...]) -> tuple[Case, ...]:
    return _kernel(sources=_sources()).import_records(records=records)


@dataclass(frozen=True, kw_only=True)
class Catalog:
    cases: Mapping[str, Case]
    records: Mapping[str, str]


@dataclass(frozen=True, kw_only=True)
class CatalogRequest:
    selection: Selection
    sources: Sources


@lru_cache(maxsize=1)
def _catalog(request: CatalogRequest) -> Catalog:
    kernel = _kernel(sources=request.sources)
    match request.selection:
        case "smoke" | Path():
            cases = decode(data=kernel.run(request=KernelRequest()))
        case "humanevalplus":
            return kernel.import_benchmark()
        case _ as unreachable:
            assert_never(unreachable)
    return Catalog(
        cases=MappingProxyType({case.id: case for case in cases}), records=MappingProxyType({})
    )


def _selected(selection: Selection) -> Catalog:
    return _catalog(
        request=CatalogRequest(
            selection=selection,
            sources=_sources(selection=selection),
        )
    )


def load_cases(*, selection: Selection = "smoke") -> tuple[Case, ...]:
    return tuple(_selected(selection=selection).cases.values())


def case_by_id(*, query: CaseQuery) -> Case:
    return _selected(selection=query.selection).cases[query.case_id]


def workspace_files(case: Case) -> Mapping[str, str]:
    match case.checks:
        case ExecutableChecks(tools=tools):
            return MappingProxyType({**case.files, **tools})
        case None:
            return case.files
        case _ as unreachable:
            assert_never(unreachable)


VerificationStatus = Literal[
    "unchecked", "passed", "failed", "invalid_submission", "timed_out", "harness_error"
]


class Verification(BaseModel):
    model_config = FROZEN

    status: VerificationStatus
    detail: str = ""


Scores = Annotated[Mapping[str, bool], AfterValidator(MappingProxyType)]


class _GradingResult(BaseModel):
    """Named score results, matching the codec-free Score primitive in OCaml.

    Score vocabulary: https://developers.openai.com/api/docs/guides/graders
    and https://evalscope.readthedocs.io/en/latest/get_started/basic_usage.html
    """

    model_config = FROZEN

    version: int = Field(ge=2, le=2)
    scores: Scores


class GradeRequest(CaseQuery):
    response: str
    changed_files: tuple[str, ...]
    verification: Verification


def grade(*, request: GradeRequest) -> Mapping[str, bool]:
    payload: dict[str, object] = {
        "version": 2,
        "case_id": request.case_id,
        "response": request.response,
        "changed_files": request.changed_files,
        "verification": request.verification.model_dump(),
    }
    match request.selection:
        case "smoke" | Path():
            operation = "--grade"
        case "humanevalplus":
            operation = "--grade-humaneval"
            payload = {
                "record": _selected(selection=request.selection).records[request.case_id],
                "request": payload,
            }
        case _ as unreachable:
            assert_never(unreachable)
    kernel = _kernel(sources=_sources(selection=request.selection))
    result = _GradingResult.model_validate_json(
        kernel.run(request=KernelRequest(arguments=(operation,), data=json.dumps(payload)))
    )
    if not {"correctness", "scope"} <= result.scores.keys():
        raise ValueError("Kernel omitted required score names")
    return result.scores
