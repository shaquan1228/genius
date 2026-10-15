"""Compile the OCaml suite once per source revision and validate its exported data."""

import subprocess
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

EVALS_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EVALS_ROOT.parent
Profile = Literal["baseline", "genius"]
Grading = Literal["ocaml", "choice", "review"]
SourceName = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*\.ml$")]
FileName = Annotated[str, Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_.-]*$")]


class Case(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    skill: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    prompt: str
    files: dict[FileName, str]
    allowed_files: list[FileName]
    grading: Grading
    sources: list[SourceName]
    heldout: str | None
    expected: dict[str, str | bool]
    solution: dict[FileName, str]
    answer: str


@lru_cache(maxsize=1)
def export_suite(suite: str, *, families: str, runner: str) -> str:
    with TemporaryDirectory(prefix="genius-suite-") as directory:
        for name, contents in {
            "fixtures.ml": families,
            "suite.ml": suite,
            "check.sh": runner,
        }.items():
            (Path(directory) / name).write_text(contents)
        return subprocess.run(
            ["sh", "check.sh", "fixtures.ml", "suite.ml"],
            cwd=directory,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout


@lru_cache(maxsize=1)
def _parsed_suite(data: str) -> dict[str, Case]:
    cases = TypeAdapter(list[Case]).validate_json(data)
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("Suite case IDs must be unique")
    return {case.id: case for case in cases}


def _suite_index(path: Path = EVALS_ROOT / "suite.ml") -> dict[str, Case]:
    data = export_suite(
        path.read_text(),
        families=(EVALS_ROOT / "fixtures.ml").read_text(),
        runner=(EVALS_ROOT / "check.sh").read_text(),
    )
    return _parsed_suite(data)


def load_cases(path: Path = EVALS_ROOT / "suite.ml") -> list[Case]:
    return [case.model_copy(deep=True) for case in _suite_index(path).values()]


def case_by_id(case_id: str) -> Case:
    return _suite_index()[case_id].model_copy(deep=True)
