"""Scripted agents for offline framework tests, never for measuring Genius."""

from dataclasses import dataclass
from typing import Literal

from inspect_ai.model import ChatMessage, ChatMessageUser, GenerateConfig, ModelOutput
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.tool import ToolChoice, ToolInfo
from inspect_ai.util import sandbox

from genius_evals.cases import CaseId, state_case
from genius_evals.workspace import GIT_IDENTITY, execute

Mode = Literal["pass", "untouched", "extra", "committed-extra", "instructions", "bad-answer"]
EDITS: dict[CaseId, dict[str, str]] = {
    "clear-task": {"receipt.py": "def total(items):\n    return sum(p * q for p, q in items)\n"},
    "known-preflight": {
        "config.py": "TIMEOUT_SECONDS = 30\n",
        "client.py": (
            "FALLBACK_TIMEOUT = 30\n\n"
            "def timeout(value=None):\n"
            "    if value is None:\n        return FALLBACK_TIMEOUT\n"
            "    if value <= 0:\n        raise ValueError('timeout must be positive')\n"
            "    return value\n"
        ),
    },
    "small-decision": {},
    "decision-review": {},
}
ANSWERS: dict[CaseId, str] = {
    "clear-task": "Fixed quantity handling.",
    "known-preflight": "Updated both defaults to 30.",
    "small-decision": '{"choice":"B","reason":"Identical service costs less."}',
    "decision-review": (
        '{"decision_was_supported":true,"change_rule":false,'
        '"reason":"One loss does not change known odds."}'
    ),
}


def echo_model(
    messages: list[ChatMessage],
    tools: list[ToolInfo],
    tool_choice: ToolChoice,
    config: GenerateConfig,
) -> ModelOutput:
    return ModelOutput.from_content("mockllm/model", messages[-1].text)


async def apply_solution(state: TaskState) -> None:
    case = state_case(state.metadata)
    for name, contents in EDITS[case.id].items():
        await sandbox().write_file(f"workspace/{name}", contents)


async def mutate(state: TaskState, mode: Mode) -> None:
    if mode in ("extra", "committed-extra"):
        await sandbox().write_file("workspace/unrequested.txt", "Extra change")
    if mode == "committed-extra":
        await execute(["git", "add", "--all"])
        await execute(["git", *GIT_IDENTITY, "commit", "-q", "-m", "Agent commit"])
    if mode == "instructions":
        await sandbox().write_file("instructions/skills/reasoning/SKILL.md", "Corrupted")


@dataclass
class Scripted:
    mode: Mode

    async def __call__(self, state: TaskState, generate: Generate) -> TaskState:
        if self.mode != "untouched":
            await apply_solution(state)
        await mutate(state, self.mode)
        answer = (
            "invalid JSON" if self.mode == "bad-answer" else ANSWERS[state_case(state.metadata).id]
        )
        state.messages.append(ChatMessageUser(content=answer))
        return await generate(state)


@solver
def scripted(mode: Mode = "pass") -> Solver:
    return Scripted(mode)
