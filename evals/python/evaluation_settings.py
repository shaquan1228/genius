"""Validated evaluation launch settings independent of runners."""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field

from evals.python.schema import FROZEN

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
