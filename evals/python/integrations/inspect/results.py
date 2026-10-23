"""Compare native Inspect logs using their recorded inputs and completeness checks."""

import json
from collections.abc import Mapping
from importlib.metadata import distribution
from itertools import chain, groupby, product
from math import inf
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from inspect_ai import Task as InspectTask
from inspect_ai.log import EvalLog, EvalSample, list_eval_logs, read_eval_log
from inspect_ai.model import get_model_info
from inspect_ai.scorer import CORRECT
from kernel import REQUIRED_SCORES, source_hash

import evals.python.integrations.inspect.pricing as pricing_adapter
import evals.python.integrations.inspect.profiles as profiles_adapter
from evals.python import EVALS_ROOT, evaluation
from evals.python.comparison import RunSummary
from evals.python.estimation import Metrics, Trials
from evals.python.evaluation import EvaluationSettings, Experiment
from evals.python.integrations.inspect import completeness


def _harness_source(path: Path) -> bool:
    return (
        path.is_file()
        and (path.suffix in (".py", ".sh") or path.parent == EVALS_ROOT / "bin")
        and "tests" not in path.relative_to(EVALS_ROOT).parts
    )


def harness_hash() -> str:
    files = {
        path.relative_to(EVALS_ROOT).as_posix(): path.read_bytes()
        for path in chain.from_iterable(
            (EVALS_ROOT / folder).rglob("*") for folder in ("python", "bin", "lib", "scripts")
        )
        if _harness_source(path)
    }
    # The installed origin, so a kernel that differs from the pin changes the hash.
    origin = json.loads(distribution("genius-bench-kernel").read_text("direct_url.json") or "{}")
    commit = origin.get("vcs_info", {}).get("commit_id", origin.get("url"))
    files["genius-bench-kernel"] = repr((source_hash(), commit)).encode()
    files["pyproject.toml"] = (EVALS_ROOT / "pyproject.toml").read_bytes()
    files["uv.lock"] = (EVALS_ROOT / "uv.lock").read_bytes()
    return profiles_adapter.content_hash(files)


def record(
    task: InspectTask, *, request: EvaluationSettings, spec: Experiment
) -> EvaluationSettings:
    metadata = dict(task.metadata or {})
    if metadata["agent_version"] in {"", "latest", "stable", "next"}:
        raise ValueError("Use an exact agent version")
    rates = request.model_cost or pricing_adapter.known_prices(
        get_model_info(request.model), request=request
    )
    resolved = request.model_copy(
        update={
            "run_id": request.run_id or uuid4().hex,
            "version": metadata["agent_version"],
            "epochs": spec.epochs,
            "cost_limit": spec.cost_limit,
            "time_limit": spec.time_limit,
            "message_limit": spec.message_limit,
            "cache": spec.cache,
            "model_cost": rates,
            "sample_ids": tuple(completeness.selected_ids(task, request=request)),
            "limit": None,
        }
    )
    metadata.update(
        execution=resolved.model_dump(mode="json", exclude={"variant", "run_id", "log_dir"}),
        run_id=resolved.run_id,
        source_ref=getattr(request.variant, "source_ref", None),
    )
    task.metadata = metadata
    return resolved


def _prepare(settings: EvaluationSettings) -> tuple[InspectTask, EvaluationSettings]:
    from evals.python.integrations.inspect import evaluation as runner  # noqa: PLC0415

    if settings.variant is None:
        raise ValueError("Prepare one explicit variant")
    spec = evaluation.resolve_experiment(settings)
    task = runner.evaluation_tasks(spec, request=settings)[0]
    runner.selected_samples(task, request=settings)
    return task, record(task, request=settings, spec=spec)


def prepare_run(settings: EvaluationSettings) -> EvaluationSettings:
    return _prepare(settings)[1]


def identity(metadata: dict[str, Any], *, instructions: bool) -> dict[str, Any]:
    excluded = {"profile", "run_id", "source_ref", "diagnostic_epoch"}
    if not instructions:
        excluded.update(("instructions_sha256", "preamble_sha256"))
    return {key: value for key, value in metadata.items() if key not in excluded}


def read_run(directory: Path) -> EvalLog:
    files = list_eval_logs(str(directory))
    if len(files) != 1:
        raise ValueError("Expected one native evaluation log per variant")
    log = read_eval_log(files[0])
    metadata = log.eval.metadata or {}
    required = (
        "execution",
        "harness_sha256",
        "instructions_sha256",
        "preamble_sha256",
        "cases_sha256",
    )
    if not all(map(metadata.get, required)):
        raise ValueError("Missing comparison provenance")
    settings = EvaluationSettings.model_validate_json(json.dumps(metadata["execution"]))
    if not settings.sample_ids:
        raise ValueError("Run has no recorded case selection")
    _complete(log, settings=settings)
    return log


def _complete(log: EvalLog, *, settings: EvaluationSettings) -> None:
    spec = evaluation.resolve_experiment(settings)
    expected = set(product([log.eval.task], settings.sample_ids or (), range(1, spec.epochs + 1)))
    if completeness.failed(completeness.report([log], expected=expected)):
        raise ValueError("Incomplete evaluation evidence")
    for sample in log.samples or []:
        elapsed(sample)


def validate_run(directory: Path, *, settings: EvaluationSettings) -> None:
    log = read_run(directory)
    task, resolved = _prepare(settings)
    metadata = log.eval.metadata or {}
    if identity(metadata, instructions=True) != identity(task.metadata or {}, instructions=True):
        raise ValueError("Saved run does not match the requested variant and measurement")
    model = resolved.model.replace("hf-inference-providers/", "genius-hf/", 1)
    if (log.eval.model, metadata.get("run_id")) != (model, settings.run_id):
        raise ValueError("Saved run model or ID differs from its reference")


def elapsed(sample: EvalSample) -> float:
    value = sample.total_time
    if value is None or not 0 <= value < inf:
        raise ValueError("Missing or invalid sample elapsed time")
    return value


def correct(sample: EvalSample) -> bool:
    value = cast(dict[str, str], (sample.scores or {})["evaluation"].value)
    return (
        not sample.limit
        and not completeness.crashed(sample)
        and all(value[name] == CORRECT for name in REQUIRED_SCORES)
    )


def checks(details: dict[str, Any], *, prefix: str = "") -> list[tuple[str, bool]]:
    """Every named check in recorded assessment details, by dotted path."""
    return [
        result
        for name, check in details.get("checks", {}).items()
        for result in ((prefix + name, check["passed"]), *checks(check, prefix=f"{prefix}{name}."))
    ]


def trial(sample: EvalSample) -> Metrics:
    """One graded try: success, elapsed time, failure indicators, and each check."""
    metadata = (sample.scores or {})["evaluation"].metadata or {}
    return {
        "accuracy": float(correct(sample)),
        "seconds": elapsed(sample),
        "crashed": float(completeness.crashed(sample)),
        "cutoff": float(sample.limit is not None),
        "unrepresentable": float(bool(metadata.get("unrepresentable"))),
        **{name: float(passed) for name, passed in checks(metadata.get("assessment", {}))},
    }


def trials(log: EvalLog) -> Trials:
    """The jagged matrix of graded trials per case, in epoch order."""
    ordered = sorted(log.samples or [], key=lambda sample: (str(sample.id), sample.epoch))
    return {
        case: tuple(map(trial, group))
        for case, group in groupby(ordered, key=lambda sample: str(sample.id))
    }


def signature(log: EvalLog) -> tuple[object, ...]:
    return (
        identity(log.eval.metadata or {}, instructions=False),
        log.eval.model,
        log.eval.model_base_url,
        log.eval.model_args,
        log.eval.model_roles,
        log.eval.config,
        log.eval.model_generate_config,
    )


def summaries(runs: Mapping[str, Path]) -> dict[str, RunSummary]:
    summaries: dict[str, RunSummary] = {}
    reference: tuple[object, ...] | None = None
    for name, directory in runs.items():
        log = read_run(directory)
        current = signature(log)
        if reference is not None and current != reference:
            raise ValueError("Incompatible measurement conditions")
        reference = current
        summaries[name] = RunSummary(trials=trials(log), created_at=log.eval.created)
        del log
    return summaries
