"""Grade correctness and file scope independently of the agent's self-report."""

from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox

from evals.python.transport import CodeChecks, case_by_id, grade, heldout_check
from evals.python.workspace import changed_files


def verdict(*, passed: bool, explanation: str | None) -> Score:
    return Score(value=CORRECT if passed else INCORRECT, explanation=explanation)


async def score_code(checks: CodeChecks) -> Score:
    command, program, marker = heldout_check(checks)
    result = await sandbox().exec(command, input=program, cwd="workspace", timeout=30)
    return verdict(
        passed=result.success and marker in result.stdout.splitlines(),
        explanation=(result.stdout + result.stderr)[-2000:] or "Held-out checks did not complete.",
    )


async def score_correctness(state: TaskState, target: Target) -> Score:  # noqa: PLR0917 - Inspect calls scorers positionally
    case = case_by_id(str(state.metadata["case_id"]))
    completion = state.output.completion
    code = await score_code(case.checks) if isinstance(case.checks, CodeChecks) else None
    scores = grade(
        case.id,
        response=completion,
        changed_files=(),
        code_passed=code is not None and code.value == CORRECT,
    )
    return verdict(
        passed=scores["correctness"],
        explanation=code.explanation if code is not None else completion,
    )


async def score_scope(state: TaskState, target: Target) -> Score:  # noqa: PLR0917 - Inspect calls scorers positionally
    case = case_by_id(str(state.metadata["case_id"]))
    changed = tuple(sorted(await changed_files(state)))
    scores = grade(
        case.id,
        response=state.output.completion,
        changed_files=changed,
        code_passed=False,
    )
    return verdict(passed=scores["scope"], explanation=f"Changed files: {list(changed)}")


@scorer(metrics=[accuracy(), stderr()])
def correctness() -> Scorer:
    return score_correctness


@scorer(metrics=[accuracy(), stderr()])
def scope() -> Scorer:
    return score_scope
