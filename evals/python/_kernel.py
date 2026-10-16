"""Private, immutable projections of the OCaml kernel domain."""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, PlainSerializer

FROZEN = ConfigDict(strict=True, extra="forbid", frozen=True)
FileName = Annotated[str, Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_.-]*$")]
Files = Annotated[Mapping[FileName, str], AfterValidator(MappingProxyType), PlainSerializer(dict)]
Attributes = Annotated[Mapping[str, str], AfterValidator(MappingProxyType), PlainSerializer(dict)]


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


VerificationStatus = Literal[
    "unchecked", "passed", "failed", "invalid_submission", "timed_out", "harness_error"
]


class Verification(BaseModel):
    model_config = FROZEN
    status: VerificationStatus
    detail: str = ""


class Inline(BaseModel):
    model_config = FROZEN
    kind: Literal["inline"] = "inline"
    text: str


class Resource(BaseModel):
    model_config = FROZEN
    kind: Literal["resource"] = "resource"
    name: str


Content = Annotated[Inline | Resource, Field(discriminator="kind")]
Artifacts = Annotated[
    Mapping[FileName, Content], AfterValidator(MappingProxyType), PlainSerializer(dict)
]
Response = Annotated[
    Mapping[str, str | bool], AfterValidator(MappingProxyType), PlainSerializer(dict)
]


class VerifierDefinition(BaseModel):
    model_config = FROZEN
    inputs: tuple[FileName, ...]
    files: Artifacts
    tools: Artifacts
    command: tuple[str, ...]
    stdin: str
    timeout_seconds: int


class Instruction(BaseModel):
    model_config = FROZEN
    skill: str
    prompt: str


class TextRule(BaseModel):
    model_config = FROZEN
    field: str
    min_words: int
    max_words: int


class AnswerCriterion(BaseModel):
    model_config = FROZEN
    kind: Literal["answer"] = "answer"
    expected: Response
    text_rule: TextRule | None = None


class CodeCriterion(BaseModel):
    model_config = FROZEN
    kind: Literal["code"] = "code"
    verifier: VerifierDefinition


class PlainCompletion(BaseModel):
    model_config = FROZEN
    kind: Literal["plain"] = "plain"
    text: str


class StructuredCompletion(BaseModel):
    model_config = FROZEN
    kind: Literal["structured"] = "structured"
    fields: Response


class ReferenceDefinition(BaseModel):
    model_config = FROZEN
    edits: Files
    completion: Annotated[PlainCompletion | StructuredCompletion, Field(discriminator="kind")]


class CaseDefinition(BaseModel):
    """Construction binding for Ast.case; Case remains its public read projection."""

    model_config = FROZEN
    id: str
    fixture: Files
    instruction: Instruction
    criterion: Annotated[CodeCriterion | AnswerCriterion, Field(discriminator="kind")]
    allowed_files: tuple[FileName, ...]
    reference: ReferenceDefinition
