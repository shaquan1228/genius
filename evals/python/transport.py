"""The only bridge between the OCaml suite and the Python harness.

It compiles the OCaml modules, decodes their export into immutable cases, and
builds the OCaml runner inputs that grade a workspace. No other Python module
reads OCaml sources or writes OCaml code.
"""

import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
from typing import Annotated, Final, Literal

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


class Case(BaseModel):
    """One exported case. Every field is read-only, so cached cases are safe to share.

    Answer cases have no checks: the kernel grades their replies.
    """

    model_config = FROZEN

    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    skill: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    prompt: str
    files: Files
    checks: CodeChecks | None
    solution: Files
    answer: str

    @model_validator(mode="after")
    def validate_files(self) -> "Case":
        if not set(self.solution) <= set(self.allowed_files):
            raise ValueError("Reference edits files outside allowed_files")
        if isinstance(self.checks, ExecutableChecks):
            self.validate_verifier_files(self.checks)
        return self

    def validate_verifier_files(self, checks: ExecutableChecks) -> None:
        if not set(checks.inputs) <= self.files.keys():
            raise ValueError("Verifier inputs missing from fixture")
        if (checks.files.keys() | checks.tools.keys()) & self.files.keys():
            raise ValueError("Verifier artifacts overlap fixture")


def decode(data: str) -> tuple[Case, ...]:
    cases = TypeAdapter(tuple[Case, ...]).validate_json(data)
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("Suite case IDs must be unique")
    return cases


@dataclass(frozen=True)
class _Kernel:
    directory: TemporaryDirectory[str]

    def run(self, *arguments: str, data: str | None = None) -> str:
        return subprocess.run(
            [str(Path(self.directory.name) / "kernel"), *arguments],
            input=data,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
            timeout=30,
        ).stdout


@lru_cache(maxsize=1)
def _kernel(
    sources: tuple[tuple[str, str], ...], *, resources: tuple[tuple[str, str], ...]
) -> _Kernel:
    directory = TemporaryDirectory(prefix="genius-kernel-")
    try:
        for name, contents in (*sources, *resources):
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
                *(name for name, _ in sources),
            ],
            cwd=directory.name,
            check=True,
            timeout=30,
        )
    except BaseException:
        directory.cleanup()
        raise
    return _Kernel(directory)


@lru_cache(maxsize=1)
def _export(sources: tuple[tuple[str, str], ...], *, resources: tuple[tuple[str, str], ...]) -> str:
    return _kernel(sources, resources=resources).run()


@lru_cache(maxsize=1)
def _index(data: str) -> Mapping[str, Case]:
    return MappingProxyType({case.id: case for case in decode(data)})


def _sources(suite: Path) -> tuple[tuple[str, str], ...]:
    return (
        *((path.name, path.read_text()) for path in LIBRARY),
        (SUITE.name, suite.read_text()),
        (EXPORTER.name, EXPORTER.read_text()),
    )


def _suite_index(suite: Path) -> Mapping[str, Case]:
    return _index(_export(_sources(suite), resources=_resources()))


def load_cases(suite: Path = SUITE) -> tuple[Case, ...]:
    return tuple(_suite_index(suite).values())


def case_by_id(case_id: str) -> Case:
    return _suite_index(SUITE)[case_id]


def workspace_files(case: Case) -> Mapping[str, str]:
    """Starting files plus any tools the case's checks give the agent."""
    tools = {} if case.checks is None else case.checks.tools
    return MappingProxyType({**case.files, **tools})


def _resources() -> tuple[tuple[str, str], ...]:
    return tuple(
        (path.name, path.read_text())
        for path in (RUNNER, *(EVALS_ROOT / "python").glob("*_verifier.py"))
    )


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


def grade(
    case_id: str,
    *,
    response: str,
    changed_files: tuple[str, ...],
    verification: Verification,
    suite: Path = SUITE,
) -> Mapping[str, bool]:
    """Apply private kernel criteria to observed evidence, without caching candidate results."""
    request = json.dumps(
        {
            "version": 2,
            "case_id": case_id,
            "response": response,
            "changed_files": changed_files,
            "verification": verification.model_dump(),
        }
    )
    kernel = _kernel(_sources(suite), resources=_resources())
    result = _GradingResult.model_validate_json(kernel.run("--grade", data=request))
    if not {"correctness", "scope"} <= result.scores.keys():
        raise ValueError("Kernel omitted required score names")
    return result.scores
