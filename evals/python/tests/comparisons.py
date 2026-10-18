"""Exercise comparisons through native Inspect logs and the public API."""

import asyncio
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest
from inspect_ai.log import EvalSampleLimit, write_eval_log
from inspect_ai.model import ModelOutput
from inspect_ai.solver import Generate, Solver, TaskState, solver

from evals.python import comparison, evaluation
from evals.python.comparison import ComparisonRequest, Measurement, VariantRequest
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
        for name in ("control", "treatment"):
            settings = comparison.prepare_run(_settings(root, name=name))
            assert asyncio.run(evaluation.evaluate(settings)) == 0
            comparison.validate_run(root / name, settings=settings)
    return root


@pytest.fixture
def changed(native_runs: Path, *, tmp_path: Path) -> Path:
    target = tmp_path / "changed"
    shutil.copytree(native_runs / "control", target)
    return target


def native_results_need_no_second_record_format(native_runs: Path) -> None:
    report = comparison.compare_runs(
        native_runs / "control", treatment=native_runs / "treatment", measurement=Measurement()
    )
    assert cast(dict[str, object], report["control"])["accuracy"] == 1
    assert "small-decision" in cast(dict[str, object], report["cases"])
    assert not (native_runs / "control/run.json").exists()
    assert "mean_seconds" in comparison.render_report(report)


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
        comparison.validate_run(changed, settings=_settings(native_runs))


@pytest.mark.parametrize("change", ["crash", "cutoff"])
def failed_attempts_remain_in_the_average(changed: Path, *, change: str) -> None:
    _rewrite(changed, change=change)
    log = results.read_run(changed)
    assert results.metrics(log.samples or [])["accuracy"] == 0


def incompatible_native_models_are_rejected(native_runs: Path, *, changed: Path) -> None:
    _rewrite(changed, change="model")
    with pytest.raises(ValueError, match="Incompatible"):
        comparison.compare_runs(
            native_runs / "control", treatment=changed, measurement=Measurement()
        )


def saved_run_requires_the_requested_settings(native_runs: Path) -> None:
    settings = _settings(native_runs).model_copy(update={"time_limit": 17})
    with pytest.raises(ValueError, match="Saved run does not match"):
        comparison.validate_run(native_runs / "control", settings=settings)


def requires_exactly_one_log(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="one native"):
        results.read_run(tmp_path)


@pytest.mark.parametrize("elapsed", [None, -1, float("nan"), float("inf")])
def invalid_timing_is_rejected(elapsed: float | None) -> None:
    from inspect_ai.log import EvalSample  # noqa: PLC0415

    sample = EvalSample(id="case", epoch=1, input="", target="", total_time=elapsed)
    with pytest.raises(ValueError, match="elapsed"):
        results.elapsed(sample)


@pytest.mark.parametrize(
    ("accuracy", "seconds", "tolerance", "expected"),
    [
        (0, -2, None, "inconclusive"),
        (-0.1, -2, 0.01, "regressed"),
        (0, 1, 0.01, "regressed"),
        (0, -2, 0.01, "improved"),
        (0, -0.5, 0.01, "inconclusive"),
    ],
)
def reports_observed_changes(
    accuracy: float, *, seconds: float, tolerance: float | None, expected: str
) -> None:
    assert (
        results.verdict(
            {"accuracy": accuracy, "mean_seconds": seconds},
            baseline=10,
            measurement=Measurement(accuracy_tolerance=tolerance, minimum_time_gain=0.1),
        )
        == expected
    )


@pytest.mark.parametrize("version", ["latest", "stable", "next"])
def preparation_rejects_unpinned_agent_versions(tmp_path: Path, *, version: str) -> None:
    with pytest.raises(ValueError, match="exact agent version"):
        comparison.prepare_run(_settings(tmp_path).model_copy(update={"version": version}))


def preparation_requires_one_variant(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="explicit variant"):
        comparison.prepare_run(_settings(tmp_path).model_copy(update={"variant": None}))


def preparation_rejects_unknown_prices(tmp_path: Path) -> None:
    settings = _settings(tmp_path).model_copy(
        update={"model": "openai/unpriced", "model_cost": None}
    )
    with (
        patch.object(results, "get_model_info", return_value=None),
        pytest.raises(ValueError, match="EVAL_MODEL_COST"),
    ):
        comparison.prepare_run(settings)


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
            control=VariantRequest(variant=VariantSettings(name="control")),
            treatment=VariantRequest(variant=VariantSettings(name="treatment")),
        )
