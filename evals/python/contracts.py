"""Immutable protocol values shared by every evaluation integration.

These are wire projections of OCaml values, not SDK models or grading policy.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Annotated, Final, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, PlainSerializer

VERSION: Final = 3
FROZEN: Final = ConfigDict(strict=True, extra="forbid", frozen=True)
FileName = Annotated[str, Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_.-]*$")]
Files = Annotated[Mapping[FileName, str], AfterValidator(MappingProxyType), PlainSerializer(dict)]
Attributes = Annotated[Mapping[str, str], AfterValidator(MappingProxyType), PlainSerializer(dict)]
Selection = str | Path


class Case(BaseModel):
    """Public agent inputs only. Private checks and references use separate projections."""

    model_config = FROZEN
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    skill: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    prompt: str
    files: Files


class ExecutableChecks(BaseModel):
    model_config = FROZEN
    inputs: tuple[FileName, ...] = Field(min_length=1)
    files: Files
    tools: Files
    command: tuple[Annotated[str, Field(min_length=1)], ...] = Field(min_length=1)
    stdin: str
    timeout_seconds: int = Field(gt=0)


class Reference(BaseModel):
    model_config = FROZEN
    solution: Files
    answer: str


class DatasetInfo(BaseModel):
    model_config = FROZEN
    source: str
    revision: str
    sha256: str
    count: int = Field(ge=0)
    attributes: Attributes


class ProfileSpec(BaseModel):
    model_config = FROZEN
    name: str
    preamble: str
    instructions: tuple[str, ...]


class Experiment(BaseModel):
    model_config = FROZEN
    profiles: tuple[ProfileSpec, ...]
    epochs: int = Field(gt=0)
    message_limit: int = Field(gt=0)
    token_limit: int = Field(gt=0)
    time_limit: int = Field(gt=0)
    cache: bool


class RunOverrides(BaseModel):
    """Unresolved launch inputs; OCaml supplies defaults and validates their meaning."""

    model_config = FROZEN
    epochs: int | None = None
    message_limit: int | None = None
    token_limit: int | None = None
    time_limit: int | None = None
    cache: bool | None = None


class CaseQuery(BaseModel):
    model_config = FROZEN
    case_id: str
    selection: Selection = "smoke"


VerificationStatus = Literal[
    "unchecked", "passed", "failed", "invalid_submission", "timed_out", "harness_error"
]


class Verification(BaseModel):
    model_config = FROZEN
    status: VerificationStatus
    detail: str = ""


class GradeRequest(CaseQuery):
    response: str
    changed_files: tuple[str, ...]
    verification: Verification


@dataclass(frozen=True, kw_only=True)
class Program:
    """Trusted compiler inputs selected by a dataset integration."""

    suite: Path
    adapter: Path
    resources: tuple[Path, ...]


@dataclass(frozen=True, kw_only=True)
class Sources:
    modules: tuple[tuple[str, str], ...]
    resources: tuple[tuple[str, str], ...]
