"""Resolve experiment settings and launch evaluations through the runner adapter."""

from typing import TYPE_CHECKING, cast

from pydantic import validate_call

from evals.python.evaluation_settings import EvaluationSettings, InstructionDelivery, ModelPricing
from evals.python.schema import FROZEN
from kernel import Experiment
from kernel._operations import experiment as experiment_ops

if TYPE_CHECKING:
    from kernel._experiment import ResolveArgs

__all__ = ["evaluate", "resolve_settings"]


@validate_call(config=FROZEN)
def resolve_settings(
    *,
    epochs: int | None = None,
    message_limit: int | None = None,
    cost_limit: float | None = None,
    time_limit: int | None = None,
    cache: bool | None = None,
) -> Experiment:
    options = {
        "epochs": epochs,
        "message_limit": message_limit,
        "cost_limit": cost_limit,
        "time_limit": time_limit,
        "cache": cache,
    }
    return experiment_ops.resolve(
        **cast("ResolveArgs", {name: value for name, value in options.items() if value is not None})
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
