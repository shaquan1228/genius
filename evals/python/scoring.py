"""Grade correctness and file scope independently of the agent's self-report."""

from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox

from evals.python.answers import grade_answer
from evals.python.transport import AnswerChecks, CodeChecks, case_by_id, heldout_check
from evals.python.workspace import changed_files


def verdict(passed: bool, explanation: str) -> Score:
    return Score(value=CORRECT if passed else INCORRECT, explanation=explanation)


async def score_code(checks: CodeChecks) -> Score:
    command, program, marker = heldout_check(checks)
    result = await sandbox().exec(command, input=program, cwd="workspace", timeout=30)
    return verdict(
        result.success and marker in result.stdout.splitlines(),
        (result.stdout + result.stderr)[-2000:] or "Held-out checks did not complete.",
    )


def score_answer(checks: AnswerChecks, completion: str) -> Score:
    return verdict(grade_answer(completion, expected=checks.expected), completion)


async def score_correctness(state: TaskState, target: Target) -> Score:
    checks = case_by_id(str(state.metadata["case_id"])).checks
    if isinstance(checks, CodeChecks):
        return await score_code(checks)
    return score_answer(checks, state.output.completion)


async def score_scope(state: TaskState, target: Target) -> Score:
    case = case_by_id(str(state.metadata["case_id"]))
    changed = await changed_files(state)
    allowed = {f"workspace/{name}" for name in case.allowed_files}
    return verdict(changed <= allowed, f"Changed files: {sorted(changed)}")


@scorer(metrics=[accuracy(), stderr()])
def correctness() -> Scorer:
    return score_correctness


@scorer(metrics=[accuracy(), stderr()])
def scope() -> Scorer:
    return score_scope
