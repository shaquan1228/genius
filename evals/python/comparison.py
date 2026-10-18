"""Validated comparison requests and paired, case-level outcome analysis."""

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Annotated, Literal

import numpy as np
from pydantic import BaseModel, Field, InstanceOf, JsonValue, model_validator, validate_call

from evals.python.evaluation import EvaluationSettings, VariantSettings
from evals.python.schema import FROZEN

__all__ = [
    "ComparisonRequest",
    "Measurement",
    "Observation",
    "PreparedRun",
    "RunRecord",
    "VariantRequest",
    "compare_observations",
    "compare_runs",
    "fingerprint",
    "prepare_run",
    "render_report",
    "validate_run",
]

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class PreparedRun(BaseModel):
    model_config = FROZEN
    settings: EvaluationSettings
    variant_sha256: Digest
    measurement_sha256: Digest


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
        if self.control.variant.name == self.treatment.variant.name:
            raise ValueError("Variant names must differ")
        return self


class RunRecord(BaseModel):
    model_config = FROZEN
    schema_version: Literal[1] = 1
    run_id: Identifier
    created_at: str
    source_ref: str | None = None
    hf_job_id: str | None = None
    variant_sha256: Digest
    measurement_sha256: Digest
    settings: EvaluationSettings
    metadata: dict[str, JsonValue]
    measurement: dict[str, JsonValue]
    case_ids: Annotated[tuple[str, ...], Field(min_length=1)]
    epochs: int = Field(gt=0)
    complete: bool
    completeness: dict[str, JsonValue]
    logs: dict[str, Digest]

    @model_validator(mode="after")
    def unique_cases(self) -> "RunRecord":
        if len(set(self.case_ids)) != len(self.case_ids):
            raise ValueError("Run case IDs must be unique")
        return self


class Observation(BaseModel):
    model_config = FROZEN
    case_id: str
    epoch: int = Field(gt=0)
    correct: bool
    elapsed_seconds: float = Field(ge=0, allow_inf_nan=False)
    crashed: bool = False
    cutoff: bool = False


class _Effects(BaseModel):
    model_config = FROZEN
    accuracy_delta: float
    mean_seconds_delta: float
    accuracy_interval: tuple[float, float]
    seconds_interval: tuple[float, float]
    case_count: int
    method: str
    cases: dict[str, dict[str, float]]


@validate_call(config=FROZEN)
def fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


@validate_call(config=FROZEN)
def compare_runs(
    control: Path, *, treatment: Path, measurement: "Measurement"
) -> dict[str, JsonValue]:
    from evals.python.integrations.inspect import results  # noqa: PLC0415 - lazy SDK composition

    return results.compare_runs(control, treatment=treatment, measurement=measurement)


@validate_call(config=FROZEN)
def prepare_run(settings: InstanceOf[EvaluationSettings]) -> "PreparedRun":
    from evals.python.integrations.inspect import results  # noqa: PLC0415 - lazy SDK composition

    return results.prepare_run(settings)


@validate_call(config=FROZEN)
def validate_run(directory: Path, *, settings: InstanceOf[EvaluationSettings]) -> None:
    from evals.python.integrations.inspect import results  # noqa: PLC0415 - lazy SDK composition

    results.validate_run(directory, settings=settings)


@validate_call(config=FROZEN)
def render_report(report: dict[str, JsonValue]) -> str:
    from evals.python.integrations.inspect import results  # noqa: PLC0415 - lazy SDK composition

    return results.markdown(report)


def _aggregate(observations: list[Observation]) -> dict[str, JsonValue]:
    return {
        "observations": len(observations),
        "accuracy": mean(int(sample.correct) for sample in observations),
        "mean_seconds": mean(sample.elapsed_seconds for sample in observations),
        "crashes": sum(sample.crashed for sample in observations),
        "cutoffs": sum(sample.cutoff for sample in observations),
    }


def _case_means(observations: list[Observation]) -> dict[str, tuple[float, float]]:
    cases: dict[str, list[Observation]] = defaultdict(list)
    for observation in observations:
        cases[observation.case_id].append(observation)
    return {
        case: (
            mean(int(sample.correct) for sample in samples),
            mean(sample.elapsed_seconds for sample in samples),
        )
        for case, samples in sorted(cases.items())
    }


def _paired_effects(control: list[Observation], *, treatment: list[Observation]) -> _Effects:
    before, after = _case_means(control), _case_means(treatment)
    deltas = np.array(
        [(after[case][0] - value[0], after[case][1] - value[1]) for case, value in before.items()]
    )
    sampled = np.random.default_rng(0).integers(0, len(deltas), size=(10000, len(deltas)))
    bounds = np.quantile(deltas[sampled].mean(axis=1), [0.025, 0.975], axis=0)
    accuracy = float(deltas[:, 0].mean())
    radius = math.sqrt(2 * math.log(40) / len(deltas))
    return _Effects(
        accuracy_delta=accuracy,
        mean_seconds_delta=float(deltas[:, 1].mean()),
        accuracy_interval=(max(-1, accuracy - radius), min(1, accuracy + radius)),
        seconds_interval=(float(bounds[0, 1]), float(bounds[1, 1])),
        case_count=len(deltas),
        method="95% accuracy Hoeffding bound; 95% time paired case bootstrap; epochs grouped",
        cases={
            case: {"accuracy_delta": float(delta[0]), "seconds_delta": float(delta[1])}
            for case, delta in zip(before, deltas, strict=True)
        },
    )


def compare_observations(
    control: list[Observation],
    *,
    treatment: list[Observation],
    measurement: Measurement,
) -> dict[str, JsonValue]:
    _coverage(control, treatment=treatment)
    effects = _paired_effects(control, treatment=treatment)
    baseline_time = mean(sample.elapsed_seconds for sample in control)
    outcome = _verdict(effects, measurement=measurement, baseline_time=baseline_time)
    return {
        "control": _aggregate(control),
        "treatment": _aggregate(treatment),
        "effects": effects.model_dump(mode="json"),
        "mean_time_change_fraction": effects.mean_seconds_delta / baseline_time
        if baseline_time > 0
        else None,
        "verdict": outcome,
    }


def _pairs(observations: list[Observation]) -> set[tuple[str, int]]:
    pairs = {(sample.case_id, sample.epoch) for sample in observations}
    if not pairs or len(pairs) != len(observations):
        raise ValueError("Comparison requires identical, unique case/epoch coverage")
    return pairs


def _coverage(control: list[Observation], *, treatment: list[Observation]) -> None:
    before, after = _pairs(control), _pairs(treatment)
    if before != after:
        raise ValueError("Comparison requires identical, unique case/epoch coverage")
    if len(set(Counter(case for case, _ in before).values())) != 1:
        raise ValueError("Comparison requires equal epoch counts per case")


def _verdict(effects: _Effects, *, measurement: Measurement, baseline_time: float) -> str:
    tolerance = measurement.accuracy_tolerance
    if tolerance is None or effects.case_count < 2:
        return "inconclusive"
    return _accuracy_verdict(
        effects, measurement=measurement, baseline_time=baseline_time, tolerance=tolerance
    )


def _accuracy_verdict(
    effects: _Effects, *, measurement: Measurement, baseline_time: float, tolerance: float
) -> str:
    accuracy, timing = effects.accuracy_interval, effects.seconds_interval
    if accuracy[1] < -tolerance:
        return "regressed"
    if accuracy[0] < -tolerance:
        return "inconclusive"
    if timing[0] > 0:
        return "regressed"
    gain = baseline_time * measurement.minimum_time_gain
    if timing[1] < -gain:
        return "improved"
    return "inconclusive"
