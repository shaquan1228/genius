"""Validate the task manifest at the framework boundary."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, TypeAdapter

EVALS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = EVALS_ROOT.parent
CaseId = Literal["clear-task", "known-preflight", "small-decision", "decision-review"]
Profile = Literal["baseline", "genius"]


class Case(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    id: CaseId
    skill: Literal["reasoning", "preflight", "bayesian"]
    fixture: Literal["clear-task", "known-preflight", "empty"]
    allowed_files: list[str]
    prompt: str


def load_cases(path: Path = EVALS_ROOT / "cases.json") -> list[Case]:
    return TypeAdapter(list[Case]).validate_json(path.read_bytes())


def state_case(metadata: dict[str, object]) -> Case:
    return Case.model_validate(metadata["case"])
