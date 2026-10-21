"""Named variants, runner-independent summaries, and pure comparison analysis."""

from collections.abc import Mapping
from math import inf
from operator import itemgetter
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, InstanceOf, model_validator, validate_call

from evals.python import FROZEN, Identifier, estimation
from evals.python.estimation import Estimate, Metrics, Trials
from evals.python.evaluation import EvaluationSettings, VariantSettings

__all__ = [
    "ComparisonReport",
    "ComparisonRequest",
    "Contrast",
    "Measurement",
    "Objective",
    "RunSummary",
    "VariantRequest",
    "compare_runs",
    "compare_summaries",
    "render_report",
]

type Verdict = Literal["inconclusive", "regressed", "improved"]
type Judgement = Literal["regressed", "unknown", "held", "gained"]


class VariantRequest(BaseModel):
    model_config = FROZEN
    variant: VariantSettings
    result_ref: Identifier | None = None


class Objective(BaseModel):
    """A metric that gates a verdict.

    `tolerance` is the loss accepted, in the metric's units. `gain` is the improvement that
    counts, as a fraction of the baseline mean; without it the metric only guards.
    """

    model_config = FROZEN
    better: Literal["higher", "lower"]
    tolerance: float = Field(default=0, ge=0, allow_inf_nan=False)
    gain: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class Measurement(BaseModel):
    """The confidence of every interval and the objectives that gate a verdict."""

    model_config = FROZEN
    confidence: float = Field(default=0.95, gt=0, lt=1, allow_inf_nan=False)
    objectives: dict[str, Objective] = Field(default_factory=dict)


class ComparisonRequest(BaseModel):
    model_config = FROZEN
    schema_version: Literal[3] = 3
    comparison_id: Identifier
    origin: dict[str, str] = Field(default_factory=dict)
    shared: EvaluationSettings
    variants: Annotated[tuple[VariantRequest, ...], Field(min_length=2)]
    baseline: Identifier
    measurement: Measurement = Field(default_factory=Measurement)

    @model_validator(mode="after")
    def shared_execution(self) -> "ComparisonRequest":
        if self.shared.variant is not None or self.shared.deliveries:
            raise ValueError("Declare variants separately from shared execution settings")
        return self

    @model_validator(mode="after")
    def named_variants(self) -> "ComparisonRequest":
        names = {selected.variant.name for selected in self.variants}
        if len(names) != len(self.variants):
            raise ValueError("Variant names must be unique")
        if self.baseline not in names:
            raise ValueError("Comparison needs a declared baseline")
        return self


class RunSummary(BaseModel):
    """Graded trials of a completed run by case, independent of its storage or runner."""

    model_config = FROZEN
    trials: Trials
    created_at: str


class Contrast(BaseModel):
    """A variant's paired change from the baseline, per case and estimated over cases."""

    model_config = FROZEN
    cases: dict[str, Metrics]
    estimates: dict[str, Estimate]
    verdict: Verdict


class ComparisonReport(BaseModel):
    model_config = FROZEN
    baseline: str
    measurement: Measurement
    runs: dict[str, RunSummary]
    estimates: dict[str, dict[str, Estimate]]
    comparisons: dict[str, Contrast]


def _improvement(change: Estimate | None, *, objective: Objective) -> tuple[float, float]:
    """A change's interval as improvement, worst bound first; unknown is unbounded."""
    low, high = (-inf, inf) if change is None or change.interval is None else change.interval
    return (low, high) if objective.better == "higher" else (-high, -low)


def _judgement(
    metric: str,
    *,
    changes: Mapping[str, Estimate],
    baseline: Mapping[str, Estimate],
    objective: Objective,
) -> Judgement:
    worst, best = _improvement(changes.get(metric), objective=objective)
    if best < -objective.tolerance:
        return "regressed"
    if worst < -objective.tolerance:
        return "unknown"
    gained = objective.gain is not None and worst > objective.gain * abs(baseline[metric].mean)
    return "gained" if gained else "held"


def _verdict(
    changes: Mapping[str, Estimate], *, baseline: Mapping[str, Estimate], measurement: Measurement
) -> Verdict:
    """Regressed when an objective is surely worse than its tolerance; improved when no
    objective can be and at least one gain is sure."""
    judged = {
        _judgement(metric, changes=changes, baseline=baseline, objective=objective)
        for metric, objective in measurement.objectives.items()
    }
    if "regressed" in judged:
        return "regressed"
    return "improved" if "gained" in judged and "unknown" not in judged else "inconclusive"


def _contrast(
    before: RunSummary,
    *,
    after: RunSummary,
    baseline: Mapping[str, Estimate],
    measurement: Measurement,
) -> Contrast:
    if before.trials.keys() != after.trials.keys():
        raise ValueError("Compared summaries must contain the same cases")
    cases = estimation.differences(before.trials, after=after.trials)
    changes = estimation.estimates(
        {case: (change,) for case, change in cases.items()}, confidence=measurement.confidence
    )
    return Contrast(
        cases=cases,
        estimates=changes,
        verdict=_verdict(changes, baseline=baseline, measurement=measurement),
    )


@validate_call(config=FROZEN)
def compare_summaries(
    runs: Annotated[Mapping[str, RunSummary], Field(min_length=2)],
    *,
    baseline: str,
    measurement: InstanceOf[Measurement],
) -> ComparisonReport:
    if baseline not in runs:
        raise ValueError("Comparison needs a declared baseline")
    estimates = {
        name: estimation.estimates(run.trials, confidence=measurement.confidence)
        for name, run in runs.items()
    }
    return ComparisonReport(
        baseline=baseline,
        measurement=measurement,
        runs=dict(runs),
        estimates=estimates,
        comparisons={
            name: _contrast(
                runs[baseline], after=run, baseline=estimates[baseline], measurement=measurement
            )
            for name, run in runs.items()
            if name != baseline
        },
    )


@validate_call(config=FROZEN)
def compare_runs(
    runs: Mapping[str, Path], *, baseline: str, measurement: InstanceOf[Measurement]
) -> ComparisonReport:
    from evals.python.integrations.inspect import results  # noqa: PLC0415 - lazy SDK composition

    return compare_summaries(results.summaries(runs), baseline=baseline, measurement=measurement)


def _objective(metric: str, *, objective: Objective) -> str:
    gain = "" if objective.gain is None else f", gain {objective.gain:g} of baseline"
    return f"{metric} {objective.better} within {objective.tolerance:g}{gain}"


def _method(measurement: Measurement) -> str:
    objectives = "; ".join(
        _objective(metric, objective=objective)
        for metric, objective in measurement.objectives.items()
    )
    return (
        f"Paired {measurement.confidence:.4g} Student-t intervals over case means. "
        f"Objectives: {objectives or 'none, so every verdict is inconclusive'}."
    )


def _number(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4g}"


def _row(estimate: Estimate, *, metric: str, label: str) -> str:
    interval = "n/a" if estimate.interval is None else "[{:.4g}, {:.4g}]".format(*estimate.interval)
    return (
        f"| {metric} | {label} | {_number(estimate.mean)} | {interval} "
        f"| {_number(estimate.stderr)} | {_number(estimate.between)} "
        f"| {_number(estimate.within)} | {estimate.cases} |"
    )


def _table(report: ComparisonReport) -> list[str]:
    """Every run's and every contrast's estimates, grouped by metric."""
    labelled = report.estimates | {
        f"{name} - {report.baseline}": contrast.estimates
        for name, contrast in report.comparisons.items()
    }
    rows = sorted(
        (
            (metric, label, estimate)
            for label, estimates in labelled.items()
            for metric, estimate in estimates.items()
        ),
        key=itemgetter(0),
    )
    return [
        "| Metric | Estimate | Mean | Interval | Std. error | Between variance "
        "| Within variance | Cases |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        *(_row(estimate, metric=metric, label=label) for metric, label, estimate in rows),
    ]


@validate_call(config=FROZEN)
def render_report(report: InstanceOf[ComparisonReport]) -> str:
    rows = [
        f"## Benchmark (baseline: {report.baseline})",
        "",
        _method(report.measurement),
        "",
        *(f"- {name}: {contrast.verdict}" for name, contrast in report.comparisons.items()),
        "",
        *_table(report),
        "",
        *(f"{name} acquired: {run.created_at}" for name, run in report.runs.items()),
    ]
    return "\n".join(rows) + "\n"
