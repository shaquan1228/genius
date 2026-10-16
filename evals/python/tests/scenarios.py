"""Scripted agents for offline framework tests, never for measuring Genius."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal, cast

from inspect_ai.agent import Agent, AgentState, agent
from inspect_ai.model import ChatMessage, ChatMessageUser, GenerateConfig, ModelOutput
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.tool import ToolChoice, ToolInfo
from inspect_ai.util import sandbox

from evals.python._kernel import Reference
from evals.python.catalog import reference
from evals.python.integrations.inspect.workspace import GIT_IDENTITY, execute

Mode = Literal[
    "pass",
    "untouched",
    "extra",
    "committed-extra",
    "instructions",
    "bad-answer",
    "tampered-checks",
    "early-exit",
]


def echo_model(  # noqa: PLR0917 - Inspect calls mock model callbacks positionally
    messages: list[ChatMessage],
    tools: list[ToolInfo],
    tool_choice: ToolChoice,
    config: GenerateConfig,
) -> ModelOutput:
    return ModelOutput.from_content("mockllm/model", messages[-1].text)


Step = Callable[[Reference], Awaitable[None]]


async def apply_solution(case: Reference) -> None:
    for name, text in case.solution.items():
        await sandbox().write_file(f"workspace/{name}", text)


async def write_extra(case: Reference) -> None:
    await sandbox().write_file("workspace/unrequested.txt", "Extra change")


async def commit(case: Reference) -> None:
    await execute(["git", "add", "--all"])
    await execute(["git", *GIT_IDENTITY, "commit", "-q", "-m", "Agent commit"])


async def corrupt_instructions(case: Reference) -> None:
    await sandbox().write_file("instructions/skills/reasoning/SKILL.md", "Corrupted")


async def tamper_runner(case: Reference) -> None:
    await sandbox().write_file("workspace/test_receipt.py", "raise SystemExit(0)\n")


async def exit_early(case: Reference) -> None:
    for name in case.solution:
        path = f"workspace/{name}"
        source = await sandbox().read_file(path)
        await sandbox().write_file(path, "import os\nos._exit(0)\n" + source)


@dataclass(frozen=True)
class Scenario:
    steps: tuple[Step, ...]
    reply: str | None = None  # None sends the reference answer.


SCENARIOS: dict[Mode, Scenario] = {
    "pass": Scenario((apply_solution,)),
    "untouched": Scenario(()),
    "extra": Scenario((apply_solution, write_extra)),
    "committed-extra": Scenario((apply_solution, write_extra, commit)),
    "instructions": Scenario((apply_solution, corrupt_instructions)),
    "bad-answer": Scenario((apply_solution,), reply="invalid JSON"),
    "tampered-checks": Scenario((tamper_runner,)),
    "early-exit": Scenario((exit_early,)),
}


@dataclass
class Scripted:
    scenario: Scenario

    async def __call__(self, state: TaskState, generate: Generate) -> TaskState:  # noqa: PLR0917 - Inspect calls solvers positionally
        case = reference(
            str(state.metadata["case_id"]),
            selection=cast(str, state.metadata.get("dataset", "smoke")),
        )
        for step in self.scenario.steps:
            await step(case)
        state.messages.append(ChatMessageUser(content=self.scenario.reply or case.answer))
        return await generate(state)


@solver
def scripted(mode: Mode = "pass") -> Solver:
    return Scripted(SCENARIOS[mode])


@agent
def crashing(*, message: str) -> Agent:
    """Stand in for an agent CLI that exits nonzero before it edits the workspace."""

    async def execute(state: AgentState) -> AgentState:
        raise RuntimeError(message)

    return execute
