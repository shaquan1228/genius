"""Select maintained Inspect SWE integrations without a custom CLI adapter."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from inspect_ai.agent import Agent, as_solver
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_swe import claude_code, codex_cli

AgentKind = str
# Long CLI output keeps the exit code at the start and the provider error at the end.
FAILURE_HEAD, FAILURE_TAIL = 200, 1800


@dataclass(frozen=True)
class AgentSpec:
    default_version: str
    factory: Callable[[], Callable[..., Agent]]
    options: dict[str, Any]
    # Inspect SWE starts the RuntimeError for a failed agent process with this text.
    failure_prefix: str
    system_prompt: str = ""


AGENT_REGISTRY: dict[AgentKind, AgentSpec] = {
    "claude": AgentSpec(
        default_version="2.1.278",
        factory=lambda: claude_code,
        options={
            "effort": "medium",
            "disallowed_tools": ["WebSearch", "WebFetch"],
            "retry_refusals": 0,
            "retry_uncaught_errors": 0,
        },
        failure_prefix="Error executing claude code agent",
    ),
    "codex": AgentSpec(
        default_version="0.137.0",
        factory=lambda: codex_cli,
        options={
            "web_search": "disabled",
            "home_dir": "/root/genius-codex",
            "network_access": False,
            "retry_refusals": 0,
            "config_overrides": {
                "model_reasoning_effort": '"medium"',
                "allow_login_shell": "false",
            },
        },
        failure_prefix="Error executing codex cli agent",
        system_prompt=(
            "Use only tools registered for this session. "
            "If apply_patch is not registered, edit files through exec_command with cmd "
            "as a shell command string, not an argv array. "
            "Do not call an unregistered apply_patch tool."
        ),
    ),
}
DEFAULT_VERSIONS: dict[AgentKind, str] = {
    kind: spec.default_version for kind, spec in AGENT_REGISTRY.items()
}


def coding_agent(kind: AgentKind, *, version: str) -> Agent:
    spec = AGENT_REGISTRY[kind]
    options = spec.options | ({"system_prompt": spec.system_prompt} if spec.system_prompt else {})
    return spec.factory()(
        cwd="workspace",
        version=version,
        attempts=1,
        **options,
    )


def truncated(message: str) -> str:
    if len(message) <= FAILURE_HEAD + FAILURE_TAIL:
        return message
    return f"{message[:FAILURE_HEAD]}\n[...]\n{message[-FAILURE_TAIL:]}"


@solver
def contained_agent(kind: AgentKind, *, version: str) -> Solver:
    """Record a crashed agent process so its sample is still scored and the task continues."""
    run_agent = as_solver(coding_agent(kind, version=version))
    prefix = AGENT_REGISTRY[kind].failure_prefix

    async def solve(state: TaskState, generate: Generate) -> TaskState:  # noqa: PLR0917 - Inspect calls solvers positionally
        try:
            return await run_agent(state, generate)
        except RuntimeError as error:
            if not str(error).startswith(prefix):
                raise
            state.metadata["agent_failure"] = truncated(str(error))
            return state

    return solve
