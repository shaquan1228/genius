"""Grade correctness and file scope independently of the agent's self-report."""

from typing import cast

from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox

from evals.python.transport import Dataset, ExecutableChecks, Verification, case_by_id, grade
from evals.python.verification import verify
from evals.python.workspace import changed_files


def verdict(*, passed: bool, explanation: str | None) -> Score:
    return Score(value=CORRECT if passed else INCORRECT, explanation=explanation)


async def score_correctness(state: TaskState, target: Target) -> Score:  # noqa: PLR0917 - Inspect calls scorers positionally
    dataset = cast(Dataset, state.metadata.get("dataset", "smoke"))
    case = case_by_id(str(state.metadata["case_id"]), dataset=dataset)
    completion = state.output.completion
    evidence, metadata = (
        await verify(case.checks, agent=sandbox())
        if isinstance(case.checks, ExecutableChecks)
        else (Verification(status="unchecked"), {})
    )
    if evidence.status == "harness_error":
        raise RuntimeError(f"Verification harness error: {evidence.detail}")
    scores = grade(
        case.id, response=completion, changed_files=(), verification=evidence, dataset=dataset
    )
    result = verdict(
        passed=scores["correctness"],
        explanation=evidence.detail if isinstance(case.checks, ExecutableChecks) else completion,
    )
    result.metadata = {"verification": evidence.model_dump(), "verifier_metadata": metadata}
    return result


async def score_scope(state: TaskState, target: Target) -> Score:  # noqa: PLR0917 - Inspect calls scorers positionally
    dataset = cast(Dataset, state.metadata.get("dataset", "smoke"))
    case = case_by_id(str(state.metadata["case_id"]), dataset=dataset)
    changed = tuple(sorted(await changed_files(state)))
    scores = grade(
        case.id,
        response=state.output.completion,
        changed_files=changed,
        verification=Verification(status="unchecked"),
        dataset=dataset,
    )
    return verdict(passed=scores["scope"], explanation=f"Changed files: {list(changed)}")


@scorer(metrics=[accuracy(), stderr()])
def correctness() -> Scorer:
    return score_correctness


@scorer(metrics=[accuracy(), stderr()])
def scope() -> Scorer:
    return score_scope
