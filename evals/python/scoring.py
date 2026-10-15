"""Grade correctness and file scope independently of the agent's self-report."""

from collections.abc import Mapping
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


def score_values(scores: Mapping[str, bool]) -> dict[str, str]:
    return {name: CORRECT if passed else INCORRECT for name, passed in scores.items()}


async def score_sample(state: TaskState, target: Target) -> Score:  # noqa: PLR0917 - Inspect calls scorers positionally
    dataset = cast(Dataset, state.metadata.get("dataset", "smoke"))
    case = case_by_id(query=CaseQuery(case_id=str(state.metadata["case_id"]), selection=dataset))
    completion = state.output.completion
    changed = tuple(sorted(await changed_files(state)))
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
            changed_files=changed,
            verification=evidence,
            selection=dataset,
        )
    )
    return Score(
        value=score_values(scores=scores),
        explanation=explanation,
        metadata={
            "verification": evidence.model_dump(),
            "verifier_metadata": metadata,
            "changed_files": changed,
        },
    )


@scorer(metrics={name: [accuracy(), stderr()] for name in ("correctness", "scope")})
def evaluation() -> Scorer:
    return score_sample
