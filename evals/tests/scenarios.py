"""Scripted agents for offline framework tests, never for measuring Genius."""

from dataclasses import dataclass
from typing import Literal

from inspect_ai.model import ChatMessage, ChatMessageUser, GenerateConfig, ModelOutput
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.tool import ToolChoice, ToolInfo
from inspect_ai.util import sandbox

from evals.cases import case_by_id
from evals.workspace import GIT_IDENTITY, execute

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


def echo_model(
    messages: list[ChatMessage],
    tools: list[ToolInfo],
    tool_choice: ToolChoice,
    config: GenerateConfig,
) -> ModelOutput:
    return ModelOutput.from_content("mockllm/model", messages[-1].text)


async def apply_solution(state: TaskState) -> None:
    case = case_by_id(str(state.metadata["case_id"]))
    for name, text in case.solution.items():
        await sandbox().write_file(f"workspace/{name}", text)


async def mutate(state: TaskState, mode: Mode) -> None:
    if mode in ("extra", "committed-extra"):
        await sandbox().write_file("workspace/unrequested.txt", "Extra change")
    if mode == "committed-extra":
        await execute(["git", "add", "--all"])
        await execute(["git", *GIT_IDENTITY, "commit", "-q", "-m", "Agent commit"])
    if mode == "tampered-checks":
        await sandbox().write_file("workspace/check.sh", "#!/bin/sh\nexit 0\n")
        await sandbox().write_file("workspace/examples.ml", "let check ~name _ _ = ()\n")
    if mode == "instructions":
        await sandbox().write_file("instructions/skills/reasoning/SKILL.md", "Corrupted")


async def exit_early(state: TaskState) -> None:
    case = case_by_id(str(state.metadata["case_id"]))
    for name in case.sources:
        path = f"workspace/{name}"
        source = await sandbox().read_file(path)
        await sandbox().write_file(path, "let () = exit 0\n" + source)


@dataclass
class Scripted:
    mode: Mode

    async def __call__(self, state: TaskState, generate: Generate) -> TaskState:
        if self.mode not in ("untouched", "tampered-checks", "early-exit"):
            await apply_solution(state)
        await mutate(state, self.mode)
        if self.mode == "early-exit":
            await exit_early(state)
        case = case_by_id(str(state.metadata["case_id"]))
        answer = "invalid JSON" if self.mode == "bad-answer" else case.answer
        state.messages.append(ChatMessageUser(content=answer))
        return await generate(state)


@solver
def scripted(mode: Mode = "pass") -> Solver:
    return Scripted(mode)
