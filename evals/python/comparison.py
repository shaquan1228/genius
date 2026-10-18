"""Comparison requests and runner-independent entry points."""

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, InstanceOf, JsonValue, model_validator, validate_call

from evals.python.evaluation import EvaluationSettings, VariantSettings
from evals.python.schema import FROZEN

__all__ = [
    "ComparisonRequest",
    "Measurement",
    "VariantRequest",
    "compare_runs",
    "prepare_run",
    "render_report",
    "validate_run",
]

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")]


class VariantRequest(BaseModel):
    model_config = FROZEN
    variant: VariantSettings
    result_ref: Identifier | None = None


class Measurement(BaseModel):
    model_config = FROZEN
    accuracy_tolerance: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    minimum_time_gain: float = Field(default=0, ge=0, le=1, allow_inf_nan=False)


class ComparisonRequest(BaseModel):
    model_config = FROZEN
    schema_version: Literal[1] = 1
    comparison_id: Identifier
    origin: dict[str, str] = Field(default_factory=dict)
    shared: EvaluationSettings
    control: VariantRequest
    treatment: VariantRequest
    measurement: Measurement = Field(default_factory=Measurement)

    @model_validator(mode="after")
    def shared_execution(self) -> "ComparisonRequest":
        if self.shared.variant is not None or self.shared.deliveries:
            raise ValueError("Declare variants separately from shared execution settings")
        return self


@validate_call(config=FROZEN)
def prepare_run(settings: InstanceOf[EvaluationSettings]) -> EvaluationSettings:
    from evals.python.integrations.inspect import results  # noqa: PLC0415 - lazy SDK composition

    return results.prepare_run(settings)


@validate_call(config=FROZEN)
def validate_run(directory: Path, *, settings: InstanceOf[EvaluationSettings]) -> None:
    from evals.python.integrations.inspect import results  # noqa: PLC0415 - lazy SDK composition

    results.validate_run(directory, settings=settings)


@validate_call(config=FROZEN)
def compare_runs(
    control: Path, *, treatment: Path, measurement: InstanceOf[Measurement]
) -> dict[str, JsonValue]:
    from evals.python.integrations.inspect import results  # noqa: PLC0415 - lazy SDK composition

    return results.compare_runs(control, treatment=treatment, measurement=measurement)


@validate_call(config=FROZEN)
def render_report(report: dict[str, JsonValue]) -> str:
    from evals.python.integrations.inspect import results  # noqa: PLC0415 - lazy SDK composition

    return results.markdown(report)
