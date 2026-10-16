from collections.abc import Mapping
from functools import partial, wraps
from typing import cast

from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox
from pydantic import JsonValue

import evals.python.integrations.inspect.environments as environments_adapter
import evals.python.integrations.inspect.workspace as workspace_adapter
from evals.python import commands, query


def score_values(scores: Mapping[str, bool]) -> dict[str, str]:
    return {name: CORRECT if passed else INCORRECT for name, passed in scores.items()}


def with_failure(explanation: str, *, failure: str | None) -> str:
    if failure is None:
        return explanation
    return f"Agent process crashed: {failure}\n\n{explanation}"


def diagnostic(value: commands.Diagnostic) -> JsonValue:
    if isinstance(value, Mapping):
        return {key: diagnostic(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [diagnostic(item) for item in value]
    return value


async def score_sample(  # noqa: PLR0917 - Inspect calls scorers positionally
    state: TaskState, target: Target, *, dataset: query.Dataset | None = None
) -> Score:
    failure = state.metadata.get("agent_failure")
    completion = state.output.completion
    changed = tuple(sorted(await workspace_adapter.changed_files(state)))
    current = sandbox()
    result = await commands.AssessCase(
        case_id=str(state.metadata["case_id"]),
        response=completion,
        changed_files=changed,
        selection=dataset
        if dataset is not None
        else cast(str, state.metadata.get("dataset", "smoke")),
        agent=environments_adapter.environment(current),
        runtime=environments_adapter.runtime(current),
    )
    explanation = (
        completion if result.verification.status == "unchecked" else result.verification.detail
    )
    return Score(
        value=score_values(result.scores),
        explanation=with_failure(explanation, failure=failure),
        metadata={
            "verification": result.verification.model_dump(),
            "verifier_metadata": diagnostic(result.metadata),
            "changed_files": changed,
            "agent_failure": failure,
        },
    )


@scorer(metrics={name: [accuracy(), stderr()] for name in ("correctness", "scope")})
def evaluation() -> Scorer:
    return score_sample


def bound_evaluation(*, dataset: query.Dataset) -> Scorer:
    # Copy only the public registration; private inputs stay in the bound callback.
    return wraps(evaluation())(partial(score_sample, dataset=dataset))
