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
from secrets import token_hex
from tempfile import TemporaryDirectory
from types import MappingProxyType
from typing import Annotated, Final, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, PlainSerializer, TypeAdapter

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
SourceName = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*\.ml$")]
FileName = Annotated[str, Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_.-]*$")]
Files = Annotated[Mapping[FileName, str], AfterValidator(MappingProxyType), PlainSerializer(dict)]


class CodeChecks(BaseModel):
    """Private OCaml assertions, compiled against the agent's sources after it finishes."""

    model_config = FROZEN

    kind: Literal["code"]
    sources: tuple[SourceName, ...]
    program: str

    def tools(self) -> Mapping[str, str]:
        """The runner that task prompts call `check.sh`."""
        return MappingProxyType({RUNNER.name: RUNNER.read_text()})


class AnswerChecks(BaseModel):
    """Opaque response grading strategy; policy stays in the kernel."""

    model_config = FROZEN

    kind: Literal["answer"]

    def tools(self) -> Mapping[str, str]:
        return MappingProxyType({})


Checks = Annotated[CodeChecks | AnswerChecks, Field(discriminator="kind")]


class Case(BaseModel):
    """One exported case. Every field is read-only, so cached cases are safe to share."""

    model_config = FROZEN

    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    skill: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    prompt: str
    files: Files
    allowed_files: tuple[FileName, ...]
    checks: Checks
    solution: Files
    answer: str


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
def _kernel(sources: tuple[tuple[str, str], ...], *, runner: str) -> _Kernel:
    directory = TemporaryDirectory(prefix="genius-kernel-")
    try:
        for name, contents in (*sources, (RUNNER.name, runner)):
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
def _export(sources: tuple[tuple[str, str], ...], *, runner: str) -> str:
    return _kernel(sources, runner=runner).run()


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
    return _index(_export(_sources(suite), runner=RUNNER.read_text()))


def load_cases(suite: Path = SUITE) -> tuple[Case, ...]:
    return tuple(_suite_index(suite).values())


def case_by_id(case_id: str) -> Case:
    return _suite_index(SUITE)[case_id]


def workspace_files(case: Case) -> Mapping[str, str]:
    """Starting files plus any tools the case's checks give the agent."""
    return MappingProxyType({**case.files, **case.checks.tools()})


def heldout_check(checks: CodeChecks) -> tuple[list[str], str, str]:
    """Return the grader command, its OCaml program for stdin, and a fresh completion marker."""
    marker = "GENIUS_HELDOUT_" + token_hex(16)
    program = f'{checks.program}\nlet () = print_endline "\\n{marker}"\n'
    command = ["sh", "-c", RUNNER.read_text(), "ocaml-check", "--stdin", *checks.sources]
    return command, program, marker


Scores = Annotated[Mapping[str, bool], AfterValidator(MappingProxyType)]


class _GradingResult(BaseModel):
    """Named score results, matching the codec-free Score primitive in OCaml.

    Score vocabulary: https://developers.openai.com/api/docs/guides/graders
    and https://evalscope.readthedocs.io/en/latest/get_started/basic_usage.html
    """

    model_config = FROZEN

    version: int = Field(ge=1, le=1)
    scores: Scores


def grade(
    case_id: str,
    *,
    response: str,
    changed_files: tuple[str, ...],
    code_passed: bool,
    suite: Path = SUITE,
) -> Mapping[str, bool]:
    """Apply private kernel criteria to observed evidence, without caching candidate results."""
    request = json.dumps(
        {
            "version": 1,
            "case_id": case_id,
            "response": response,
            "changed_files": changed_files,
            "code_passed": code_passed,
        }
    )
    kernel = _kernel(_sources(suite), runner=RUNNER.read_text())
    result = _GradingResult.model_validate_json(kernel.run("--grade", data=request))
    if not {"correctness", "scope"} <= result.scores.keys():
        raise ValueError("Kernel omitted required score names")
    return result.scores
