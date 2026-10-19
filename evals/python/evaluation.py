"""Resolve experiment settings and launch evaluations through the runner adapter."""

from pathlib import Path, PurePosixPath
from typing import Annotated, Literal, cast

from pydantic import AfterValidator, BaseModel, Field, InstanceOf, validate_call

from evals.python import FROZEN, Identifier
from kernel import Experiment, Profile

__all__ = [
    "EvaluationSettings",
    "InstructionDelivery",
    "ModelPricing",
    "VariantSettings",
    "evaluate",
    "prepare_run",
    "resolve_experiment",
    "resolve_settings",
    "validate_run",
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


def _instruction_paths(paths: tuple[str, ...]) -> tuple[str, ...]:
    for path in paths:
        _instruction_path(path)
    return _unique(paths)


def _instruction_path(path: str) -> None:
    if str(PurePosixPath(path)) != path or path.startswith("/") or ".." in path.split("/"):
        raise ValueError("Instruction paths must be relative and normalized")
    if path == ".":
        raise ValueError("Instruction paths must name a file or directory")


class VariantSettings(BaseModel):
    """One instruction intervention, independent of its comparison role."""

    model_config = FROZEN
    name: Identifier
    instructions: Annotated[tuple[str, ...], AfterValidator(_instruction_paths)] = tuple(
        Experiment.default.profiles[1].instructions
    )
    preamble: str = Experiment.default.profiles[1].preamble
    source_dir: str | None = None
    source_ref: str | None = None

    @property
    def profile(self) -> Profile:
        return Profile.create(
            name=self.name, preamble=self.preamble, instructions=self.instructions
        )


class EvaluationSettings(BaseModel):
    model_config = FROZEN
    model: str
    run_id: str | None = None
    agent: str = "claude"
    version: str = ""
    variant: VariantSettings | None = None
    dataset: str = "smoke"
    sandbox: str = "local"
    sandbox_image: str = ""
    instruction_root: str = "../instructions"
    epochs: int | None = None
    cost_limit: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    time_limit: int | None = Field(default=None, gt=0)
    message_limit: int | None = Field(default=None, gt=0)
    cache: bool | None = None
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
    return Experiment.resolve(
        **cast(
            "Experiment.ResolveArgs",
            {name: value for name, value in options.items() if value is not None},
        )
    )


@validate_call(config=FROZEN)
def resolve_experiment(settings: InstanceOf[EvaluationSettings]) -> Experiment:
    return resolve_settings(
        epochs=settings.epochs,
        cost_limit=settings.cost_limit,
        time_limit=settings.time_limit,
        message_limit=settings.message_limit,
        cache=settings.cache,
    )


@validate_call(config=FROZEN)
async def evaluate(settings: InstanceOf[EvaluationSettings]) -> int:
    from evals.python.integrations.inspect import evaluation  # noqa: PLC0415 - lazy SDK composition

    return await evaluation.evaluate_async(settings)


@validate_call(config=FROZEN)
def prepare_run(settings: InstanceOf[EvaluationSettings]) -> EvaluationSettings:
    from evals.python.integrations.inspect import results  # noqa: PLC0415 - lazy SDK composition

    return results.prepare_run(settings)


@validate_call(config=FROZEN)
def validate_run(directory: Path, *, settings: InstanceOf[EvaluationSettings]) -> None:
    from evals.python.integrations.inspect import results  # noqa: PLC0415 - lazy SDK composition

    results.validate_run(directory, settings=settings)
