"""Public commands own execution effects and provider composition."""

from typing import Literal, assert_never

from pydantic import InstanceOf, validate_call

import kernel
from evals.python import datasets, evaluation_settings, schema
from evals.python import queries as _queries
from evals.python import verification as _verification
from kernel._operations import fixture as fixture_ops
from kernel._operations import projection as projection_ops

__all__ = ["assess", "create_runtime", "evaluate", "validate_reference", "verify"]


@validate_call(config=schema.FROZEN)
def create_runtime(*, provider: Literal["local", "hf"] = "local") -> _verification.Runtime:
    match provider:
        case "local":
            from evals.python.integrations.inspect import environments  # noqa: PLC0415 - lazy local SDK composition

            return environments.runtime()
        case "hf":
            from evals.python.integrations.hugging_face import sandbox  # noqa: PLC0415 - lazy HF SDK composition

            return sandbox.runtime()
        case _ as unreachable:
            assert_never(unreachable)


@validate_call(config=schema.FROZEN)
async def verify(
    *,
    case_id: str,
    selection: datasets.Selection = "smoke",
    agent: InstanceOf[_verification.Environment],
    runtime: InstanceOf[_verification.Runtime],
) -> _verification.VerificationResult:
    checks = projection_ops.verifier(datasets.record(case_id, selection=selection))
    if checks is None:
        return _verification.VerificationResult(verification=kernel.Verification.Unchecked())
    return await _verification.verify(checks, agent=agent, runtime=runtime)


@validate_call(config=schema.FROZEN)
async def assess(
    *,
    case_id: str,
    response: str,
    changed_files: tuple[str, ...],
    selection: datasets.Selection = "smoke",
    agent: InstanceOf[_verification.Environment],
    runtime: InstanceOf[_verification.Runtime],
) -> _verification.Assessment:
    result = await verify(case_id=case_id, selection=selection, agent=agent, runtime=runtime)
    if isinstance(result.verification, kernel.Verification.HarnessError):
        raise RuntimeError(f"Verification harness error: {result.verification[0]}")
    return _verification.Assessment(
        verification=result.verification,
        detail=result.detail,
        metadata=result.metadata,
        scores=_queries.score_case(
            case_id=case_id,
            response=response,
            changed_files=changed_files,
            verification=result.verification,
            selection=selection,
        ),
    )


@validate_call(config=schema.FROZEN)
async def validate_reference(
    *,
    case_id: str,
    selection: datasets.Selection = "smoke",
    runtime: InstanceOf[_verification.Runtime] | None = None,
) -> _verification.VerificationResult:
    if projection_ops.verifier(datasets.record(case_id, selection=selection)) is None:
        return _verification.VerificationResult(verification=kernel.Verification.Unchecked())
    runtime = runtime or create_runtime()
    try:
        async with _verification.allocated(runtime) as agent:
            await _verification.stage_reference(
                dict(
                    fixture_ops.files(
                        projection_ops.reference(
                            datasets.record(case_id, selection=selection)
                        ).edits
                    )
                ),
                agent=agent,
            )
            return await verify(case_id=case_id, selection=selection, agent=agent, runtime=runtime)
    except Exception as error:
        return _verification.VerificationResult(
            verification=kernel.Verification.HarnessError(str(error))
        )


async def evaluate(
    *,
    model: str,
    run_id: str | None = None,
    agent: str = "claude",
    version: str = "",
    dataset: str = "smoke",
    sandbox: str = "local",
    instruction_root: str = "../instructions",
    epochs: int | None = None,
    cost_limit: float | None = None,
    model_cost: evaluation_settings.ModelPricing | None = None,
    max_samples: int = 1,
    limit: int | None = None,
    sample_ids: tuple[str, ...] | None = None,
    instruction_delivery: evaluation_settings.InstructionDelivery = "files",
    deliveries: tuple[evaluation_settings.InstructionDelivery, ...] | None = None,
    log_dir: str = "/results/live",
) -> int:
    settings = evaluation_settings.EvaluationSettings(
        model=model,
        run_id=run_id,
        agent=agent,
        version=version,
        dataset=dataset,
        sandbox=sandbox,
        instruction_root=instruction_root,
        epochs=epochs,
        cost_limit=cost_limit,
        model_cost=model_cost,
        max_samples=max_samples,
        limit=limit,
        sample_ids=sample_ids,
        instruction_delivery=instruction_delivery,
        deliveries=deliveries,
        log_dir=log_dir,
    )
    from evals.python.integrations.inspect import evaluation  # noqa: PLC0415 - lazy SDK composition

    return await evaluation.evaluate_async(settings)
