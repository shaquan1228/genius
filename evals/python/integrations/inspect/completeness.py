"""Compare native scored records with the exact requested task/case/epoch tuples."""

from collections import Counter
from collections.abc import Sequence

from inspect_ai import Task as InspectTask
from inspect_ai.log import EvalLog, EvalSample
from inspect_ai.scorer import CORRECT, INCORRECT

from evals.python.evaluation import EvaluationSettings
from kernel import Task

Pair = tuple[str, str, int]


def selected_ids(task: InspectTask, *, request: EvaluationSettings) -> list[str]:
    ids = [str(sample.id) for sample in task.dataset]
    if request.sample_ids is not None:
        ids = [case for case in ids if case in request.sample_ids]
    return ids[: request.limit]


def task_pairs(task: InspectTask, *, ids: list[str], epochs: int) -> set[Pair]:
    return {(task.name, case, epoch) for case in ids for epoch in range(1, epochs + 1)}


def expected_pairs(
    tasks: list[InspectTask], *, request: EvaluationSettings, epochs: int
) -> set[Pair]:
    result: set[Pair] = set()
    for task in tasks:
        result.update(task_pairs(task, ids=selected_ids(task, request=request), epochs=epochs))
    return result


def sample_records(logs: Sequence[EvalLog]) -> list[tuple[str, EvalSample]]:
    return [(log.eval.task, sample) for log in logs for sample in log.samples or []]


def crashed(sample: EvalSample) -> bool:
    return any(
        (score.metadata or {}).get("agent_failure") for score in (sample.scores or {}).values()
    )


def scored(sample: EvalSample) -> bool:
    return any(complete_value(score.value) for score in (sample.scores or {}).values())


def complete_value(value: object) -> bool:
    return isinstance(value, dict) and all(
        value.get(name) in (CORRECT, INCORRECT) for name in Task.required_scores
    )


def counts(records: list[tuple[str, EvalSample]]) -> dict[str, object]:
    return {
        "errors": sum(s.error is not None for _, s in records),
        "crashes": sum(crashed(s) for _, s in records),
        "cutoffs": sum(s.limit is not None for _, s in records),
    }


def report(logs: Sequence[EvalLog], *, expected: set[Pair]) -> dict[str, object]:
    records = sample_records(logs)
    observed = Counter((task, str(s.id), s.epoch) for task, s in records)
    scored_pairs = {(task, str(s.id), s.epoch) for task, s in records if scored(s)}
    return {
        "expected": len(expected),
        "scored": len(scored_pairs),
        "missing": sorted(expected - scored_pairs),
        "unexpected": sorted(observed.keys() - expected),
        "duplicates": duplicates(observed),
        "failed_tasks": sum(log.status != "success" for log in logs),
        **counts(records),
    }


def duplicates(observed: Counter[Pair]) -> list[Pair]:
    return sorted(pair for pair, count in observed.items() if count != 1)


def failed(summary: dict[str, object]) -> bool:
    keys = (
        "missing",
        "unexpected",
        "duplicates",
        "errors",
        "failed_tasks",
        "telemetry_errors",
        "lifecycle_missing",
    )
    return any(summary.get(key) for key in keys)
