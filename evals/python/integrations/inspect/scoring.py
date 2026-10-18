from collections.abc import Mapping
from functools import partial, wraps
from typing import assert_never, cast

from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox

import evals.python.integrations.inspect.environments as environments_adapter
import evals.python.integrations.inspect.workspace as workspace_adapter
from evals.python import assessment
from evals.python.datasets import Dataset
from kernel import Assessment as NativeAssessment
from kernel import Evidence, ResponseValue, Task, Verification


def response_value(value: ResponseValue.Value | None) -> str | bool | None:
    return None if value is None else value.value


def evidence_details(check: NativeAssessment.Check) -> dict[str, object]:
    evidence = check.evidence
    match evidence:
        case Evidence.Present():
            return {"response_present": evidence.response is not None}
        case Evidence.Field():
            return {
                "expected": response_value(evidence.comparison.before),
                "actual": response_value(evidence.comparison.after),
            }
        case Evidence.Text():
            return {
                "field": evidence.rule.field,
                "actual": response_value(evidence.value),
                "word_count": NativeAssessment.word_count(value=evidence.value),
                "min_words": evidence.rule.min_words,
                "max_words": evidence.rule.max_words,
            }
        case _:
            return execution_details(evidence, check=check)


def execution_details(
    evidence: Evidence.Verified | Evidence.Scope, *, check: NativeAssessment.Check
) -> dict[str, object]:
    match evidence:
        case Evidence.Verified():
            return {"verification": type(evidence.verification).__name__.lower()}
        case Evidence.Scope():
            return {"unexpected_files": list(NativeAssessment.unexpected_files(assessment=check))}
        case _ as unreachable:
            assert_never(unreachable)


def assessment_details(value: NativeAssessment.Value) -> dict[str, object]:
    result: dict[str, object] = {"passed": NativeAssessment.passed(assessment=value)}
    if isinstance(value, NativeAssessment.All):
        result["checks"] = {name: assessment_details(check) for name, check in value.checks}
    else:
        result.update(evidence_details(value))
    return result


def score_values(scores: Mapping[str, bool]) -> dict[str, str]:
    return {name: CORRECT if passed else INCORRECT for name, passed in scores.items()}


def with_failure(explanation: str, *, failure: str | None) -> str:
    if failure is None:
        return explanation
    return f"Agent process crashed: {failure}\n\n{explanation}"


async def score_sample(  # noqa: PLR0917 - Inspect calls scorers positionally
    state: TaskState, target: Target, *, dataset: Dataset | None = None
) -> Score:
    failure = state.metadata.get("agent_failure")
    completion = state.output.completion
    changed = tuple(sorted(await workspace_adapter.changed_files(state)))
    current = sandbox()
    result = await assessment.assess(
        case_id=str(state.metadata["case_id"]),
        response=completion,
        changed_files=changed,
        selection=dataset
        if dataset is not None
        else cast(str, state.metadata.get("dataset", "smoke")),
        agent=environments_adapter.environment(current),
        runtime=environments_adapter.runtime(current),
    )
    evidence = result.evidence
    explanation = (
        completion if isinstance(evidence.verification, Verification.Unchecked) else evidence.detail
    )
    return Score(
        value=score_values(result.scores),
        explanation=with_failure(explanation, failure=failure),
        metadata={
            "verification": {
                "status": type(evidence.verification).__name__.lower(),
                "detail": evidence.detail,
            },
            "verifier_metadata": evidence.metadata_json(),
            "changed_files": changed,
            "agent_failure": failure,
            "assessment": assessment_details(result.assessment),
        },
    )


@scorer(metrics={name: [accuracy(), stderr()] for name in Task.required_scores})
def evaluation() -> Scorer:
    return score_sample


def bound_evaluation(*, dataset: Dataset) -> Scorer:
    # Copy only the public registration; private inputs stay in the bound callback.
    return wraps(evaluation())(partial(score_sample, dataset=dataset))
