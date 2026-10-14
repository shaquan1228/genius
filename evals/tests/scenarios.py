"""Scripted agents for offline framework tests, never for measuring Genius."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from inspect_ai.model import ChatMessage, ChatMessageUser, GenerateConfig, ModelOutput
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.tool import ToolChoice, ToolInfo
from inspect_ai.util import sandbox

from evals.cases import Case
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
SOLUTIONS = Path(__file__).parent / "solutions"


def echo_model(
    messages: list[ChatMessage],
    tools: list[ToolInfo],
    tool_choice: ToolChoice,
    config: GenerateConfig,
) -> ModelOutput:
    return ModelOutput.from_content("mockllm/model", messages[-1].text)


async def apply_solution(state: TaskState) -> None:
    case = Case.model_validate(state.metadata["case"])
    for path in (SOLUTIONS / case.id).iterdir():
        if path.name != "answer.txt":
            await sandbox().write_file(f"workspace/{path.name}", path.read_text())


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
    case = Case.model_validate(state.metadata["case"])
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
        case = Case.model_validate(state.metadata["case"])
        answer = (
            "invalid JSON"
            if self.mode == "bad-answer"
            else (SOLUTIONS / case.id / "answer.txt").read_text()
        )
        state.messages.append(ChatMessageUser(content=answer))
        return await generate(state)


@solver
def scripted(mode: Mode = "pass") -> Solver:
    return Scripted(mode)
