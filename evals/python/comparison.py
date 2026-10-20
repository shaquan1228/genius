"""Named variants, runner-independent summaries, and pure comparison analysis."""

from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, InstanceOf, model_validator, validate_call

from evals.python import FROZEN, Identifier, estimation
from evals.python.estimation import Estimate, Interval, Units
from evals.python.evaluation import EvaluationSettings, VariantSettings

__all__ = [
    "ComparisonReport",
    "ComparisonRequest",
    "Contrast",
    "Measurement",
    "RunSummary",
    "VariantRequest",
    "compare_runs",
    "compare_summaries",
    "render_report",
]

type Verdict = Literal["inconclusive", "regressed", "improved"]
type Metrics = dict[str, Annotated[float, Field(allow_inf_nan=False)]]


class VariantRequest(BaseModel):
    model_config = FROZEN
    variant: VariantSettings
    result_ref: Identifier | None = None


class Measurement(BaseModel):
    """Optional accuracy/time decision rule, judged on paired intervals over cases."""

    model_config = FROZEN
    accuracy_tolerance: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    minimum_time_gain: float = Field(default=0, ge=0, le=1, allow_inf_nan=False)
    confidence: float = Field(default=0.95, gt=0, lt=1, allow_inf_nan=False)


class ComparisonRequest(BaseModel):
    model_config = FROZEN
    schema_version: Literal[2] = 2
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
    """Numeric observations from a completed run, independent of its storage or runner.

    `metrics` and `cases` are aggregates. `units` keeps each case's graded attempts, the
    jagged matrix that estimates and paired intervals are computed from.
    """

    model_config = FROZEN
    metrics: Metrics
    cases: dict[str, Metrics] = Field(default_factory=dict)
    units: Units = Field(default_factory=dict)
    created_at: str


class Contrast(BaseModel):
    model_config = FROZEN
    differences: Metrics
    cases: dict[str, Metrics]
    intervals: dict[str, Interval] = Field(default_factory=dict)
    verdict: Verdict


class ComparisonReport(BaseModel):
    model_config = FROZEN
    baseline: str
    measurement: Measurement
    runs: dict[str, RunSummary]
    estimates: dict[str, dict[str, Estimate]]
    comparisons: dict[str, Contrast]


def _differences(before: Metrics, *, after: Metrics) -> Metrics:
    if before.keys() != after.keys():
        raise ValueError("Compared summaries must contain the same metrics")
    return {key: after[key] - value for key, value in before.items()}


def _regressed(accuracy: Interval, *, seconds: Interval, tolerance: float) -> bool:
    return accuracy.high < -tolerance or seconds.low > 0


def _improved(accuracy: Interval, *, seconds: Interval, tolerance: float, gain: float) -> bool:
    return accuracy.low >= -tolerance and seconds.high < -seconds.baseline * gain


def _verdict(intervals: dict[str, Interval], *, measurement: Measurement) -> Verdict:
    """Regressed when an interval excludes acceptable change; improved when both do."""
    tolerance = measurement.accuracy_tolerance
    if tolerance is None or not {"accuracy", "seconds"} <= intervals.keys():
        return "inconclusive"
    accuracy, seconds = intervals["accuracy"], intervals["seconds"]
    if _regressed(accuracy, seconds=seconds, tolerance=tolerance):
        return "regressed"
    if _improved(
        accuracy, seconds=seconds, tolerance=tolerance, gain=measurement.minimum_time_gain
    ):
        return "improved"
    return "inconclusive"


def _contrast(before: RunSummary, *, after: RunSummary, measurement: Measurement) -> Contrast:
    if (before.cases.keys(), before.units.keys()) != (after.cases.keys(), after.units.keys()):
        raise ValueError("Compared summaries must contain the same cases")
    intervals = estimation.intervals(
        before.units, after=after.units, confidence=measurement.confidence
    )
    return Contrast(
        differences=_differences(before.metrics, after=after.metrics),
        cases={
            case: _differences(values, after=after.cases[case])
            for case, values in before.cases.items()
        },
        intervals=intervals,
        verdict=_verdict(intervals, measurement=measurement),
    )


def _estimates(runs: Mapping[str, RunSummary]) -> dict[str, dict[str, Estimate]]:
    return {name: estimation.estimates(summary.units) for name, summary in runs.items()}


@validate_call(config=FROZEN)
def compare_summaries(
    runs: Mapping[str, RunSummary], *, baseline: str, measurement: InstanceOf[Measurement]
) -> ComparisonReport:
    if len(runs) < 2 or baseline not in runs:
        raise ValueError("Comparison needs at least two variants and a declared baseline")
    return ComparisonReport(
        baseline=baseline,
        measurement=measurement,
        runs=dict(runs),
        estimates=_estimates(runs),
        comparisons={
            name: _contrast(runs[baseline], after=summary, measurement=measurement)
            for name, summary in runs.items()
            if name != baseline
        },
    )


@validate_call(config=FROZEN)
def compare_runs(
    runs: Mapping[str, Path], *, baseline: str, measurement: InstanceOf[Measurement]
) -> ComparisonReport:
    from evals.python.integrations.inspect import results  # noqa: PLC0415 - lazy SDK composition

    return compare_summaries(results.summaries(runs), baseline=baseline, measurement=measurement)


def _method(measurement: Measurement) -> str:
    rule = (
        "no verdict without an accuracy tolerance"
        if measurement.accuracy_tolerance is None
        else f"accuracy tolerance {measurement.accuracy_tolerance:g}, "
        f"minimum time gain {measurement.minimum_time_gain:g}"
    )
    return f"Paired {measurement.confidence:.4g} Student-t intervals over case means; {rule}."


def _optional(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4g}"


def _interval_rows(contrast: Contrast, *, baseline: str) -> list[str]:
    if not contrast.intervals:
        return []
    return [
        f"| Paired metric | {baseline} | Difference | Interval | Cases |",
        "| --- | ---: | ---: | ---: | ---: |",
        *(
            f"| {key} | {pair.baseline:.4g} | {pair.mean:+.4g} "
            f"| [{pair.low:+.4g}, {pair.high:+.4g}] | {pair.cases} |"
            for key, pair in contrast.intervals.items()
        ),
        "",
    ]


def _estimate_rows(estimates: dict[str, dict[str, Estimate]]) -> list[str]:
    rows = [
        f"| {name} | {key} | {value.mean:.4g} | {value.stderr:.4g} | {_optional(value.between)} "
        f"| {_optional(value.within)} | {value.cases} | {value.units} |"
        for name, metrics in estimates.items()
        for key, value in metrics.items()
    ]
    if not rows:
        return []
    return [
        "### Estimates",
        "",
        "| Run | Metric | Mean | Std. error | Between variance | Within variance | Cases | Units |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        *rows,
        "",
    ]


@validate_call(config=FROZEN)
def render_report(report: InstanceOf[ComparisonReport]) -> str:
    rows = [f"## Benchmark (baseline: {report.baseline})", "", _method(report.measurement), ""]
    for name, contrast in report.comparisons.items():
        rows.extend(
            [
                f"### {name}: {contrast.verdict}",
                "",
                f"| Metric | {report.baseline} | {name} | Difference |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        rows.extend(
            f"| {key} | {value:.4g} | {report.runs[name].metrics[key]:.4g} "
            f"| {contrast.differences[key]:+.4g} |"
            for key, value in report.runs[report.baseline].metrics.items()
        )
        rows.append("")
        rows.extend(_interval_rows(contrast, baseline=report.baseline))
    rows.extend(_estimate_rows(report.estimates))
    rows.extend(f"{name} acquired: {run.created_at}" for name, run in report.runs.items())
    return "\n".join(rows) + "\n"
