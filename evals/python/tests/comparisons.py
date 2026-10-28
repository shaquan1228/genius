"""Exercise comparisons through native Inspect logs and the public API."""

import asyncio
import shutil
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from inspect_ai.log import EvalSampleLimit, write_eval_log
from inspect_ai.model import ModelOutput
from inspect_ai.solver import Generate, Solver, TaskState, solver

from evals.python import comparison, evaluation
from evals.python.comparison import (
    ComparisonReport,
    ComparisonRequest,
    Contrast,
    Measurement,
    RunSummary,
    VariantRequest,
)
from evals.python.estimation import Estimate
from evals.python.evaluation import EvaluationSettings, ModelPricing, VariantSettings
from evals.python.integrations.inspect import agents, results


@solver
def _answer() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:  # noqa: PLR0917
        state.output = ModelOutput.from_content(
            "mockllm/model", '{"choice":"B","reason":"B costs less."}'
        )
        return state

    return solve


def _settings(root: Path, *, name: str = "control") -> EvaluationSettings:
    return EvaluationSettings(
        model="mockllm/model",
        agent="codex",
        epochs=1,
        run_id=name,
        log_dir=str(root),
        sample_ids=("small-decision",),
        variant=VariantSettings(name=name, instructions=(), preamble=""),
        model_cost=ModelPricing(input=0, output=0, input_cache_write=0, input_cache_read=0),
    )


@pytest.fixture(scope="module")
def native_runs(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("native-comparison")
    with patch.object(agents, "contained_agent", return_value=_answer()):
        for name in ("control", "treatment", "alternative"):
            settings = evaluation.prepare_run(_settings(root, name=name))
            assert asyncio.run(evaluation.evaluate(settings)) == 0
            evaluation.validate_run(root / name, settings=settings)
    return root


@pytest.fixture
def changed(native_runs: Path, *, tmp_path: Path) -> Path:
    target = tmp_path / "changed"
    shutil.copytree(native_runs / "control", target)
    return target


def native_results_need_no_second_record_format(native_runs: Path) -> None:
    report = comparison.compare_runs(
        {name: native_runs / name for name in ("control", "treatment", "alternative")},
        baseline="treatment",
        measurement=Measurement(),
    )
    (trial,) = report.runs["control"].trials["small-decision"]
    checks = {"seconds", "correctness.response", "correctness.choice", "correctness.text"}
    assert (
        report.estimates["control"]["accuracy"].mean,
        set(report.comparisons),
        set(report.comparisons["alternative"].cases),
        (trial["accuracy"], trial["crashed"], trial["cutoff"], trial["scope"]),
        checks <= set(trial),
        (native_runs / "control/run.json").exists(),
        "| seconds | control |" in comparison.render_report(report),
    ) == (1.0, {"control", "alternative"}, {"small-decision"}, (1, 0, 0, 1), True, False, True)
    assert ComparisonReport.model_validate_json(report.model_dump_json()) == report


def _rewrite(directory: Path, *, change: str) -> None:
    log = results.read_run(directory)
    _change(log, change=change)
    path = next(directory.glob("*.eval"))
    write_eval_log(log, str(path.with_suffix(".json")))
    path.unlink()


def _change(log: Any, *, change: str) -> None:
    mutations: dict[str, Callable[[], object]] = {
        "missing": lambda: setattr(log, "samples", []),
        "duplicate": lambda: log.samples.append(log.samples[0]),
        "extra": lambda: setattr(log.samples[0], "id", "unexpected"),
        "elapsed": lambda: setattr(log.samples[0], "total_time", None),
        "status": lambda: setattr(log, "status", "error"),
        "scores": lambda: setattr(log.samples[0], "scores", {}),
        "selection": lambda: log.eval.metadata["execution"].update(sample_ids=None),
        "metadata": lambda: setattr(log.eval, "metadata", {}),
        "model": lambda: setattr(log.eval, "model", "mockllm/other"),
        "crash": lambda: (
            log.samples[0].scores["evaluation"].metadata.update(agent_failure="crashed")
        ),
        "cutoff": lambda: setattr(log.samples[0], "limit", EvalSampleLimit(type="time", limit=1)),
        "unrepresentable": lambda: (
            log.samples[0].scores["evaluation"].metadata.update(unrepresentable=["response"])
        ),
    }
    mutations[change]()


@pytest.mark.parametrize(
    "change",
    ["missing", "duplicate", "extra", "elapsed", "status", "scores", "metadata", "selection"],
)
def rejects_incomplete_native_evidence(changed: Path, *, change: str) -> None:
    _rewrite(changed, change=change)
    with pytest.raises(
        ValueError, match=r"Incomplete|elapsed|validation error|case selection|provenance"
    ):
        results.read_run(changed)


@pytest.mark.parametrize("change", ["model", "metadata"])
def rejects_wrong_saved_variant(native_runs: Path, *, changed: Path, change: str) -> None:
    _rewrite(changed, change=change)
    with pytest.raises(ValueError, match=r"Saved run|validation error|provenance"):
        evaluation.validate_run(changed, settings=_settings(native_runs))


@pytest.mark.parametrize(("change", "indicator"), [("crash", "crashed"), ("cutoff", "cutoff")])
def failed_trials_count_as_incorrect(changed: Path, *, change: str, indicator: str) -> None:
    _rewrite(changed, change=change)
    (trial,) = results.trials(results.read_run(changed))["small-decision"]
    assert (trial["accuracy"], trial[indicator]) == (0, 1)


def unrepresentable_channels_are_a_trial_indicator(changed: Path) -> None:
    _rewrite(changed, change="unrepresentable")
    (trial,) = results.trials(results.read_run(changed))["small-decision"]
    assert trial["unrepresentable"] == 1


def harness_hash_tracks_the_installed_kernel_origin() -> None:
    pinned = results.harness_hash()
    local = SimpleNamespace(read_text=lambda _: '{"url": "file:///tmp/genius-bench"}')
    with patch("evals.python.integrations.inspect.results.distribution", return_value=local):
        assert results.harness_hash() != pinned


def incompatible_native_models_are_rejected(native_runs: Path, *, changed: Path) -> None:
    _rewrite(changed, change="model")
    with pytest.raises(ValueError, match="Incompatible"):
        comparison.compare_runs(
            {"control": native_runs / "control", "changed": changed},
            baseline="control",
            measurement=Measurement(),
        )


def saved_run_requires_the_requested_settings(native_runs: Path) -> None:
    settings = _settings(native_runs).model_copy(update={"time_limit": 17})
    with pytest.raises(ValueError, match="Saved run does not match"):
        evaluation.validate_run(native_runs / "control", settings=settings)


def requires_exactly_one_log(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="one native"):
        results.read_run(tmp_path)


@pytest.mark.parametrize("elapsed", [None, -1, float("nan"), float("inf")])
def invalid_timing_is_rejected(elapsed: float | None) -> None:
    from inspect_ai.log import EvalSample  # noqa: PLC0415

    sample = EvalSample(id="case", epoch=1, input="", target="", total_time=elapsed)
    with pytest.raises(ValueError, match="elapsed"):
        results.elapsed(sample)


@pytest.mark.parametrize("version", ["latest", "stable", "next"])
def preparation_rejects_unpinned_agent_versions(tmp_path: Path, *, version: str) -> None:
    with pytest.raises(ValueError, match="exact agent version"):
        evaluation.prepare_run(_settings(tmp_path).model_copy(update={"version": version}))


def preparation_requires_one_variant(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="explicit variant"):
        evaluation.prepare_run(_settings(tmp_path).model_copy(update={"variant": None}))


def preparation_rejects_unknown_prices(tmp_path: Path) -> None:
    settings = _settings(tmp_path).model_copy(
        update={"model": "openai/unpriced", "model_cost": None}
    )
    with (
        patch.object(results, "get_model_info", return_value=None),
        pytest.raises(ValueError, match="EVAL_MODEL_COST"),
    ):
        evaluation.prepare_run(settings)


@pytest.mark.parametrize(
    "shared",
    [
        EvaluationSettings(model="mockllm/model", variant=VariantSettings(name="x")),
        EvaluationSettings(model="mockllm/model", deliveries=("files", "inline")),
    ],
)
def shared_settings_cannot_override_variants(shared: EvaluationSettings) -> None:
    with pytest.raises(ValueError, match="separately"):
        ComparisonRequest(
            comparison_id="request",
            shared=shared,
            baseline="control",
            variants=tuple(
                VariantRequest(variant=VariantSettings(name=name))
                for name in ("control", "treatment")
            ),
        )


def comparison_accepts_named_variants_without_fixed_roles() -> None:
    request = ComparisonRequest(
        comparison_id="three-way",
        shared=EvaluationSettings(model="mockllm/model"),
        baseline="plain",
        variants=tuple(
            VariantRequest(variant=VariantSettings(name=name))
            for name in ("plain", "concise", "detailed")
        ),
    )
    assert tuple(v.variant.name for v in request.variants) == ("plain", "concise", "detailed")


@pytest.mark.parametrize("names", [(), ("solo",), ("same", "same"), ("a", "b")])
def invalid_variant_sets_are_rejected(names: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match=r"at least|baseline|unique"):
        ComparisonRequest(
            comparison_id="invalid",
            shared=EvaluationSettings(model="mockllm/model"),
            baseline="same",
            variants=tuple(VariantRequest(variant=VariantSettings(name=name)) for name in names),
        )


def other_runners_can_compare_custom_metrics_without_inspect_logs() -> None:
    runs = {
        name: RunSummary(trials={"case": ({"tokens": tokens},)}, created_at=name)
        for name, tokens in (("plain", 100), ("short", 50), ("long", 200))
    }
    report = comparison.compare_summaries(runs, baseline="short", measurement=Measurement())
    assert report.comparisons == {
        name: Contrast(
            cases={"case": {"tokens": change}},
            estimates={"tokens": Estimate(cases=1, mean=change)},
            verdict="inconclusive",
        )
        for name, change in (("plain", 50), ("long", 150))
    }
    assert "| tokens | long - short | 150 | n/a |" in comparison.render_report(report)
    assert ComparisonReport.model_validate_json(report.model_dump_json()) == report


@pytest.mark.parametrize("change", ["cases", "baseline", "cardinality"])
def incomparable_summaries_are_rejected(change: str) -> None:
    before = RunSummary(trials={"case": ({"x": 1},)}, created_at="before")
    changes: dict[str, dict[str, object]] = {"cases": {"trials": {"other": ({"x": 1},)}}}
    runs = {"base": before, "other": before.model_copy(update=changes.get(change, {}))}
    if change == "cardinality":
        runs.pop("other")
    with pytest.raises(ValueError, match=r"same|baseline|at least 2"):
        comparison.compare_summaries(
            runs, baseline="missing" if change == "baseline" else "base", measurement=Measurement()
        )


@pytest.mark.parametrize(
    "rows", [(), *(({"custom": value},) for value in (float("nan"), float("inf"), -float("inf")))]
)
def summaries_reject_empty_or_nonfinite_trials(rows: tuple[dict[str, float], ...]) -> None:
    with pytest.raises(ValueError, match=r"at least 1|finite"):
        RunSummary(trials={"case": rows}, created_at="now")
