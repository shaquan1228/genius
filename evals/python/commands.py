"""Public commands own execution effects and provider composition."""

from typing import Literal, assert_never

from pydantic import InstanceOf, validate_call

from evals.python import datasets
from evals.python import queries as _queries
from evals.python import verification as _verification
from evals.python.datasets import Selection
from evals.python.evaluation_settings import EvaluationSettings, InstructionDelivery, ModelPricing
from evals.python.schema import FROZEN
from evals.python.verification import Assessment, Environment, Runtime, VerificationResult
from kernel import Verification
from kernel._operations import fixture as fixture_ops
from kernel._operations import projection as projection_ops

__all__ = ["assess", "create_runtime", "evaluate", "validate_reference", "verify"]


@validate_call(config=FROZEN)
def create_runtime(*, provider: Literal["local", "hf"] = "local") -> Runtime:
    match provider:
        case "local":
            from evals.python.integrations.inspect import environments  # noqa: PLC0415 - lazy local SDK composition

            return environments.runtime()
        case "hf":
            from evals.python.integrations.hugging_face import sandbox  # noqa: PLC0415 - lazy HF SDK composition

            return sandbox.runtime()
        case _ as unreachable:
            assert_never(unreachable)


@validate_call(config=FROZEN)
async def verify(
    *,
    case_id: str,
    selection: Selection = "smoke",
    agent: InstanceOf[Environment],
    runtime: InstanceOf[Runtime],
) -> VerificationResult:
    checks = projection_ops.verifier(datasets.record(case_id, selection=selection))
    if checks is None:
        return VerificationResult(verification=Verification.Unchecked())
    return await _verification.verify(checks, agent=agent, runtime=runtime)


@validate_call(config=FROZEN)
async def assess(
    *,
    case_id: str,
    response: str,
    changed_files: tuple[str, ...],
    selection: Selection = "smoke",
    agent: InstanceOf[Environment],
    runtime: InstanceOf[Runtime],
) -> Assessment:
    result = await verify(case_id=case_id, selection=selection, agent=agent, runtime=runtime)
    if isinstance(result.verification, Verification.HarnessError):
        raise RuntimeError(f"Verification harness error: {result.verification[0]}")
    return Assessment(
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


@validate_call(config=FROZEN)
async def validate_reference(
    *,
    case_id: str,
    selection: Selection = "smoke",
    runtime: InstanceOf[Runtime] | None = None,
) -> VerificationResult:
    if projection_ops.verifier(datasets.record(case_id, selection=selection)) is None:
        return VerificationResult(verification=Verification.Unchecked())
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
        return VerificationResult(verification=Verification.HarnessError(str(error)))


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
    model_cost: ModelPricing | None = None,
    max_samples: int = 1,
    limit: int | None = None,
    sample_ids: tuple[str, ...] | None = None,
    instruction_delivery: InstructionDelivery = "files",
    deliveries: tuple[InstructionDelivery, ...] | None = None,
    log_dir: str = "/results/live",
) -> int:
    settings = EvaluationSettings(
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
