"""Grade correctness and file scope independently of the agent's self-report."""

from secrets import token_hex

from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox

from evals.answers import grade_answer
from evals.cases import EVALS_ROOT, Case, case_by_id
from evals.workspace import changed_files


def verdict(passed: bool, explanation: str) -> Score:
    return Score(value=CORRECT if passed else INCORRECT, explanation=explanation)


def heldout_check(case: Case) -> tuple[list[str], str, str]:
    script = str(case.heldout)
    command = [
        "sh",
        "-c",
        (EVALS_ROOT / "check.sh").read_text(),
        "ocaml-check",
        "--stdin",
        *case.sources,
    ]
    marker = "GENIUS_HELDOUT_" + token_hex(16)
    script += f'\nlet () = print_endline "\\n{marker}"\n'
    return command, script, marker


async def score_correctness(state: TaskState, target: Target) -> Score:
    case = case_by_id(str(state.metadata["case_id"]))
    if case.grading != "ocaml":
        return verdict(
            grade_answer(case.grading, state.output.completion, expected=case.expected),
            state.output.completion,
        )
    command, script, marker = heldout_check(case)
    result = await sandbox().exec(command, input=script, cwd="workspace", timeout=30)
    return verdict(
        result.success and marker in result.stdout.splitlines(),
        (result.stdout + result.stderr)[-2000:] or "Held-out checks did not complete.",
    )


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
