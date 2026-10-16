"""Typed public queries return canonical values directly."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, assert_never

from pydantic import validate_call

from evals.python import catalog
from evals.python._kernel import (
    FROZEN,
    AnswerCriterion,
    Case,
    CaseDefinition,
    CodeCriterion,
    DatasetInfo,
    Experiment,
    Files,
    Inline,
    Instruction,
    PlainCompletion,
    ReferenceDefinition,
    Resource,
    StructuredCompletion,
    TextRule,
    Verification,
    VerifierDefinition,
)
from evals.python.catalog import Catalog as Dataset
from evals.python.catalog import Selection
from evals.python.verification import Runtime

__all__ = [
    "AnswerCriterion",
    "Case",
    "CaseDefinition",
    "Cases",
    "CodeCriterion",
    "CompileDataset",
    "Dataset",
    "DatasetInfo",
    "DatasetProvenance",
    "DescribeDataset",
    "ExecutionRuntime",
    "Experiment",
    "ExperimentSettings",
    "GradeCase",
    "Inline",
    "Instruction",
    "LoadDataset",
    "PlainCompletion",
    "Provenance",
    "ReferenceDefinition",
    "Resource",
    "Runtime",
    "Scores",
    "Selection",
    "StructuredCompletion",
    "TextRule",
    "Verification",
    "VerifierDefinition",
]

type Scores = Mapping[str, bool]
_UNCHECKED = Verification(status="unchecked")


@dataclass(frozen=True, kw_only=True)
class DatasetProvenance:
    info: DatasetInfo | None
    source_hash: str
    cases_hash: str


@validate_call(config=FROZEN)
def CompileDataset(
    *,
    cases: tuple[CaseDefinition, ...],
    info: DatasetInfo | None = None,
    resources: Files | None = None,
) -> Dataset:
    return catalog.compile_declarations(
        cases, info=info, resources={} if resources is None else resources
    )


@validate_call(config=FROZEN)
def LoadDataset(*, selection: Selection = "smoke") -> Dataset:
    return catalog.load_dataset(selection)


@validate_call(config=FROZEN)
def Cases(*, selection: Selection = "smoke") -> tuple[Case, ...]:
    return catalog.load_cases(selection=selection)


@validate_call(config=FROZEN)
def ExperimentSettings(
    *,
    epochs: int | None = None,
    message_limit: int | None = None,
    cost_limit: float | None = None,
    time_limit: int | None = None,
    cache: bool | None = None,
) -> Experiment:
    return catalog.experiment(
        epochs=epochs,
        message_limit=message_limit,
        cost_limit=cost_limit,
        time_limit=time_limit,
        cache=cache,
    )


@validate_call(config=FROZEN)
def DescribeDataset(*, selection: Selection = "smoke") -> DatasetInfo | None:
    return catalog.dataset_info(selection)


@validate_call(config=FROZEN)
def Provenance(*, selection: Selection = "smoke") -> DatasetProvenance:
    return DatasetProvenance(
        info=catalog.dataset_info(selection),
        source_hash=catalog.source_hash(selection),
        cases_hash=catalog.cases_hash(selection),
    )


@validate_call(config=FROZEN)
def GradeCase(
    *,
    case_id: str,
    response: str,
    changed_files: tuple[str, ...],
    verification: Verification = _UNCHECKED,
    selection: Selection = "smoke",
) -> Scores:
    return catalog.grade(
        case_id=case_id,
        response=response,
        changed_files=changed_files,
        verification=verification,
        selection=selection,
    )


@validate_call(config=FROZEN)
def ExecutionRuntime(*, provider: Literal["local", "hf"] = "local") -> Runtime:
    match provider:
        case "local":
            from evals.python.integrations.inspect import environments  # noqa: PLC0415 - lazy local SDK composition

            return environments.runtime()
        case "hf":
            from evals.python.integrations.hugging_face import sandbox  # noqa: PLC0415 - lazy HF SDK composition

            return sandbox.runtime()
        case _ as unreachable:
            assert_never(unreachable)
