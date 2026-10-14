"""Grade correctness and file scope independently of the agent's self-report."""

from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox

from evals.answers import grade_answer
from evals.cases import EVALS_ROOT, Case
from evals.workspace import changed_files


def verdict(passed: bool, explanation: str) -> Score:
    return Score(value=CORRECT if passed else INCORRECT, explanation=explanation)


async def score_correctness(state: TaskState, target: Target) -> Score:
    case = Case.model_validate(state.metadata["case"])
    if case.heldout_test is None:
        return verdict(grade_answer(case.id, state.output.completion), state.output.completion)
    script = (EVALS_ROOT / "heldout" / case.heldout_test).read_text()
    script += "\nraise SystemExit(not verify())\n"
    result = await sandbox().exec(["python3", "-B", "-c", script], cwd="workspace", timeout=30)
    return verdict(
        result.success, (result.stdout + result.stderr)[-2000:] or "Held-out checks ran."
    )


async def score_scope(state: TaskState, target: Target) -> Score:
    case = Case.model_validate(state.metadata["case"])
    changed = await changed_files(state)
    allowed = {f"workspace/{name}" for name in case.allowed_files}
    return verdict(changed <= allowed, f"Changed files: {sorted(changed)}")


@scorer(metrics=[accuracy(), stderr()])
def correctness() -> Scorer:
    return score_correctness


@scorer(metrics=[accuracy(), stderr()])
def scope() -> Scorer:
    return score_scope
