"""Validate the task manifest at the framework boundary."""

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

EVALS_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EVALS_ROOT.parent
Profile = Literal["baseline", "genius"]
FixtureName = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]*$")]
SourceName = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*\.ml$")]


class Case(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    skill: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    fixtures: list[FixtureName] = Field(min_length=1)
    sources: list[SourceName] = Field(default_factory=list)
    allowed_files: list[str]
    prompt: str
    heldout_test: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_-]*\.ml$")


def load_cases(path: Path = EVALS_ROOT / "cases.json") -> list[Case]:
    return TypeAdapter(list[Case]).validate_json(path.read_bytes())
