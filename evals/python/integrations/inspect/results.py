"""Persist native logs and validate their provenance before comparing runs."""

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from itertools import chain, product
from pathlib import Path
from typing import cast

from inspect_ai import Task
from inspect_ai.log import EvalLog, EvalSample, read_eval_log
from inspect_ai.model import get_model_info
from inspect_ai.scorer import CORRECT, Score
from pydantic import JsonValue

import evals.python.integrations.inspect.pricing as pricing_adapter
from evals.python import comparison, evaluation
from evals.python.comparison import Measurement, Observation, PreparedRun, RunRecord
from evals.python.evaluation import EvaluationSettings
from evals.python.integrations.inspect import completeness
from evals.python.paths import EVALS_ROOT
from kernel import Experiment
from kernel import Task as NativeTask


def harness_source(path: Path) -> bool:
    return path.suffix in (".py", ".ml", ".mli", ".sh") and "tests" not in path.parts


def harness_hash() -> str:
    files = {
        path.relative_to(EVALS_ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in chain.from_iterable(
            (EVALS_ROOT / folder).rglob("*") for folder in ("python", "ocaml", "bin")
        )
        if harness_source(path)
    }
    for name in ("pyproject.toml", "uv.lock"):
        files[name] = hashlib.sha256((EVALS_ROOT / name).read_bytes()).hexdigest()
    return comparison.fingerprint(files)


def identities(task: Task, *, request: EvaluationSettings, spec: Experiment) -> tuple[str, str]:
    metadata = dict(task.metadata or {})
    measured = measurement_definition(
        metadata,
        request=request,
        spec=spec,
        case_ids=completeness.selected_ids(task, request=request),
    )
    return variant_identity(metadata), comparison.fingerprint(measured)


def prepare_run(settings: EvaluationSettings) -> PreparedRun:
    from evals.python.integrations.inspect import evaluation as runner  # noqa: PLC0415

    if settings.variant is None:
        raise ValueError("Prepare one explicit variant")
    spec = evaluation.resolve_experiment(settings)
    task = runner.evaluation_tasks(spec, request=settings)[0]
    runner.selected_samples(task, request=settings)
    resolved = resolved_settings(settings, spec=spec, metadata=dict(task.metadata or {}))
    rates = settings.model_cost
    if rates is None:
        rates = pricing_adapter.known_prices(get_model_info(settings.model), request=settings)
    resolved = resolved.model_copy(
        update={
            "sample_ids": tuple(completeness.selected_ids(task, request=settings)),
            "limit": None,
            "model_cost": rates,
        }
    )
    variant, measured = identities(task, request=resolved, spec=spec)
    return PreparedRun(settings=resolved, variant_sha256=variant, measurement_sha256=measured)


def validate_run(directory: Path, *, settings: EvaluationSettings) -> None:
    record, expected = read_record(directory), prepare_run(settings)
    if (expected.variant_sha256, expected.measurement_sha256) != (
        record.variant_sha256,
        record.measurement_sha256,
    ):
        raise ValueError("Saved run does not match the requested variant and measurement")
    if record.run_id != settings.run_id:
        raise ValueError("Saved run ID does not match its reference")
    observations(directory, record=record)


def variant_identity(metadata: dict[str, JsonValue]) -> str:
    return comparison.fingerprint(
        {key: metadata[key] for key in ("instructions_sha256", "preamble_sha256")}
    )


def resolved_settings(
    request: EvaluationSettings, *, spec: Experiment, metadata: dict[str, JsonValue]
) -> EvaluationSettings:
    return request.model_copy(
        update={
            "epochs": spec.epochs,
            "cost_limit": spec.cost_limit,
            "cache": spec.cache,
            "time_limit": spec.time_limit,
            "message_limit": spec.message_limit,
            "version": metadata["agent_version"],
        }
    )


def measurement_definition(
    metadata: dict[str, JsonValue],
    *,
    request: EvaluationSettings,
    spec: Experiment,
    case_ids: list[str],
) -> dict[str, JsonValue]:
    settings = resolved_settings(request, spec=spec, metadata=metadata).model_dump(
        mode="json",
        exclude={"variant", "run_id", "log_dir", "limit", "sample_ids", "instruction_root"},
    )
    common = dict(metadata)
    for key in ("instructions_sha256", "preamble_sha256", "profile"):
        common.pop(key)
    return {"settings": settings, "metadata": common, "case_ids": cast(list[JsonValue], case_ids)}


def persist(  # noqa: PLR0913 - explicit native log, task and execution provenance
    logs: list[EvalLog],
    *,
    tasks: list[Task],
    request: EvaluationSettings,
    spec: Experiment,
    run_id: str,
    summary: dict[str, object],
) -> None:
    root = Path(request.log_dir) / run_id
    root.mkdir(parents=True, exist_ok=True)
    variant, measured = identities(tasks[0], request=request, spec=spec)
    paths = [Path(str(log.location)).resolve() for log in logs]
    metadata = cast(dict[str, JsonValue], tasks[0].metadata)
    record = RunRecord(
        run_id=run_id,
        created_at=datetime.now(UTC).isoformat(),
        source_ref=request.variant.source_ref if request.variant else None,
        variant_sha256=variant,
        measurement_sha256=measured,
        settings=resolved_settings(request, spec=spec, metadata=metadata),
        metadata=metadata,
        measurement=measurement_definition(
            metadata,
            request=request,
            spec=spec,
            case_ids=completeness.selected_ids(tasks[0], request=request),
        ),
        case_ids=tuple(completeness.selected_ids(tasks[0], request=request)),
        epochs=spec.epochs,
        complete=not completeness.failed(summary),
        completeness=cast(dict[str, JsonValue], summary),
        logs={
            path.relative_to(root.resolve()).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in paths
        },
    )
    with (root / "run.json").open("x") as output:
        output.write(record.model_dump_json(indent=2))


def read_record(directory: Path) -> RunRecord:
    record = RunRecord.model_validate_json((directory / "run.json").read_text())
    if not record.complete or not record.logs:
        raise ValueError(f"Incomplete run: {record.run_id}")
    if variant_identity(record.metadata) != record.variant_sha256:
        raise ValueError("Variant identity does not match run metadata")
    if comparison.fingerprint(record.measurement) != record.measurement_sha256:
        raise ValueError("Measurement identity does not match run metadata")
    verify_measurement(record)
    return record


def verify_measurement(record: RunRecord) -> None:
    settings = record.settings
    spec = evaluation.resolve_experiment(settings)
    expected = measurement_definition(
        record.metadata, request=settings, spec=spec, case_ids=list(record.case_ids)
    )
    if expected != record.measurement:
        raise ValueError("Run settings differ from recorded measurement")


def observations(directory: Path, *, record: RunRecord) -> list[Observation]:
    samples = [
        observation(sample)
        for name in record.logs
        for sample in checked_log(directory, name=name, record=record).samples or []
    ]
    verify_coverage(samples, record=record)
    return samples


def checked_log(directory: Path, *, name: str, record: RunRecord) -> EvalLog:
    path = log_path(directory, name=name)
    if hashlib.sha256(path.read_bytes()).hexdigest() != record.logs[name]:
        raise ValueError(f"Log checksum mismatch: {name}")
    log = read_eval_log(str(path))
    if log.eval.metadata != record.metadata:
        raise ValueError("Native log provenance differs from run metadata")
    if log.eval.model != record.settings.model.replace("hf-inference-providers/", "genius-hf/", 1):
        raise ValueError("Native log model differs from run settings")
    if log.status != "success":
        raise ValueError("Run contains a failed task")
    return log


def log_path(directory: Path, *, name: str) -> Path:
    original = directory / name
    path = original.resolve()
    if not path.is_relative_to(directory.resolve()) or original.is_symlink():
        raise ValueError("Log reference escapes the run directory")
    return path


def verify_coverage(samples: list[Observation], *, record: RunRecord) -> None:
    expected = set(product(record.case_ids, range(1, record.epochs + 1)))
    seen = {(sample.case_id, sample.epoch) for sample in samples}
    if seen != expected or len(seen) != len(samples):
        raise ValueError("Run does not contain its declared case/epoch coverage")


def correct(values: Mapping[str, object], *, crashed: bool, cutoff: bool) -> bool:
    return (
        not crashed
        and not cutoff
        and all(values[name] == CORRECT for name in NativeTask.required_scores)
    )


def observation(sample: EvalSample) -> Observation:
    if sample.error is not None or sample.total_time is None:
        raise ValueError("Sample has a harness error or missing elapsed time")
    values = evaluation_score(sample)
    crashed, cutoff = completeness.crashed(sample), sample.limit is not None
    assert isinstance(values.value, dict)
    return Observation(
        case_id=str(sample.id),
        epoch=sample.epoch,
        correct=correct(values.value, crashed=crashed, cutoff=cutoff),
        elapsed_seconds=sample.total_time,
        crashed=crashed,
        cutoff=cutoff,
    )


def evaluation_score(sample: EvalSample) -> Score:
    values = (sample.scores or {}).get("evaluation")
    if values is None or not completeness.complete_value(values.value):
        raise ValueError("Sample has no complete evaluation score")
    return values


def compare_runs(
    control: Path, *, treatment: Path, measurement: Measurement
) -> dict[str, JsonValue]:
    before, after = read_record(control), read_record(treatment)
    if before.measurement_sha256 != after.measurement_sha256:
        raise ValueError("Incompatible measurement conditions")
    report = comparison.compare_observations(
        observations(control, record=before),
        treatment=observations(treatment, record=after),
        measurement=measurement,
    )
    report.update(
        control_run=before.run_id,
        treatment_run=after.run_id,
        control_created_at=before.created_at,
        treatment_created_at=after.created_at,
        control_source=before.source_ref,
        treatment_source=after.source_ref,
        measurement_sha256=before.measurement_sha256,
    )
    return report


def markdown(report: dict[str, JsonValue]) -> str:
    control, treatment = report["control"], report["treatment"]
    assert isinstance(control, dict)
    assert isinstance(treatment, dict)
    rows = [
        "## Benchmark comparison",
        "",
        f"Verdict: **{report['verdict']}**",
        "",
        "| Metric | Control | Treatment | Difference |",
        "| --- | ---: | ---: | ---: |",
    ]
    for key in control:
        before, after = float(str(control[key])), float(str(treatment[key]))
        rows.append(f"| {key} | {before:.4g} | {after:.4g} | {after - before:+.4g} |")
    rows.extend(
        [
            "",
            "Effects and uncertainty:",
            "",
            "```json",
            json.dumps(report["effects"], indent=2),
            "```",
            "",
            f"Control acquired: {report['control_created_at']}",
            f"Treatment acquired: {report['treatment_created_at']}",
            "",
            "Historical runs may differ in provider load. "
            "Repeated epochs do not add case diversity.",
        ]
    )
    change = report.get("mean_time_change_fraction")
    if change is not None:
        rows.append(f"\nMean task time change: {float(str(change)):+.1%}")
    return "\n".join(rows) + "\n"
