"""Estimate variance from a jagged unit matrix and judge verdicts on paired intervals."""

from collections.abc import Sequence
from math import sqrt
from statistics import fmean

import pytest

from evals.python import comparison, estimation
from evals.python.comparison import ComparisonReport, Measurement, RunSummary
from evals.python.estimation import Estimate, Units

JAGGED: Units = {
    "a": ({"x": 1, "y": 2}, {"x": 0}),
    "b": ({"x": 1}, {"x": 1}, {"x": 1}),
    "c": ({"x": 0, "y": 4},),
}


def jagged_units_estimate_each_metric_over_the_cases_that_observe_it() -> None:
    within = 0.5 / 3
    result = estimation.estimates(JAGGED)
    assert set(result) == {"x", "y"}
    assert result["x"].model_dump() == pytest.approx(
        {
            "cases": 3,
            "units": 6,
            "mean": 0.5,
            "stderr": sqrt(0.25 / 3),
            "between": 0.25 - within * fmean((1 / 2, 1 / 3, 1)),
            "within": within,
        }
    )
    assert result["y"] == Estimate(cases=2, units=2, mean=3, stderr=1, between=None, within=None)


def one_case_has_no_estimate() -> None:
    assert estimation.estimates({"a": ({"x": 1},)}) == {}


def between_variance_is_truncated_at_zero() -> None:
    result = estimation.estimates({"a": ({"x": 0}, {"x": 1}), "b": ({"x": 0}, {"x": 1})})["x"]
    assert (result.between, result.within) == (0, 0.5)


def _spread(cases: int) -> tuple[Units, Units]:
    return (
        {f"c{index}": ({"x": 0},) for index in range(cases)},
        {f"c{index}": ({"x": index},) for index in range(cases)},
    )


@pytest.mark.parametrize(
    ("cases", "confidence", "critical"),
    [
        (2, 0.95, 12.7062),
        (3, 0.95, 4.30265),
        (4, 0.95, 3.18245),
        (11, 0.95, 2.22814),
        (31, 0.95, 2.04227),
        (6, 0.99, 4.03214),
        (2, 0.5, 1.0),
    ],
)
def paired_intervals_use_student_t_critical_values(
    cases: int, *, confidence: float, critical: float
) -> None:
    before, after = _spread(cases)
    pair = estimation.intervals(before, after=after, confidence=confidence)["x"]
    assert (pair.high - pair.mean, pair.mean - pair.low) == pytest.approx(
        (critical * pair.stderr, critical * pair.stderr), rel=1e-5
    )


def paired_intervals_difference_case_means_over_shared_cases() -> None:
    after: Units = {"a": ({"x": 1, "z": 1},), "b": ({"x": 1}, {"x": 1}), "c": ({"x": 1},)}
    pairs = estimation.intervals(JAGGED, after=after, confidence=0.95)
    assert set(pairs) == {"x"}
    assert (pairs["x"].cases, pairs["x"].baseline, pairs["x"].mean, pairs["x"].stderr) == (
        pytest.approx((3, 0.5, 0.5, 0.5 / sqrt(3)))
    )


@pytest.mark.parametrize("confidence", [0, 1, float("nan")])
def intervals_reject_invalid_confidence(confidence: float) -> None:
    with pytest.raises(ValueError, match=r"greater than 0|less than 1|finite"):
        estimation.intervals(JAGGED, after=JAGGED, confidence=confidence)


@pytest.mark.parametrize("units", [{"a": ()}, {"a": ({"x": float("nan")},)}])
def summaries_reject_empty_or_nonfinite_units(units: Units) -> None:
    with pytest.raises(ValueError, match=r"at least 1|finite"):
        RunSummary(metrics={}, units=units, created_at="now")


BASE_SECONDS = (10, 11, 12, 13, 10, 11, 12, 13)
FASTER = (-5, -4.9, -5.1, -5, -4.9, -5.1, -5, -5)


def _run(accuracy: Sequence[float], *, seconds: Sequence[float]) -> RunSummary:
    return RunSummary(
        metrics={"accuracy": fmean(accuracy), "mean_seconds": fmean(seconds)},
        units={
            f"case-{index}": ({"accuracy": correct, "seconds": elapsed},)
            for index, (correct, elapsed) in enumerate(zip(accuracy, seconds, strict=True))
        },
        created_at="test",
    )


def _compare(
    accuracy: Sequence[float], *, shift: Sequence[float], tolerance: float | None
) -> ComparisonReport:
    seconds = BASE_SECONDS[: len(accuracy)]
    return comparison.compare_summaries(
        {
            "base": _run((1,) * len(accuracy), seconds=seconds),
            "candidate": _run(
                accuracy,
                seconds=[base + delta for base, delta in zip(seconds, shift, strict=False)],
            ),
        },
        baseline="base",
        measurement=Measurement(accuracy_tolerance=tolerance, minimum_time_gain=0.1),
    )


@pytest.mark.parametrize(
    ("accuracy", "shift", "tolerance", "expected"),
    [
        ((1,) * 8, FASTER, 0.01, "improved"),
        ((0,) * 8, FASTER, 0.01, "regressed"),
        ((1,) * 8, [-delta for delta in FASTER], 0.01, "regressed"),
        ((1,) * 8, (-10, 6) * 4, 0.01, "inconclusive"),
        ((1,) * 8, (-0.5, -0.4, -0.6, -0.5) * 2, 0.01, "inconclusive"),
        ((1, 1, 1, 0, 1, 1, 1, 1), FASTER, 0.01, "inconclusive"),
        ((1,) * 8, FASTER, None, "inconclusive"),
        ((1,), FASTER, 0.01, "inconclusive"),
    ],
)
def verdicts_require_intervals_to_exclude_acceptable_change(
    accuracy: Sequence[float],
    *,
    shift: Sequence[float],
    tolerance: float | None,
    expected: str,
) -> None:
    report = _compare(accuracy, shift=shift, tolerance=tolerance)
    assert report.comparisons["candidate"].verdict == expected


def noisy_mean_gain_is_not_an_improvement() -> None:
    contrast = _compare((1,) * 8, shift=(-10, 6) * 4, tolerance=0.01).comparisons["candidate"]
    seconds = contrast.intervals["seconds"]
    assert (contrast.differences["mean_seconds"], seconds.low < 0 < seconds.high) == (-2, True)


def reports_carry_estimates_intervals_and_their_method() -> None:
    report = _compare((1,) * 8, shift=FASTER, tolerance=0.01)
    rendered = comparison.render_report(report)
    assert report.estimates["base"]["seconds"].cases == 8
    assert all(
        text in rendered
        for text in (
            "Paired 0.95 Student-t intervals over case means; accuracy tolerance 0.01",
            "| seconds | 11.5 | -5 | [",
            "| base | seconds | 11.5 |",
            "| n/a | n/a | 8 | 8 |",
        )
    )
    assert ComparisonReport.model_validate_json(report.model_dump_json()) == report
    assert "no verdict without an accuracy tolerance" in comparison.render_report(
        _compare((1,) * 8, shift=FASTER, tolerance=None)
    )
