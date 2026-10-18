from collections.abc import Mapping
from functools import partial, wraps
from typing import cast

from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox

import evals.python.integrations.inspect.environments as environments_adapter
import evals.python.integrations.inspect.workspace as workspace_adapter
from evals.python import assessment
from evals.python.datasets import Dataset
from kernel import RubricGrade, Task, TaskGrade, Verification


def answer_details(answer: RubricGrade) -> dict[str, object]:
    rule = answer.text_rule
    return {
        "response_present": answer.response_present,
        "fields": [{"name": field.name, "passed": field.equal} for field in answer.fields.fields],
        "text_rule": None
        if rule is None
        else {
            "field": rule.field,
            "passed": rule.passed,
            "word_count": rule.word_count,
            "min_words": rule.min_words,
            "max_words": rule.max_words,
        },
    }


def grade_details(grade: TaskGrade | None) -> dict[str, object] | None:
    if grade is None:
        return None
    answer = grade.correctness.answer
    return {
        "correctness": grade.correctness.passed,
        "unexpected_files": list(grade.scope.unexpected_files),
        "answer": None if answer is None else answer_details(answer),
    }


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
            "grade": grade_details(result.grade),
        },
    )


@scorer(metrics={name: [accuracy(), stderr()] for name in Task.required_scores})
def evaluation() -> Scorer:
    return score_sample


def bound_evaluation(*, dataset: Dataset) -> Scorer:
    # Copy only the public registration; private inputs stay in the bound callback.
    return wraps(evaluation())(partial(score_sample, dataset=dataset))
