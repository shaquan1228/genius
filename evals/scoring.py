"""Grade correctness and file scope independently of the agent's self-report."""

from secrets import token_hex

from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox

from evals.answers import grade_answer
from evals.cases import EVALS_ROOT, Case
from evals.workspace import changed_files


def verdict(passed: bool, explanation: str) -> Score:
    return Score(value=CORRECT if passed else INCORRECT, explanation=explanation)


def heldout_check(case: Case) -> tuple[list[str], str, str]:
    script = (EVALS_ROOT / "heldout" / str(case.heldout_test)).read_text()
    shared = EVALS_ROOT / "fixtures/ocaml"
    script = (
        "module Examples = struct\n" + (shared / "examples.ml").read_text() + "\nend\n" + script
    )
    command = [
        "sh",
        "-c",
        (shared / "check.sh").read_text(),
        "ocaml-check",
        "--stdin",
        *case.sources,
    ]
    marker = "GENIUS_HELDOUT_" + token_hex(16)
    script += f'\nlet () = print_endline "\\n{marker}"\n'
    return command, script, marker


async def score_correctness(state: TaskState, target: Target) -> Score:
    case = Case.model_validate(state.metadata["case"])
    if case.heldout_test is None:
        return verdict(grade_answer(case.id, state.output.completion), state.output.completion)
    command, script, marker = heldout_check(case)
    result = await sandbox().exec(command, input=script, cwd="workspace", timeout=30)
    return verdict(
        result.success and marker in result.stdout.splitlines(),
        (result.stdout + result.stderr)[-2000:] or "Held-out checks did not complete.",
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
