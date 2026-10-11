"""Select maintained Inspect SWE integrations without a custom CLI adapter."""

from typing import Literal

from inspect_ai.agent import Agent
from inspect_swe import claude_code, codex_cli

AgentKind = Literal["claude", "codex"]
DEFAULT_VERSIONS: dict[AgentKind, str] = {"claude": "2.1.278", "codex": "0.137.0"}


def coding_agent(kind: AgentKind, version: str) -> Agent:
    if kind == "claude":
        return claude_code(
            cwd="workspace",
            version=version,
            attempts=1,
            effort="medium",
            disallowed_tools=["WebSearch", "WebFetch"],
            retry_refusals=0,
            retry_uncaught_errors=0,
        )
    return codex_cli(
        cwd="workspace",
        version=version,
        attempts=1,
        web_search="disabled",
        network_access=False,
        retry_refusals=0,
        config_overrides={"model_reasoning_effort": '"medium"'},
    )
