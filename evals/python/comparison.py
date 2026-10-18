"""Named variants, runner-independent summaries, and pure comparison analysis."""

from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, InstanceOf, model_validator, validate_call

from evals.python.evaluation import EvaluationSettings, VariantSettings
from evals.python.schema import FROZEN, Identifier

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
    """Optional accuracy/time decision rule; summaries can contain any numeric metrics."""

    model_config = FROZEN
    accuracy_tolerance: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    minimum_time_gain: float = Field(default=0, ge=0, le=1, allow_inf_nan=False)


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
    """Numeric observations from a completed run, independent of its storage or runner."""

    model_config = FROZEN
    metrics: Metrics
    cases: dict[str, Metrics] = Field(default_factory=dict)
    created_at: str


class Contrast(BaseModel):
    model_config = FROZEN
    differences: Metrics
    cases: dict[str, Metrics]
    verdict: Verdict


class ComparisonReport(BaseModel):
    model_config = FROZEN
    baseline: str
    runs: dict[str, RunSummary]
    comparisons: dict[str, Contrast]


def _differences(before: Metrics, *, after: Metrics) -> Metrics:
    if before.keys() != after.keys():
        raise ValueError("Compared summaries must contain the same metrics")
    return {key: after[key] - value for key, value in before.items()}


def _verdict(delta: Metrics, *, baseline: Metrics, measurement: Measurement) -> Verdict:
    if measurement.accuracy_tolerance is None:
        return "inconclusive"
    if delta["accuracy"] < -measurement.accuracy_tolerance or delta["mean_seconds"] > 0:
        return "regressed"
    if delta["mean_seconds"] < -baseline["mean_seconds"] * measurement.minimum_time_gain:
        return "improved"
    return "inconclusive"


def _contrast(before: RunSummary, *, after: RunSummary, measurement: Measurement) -> Contrast:
    if before.cases.keys() != after.cases.keys():
        raise ValueError("Compared summaries must contain the same cases")
    delta = _differences(before.metrics, after=after.metrics)
    return Contrast(
        differences=delta,
        cases={
            case: _differences(values, after=after.cases[case])
            for case, values in before.cases.items()
        },
        verdict=(
            _verdict(delta, baseline=before.metrics, measurement=measurement)
            if {"accuracy", "mean_seconds"} <= delta.keys()
            else "inconclusive"
        ),
    )


@validate_call(config=FROZEN)
def compare_summaries(
    runs: Mapping[str, RunSummary], *, baseline: str, measurement: InstanceOf[Measurement]
) -> ComparisonReport:
    if len(runs) < 2 or baseline not in runs:
        raise ValueError("Comparison needs at least two variants and a declared baseline")
    return ComparisonReport(
        baseline=baseline,
        runs=dict(runs),
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


@validate_call(config=FROZEN)
def render_report(report: InstanceOf[ComparisonReport]) -> str:
    rows = [f"## Benchmark (baseline: {report.baseline})", ""]
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
    rows.extend(f"{name} acquired: {run.created_at}" for name, run in report.runs.items())
    return "\n".join(rows) + "\n"
