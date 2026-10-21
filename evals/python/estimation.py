"""Case-clustered estimates over a jagged matrix of trials.

A trial is one graded try at one case. Cases are the sampling unit: repeated trials
refine a case mean and measure within-case variance, but never add cases. Each case holds
its own number of trials and observes its own metrics, so the matrix is jagged; a metric
is estimated over the cases that observe it. Per-case differences of case means are a
matrix of one trial per case, so a paired contrast is estimated the same way.
https://arxiv.org/abs/2411.00640 (Miller, Adding Error Bars to Evals)
"""

from collections.abc import Iterable, Sequence
from functools import reduce
from itertools import accumulate, chain, count, islice
from math import atan, cos, fsum, pi, sin, sqrt
from statistics import fmean, variance
from typing import Annotated

from pydantic import BaseModel, Field, validate_call

from evals.python import FROZEN

__all__ = ["Estimate", "Metrics", "Trials", "differences", "estimates"]

type Metrics = dict[str, Annotated[float, Field(allow_inf_nan=False)]]
type Trials = dict[str, Annotated[tuple[Metrics, ...], Field(min_length=1)]]
type Groups = Sequence[Sequence[float]]


class Estimate(BaseModel):
    """A metric's mean over cases; with two or more cases, its uncertainty.

    `interval` is a two-sided Student-t interval. `between` is the variance of true case
    means and `within` the pooled variance of trials around their case mean. Both need
    repeated trials; `between` is truncated at zero.
    """

    model_config = FROZEN
    cases: int
    mean: float
    stderr: float | None = None
    interval: tuple[float, float] | None = None
    between: float | None = None
    within: float | None = None


def _metrics(rows: Iterable[Metrics]) -> list[str]:
    return sorted({metric for trial in rows for metric in trial})


def _values(rows: Sequence[Metrics], *, metric: str) -> list[float]:
    return [trial[metric] for trial in rows if metric in trial]


def _groups(trials: Trials, *, metric: str) -> list[list[float]]:
    groups = (_values(rows, metric=metric) for rows in trials.values())
    return [values for values in groups if values]


def _squares(values: Sequence[float]) -> float:
    return (len(values) - 1) * variance(values)


def _within(groups: Groups) -> float | None:
    repeated = [values for values in groups if len(values) > 1]
    if not repeated:
        return None
    return fsum(map(_squares, repeated)) / (sum(map(len, repeated)) - len(repeated))


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


def _estimate(groups: Groups, *, confidence: float) -> Estimate:
    means = [fmean(values) for values in groups]
    estimate = Estimate(cases=len(means), mean=fmean(means), within=_within(groups))
    if len(means) < 2:
        return estimate
    spread = variance(means)
    stderr = sqrt(spread / len(means))
    margin = _critical(confidence, df=len(means) - 1) * stderr
    shrinkage = fmean(1 / len(values) for values in groups)
    between = None if estimate.within is None else max(0.0, spread - estimate.within * shrinkage)
    return estimate.model_copy(
        update={
            "stderr": stderr,
            "interval": (estimate.mean - margin, estimate.mean + margin),
            "between": between,
        }
    )


@validate_call(config=FROZEN)
def estimates(
    trials: Trials, *, confidence: Annotated[float, Field(gt=0, lt=1)]
) -> dict[str, Estimate]:
    """Estimate every metric over the cases that observe it."""
    return {
        metric: _estimate(_groups(trials, metric=metric), confidence=confidence)
        for metric in _metrics(chain.from_iterable(trials.values()))
    }


def _means(rows: Sequence[Metrics]) -> Metrics:
    return {metric: fmean(_values(rows, metric=metric)) for metric in _metrics(rows)}


def _change(before: Sequence[Metrics], *, after: Sequence[Metrics]) -> Metrics:
    left, right = _means(before), _means(after)
    return {metric: right[metric] - value for metric, value in left.items() if metric in right}


@validate_call(config=FROZEN)
def differences(before: Trials, *, after: Trials) -> dict[str, Metrics]:
    """Each shared case's change in mean for every metric that both runs observe in it."""
    return {
        case: _change(before[case], after=after[case])
        for case in sorted(before.keys() & after.keys())
    }
