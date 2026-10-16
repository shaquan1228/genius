"""Typed host operations preserving canonical kernel projections in process."""

from evals.python import verification as _verification
from evals.python.catalog import (
    Selection,
    cases_hash,
    dataset_info,
    experiment,
    grade,
    load_cases,
    reference,
    source_hash,
    verifier,
)
from evals.python.contracts import GradeRequest, Verification
from evals.python.verification import (
    Assessment,
    Completion,
    Environment,
    Execution,
    Runtime,
    VerificationResult,
)

__all__ = [
    "Assessment",
    "Completion",
    "Environment",
    "Execution",
    "GradeRequest",
    "Runtime",
    "Selection",
    "Verification",
    "VerificationResult",
    "assess_case",
    "cases_hash",
    "dataset_info",
    "experiment",
    "grade",
    "load_cases",
    "reference",
    "source_hash",
    "validate_reference",
    "verifier",
    "verify_case",
]


async def verify_case(
    case_id: str, *, selection: Selection = "smoke", agent: Environment, runtime: Runtime
) -> VerificationResult:
    checks = verifier(case_id, selection=selection)
    if checks is None:
        return VerificationResult(verification=Verification(status="unchecked"))
    return await _verification.verify(checks, agent=agent, runtime=runtime)


async def assess_case(
    request: GradeRequest, *, selection: Selection = "smoke", agent: Environment, runtime: Runtime
) -> Assessment:
    result = await verify_case(request.case_id, selection=selection, agent=agent, runtime=runtime)
    if result.verification.status == "harness_error":
        raise RuntimeError(f"Verification harness error: {result.verification.detail}")
    observed = request.model_copy(update={"verification": result.verification})
    return Assessment(
        verification=result.verification,
        metadata=result.metadata,
        scores=grade(request=observed, selection=selection),
    )


async def validate_reference(
    case_id: str, *, selection: Selection = "smoke", runtime: Runtime | None = None
) -> VerificationResult:
    if verifier(case_id, selection=selection) is None:
        return VerificationResult(verification=Verification(status="unchecked"))
    if runtime is None:
        from evals.python.integrations.inspect.environments import (  # noqa: PLC0415 - lazy local composition
            runtime as local_runtime,
        )

        runtime = local_runtime()
    try:
        async with _verification.allocated(runtime) as agent:
            await _verification.stage_reference(
                reference(case_id, selection=selection).solution, agent=agent
            )
            return await verify_case(case_id, selection=selection, agent=agent, runtime=runtime)
    except Exception as error:
        return VerificationResult(
            verification=Verification(status="harness_error", detail=str(error))
        )
