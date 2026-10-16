"""Immutable public operations and their canonical, correlated results."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Annotated, Literal, assert_never, overload

from pydantic import AfterValidator, BaseModel, Field, InstanceOf

from evals.python import catalog
from evals.python import verification as _verification
from evals.python._kernel import (
    FROZEN,
    Case,
    DatasetInfo,
    Experiment,
    ProfileSpec,
    Verification,
)
from evals.python.catalog import Selection
from evals.python.verification import (
    Assessment,
    Cleanup,
    Completion,
    Diagnostic,
    Environment,
    Execution,
    Runtime,
    VerificationResult,
)

__all__ = [
    "AssessCase",
    "Assessment",
    "Case",
    "Cases",
    "Cleanup",
    "Completion",
    "DatasetInfo",
    "DatasetProvenance",
    "DescribeDataset",
    "Diagnostic",
    "Environment",
    "Evaluate",
    "Execution",
    "Experiment",
    "ExperimentSettings",
    "GradeCase",
    "InstructionDelivery",
    "ProfileSpec",
    "Provenance",
    "Runtime",
    "Scores",
    "Selection",
    "ValidateReference",
    "Verification",
    "VerificationResult",
    "VerifyCase",
    "execute",
    "query",
]

type Scores = Mapping[str, bool]
type InstructionDelivery = Literal["files", "manifest", "inline"]


def _unique[T](values: tuple[T, ...]) -> tuple[T, ...]:
    if len(set(values)) != len(values):
        raise ValueError("Selection must contain unique values")
    return values


class Cases(BaseModel):
    model_config = FROZEN
    selection: Selection = "smoke"


class ExperimentSettings(BaseModel):
    model_config = FROZEN
    epochs: int | None = None
    message_limit: int | None = None
    token_limit: int | None = None
    time_limit: int | None = None
    cache: bool | None = None


class DescribeDataset(BaseModel):
    model_config = FROZEN
    selection: Selection = "smoke"


class Provenance(BaseModel):
    model_config = FROZEN
    selection: Selection = "smoke"


@dataclass(frozen=True, kw_only=True)
class DatasetProvenance:
    info: DatasetInfo | None
    source_hash: str
    cases_hash: str


class GradeCase(BaseModel):
    model_config = FROZEN
    case_id: str
    response: str
    changed_files: tuple[str, ...]
    verification: Verification = Verification(status="unchecked")
    selection: Selection = "smoke"


class VerifyCase(BaseModel):
    model_config = FROZEN
    case_id: str
    selection: Selection = "smoke"
    agent: InstanceOf[Environment]
    runtime: InstanceOf[Runtime]


class AssessCase(BaseModel):
    model_config = FROZEN
    case_id: str
    response: str
    changed_files: tuple[str, ...]
    selection: Selection = "smoke"
    agent: InstanceOf[Environment]
    runtime: InstanceOf[Runtime]


class ValidateReference(BaseModel):
    model_config = FROZEN
    case_id: str
    selection: Selection = "smoke"
    runtime: InstanceOf[Runtime] | None = None


class Evaluate(BaseModel):
    model_config = FROZEN
    model: str
    agent: str = "claude"
    version: str = ""
    dataset: str = "smoke"
    sandbox: str = "local"
    instruction_root: str = "../instructions"
    epochs: int | None = None
    token_limit: int | None = None
    limit: int | None = Field(default=None, gt=0)
    sample_ids: Annotated[tuple[str, ...], Field(min_length=1), AfterValidator(_unique)] | None = (
        None
    )
    instruction_delivery: InstructionDelivery = "files"
    deliveries: (
        Annotated[tuple[InstructionDelivery, ...], Field(min_length=2), AfterValidator(_unique)]
        | None
    ) = None
    log_dir: str = "/results/live"


@overload
def query(operation: Cases) -> tuple[Case, ...]: ...


@overload
def query(operation: ExperimentSettings) -> Experiment: ...


@overload
def query(operation: DescribeDataset) -> DatasetInfo | None: ...


@overload
def query(operation: Provenance) -> DatasetProvenance: ...


@overload
def query(operation: GradeCase) -> Scores: ...


def query(
    operation: Cases | ExperimentSettings | DescribeDataset | Provenance | GradeCase,
) -> tuple[Case, ...] | Experiment | DatasetInfo | DatasetProvenance | Scores | None:
    match operation:
        case Cases():
            return catalog.load_cases(selection=operation.selection)
        case ExperimentSettings():
            return catalog.experiment(
                epochs=operation.epochs,
                message_limit=operation.message_limit,
                token_limit=operation.token_limit,
                time_limit=operation.time_limit,
                cache=operation.cache,
            )
        case DescribeDataset() | Provenance():
            return _describe(operation)
        case GradeCase():
            return catalog.grade(
                case_id=operation.case_id,
                response=operation.response,
                changed_files=operation.changed_files,
                verification={
                    "status": operation.verification.status,
                    "detail": operation.verification.detail,
                },
                selection=operation.selection,
            )
        case _:
            assert_never(operation)


def _describe(operation: DescribeDataset | Provenance) -> DatasetInfo | DatasetProvenance | None:
    info = catalog.dataset_info(operation.selection)
    match operation:
        case DescribeDataset():
            return info
        case Provenance():
            return DatasetProvenance(
                info=info,
                source_hash=catalog.source_hash(operation.selection),
                cases_hash=catalog.cases_hash(operation.selection),
            )
        case _ as unreachable:
            assert_never(unreachable)


@overload
async def execute(operation: VerifyCase) -> VerificationResult: ...


@overload
async def execute(operation: AssessCase) -> Assessment: ...


@overload
async def execute(operation: ValidateReference) -> VerificationResult: ...


@overload
async def execute(operation: Evaluate) -> int: ...


async def execute(
    operation: VerifyCase | AssessCase | ValidateReference | Evaluate,
) -> VerificationResult | Assessment | int:
    match operation:
        case VerifyCase():
            return await _verify(operation)
        case AssessCase():
            return await _assess(operation)
        case ValidateReference():
            return await _validate_reference(operation)
        case Evaluate():
            from evals.python.integrations.inspect.evaluation import (  # noqa: PLC0415 - lazy SDK composition
                evaluate_async,
            )

            return await evaluate_async(operation)
        case _:
            assert_never(operation)


GradeRequest = GradeCase
RunOverrides = ExperimentSettings
load_cases = catalog.load_cases
dataset_info = catalog.dataset_info
source_hash = catalog.source_hash
cases_hash = catalog.cases_hash
verifier = catalog.verifier
reference = catalog.reference


def experiment(overrides: ExperimentSettings | None = None) -> Experiment:
    return query(overrides or ExperimentSettings())


def grade(*, request: GradeCase, selection: Selection = "smoke") -> Scores:
    return query(request.model_copy(update={"selection": selection}))


async def _verify(operation: VerifyCase) -> VerificationResult:
    checks = catalog.verifier(operation.case_id, selection=operation.selection)
    if checks is None:
        return VerificationResult(verification=Verification(status="unchecked"))
    return await _verification.verify(checks, agent=operation.agent, runtime=operation.runtime)


async def _assess(operation: AssessCase) -> Assessment:
    result = await execute(
        VerifyCase(
            case_id=operation.case_id,
            selection=operation.selection,
            agent=operation.agent,
            runtime=operation.runtime,
        )
    )
    if result.verification.status == "harness_error":
        raise RuntimeError(f"Verification harness error: {result.verification.detail}")
    return Assessment(
        verification=result.verification,
        metadata=result.metadata,
        scores=query(
            GradeCase(
                case_id=operation.case_id,
                response=operation.response,
                changed_files=operation.changed_files,
                verification=result.verification,
                selection=operation.selection,
            )
        ),
    )


async def _validate_reference(operation: ValidateReference) -> VerificationResult:
    if catalog.verifier(operation.case_id, selection=operation.selection) is None:
        return VerificationResult(verification=Verification(status="unchecked"))
    runtime = operation.runtime
    if runtime is None:
        from evals.python.integrations.inspect.environments import (  # noqa: PLC0415 - lazy local composition
            runtime as local_runtime,
        )

        runtime = local_runtime()
    try:
        async with _verification.allocated(runtime) as agent:
            await _verification.stage_reference(
                catalog.reference(operation.case_id, selection=operation.selection).solution,
                agent=agent,
            )
            return await execute(
                VerifyCase(
                    case_id=operation.case_id,
                    selection=operation.selection,
                    agent=agent,
                    runtime=runtime,
                )
            )
    except Exception as error:
        return VerificationResult(
            verification=Verification(status="harness_error", detail=str(error))
        )


async def verify_case(
    case_id: str, *, selection: Selection = "smoke", agent: Environment, runtime: Runtime
) -> VerificationResult:
    return await execute(
        VerifyCase(case_id=case_id, selection=selection, agent=agent, runtime=runtime)
    )


async def assess_case(
    request: GradeCase, *, selection: Selection = "smoke", agent: Environment, runtime: Runtime
) -> Assessment:
    return await execute(
        AssessCase(
            case_id=request.case_id,
            response=request.response,
            changed_files=request.changed_files,
            selection=selection,
            agent=agent,
            runtime=runtime,
        )
    )


async def validate_reference(
    case_id: str, *, selection: Selection = "smoke", runtime: Runtime | None = None
) -> VerificationResult:
    return await execute(ValidateReference(case_id=case_id, selection=selection, runtime=runtime))
