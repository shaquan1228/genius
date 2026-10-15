"""Registered Inspect tasks: identical agents and limits, different instructions."""

from inspect_ai import Task, task
from inspect_ai.model import GenerateConfig

import evals.python.hf_sandbox  # noqa: F401 - registers the Hugging Face Sandbox provider
from evals.python.agents import DEFAULT_VERSIONS, AgentKind, coding_agent
from evals.python.profiles import (
    BASELINE,
    GENIUS,
    Profile,
    content_hash,
    instruction_files,
    samples,
)
from evals.python.scoring import correctness, scope
from evals.python.transport import EXPORTER, LIBRARY, RUNNER, SUITE
from evals.python.workspace import prepare


def build_task(profile: Profile, *, agent: AgentKind, version: str) -> Task:
    agent_version = version or DEFAULT_VERSIONS[agent]
    return Task(
        name=profile.name,
        dataset=samples(profile),
        setup=prepare(),
        solver=coding_agent(agent, agent_version),
        scorer=[correctness(), scope()],
        sandbox="hf",
        config=GenerateConfig(cache=False),
        epochs=5,
        message_limit=40,
        token_limit=50_000,
        time_limit=300,
        metadata={
            "profile": profile.name,
            "agent": agent,
            "agent_version": agent_version,
            "instructions_sha256": content_hash(instruction_files()),
            "fixtures_sha256": content_hash(
                {path.name: str(path) for path in (*LIBRARY, EXPORTER, RUNNER)}
            ),
            "cases_sha256": content_hash({SUITE.name: str(SUITE)}),
        },
    )


@task
def baseline(agent: AgentKind = "claude", version: str = "") -> Task:
    return build_task(BASELINE, agent=agent, version=version)


@task
def genius(agent: AgentKind = "claude", version: str = "") -> Task:
    return build_task(GENIUS, agent=agent, version=version)
