"""Grade correctness and file scope independently of the agent's self-report."""

from typing import assert_never, cast

from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox

from evals.python.transport import (
    CaseQuery,
    Dataset,
    ExecutableChecks,
    GradeRequest,
    Verification,
    case_by_id,
    grade,
)
from evals.python.verification import Verifier
from evals.python.workspace import changed_files


def score_value(*, passed: bool) -> str:
    return CORRECT if passed else INCORRECT


async def score_correctness(state: TaskState, target: Target) -> Score:  # noqa: PLR0917 - Inspect calls scorers positionally
    dataset = cast(Dataset, state.metadata.get("dataset", "smoke"))
    case = case_by_id(query=CaseQuery(case_id=str(state.metadata["case_id"]), selection=dataset))
    completion = state.output.completion
    match case.checks:
        case ExecutableChecks() as checks:
            evidence, metadata = await Verifier(checks=checks, agent=sandbox()).verify()
            explanation = evidence.detail
        case None:
            evidence, metadata = Verification(status="unchecked"), {}
            explanation = completion
        case _ as unreachable:
            assert_never(unreachable)
    if evidence.status == "harness_error":
        raise RuntimeError(f"Verification harness error: {evidence.detail}")
    scores = grade(
        request=GradeRequest(
            case_id=case.id,
            response=completion,
            changed_files=(),
            verification=evidence,
            selection=dataset,
        )
    )
    return Score(
        value=score_value(passed=scores["correctness"]),
        explanation=explanation,
        metadata={"verification": evidence.model_dump(), "verifier_metadata": metadata},
    )


async def score_scope(state: TaskState, target: Target) -> Score:  # noqa: PLR0917 - Inspect calls scorers positionally
    dataset = cast(Dataset, state.metadata.get("dataset", "smoke"))
    case = case_by_id(query=CaseQuery(case_id=str(state.metadata["case_id"]), selection=dataset))
    changed = tuple(sorted(await changed_files(state)))
    scores = grade(
        request=GradeRequest(
            case_id=case.id,
            response=state.output.completion,
            changed_files=changed,
            verification=Verification(status="unchecked"),
            selection=dataset,
        )
    )
    return Score(
        value=score_value(passed=scores["scope"]),
        explanation=f"Changed files: {list(changed)}",
    )


@scorer(metrics=[accuracy(), stderr()])
def correctness() -> Scorer:
    return score_correctness


@scorer(metrics=[accuracy(), stderr()])
def scope() -> Scorer:
    return score_scope
