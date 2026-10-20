"""Case-clustered estimates over a jagged matrix of graded units.

A unit is one graded attempt at one case. Cases are the sampling unit: repeated attempts
refine a case mean and measure within-case variance, but never add cases. Each case holds
its own number of attempts and observes its own checks, so the matrix is jagged; a metric
is estimated over the cases that observe it. Paired intervals difference case means.
https://arxiv.org/abs/2411.00640 (Miller, Adding Error Bars to Evals)
"""

from collections.abc import Sequence
from functools import reduce
from itertools import accumulate, count, islice
from math import atan, cos, fsum, pi, sin, sqrt
from statistics import fmean, variance
from typing import Annotated

from pydantic import BaseModel, Field, validate_call

from evals.python import FROZEN

__all__ = ["Estimate", "Interval", "Units", "estimates", "intervals"]

type Unit = dict[str, Annotated[float, Field(allow_inf_nan=False)]]
type Units = dict[str, Annotated[tuple[Unit, ...], Field(min_length=1)]]
type Groups = Sequence[Sequence[float]]


class Estimate(BaseModel):
    """A case-weighted mean with its standard error and variance components.

    `between` is the variance of true case means and `within` the pooled variance of
    units around their case mean. Both need repeated attempts; `between` is truncated
    at zero.
    """

    model_config = FROZEN
    cases: int
    units: int
    mean: float
    stderr: float
    between: float | None
    within: float | None


class Interval(BaseModel):
    """A paired difference of case means with a two-sided Student-t interval."""

    model_config = FROZEN
    cases: int
    baseline: float
    mean: float
    stderr: float
    low: float
    high: float


def _values(attempts: Sequence[Unit], *, metric: str) -> list[float]:
    return [unit[metric] for unit in attempts if metric in unit]


def _observed(units: Units, *, metric: str) -> dict[str, list[float]]:
    groups = {case: _values(attempts, metric=metric) for case, attempts in units.items()}
    return {case: values for case, values in groups.items() if values}


def _metrics(units: Units) -> set[str]:
    return {metric for attempts in units.values() for unit in attempts for metric in unit}


def _squares(values: Sequence[float]) -> float:
    return (len(values) - 1) * variance(values)


def _within(groups: Groups) -> float | None:
    repeated = [values for values in groups if len(values) > 1]
    if not repeated:
        return None
    return fsum(map(_squares, repeated)) / (sum(map(len, repeated)) - len(repeated))


def _estimate(groups: Groups) -> Estimate:
    means = [fmean(values) for values in groups]
    spread = variance(means)
    within = _within(groups)
    return Estimate(
        cases=len(means),
        units=sum(map(len, groups)),
        mean=fmean(means),
        stderr=sqrt(spread / len(means)),
        between=(
            None
            if within is None
            else max(0.0, spread - within * fmean(1 / len(values) for values in groups))
        ),
        within=within,
    )


@validate_call(config=FROZEN)
def estimates(units: Units) -> dict[str, Estimate]:
    """Estimate every metric that at least two cases observe."""
    groups = {
        metric: list(_observed(units, metric=metric).values()) for metric in sorted(_metrics(units))
    }
    return {metric: _estimate(values) for metric, values in groups.items() if len(values) > 1}


def _coverage(t: float, *, df: int) -> float:
    """P(|T| <= t) for integer degrees of freedom (Abramowitz and Stegun 26.7.3-4)."""
    theta = atan(t / sqrt(df))
    terms = accumulate(
        count(1 + df % 2, 2), lambda term, k: term * cos(theta) ** 2 * k / (k + 1), initial=1.0
    )
    series = fsum(islice(terms, df // 2))
    if df % 2:
        return 2 / pi * (theta + sin(theta) * cos(theta) * series)
    return sin(theta) * series


def _halve(bounds: tuple[float, float], *, confidence: float, df: int) -> tuple[float, float]:
    low, high = bounds
    middle = (low + high) / 2
    return (low, middle) if _coverage(middle, df=df) >= confidence else (middle, high)


def _critical(confidence: float, *, df: int) -> float:
    upper = next(
        bound for bound in (2.0**k for k in count()) if _coverage(bound, df=df) >= confidence
    )
    low, high = reduce(
        lambda bounds, _: _halve(bounds, confidence=confidence, df=df), range(64), (0.0, upper)
    )
    return (low + high) / 2


def _interval(before: Sequence[float], *, after: Sequence[float], confidence: float) -> Interval:
    differences = [right - left for left, right in zip(before, after, strict=True)]
    mean = fmean(differences)
    stderr = sqrt(variance(differences) / len(differences))
    margin = _critical(confidence, df=len(differences) - 1) * stderr
    return Interval(
        cases=len(differences),
        baseline=fmean(before),
        mean=mean,
        stderr=stderr,
        low=mean - margin,
        high=mean + margin,
    )


def _pairs(before: Units, *, after: Units, metric: str) -> tuple[list[float], list[float]]:
    left, right = (
        {case: fmean(values) for case, values in _observed(units, metric=metric).items()}
        for units in (before, after)
    )
    shared = sorted(left.keys() & right.keys())
    return [left[case] for case in shared], [right[case] for case in shared]


@validate_call(config=FROZEN)
def intervals(
    before: Units, *, after: Units, confidence: Annotated[float, Field(gt=0, lt=1)]
) -> dict[str, Interval]:
    """Pair case means of every metric that both runs observe in at least two shared cases."""
    pairs = {
        metric: _pairs(before, after=after, metric=metric)
        for metric in sorted(_metrics(before) & _metrics(after))
    }
    return {
        metric: _interval(left, after=right, confidence=confidence)
        for metric, (left, right) in pairs.items()
        if len(left) > 1
    }
