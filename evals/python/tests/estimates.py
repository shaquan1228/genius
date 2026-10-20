"""Estimate variance from a jagged trial matrix and judge verdicts on paired intervals."""

from collections.abc import Sequence
from math import sqrt
from statistics import fmean, variance

import pytest

from evals.python import comparison, estimation
from evals.python.comparison import ComparisonReport, Measurement, Objective, RunSummary
from evals.python.estimation import Estimate, Trials

JAGGED: Trials = {
    "a": ({"x": 1, "y": 2}, {"x": 0}),
    "b": ({"x": 1}, {"x": 1}, {"x": 1}),
    "c": ({"x": 0, "y": 4},),
}


def jagged_trials_estimate_each_metric_over_the_cases_that_observe_it() -> None:
    within, stderr = 0.5 / 3, sqrt(0.25 / 3)
    x, y = estimation.estimates(JAGGED, confidence=0.95).values()
    assert x.model_dump(exclude={"interval"}) == pytest.approx(
        {
            "cases": 3,
            "mean": 0.5,
            "stderr": stderr,
            "between": 0.25 - within * fmean((1 / 2, 1 / 3, 1)),
            "within": within,
        }
    )
    assert y.model_dump(exclude={"interval"}) == {
        "cases": 2,
        "mean": 3,
        "stderr": 1,
        "between": None,
        "within": None,
    }
    assert [*x.model_dump()["interval"], *y.model_dump()["interval"]] == pytest.approx(
        [0.5 - 4.30265 * stderr, 0.5 + 4.30265 * stderr, 3 - 12.7062, 3 + 12.7062], rel=1e-5
    )


def one_case_has_a_mean_without_uncertainty() -> None:
    assert estimation.estimates({"a": ({"x": 1}, {"x": 3})}, confidence=0.95) == {
        "x": Estimate(cases=1, mean=2, within=2)
    }


def between_variance_is_truncated_at_zero() -> None:
    result = estimation.estimates(
        {"a": ({"x": 0}, {"x": 1}), "b": ({"x": 0}, {"x": 1})}, confidence=0.95
    )["x"]
    assert (result.between, result.within) == (0, 0.5)


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
def intervals_use_student_t_critical_values(
    cases: int, *, confidence: float, critical: float
) -> None:
    trials: Trials = {f"c{index}": ({"x": index},) for index in range(cases)}
    mean, margin = (cases - 1) / 2, critical * sqrt(variance(range(cases)) / cases)
    assert estimation.estimates(trials, confidence=confidence)["x"].interval == pytest.approx(
        (mean - margin, mean + margin), rel=1e-5
    )


def differences_pair_case_means_over_shared_cases() -> None:
    after: Trials = {
        "a": ({"x": 1, "z": 1},),
        "b": ({"x": 1}, {"x": 1}),
        "c": ({"x": 1},),
        "d": ({"x": 0},),
    }
    assert estimation.differences(JAGGED, after=after) == {
        "a": {"x": 0.5},
        "b": {"x": 0},
        "c": {"x": 1},
    }


@pytest.mark.parametrize("confidence", [0, 1, float("nan")])
def estimates_reject_invalid_confidence(confidence: float) -> None:
    with pytest.raises(ValueError, match=r"greater than 0|less than 1|finite"):
        estimation.estimates(JAGGED, confidence=confidence)


BASE_SECONDS = (10, 11, 12, 13, 10, 11, 12, 13)
FASTER = (-5, -4.9, -5.1, -5, -4.9, -5.1, -5, -5)
SPEED = {
    "accuracy": Objective(better="higher", tolerance=0.01),
    "seconds": Objective(better="lower", gain=0.1),
}


def _run(accuracy: Sequence[float], *, seconds: Sequence[float]) -> RunSummary:
    return RunSummary(
        trials={
            f"case-{index}": ({"accuracy": correct, "seconds": elapsed},)
            for index, (correct, elapsed) in enumerate(zip(accuracy, seconds, strict=True))
        },
        created_at="test",
    )


def _compare(
    accuracy: Sequence[float], *, shift: Sequence[float], objectives: dict[str, Objective]
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
        measurement=Measurement(objectives=objectives),
    )


@pytest.mark.parametrize(
    ("accuracy", "shift", "objectives", "expected"),
    [
        ((1,) * 8, FASTER, SPEED, "improved"),
        ((0,) * 8, FASTER, SPEED, "regressed"),
        ((1,) * 8, [-delta for delta in FASTER], SPEED, "regressed"),
        ((1,) * 8, (-10, 6) * 4, SPEED, "inconclusive"),
        ((1,) * 8, (-0.5, -0.4, -0.6, -0.5) * 2, SPEED, "inconclusive"),
        ((1, 1, 1, 0, 1, 1, 1, 1), FASTER, SPEED, "inconclusive"),
        ((1,) * 8, FASTER, {}, "inconclusive"),
        ((1,), FASTER, SPEED, "inconclusive"),
    ],
)
def verdicts_require_intervals_to_exclude_acceptable_change(
    accuracy: Sequence[float],
    *,
    shift: Sequence[float],
    objectives: dict[str, Objective],
    expected: str,
) -> None:
    report = _compare(accuracy, shift=shift, objectives=objectives)
    assert report.comparisons["candidate"].verdict == expected


@pytest.mark.parametrize(
    ("objectives", "expected"),
    [
        ({"tokens": Objective(better="lower", gain=0.1)}, "improved"),
        ({"tokens": Objective(better="higher")}, "regressed"),
        ({"tokens": Objective(better="lower", gain=0.9)}, "inconclusive"),
        (
            {
                "tokens": Objective(better="lower", gain=0.1),
                "check": Objective(better="higher", gain=0),
            },
            "improved",
        ),
        ({"missing": Objective(better="higher")}, "inconclusive"),
    ],
)
def any_metric_can_gate_a_verdict(objectives: dict[str, Objective], *, expected: str) -> None:
    runs = {
        name: RunSummary(
            trials={f"c{index}": ({"tokens": base + index, "check": 1},) for index in range(8)},
            created_at=name,
        )
        for name, base in (("long", 100), ("short", 50))
    }
    report = comparison.compare_summaries(
        runs, baseline="long", measurement=Measurement(objectives=objectives)
    )
    assert report.comparisons["short"].verdict == expected


def noisy_mean_gain_is_not_an_improvement() -> None:
    contrast = _compare((1,) * 8, shift=(-10, 6) * 4, objectives=SPEED).comparisons["candidate"]
    seconds = contrast.estimates["seconds"]
    assert seconds.interval is not None
    assert (seconds.mean, seconds.interval[0] < 0 < seconds.interval[1]) == (-2, True)


def reports_carry_estimates_and_their_method() -> None:
    report = _compare((1,) * 8, shift=FASTER, objectives=SPEED)
    rendered = comparison.render_report(report)
    assert all(
        text in rendered
        for text in (
            "Paired 0.95 Student-t intervals over case means. Objectives: accuracy higher "
            "within 0.01; seconds lower within 0, gain 0.1 of baseline.",
            "- candidate: improved",
            "| seconds | base | 11.5 | [",
            "| seconds | candidate - base | -5 | [",
            "| n/a | n/a | 8 |",
        )
    )
    assert ComparisonReport.model_validate_json(report.model_dump_json()) == report
    assert "Objectives: none, so every verdict is inconclusive." in comparison.render_report(
        _compare((1,) * 8, shift=FASTER, objectives={})
    )
