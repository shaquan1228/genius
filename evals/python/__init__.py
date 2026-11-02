"""Genius records over the native kernel: what a run measures and what a candidate receives.

The kernel owns grading semantics; these records own the Genius policy it leaves out.
"""

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

from kernel import SourceFile, Task
from pydantic import AfterValidator, BaseModel, ConfigDict, Field

FROZEN = ConfigDict(strict=True, extra="forbid", frozen=True, arbitrary_types_allowed=True)
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")]

REPO_ROOT = Path(__file__).resolve().parents[2]
EVALS_ROOT = REPO_ROOT / "evals"


def unique[T](values: tuple[T, ...]) -> tuple[T, ...]:
    if len(set(values)) != len(values):
        raise ValueError("Selection must contain unique values")
    return values


def _instruction_paths(paths: tuple[str, ...]) -> tuple[str, ...]:
    for path in paths:
        _instruction_path(path)
    return unique(paths)


def _instruction_path(path: str) -> None:
    if str(PurePosixPath(path)) != path or path.startswith("/") or ".." in path.split("/"):
        raise ValueError("Instruction paths must be relative and normalized")
    if path == ".":
        raise ValueError("Instruction paths must name a file or directory")


Instructions = Annotated[tuple[str, ...], AfterValidator(_instruction_paths)]


@dataclass(frozen=True, kw_only=True)
class Case:
    """The public projection a candidate receives, with the skill it exercises."""

    case_id: str
    skill: str
    prompt: str
    files: tuple[SourceFile, ...]


type RouteChoice = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]*$")] | None


class Declaration(BaseModel):
    """A native task and the Genius skill it evaluates.

    `routes` overrides the accepted choices per route kind; the skill route accepts only
    `skill` unless overridden. `None` accepts choosing nothing.
    """

    model_config = FROZEN
    skill: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    task: Task
    routes: dict[str, Annotated[tuple[RouteChoice, ...], Field(min_length=1)]] = Field(
        default_factory=dict
    )

    def project(self) -> Case:
        case = self.task.project()
        return Case(case_id=case.case_id, skill=self.skill, prompt=case.prompt, files=case.files)


type Placement = Literal["instructions", "discoverable"]


class Profile(BaseModel):
    """One instruction variant delivered to the candidate.

    `instructions` placement copies documents beside the workspace for the preamble to
    name. `discoverable` installs them where the agent finds skills itself, so the agent
    chooses which skill to load.
    """

    model_config = FROZEN
    name: Identifier
    preamble: str
    instructions: Instructions
    placement: Placement = "instructions"


BASELINE = Profile(name="baseline", preamble="", instructions=())
GENIUS = Profile(
    name="genius",
    preamble="Read ../instructions/skills/{skill}/SKILL.md and its referenced files. Apply that "
    "skill to this task.\n\n",
    instructions=("docs", "skills"),
)
ROUTING = Profile(
    name="routing", preamble="", instructions=("docs", "skills"), placement="discoverable"
)


class Experiment(BaseModel):
    """The measurement settings a run is executed under."""

    model_config = FROZEN
    profiles: tuple[Profile, ...] = (BASELINE, GENIUS)
    epochs: int = Field(default=5, gt=0)
    message_limit: int | None = Field(default=None, gt=0)
    cost_limit: float = Field(default=0.25, gt=0, allow_inf_nan=False)
    time_limit: int = Field(default=300, gt=0)
    cache: bool = False
