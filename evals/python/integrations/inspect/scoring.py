import json
from collections.abc import Callable, Sequence
from contextlib import suppress
from functools import partial, wraps
from typing import Any, cast

from inspect_ai.model import ChatMessageAssistant
from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox
from pydantic import ConfigDict, JsonValue, TypeAdapter

import evals.python.integrations.inspect.environments as environments_adapter
import evals.python.integrations.inspect.workspace as workspace_adapter
from evals.python import datasets, verification
from evals.python.datasets import Dataset
from kernel import (
    Assessment,
    Completion,
    Outcome,
    Predicate,
    Response,
    ResponseField,
    ResponseValue,
    Task,
    Value,
    Verification,
)

_RESPONSE_FIELDS = TypeAdapter(dict[str, str | bool], config=ConfigDict(strict=True))
WORKSPACE = "workspace/"


def decode_response(text: str) -> Response | None:
    text = Completion.trim(text=text)
    if text.startswith("```json\n") and text.endswith("\n```"):
        text = text[8:-4]
    with suppress(ValueError, RecursionError):
        fields = _RESPONSE_FIELDS.validate_python(json.loads(text))
        return Response.create(
            fields=[
                ResponseField.create(
                    name=name,
                    value=(
                        ResponseValue.create(bool=value)
                        if isinstance(value, bool)
                        else ResponseValue.create(string=value)
                    ),
                )
                for name, value in fields.items()
            ]
        )
    return None


_ENCODERS: dict[type, Callable[[Any], Value.Value]] = {
    type(None): lambda _: Value.Null(),
    bool: lambda data: Value.Bool(value=data),
    int: lambda data: Value.Int(value=data),
    float: lambda data: Value.Float(value=data),
    str: lambda data: Value.String(value=data),
    list: lambda data: Value.List(items=[value(item) for item in data]),
    tuple: lambda data: Value.List(items=[value(item) for item in data]),
    dict: lambda data: Value.Record(fields=[(str(key), value(item)) for key, item in data.items()]),
}


def value(data: object) -> Value.Value:
    """Encode JSON-shaped data as a native value; any other object becomes its text."""
    encode = _ENCODERS.get(type(data), lambda data: Value.String(value=str(data)))
    return encode(data)


def plain(data: Value.Value) -> JsonValue:
    match data:
        case Value.Null():
            return None
        case Value.List():
            return [plain(item) for item in data.items]
        case Value.Record():
            return {name: plain(item) for name, item in data.fields}
        case _:
            return data.value


def trace(state: TaskState) -> Value.Value:
    """Every recorded tool call, as the agent's interaction trace."""
    return value(
        [
            {"name": call.function, "arguments": call.arguments}
            for message in state.messages
            if isinstance(message, ChatMessageAssistant)
            for call in message.tool_calls or []
        ]
    )


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
        Task.verifier(task=task),
        agent=environments_adapter.environment(current),
        runtime=environments_adapter.runtime(current),
    )
    facts = [("trace", trace(state)), ("state", value(dict(state.store.items())))]
    result = Task.assess(
        task=task,
        response=decode_response(completion),
        outcome=Outcome.create(
            changed_files=changed, verification=evidence.verification, facts=facts
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
                "status": Verification.name(status=evidence.verification),
                "detail": evidence.detail,
            },
            "verifier_metadata": evidence.metadata_json(),
            "changed_files": changed,
            "facts": {name: plain(fact) for name, fact in facts},
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
