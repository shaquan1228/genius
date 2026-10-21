import json
from collections.abc import Callable, Sequence
from contextlib import suppress
from functools import partial, wraps
from operator import attrgetter
from typing import Any, cast

from inspect_ai.model import ChatMessageAssistant
from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox
from pydantic import JsonValue

import evals.python.integrations.inspect.environments as environments_adapter
import evals.python.integrations.inspect.workspace as workspace_adapter
from evals.python import datasets, verification
from evals.python.datasets import Dataset
from kernel import Assessment, Outcome, Predicate, Task, Value, Verification

WORKSPACE = "workspace/"


def decode_response(text: str) -> JsonValue:
    """Decode a JSON reply; anything else is a null response."""
    text = text.strip()
    if text.startswith("```json\n") and text.endswith("\n```"):
        text = text[8:-4]
    with suppress(ValueError, RecursionError):
        return cast(JsonValue, json.loads(text))
    return None


_PLAIN: dict[type, Callable[[Any], JsonValue]] = {
    Value.Null: lambda _: None,
    Value.List: lambda data: [plain(item) for item in data.items],
    Value.Record: lambda data: {name: plain(item) for name, item in data.fields},
}
_SCALAR: Callable[[Any], JsonValue] = attrgetter("value")


def plain(data: Value.Value) -> JsonValue:
    return _PLAIN.get(type(data), _SCALAR)(data)


def trace(state: TaskState) -> list[JsonValue]:
    """Every recorded tool call, as the agent's interaction trace."""
    return [
        {"name": call.function, "arguments": cast(JsonValue, call.arguments)}
        for message in state.messages
        if isinstance(message, ChatMessageAssistant)
        for call in message.tool_calls or []
    ]


def workspace_path(path: str) -> str:
    return path.removeprefix(WORKSPACE) if path.startswith(WORKSPACE) else f"../{path}"


_PREDICATES: dict[type, Callable[[Any], dict[str, JsonValue]]] = {
    Predicate.Present: lambda _: {},
    Predicate.Equals: lambda check: {"expected": plain(check.expected)},
    Predicate.Within: lambda check: {"allowed": [plain(item) for item in check.allowed]},
    Predicate.Contains: lambda check: {"item": plain(check.item)},
    Predicate.Words: lambda check: {"min_words": check.min_words, "max_words": check.max_words},
    Predicate.All: lambda check: {"checks": [name for name, _ in check.checks]},
    Predicate.Any: lambda check: {"checks": [name for name, _ in check.checks]},
    Predicate.Not: lambda check: {"check": predicate_details(check.check)},
}


def predicate_details(predicate: Predicate.Value) -> dict[str, JsonValue]:
    details: dict[str, JsonValue] = {"kind": type(predicate).__name__.lower()}
    path = getattr(predicate, "path", None)
    if path is not None:
        details["path"] = list(path)
    details.update(_PREDICATES[type(predicate)](predicate))
    return details


def assessment_details(assessment: Assessment.Value) -> dict[str, JsonValue]:
    result: dict[str, JsonValue] = {"passed": Assessment.passed(assessment=assessment)}
    if isinstance(assessment, Assessment.All):
        result["checks"] = {name: assessment_details(check) for name, check in assessment.checks}
        return result
    observed = Assessment.observed(assessment=assessment)
    result["predicate"] = predicate_details(assessment.predicate)
    result["observed"] = None if observed is None else plain(observed)
    return result


def score_values(scores: Sequence[tuple[str, bool]]) -> dict[str, str]:
    return {name: CORRECT if passed else INCORRECT for name, passed in scores}


def with_failure(explanation: str, *, failure: str | None) -> str:
    if failure is None:
        return explanation
    return f"Agent process crashed: {failure}\n\n{explanation}"


async def score_sample(  # noqa: PLR0917 - Inspect calls scorers positionally
    state: TaskState, target: Target, *, dataset: Dataset | None = None
) -> Score:
    failure = state.metadata.get("agent_failure")
    completion = state.output.completion
    changed = tuple(sorted(map(workspace_path, await workspace_adapter.changed_files(state))))
    current = sandbox()
    selected = datasets.load_dataset(
        selection=dataset
        if dataset is not None
        else cast(str, state.metadata.get("dataset", "smoke"))
    )
    task = selected.records[str(state.metadata["case_id"])]
    evidence = await verification.verify(
        Task.checks(task=task),
        agent=environments_adapter.environment(current),
        runtime=environments_adapter.runtime(current),
    )
    facts: dict[str, JsonValue] = {"trace": trace(state), "state": dict(state.store.items())}
    result = Task.assess(
        task=task,
        outcome=Outcome.create(
            changed_files=changed,
            verification=evidence.verification,
            response=decode_response(completion),
            facts=facts,
        ),
    )
    explanation = (
        completion if isinstance(evidence.verification, Verification.Unchecked) else evidence.detail
    )
    return Score(
        value=score_values(Assessment.scores(assessment=result)),
        explanation=with_failure(explanation, failure=failure),
        metadata={
            "verification": {
                "status": Outcome.status(verification=evidence.verification),
                "detail": evidence.detail,
            },
            "verifier_metadata": evidence.metadata_json(),
            "changed_files": changed,
            "facts": facts,
            "agent_failure": failure,
            "assessment": assessment_details(result),
        },
    )


@scorer(metrics={name: [accuracy(), stderr()] for name in Task.required_scores})
def evaluation() -> Scorer:
    return score_sample


def bound_evaluation(*, dataset: Dataset) -> Scorer:
    # Copy only the public registration; private inputs stay in the bound callback.
    return wraps(evaluation())(partial(score_sample, dataset=dataset))
