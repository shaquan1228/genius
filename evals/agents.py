"""Select maintained Inspect SWE integrations without a custom CLI adapter."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from inspect_ai.agent import Agent
from inspect_swe import claude_code, codex_cli

AgentKind = str


@dataclass(frozen=True)
class AgentSpec:
    default_version: str
    factory: Callable[[], Callable[..., Agent]]
    options: dict[str, Any]


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
    ),
    "codex": AgentSpec(
        default_version="0.137.0",
        factory=lambda: codex_cli,
        options={
            "web_search": "disabled",
            "network_access": False,
            "retry_refusals": 0,
            "config_overrides": {"model_reasoning_effort": '"medium"'},
        },
    ),
}
DEFAULT_VERSIONS: dict[AgentKind, str] = {
    kind: spec.default_version for kind, spec in AGENT_REGISTRY.items()
}


def coding_agent(kind: AgentKind, version: str) -> Agent:
    spec = AGENT_REGISTRY[kind]
    return spec.factory()(
        cwd="workspace",
        version=version,
        attempts=1,
        **spec.options,
    )
