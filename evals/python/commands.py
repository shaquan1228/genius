"""Typed public commands perform effects and return canonical results directly."""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, InstanceOf, validate_call

from evals.python import catalog
from evals.python import query as _query
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
    "Cleanup",
    "Completion",
    "DatasetInfo",
    "Diagnostic",
    "Environment",
    "Evaluate",
    "EvaluationSettings",
    "Execution",
    "Experiment",
    "InstructionDelivery",
    "ProfileSpec",
    "Runtime",
    "ValidateReference",
    "Verification",
    "VerificationResult",
    "VerifyCase",
]

type InstructionDelivery = Literal["files", "manifest", "inline"]


def _unique[T](values: tuple[T, ...]) -> tuple[T, ...]:
    if len(set(values)) != len(values):
        raise ValueError("Selection must contain unique values")
    return values


class EvaluationSettings(BaseModel):
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


@validate_call(config=FROZEN)
async def VerifyCase(
    *,
    case_id: str,
    selection: Selection = "smoke",
    agent: InstanceOf[Environment],
    runtime: InstanceOf[Runtime],
) -> VerificationResult:
    checks = catalog.verifier(case_id, selection=selection)
    if checks is None:
        return VerificationResult(verification=Verification(status="unchecked"))
    return await _verification.verify(checks, agent=agent, runtime=runtime)


@validate_call(config=FROZEN)
async def AssessCase(
    *,
    case_id: str,
    response: str,
    changed_files: tuple[str, ...],
    selection: Selection = "smoke",
    agent: InstanceOf[Environment],
    runtime: InstanceOf[Runtime],
) -> Assessment:
    result = await VerifyCase(case_id=case_id, selection=selection, agent=agent, runtime=runtime)
    if result.verification.status == "harness_error":
        raise RuntimeError(f"Verification harness error: {result.verification.detail}")
    return Assessment(
        verification=result.verification,
        metadata=result.metadata,
        scores=_query.GradeCase(
            case_id=case_id,
            response=response,
            changed_files=changed_files,
            verification=result.verification,
            selection=selection,
        ),
    )


@validate_call(config=FROZEN)
async def ValidateReference(
    *,
    case_id: str,
    selection: Selection = "smoke",
    runtime: InstanceOf[Runtime] | None = None,
) -> VerificationResult:
    if catalog.verifier(case_id, selection=selection) is None:
        return VerificationResult(verification=Verification(status="unchecked"))
    runtime = runtime or _query.ExecutionRuntime()
    try:
        async with _verification.allocated(runtime) as agent:
            await _verification.stage_reference(
                catalog.reference(case_id, selection=selection).solution,
                agent=agent,
            )
            return await VerifyCase(
                case_id=case_id, selection=selection, agent=agent, runtime=runtime
            )
    except Exception as error:
        return VerificationResult(
            verification=Verification(status="harness_error", detail=str(error))
        )


async def Evaluate(
    *,
    model: str,
    agent: str = "claude",
    version: str = "",
    dataset: str = "smoke",
    sandbox: str = "local",
    instruction_root: str = "../instructions",
    epochs: int | None = None,
    token_limit: int | None = None,
    limit: int | None = None,
    sample_ids: tuple[str, ...] | None = None,
    instruction_delivery: InstructionDelivery = "files",
    deliveries: tuple[InstructionDelivery, ...] | None = None,
    log_dir: str = "/results/live",
) -> int:
    settings = EvaluationSettings(
        model=model,
        agent=agent,
        version=version,
        dataset=dataset,
        sandbox=sandbox,
        instruction_root=instruction_root,
        epochs=epochs,
        token_limit=token_limit,
        limit=limit,
        sample_ids=sample_ids,
        instruction_delivery=instruction_delivery,
        deliveries=deliveries,
        log_dir=log_dir,
    )
    from evals.python.integrations.inspect import evaluation  # noqa: PLC0415 - lazy SDK composition

    return await evaluation.evaluate_async(settings)
