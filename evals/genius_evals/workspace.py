"""Initialize and inspect sample files through Inspect's sandbox API."""

from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import sandbox

GIT_IDENTITY = [
    "-c",
    "user.name=Eval",
    "-c",
    "user.email=eval@example.invalid",
    "-c",
    "commit.gpgsign=false",
    "-c",
    "core.hooksPath=/dev/null",
]


async def execute(command: list[str], cwd: str | None = None) -> str:
    result = await sandbox().exec(command, cwd=cwd, timeout=30)
    if not result.success:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


async def prepare_sample(state: TaskState, generate: Generate) -> TaskState:
    await execute(["git", "init", "-q", "-b", "eval"])
    await execute(["git", "add", "--all"])
    await execute(["git", *GIT_IDENTITY, "commit", "-q", "-m", "Eval fixture"])
    state.metadata["initial_commit"] = (await execute(["git", "rev-parse", "HEAD"])).strip()
    return state


@solver
def prepare() -> Solver:
    return prepare_sample


async def changed_files(state: TaskState) -> set[str]:
    revision = str(state.metadata["initial_commit"])
    tracked = await execute(["git", "diff", "--name-only", "--no-renames", "-z", revision, "--"])
    untracked = await execute(["git", "ls-files", "--others", "-z"])
    return set(filter(None, (tracked + untracked).split("\0")))
