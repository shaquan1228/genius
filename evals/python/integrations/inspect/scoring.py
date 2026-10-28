import json
from collections.abc import Mapping, Sequence
from contextlib import suppress
from functools import partial, wraps
from itertools import repeat
from typing import cast

from inspect_ai.model import ChatMessageAssistant
from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox
from kernel import REQUIRED_SCORES, Assessment, Outcome
from pydantic import JsonValue

import evals.python.integrations.inspect.environments as environments_adapter
import evals.python.integrations.inspect.workspace as workspace_adapter
from evals.python import datasets, verification
from evals.python.datasets import Dataset
from evals.python.provenance import plain

WORKSPACE = "workspace/"
# The kernel nests values 256 levels deep, and its observation record takes the first.
NESTING = 255
INT64 = range(-(2**63), 2**63)


def decode_response(text: str) -> JsonValue:
    """Decode a JSON reply; anything else is a null response."""
    text = text.strip()
    if text.startswith("```json\n") and text.endswith("\n```"):
        text = text[8:-4]
    with suppress(ValueError, RecursionError):
        return cast(JsonValue, json.loads(text))
    return None


def held(data: object) -> bool:
    """Whether the kernel holds a scalar as given: null, boolean, float, string or int64."""
    return (
        data is None
        or isinstance(data, bool | float | str)
        or (isinstance(data, int) and data in INT64)
    )


def representable(data: object, *, depth: int = 0) -> bool:
    """Whether the kernel holds harness data as given, under an outcome channel."""
    match data:
        case dict():
            keyed = all(map(isinstance, data, repeat(str)))
            return keyed and representable([*data.values()], depth=depth)
        case list() | tuple():
            return depth < NESTING and all(map(partial(representable, depth=depth + 1), data))
        case _:
            return held(data)


def observed(data: object, *, depth: int = 0) -> object:
    """Harness data the kernel can hold, as plain values.

    Data the kernel holds as given is returned unchanged. A part it cannot hold, such as an
    integer beyond signed 64 bits, becomes a record naming its type. The part stays present,
    so a negated check cannot pass on it.
    """
    if representable(data, depth=depth):
        return data
    part = partial(observed, depth=depth + 1)
    match data:
        case dict() if depth < NESTING - 1:
            return dict(zip(map(str, data), map(part, data.values()), strict=True))
        case list() | tuple() if depth < NESTING - 1:
            return [*map(part, data)]
    return {"unrepresentable": type(data).__name__}


def unrepresentable(channels: Mapping[str, object]) -> list[str]:
    """Channels the kernel cannot hold as given, so each arm's rate can be estimated."""
    return [name for name, data in channels.items() if not representable(data)]


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


def assessment_details(assessment: Assessment) -> dict[str, JsonValue]:
    if assessment.kind == "all":
        return {
            "passed": assessment.passed(),
            "checks": {name: assessment_details(check) for name, check in assessment.checks},
        }
    return {
        "passed": assessment.passed(),
        "predicate": plain(assessment.predicate),
        "observed": plain(assessment.observed()),
    }


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
    response = decode_response(completion)
    facts: dict[str, JsonValue] = {"trace": trace(state), "state": dict(state.store.items())}
    result = task.assess(
        outcome=Outcome(
            changed_files=changed,
            verification=evidence.verification,
            response=observed(response),
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
            "unrepresentable": unrepresentable({"response": response, **facts}),
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
