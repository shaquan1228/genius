"""Resolve experiment settings and launch evaluations through the runner adapter."""

from typing import TYPE_CHECKING, Annotated, Literal, cast

from pydantic import AfterValidator, BaseModel, Field, validate_call

from evals.python.schema import FROZEN
from kernel import Experiment
from kernel._operations import experiment as experiment_ops

if TYPE_CHECKING:
    from kernel._experiment import ResolveArgs

__all__ = [
    "EvaluationSettings",
    "InstructionDelivery",
    "ModelPricing",
    "evaluate",
    "resolve_settings",
]


type InstructionDelivery = Literal["files", "manifest", "inline"]


def _unique[T](values: tuple[T, ...]) -> tuple[T, ...]:
    if len(set(values)) != len(values):
        raise ValueError("Selection must contain unique values")
    return values


class ModelPricing(BaseModel):
    """Exact provider prices in USD per million tokens, including cache usage."""

    model_config = FROZEN
    input: float = Field(ge=0, allow_inf_nan=False)
    output: float = Field(ge=0, allow_inf_nan=False)
    input_cache_write: float = Field(ge=0, allow_inf_nan=False)
    input_cache_read: float = Field(ge=0, allow_inf_nan=False)


class EvaluationSettings(BaseModel):
    model_config = FROZEN
    model: str
    run_id: str | None = None
    agent: str = "claude"
    version: str = ""
    dataset: str = "smoke"
    sandbox: str = "local"
    instruction_root: str = "../instructions"
    epochs: int | None = None
    cost_limit: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    model_cost: ModelPricing | None = None
    max_samples: int = Field(default=1, gt=0, le=16)
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
