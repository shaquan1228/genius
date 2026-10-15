"""The only bridge between the OCaml suite and the Python harness.

It compiles the OCaml modules, decodes their export into immutable cases, and
builds the OCaml runner inputs that grade a workspace. No other Python module
reads OCaml sources or writes OCaml code.
"""

import subprocess
from collections.abc import Mapping
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
        "fixture.mli",
        "fixture.ml",
        "fixtures.ml",
        "check.ml",
        "task.ml",
        "reference.ml",
        "eval.ml",
    )
)
SUITE: Final = OCAML_ROOT / "suite.ml"
EXPORTER: Final = OCAML_ROOT / "transport.ml"
RUNNER: Final = OCAML_ROOT / "check.sh"

FROZEN: Final = ConfigDict(strict=True, extra="forbid", frozen=True)
SourceName = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*\.ml$")]
FileName = Annotated[str, Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_.-]*$")]
Files = Annotated[Mapping[FileName, str], AfterValidator(MappingProxyType), PlainSerializer(dict)]
Expected = Annotated[
    Mapping[str, str | bool], AfterValidator(MappingProxyType), PlainSerializer(dict)
]


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
    """Expected fields of the agent's JSON reply."""

    model_config = FROZEN

    kind: Literal["answer"]
    expected: Expected

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


@lru_cache(maxsize=1)
def _export(sources: tuple[tuple[str, str], ...], *, runner: str) -> str:
    with TemporaryDirectory(prefix="genius-suite-") as directory:
        for name, contents in (*sources, (RUNNER.name, runner)):
            (Path(directory) / name).write_text(contents)
        # Compiler and assembly errors stay on stderr so suite authors can read them.
        return subprocess.run(
            ["sh", RUNNER.name, *(name for name, _ in sources)],
            cwd=directory,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
            timeout=30,
        ).stdout


@lru_cache(maxsize=1)
def _index(data: str) -> Mapping[str, Case]:
    return MappingProxyType({case.id: case for case in decode(data)})


def _suite_index(suite: Path) -> Mapping[str, Case]:
    sources = (
        *((path.name, path.read_text()) for path in LIBRARY),
        (SUITE.name, suite.read_text()),
        (EXPORTER.name, EXPORTER.read_text()),
    )
    return _index(_export(sources, runner=RUNNER.read_text()))


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
