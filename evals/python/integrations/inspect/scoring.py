import json
from collections.abc import Callable, Sequence
from contextlib import suppress
from functools import partial, wraps
from typing import Any, cast

from inspect_ai.model import ChatMessageAssistant
from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox
from kernel import REQUIRED_SCORES, Assessment, Outcome, Predicate, Value
from pydantic import JsonValue

import evals.python.integrations.inspect.environments as environments_adapter
import evals.python.integrations.inspect.workspace as workspace_adapter
from evals.python import datasets, verification
from evals.python.datasets import Dataset

WORKSPACE = "workspace/"


def decode_response(text: str) -> JsonValue:
    """Decode a JSON reply; anything else is a null response."""
    text = text.strip()
    if text.startswith("```json\n") and text.endswith("\n```"):
        text = text[8:-4]
    with suppress(ValueError, RecursionError):
        return cast(JsonValue, json.loads(text))
    return None


def observed(data: object) -> Value:
    with suppress(TypeError, ValueError, OverflowError):
        return Value.from_python(value=data)
    return Value.from_python(value=None)


def plain(data: Value) -> JsonValue:
    match data.kind:
        case "list":
            return [plain(item) for item in data.items]
        case "record":
            return {name: plain(item) for name, item in data.fields}
        case _:
            return data.scalar


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


_PREDICATES: dict[str, Callable[[Any], dict[str, JsonValue]]] = {
    "present": lambda _: {},
    "equals": lambda check: {"expected": plain(check.expected)},
    "within": lambda check: {"allowed": [plain(item) for item in check.allowed]},
    "contains": lambda check: {"item": plain(check.item)},
    "words": lambda check: {"min_words": check.min_words, "max_words": check.max_words},
    "all": lambda check: {"checks": [name for name, _ in check.checks]},
    "any": lambda check: {"checks": [name for name, _ in check.checks]},
    "not": lambda check: {"check": predicate_details(check.check)},
}


def predicate_details(predicate: Predicate) -> dict[str, JsonValue]:
    details: dict[str, JsonValue] = {"kind": predicate.kind}
    if predicate.path is not None:
        details["path"] = list(predicate.path)
    details.update(_PREDICATES[predicate.kind](predicate))
    return details


def assessment_details(assessment: Assessment) -> dict[str, JsonValue]:
    result: dict[str, JsonValue] = {"passed": assessment.passed()}
    if assessment.kind == "all":
        result["checks"] = {name: assessment_details(check) for name, check in assessment.checks}
        return result
    observed = assessment.observed()
    result["predicate"] = predicate_details(cast(Predicate, assessment.predicate))
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
    task = selected.records[str(state.metadata["case_id"])].task
    evidence = await verification.verify(
        task.checks(),
        agent=environments_adapter.environment(current),
        runtime=environments_adapter.runtime(current),
    )
    facts: dict[str, JsonValue] = {"trace": trace(state), "state": dict(state.store.items())}
    result = task.assess(
        outcome=Outcome(
            changed_files=changed,
            verification=evidence.verification,
            response=observed(decode_response(completion)),
            facts=[(name, observed(fact)) for name, fact in facts.items()],
        )
    )
    explanation = completion if evidence.verification.status == "unchecked" else evidence.detail
    return Score(
        value=score_values(result.scores()),
        explanation=with_failure(explanation, failure=failure),
        metadata={
            "verification": {
                "status": evidence.verification.status,
                "detail": evidence.detail,
            },
            "verifier_metadata": evidence.metadata_json(),
            "changed_files": changed,
            "facts": facts,
            "agent_failure": failure,
            "assessment": assessment_details(result),
        },
    )


@scorer(metrics={name: [accuracy(), stderr()] for name in REQUIRED_SCORES})
def evaluation() -> Scorer:
    return score_sample


def bound_evaluation(*, dataset: Dataset) -> Scorer:
    # Copy only the public registration; private inputs stay in the bound callback.
    return wraps(evaluation())(partial(score_sample, dataset=dataset))
