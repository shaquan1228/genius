"""Compare real native evidence and reject incompatible or corrupted artifacts."""

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, cast

import pytest
from inspect_ai.log import EvalError, EvalSample, EvalSampleLimit, read_eval_log, write_eval_log
from inspect_ai.model import ModelOutput
from inspect_ai.scorer import CORRECT, INCORRECT, Score
from inspect_ai.solver import Generate, Solver, TaskState, solver
from pydantic import ValidationError

from evals.python import comparison, datasets, evaluation
from evals.python.comparison import Measurement, Observation, RunRecord
from evals.python.evaluation import EvaluationSettings, ModelPricing, VariantSettings
from evals.python.integrations.inspect import completeness, profiles, results
from evals.python.integrations.inspect.tasks import build_task
from evals.python.tests.support import choice_case, offline_run


@solver
def _fixed_answer() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:  # noqa: PLR0917
        state.output = ModelOutput.from_content(
            "mockllm/model", '{"choice":"A","reason":"The cost is lower."}'
        )
        return state

    return solve


@pytest.fixture(scope="module")
def native_runs(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("native-comparison")
    spec = evaluation.resolve_settings(epochs=1)
    dataset = datasets.compile_dataset(cases=(choice_case(case_id="choice", a=1, b=2),))
    for name in ("baseline", "genius"):
        task = build_task(
            profile=profiles.load_profile(name, spec=spec),
            spec=spec,
            catalog=dataset,
            documents=profiles.load_documents(spec),
            provenance=datasets.get_provenance(selection=dataset),
            agent="codex",
        )
        task.solver = _fixed_answer()
        logs = offline_run([task], mode=None, directory=root / name)
        request = EvaluationSettings(model="mockllm/model", log_dir=str(root), agent="codex")
        summary = completeness.report(
            logs, expected=completeness.expected_pairs([task], request=request, epochs=1)
        )
        results.persist(
            logs, tasks=[task], request=request, spec=spec, run_id=name, summary=summary
        )
    return root


@pytest.fixture
def run_dir(native_runs: Path, *, tmp_path: Path) -> Path:
    target = tmp_path / "run"
    shutil.copytree(native_runs / "baseline", target)
    return target


def _read_json(directory: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((directory / "run.json").read_text()))


def _save_json(directory: Path, *, value: dict[str, Any]) -> None:
    (directory / "run.json").write_text(json.dumps(value))


def native_roundtrip_persists_and_compares(native_runs: Path) -> None:
    report = comparison.compare_runs(
        native_runs / "baseline",
        treatment=native_runs / "genius",
        measurement=Measurement(accuracy_tolerance=0.1),
    )
    control, treatment = report["control"], report["treatment"]
    assert isinstance(control, dict)
    assert isinstance(treatment, dict)
    assert (
        report["verdict"],
        control["accuracy"],
        treatment["accuracy"],
        report["control_run"],
        report["treatment_run"],
        "Historical runs" in results.markdown(report),
    ) == ("inconclusive", 1, 1, "baseline", "genius", True)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("complete", False, "Incomplete"),
        ("logs", {}, "Incomplete"),
        ("variant_sha256", "0" * 64, "Variant identity"),
        ("measurement_sha256", "0" * 64, "Measurement identity"),
        ("case_ids", [], "at least 1"),
        ("case_ids", ["choice", "choice"], "unique"),
    ],
)
def rejects_invalid_manifest(run_dir: Path, *, field: str, value: Any, message: str) -> None:
    manifest = _read_json(run_dir)
    manifest[field] = value
    _save_json(run_dir, value=manifest)
    with pytest.raises(ValueError, match=message):
        results.read_record(run_dir)


def rejects_forged_settings(run_dir: Path) -> None:
    manifest = _read_json(run_dir)
    manifest["settings"]["model"] = "mockllm/other"
    _save_json(run_dir, value=manifest)
    with pytest.raises(ValueError, match="settings differ"):
        results.read_record(run_dir)


def rejects_rehashed_measurement_forgery(run_dir: Path) -> None:
    manifest = _read_json(run_dir)
    manifest["measurement"]["settings"]["model"] = "mockllm/other"
    manifest["measurement_sha256"] = comparison.fingerprint(manifest["measurement"])
    _save_json(run_dir, value=manifest)
    with pytest.raises(ValueError, match="settings differ"):
        results.read_record(run_dir)


def _rewrite_log(directory: Path, *, change: str) -> RunRecord:
    record = results.read_record(directory)
    name = next(iter(record.logs))
    path = directory / name
    log = read_eval_log(str(path))
    _mutate_native(log, change=change)
    write_eval_log(log, str(path))
    manifest = _read_json(directory)
    manifest["logs"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    _save_json(directory, value=manifest)
    return results.read_record(directory)


def _mutate_native(log: Any, *, change: str) -> None:
    changes = {
        "metadata": lambda: setattr(log.eval, "metadata", {}),
        "model": lambda: setattr(log.eval, "model", "mockllm/other"),
        "status": lambda: setattr(log, "status", "error"),
        "missing": lambda: setattr(log, "samples", []),
        "duplicate": lambda: setattr(log, "samples", [log.samples[0], log.samples[0]]),
        "extra": lambda: setattr(log.samples[0], "id", "unexpected"),
    }
    changes[change]()


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ("metadata", "provenance"),
        ("model", "model differs"),
        ("status", "failed task"),
        ("missing", "coverage"),
        ("duplicate", "coverage"),
        ("extra", "coverage"),
    ],
)
def rejects_wrong_native_artifacts(run_dir: Path, *, change: str, message: str) -> None:
    record = _rewrite_log(run_dir, change=change)
    with pytest.raises(ValueError, match=message):
        results.observations(run_dir, record=record)


def rejects_checksum_change(run_dir: Path) -> None:
    record = results.read_record(run_dir)
    (run_dir / next(iter(record.logs))).write_text("corrupted")
    with pytest.raises(ValueError, match="checksum"):
        results.observations(run_dir, record=record)


@pytest.mark.parametrize("name", ["../escape.eval", "/tmp/escape.eval", "linked.eval"])
def rejects_escaping_log_paths(run_dir: Path, *, name: str) -> None:
    (run_dir / "linked.eval").symlink_to(run_dir / "run.json")
    with pytest.raises(ValueError, match="escapes"):
        results.log_path(run_dir, name=name)


def rejects_incompatible_runs(run_dir: Path, *, native_runs: Path) -> None:
    manifest = _read_json(run_dir)
    manifest["settings"]["model"] = "mockllm/other"
    manifest["measurement"]["settings"]["model"] = "mockllm/other"
    manifest["measurement_sha256"] = comparison.fingerprint(manifest["measurement"])
    _save_json(run_dir, value=manifest)
    with pytest.raises(ValueError, match="Incompatible"):
        results.compare_runs(run_dir, treatment=native_runs / "genius", measurement=Measurement())


def _native_sample() -> EvalSample:
    return EvalSample(
        id="choice",
        epoch=1,
        input="choose",
        target="A",
        total_time=3,
        scores={"evaluation": Score(value={"correctness": CORRECT, "scope": CORRECT})},
    )


@pytest.mark.parametrize("kind", ["crash", "cutoff", "extra-metric"])
def counts_failed_agents_and_ignores_unrequired_metrics(kind: str) -> None:
    sample = _native_sample()
    assert sample.scores is not None
    sample.scores["evaluation"].value = {
        "correctness": CORRECT,
        "scope": CORRECT,
        "irrelevant": INCORRECT,
    }
    _alter_sample(sample, kind=kind)
    observation = results.observation(sample)
    assert observation.correct == (kind == "extra-metric")
    assert observation.crashed == (kind == "crash")
    assert observation.cutoff == (kind == "cutoff")


def _alter_sample(sample: EvalSample, *, kind: str) -> None:
    if kind == "crash":
        assert sample.scores is not None
        sample.scores["evaluation"].metadata = {"agent_failure": "process exited"}
    if kind == "cutoff":
        sample.limit = EvalSampleLimit(type="time", limit=3)


@pytest.mark.parametrize("kind", ["error", "timing", "missing-score", "partial-score"])
def rejects_unmeasured_samples(kind: str) -> None:
    sample = _native_sample()
    changes: dict[str, dict[str, Any]] = {
        "error": {"error": EvalError(message="failed", traceback="", traceback_ansi="")},
        "timing": {"total_time": None},
        "missing-score": {"scores": None},
        "partial-score": {"scores": {"evaluation": Score(value={"correctness": CORRECT})}},
    }
    with pytest.raises(ValueError, match="Sample"):
        results.observation(sample.model_copy(update=changes[kind]))


def _observations(
    *, count: int = 100, epochs: int = 1, correct: bool = True, seconds: int = 10
) -> list[Observation]:
    return [
        Observation(case_id=str(case), epoch=epoch, correct=correct, elapsed_seconds=seconds)
        for case in range(count)
        for epoch in range(1, epochs + 1)
    ]


@pytest.mark.parametrize(
    ("count", "correct", "seconds", "tolerance", "gain", "verdict"),
    [
        (4, True, 5, 0.0, 0.0, "inconclusive"),
        (100, True, 5, 0.3, 0.0, "improved"),
        (100, False, 5, 0.3, 0.0, "regressed"),
        (100, True, 15, 0.3, 0.0, "regressed"),
        (100, True, 9, 0.3, 0.2, "inconclusive"),
        (100, True, 5, None, 0.0, "inconclusive"),
        (1, True, 5, 1.0, 0.0, "inconclusive"),
    ],
)
def evidence_controls_verdict(  # noqa: PLR0913 - independently varied evidence
    count: int, *, correct: bool, seconds: int, tolerance: float | None, gain: float, verdict: str
) -> None:
    report = comparison.compare_observations(
        _observations(count=count),
        treatment=_observations(count=count, correct=correct, seconds=seconds),
        measurement=Measurement(accuracy_tolerance=tolerance, minimum_time_gain=gain),
    )
    assert report["verdict"] == verdict


def repetitions_do_not_fake_case_diversity() -> None:
    reports = [
        comparison.compare_observations(
            _observations(count=4, epochs=epochs),
            treatment=_observations(count=4, epochs=epochs, seconds=5),
            measurement=Measurement(accuracy_tolerance=0.3),
        )
        for epochs in (1, 20)
    ]
    assert reports[0]["effects"] == reports[1]["effects"]
    assert reports[1]["verdict"] == "inconclusive"


@pytest.mark.parametrize("kind", ["empty", "duplicate", "different", "unequal-epochs"])
def rejects_unpaired_coverage(kind: str) -> None:
    base = _observations(count=2)
    variants = {
        "empty": [],
        "duplicate": [base[0], base[0]],
        "different": _observations(count=3),
        "unequal-epochs": [*base, base[0].model_copy(update={"epoch": 2})],
    }
    control = variants[kind] if kind == "unequal-epochs" else base
    with pytest.raises(ValueError, match=r"coverage|epoch counts"):
        comparison.compare_observations(
            control, treatment=variants[kind], measurement=Measurement()
        )


@pytest.mark.parametrize("kind", ["variant", "deliveries", "equal-names"])
def rejects_ambiguous_requests(kind: str) -> None:
    shared = {"model": "mockllm/model"}
    extras: dict[str, dict[str, Any]] = {
        "variant": {"variant": {"name": "shared"}},
        "deliveries": {"deliveries": ["files", "inline"]},
        "equal-names": {},
    }
    data = {
        "comparison_id": "pr80",
        "shared": shared | extras[kind],
        "control": {"variant": {"name": "control"}},
        "treatment": {"variant": {"name": "control" if kind == "equal-names" else "treatment"}},
    }
    with pytest.raises(ValidationError):
        comparison.ComparisonRequest.model_validate_json(json.dumps(data))


def valid_request_and_safe_source_filter() -> None:
    request = comparison.ComparisonRequest(
        comparison_id="pr80",
        shared=EvaluationSettings(model="mockllm/model"),
        control=comparison.VariantRequest(variant=VariantSettings(name="control", instructions=())),
        treatment=comparison.VariantRequest(variant=VariantSettings(name="treatment")),
    )
    assert request.control.result_ref is None
    assert results.harness_source(Path("python/evaluation.py"))
    assert not results.harness_source(Path("python/tests/support.py"))
    assert not results.harness_source(Path("docs/readme.md"))


def prepares_exact_variant_and_cohort() -> None:
    settings = EvaluationSettings(
        model="mockllm/model",
        agent="codex",
        epochs=2,
        limit=1,
        time_limit=17,
        message_limit=9,
        cache=False,
        model_cost=ModelPricing(input=0, output=0, input_cache_write=0, input_cache_read=0),
        variant=VariantSettings(name="control", instructions=(), preamble=""),
    )
    prepared = comparison.prepare_run(settings)
    assert (prepared.settings.sample_ids, prepared.settings.limit) == (("clear-task",), None)
    assert prepared.settings.version
    assert (prepared.settings.time_limit, prepared.settings.message_limit) == (17, 9)
    assert prepared.settings.cache is False


def refuses_implicit_pair_preparation() -> None:
    with pytest.raises(ValueError, match="one explicit variant"):
        comparison.prepare_run(EvaluationSettings(model="mockllm/model"))


def public_report_renders_native_evidence(native_runs: Path) -> None:
    report = comparison.compare_runs(
        native_runs / "baseline", treatment=native_runs / "genius", measurement=Measurement()
    )
    assert "Difference" in comparison.render_report(report)


def validates_expected_saved_run(native_runs: Path) -> None:
    from unittest.mock import patch  # noqa: PLC0415

    directory = native_runs / "baseline"
    record = results.read_record(directory)
    expected = comparison.PreparedRun(
        settings=record.settings,
        variant_sha256=record.variant_sha256,
        measurement_sha256=record.measurement_sha256,
    )
    settings = record.settings.model_copy(update={"run_id": record.run_id})
    with patch.object(results, "prepare_run", return_value=expected):
        comparison.validate_run(directory, settings=settings)


@pytest.mark.parametrize("mismatch", ["variant_sha256", "measurement_sha256", "run_id"])
def refuses_wrong_saved_reference(native_runs: Path, *, mismatch: str) -> None:
    from unittest.mock import patch  # noqa: PLC0415

    directory = native_runs / "baseline"
    record = results.read_record(directory)
    expected = comparison.PreparedRun(
        settings=record.settings,
        variant_sha256=record.variant_sha256,
        measurement_sha256=record.measurement_sha256,
    )
    settings = record.settings.model_copy(update={"run_id": record.run_id})
    if mismatch == "run_id":
        settings = settings.model_copy(update={"run_id": "another-run"})
    else:
        expected = expected.model_copy(update={mismatch: "0" * 64})
    with (
        patch.object(results, "prepare_run", return_value=expected),
        pytest.raises(ValueError, match="Saved run"),
    ):
        comparison.validate_run(directory, settings=settings)


def hosted_environment_preserves_resolved_limits() -> None:
    from evals.python.integrations.hugging_face.compare import environment  # noqa: PLC0415
    from evals.python.integrations.hugging_face.job import configuration  # noqa: PLC0415

    settings = EvaluationSettings(
        model="mockllm/model",
        sandbox="hf",
        instruction_root="/eval/instructions",
        log_dir="/results",
        time_limit=17,
        message_limit=9,
        cache=False,
    )
    assert configuration(environment(settings)) == settings


def explicit_variant_evaluation_publishes_manifest(
    tmp_path: Path, *, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio  # noqa: PLC0415

    from evals.python.integrations.inspect import agents  # noqa: PLC0415

    monkeypatch.setattr(agents, "contained_agent", lambda *args, **kwargs: _fixed_answer())
    settings = EvaluationSettings(
        model="mockllm/model",
        agent="codex",
        epochs=1,
        variant=VariantSettings(name="single", instructions=(), preamble=""),
        sample_ids=("small-decision",),
        log_dir=str(tmp_path),
        run_id="single",
        model_cost=ModelPricing(input=0, output=0, input_cache_write=0, input_cache_read=0),
    )
    prepared = comparison.prepare_run(settings)
    assert asyncio.run(evaluation.evaluate(prepared.settings)) == 0
    record = results.read_record(tmp_path / "single")
    assert record.case_ids == ("small-decision",)
    assert not results.observations(tmp_path / "single", record=record)[0].correct
    comparison.validate_run(tmp_path / "single", settings=prepared.settings)


def missing_prices_rejected_during_preparation() -> None:
    from unittest.mock import patch  # noqa: PLC0415

    settings = EvaluationSettings(
        model="openai/unpriced-model",
        variant=VariantSettings(name="unpriced", instructions=(), preamble=""),
    )
    with (
        patch.object(results, "get_model_info", return_value=None),
        pytest.raises(ValueError, match="EVAL_MODEL_COST"),
    ):
        comparison.prepare_run(settings)


def resolves_builtin_prices_before_execution() -> None:
    from unittest.mock import patch  # noqa: PLC0415

    from inspect_ai.model import ModelCost, ModelInfo  # noqa: PLC0415

    rates = ModelPricing(input=1, output=2, input_cache_write=0, input_cache_read=0)
    settings = EvaluationSettings(
        model="openai/catalogue",
        variant=VariantSettings(name="priced", instructions=(), preamble=""),
    )
    info = ModelInfo(cost=ModelCost(**rates.model_dump()))
    with patch.object(results, "get_model_info", return_value=info):
        prepared = comparison.prepare_run(settings)
    assert prepared.settings.model_cost == rates


def zero_baseline_time_has_no_relative_change() -> None:
    samples = [Observation(case_id="zero", epoch=1, correct=True, elapsed_seconds=0)]
    report = comparison.compare_observations(samples, treatment=samples, measurement=Measurement())
    assert report["mean_time_change_fraction"] is None
    report.update(
        control_created_at="2026-10-18T00:00:00+00:00",
        treatment_created_at="2026-10-18T00:00:00+00:00",
    )
    assert "Mean task time change:" not in comparison.render_report(report)
