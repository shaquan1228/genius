"""Registered Inspect tasks: identical agents and limits, different instructions."""

import hashlib

from inspect_ai import Task, task
from inspect_ai.model import GenerateConfig

import evals.python.hf_sandbox  # noqa: F401 - registers the Hugging Face Sandbox provider
from evals.python.agents import DEFAULT_VERSIONS, AgentKind, coding_agent
from evals.python.profiles import BASELINE, GENIUS, Profile, content_hash
from evals.python.scoring import correctness, scope
from evals.python.transport import (
    EXPORTER,
    LIBRARY,
    RUNNER,
    Dataset,
    humaneval_info,
    load_cases,
)
from evals.python.workspace import prepare


def build_task(
    profile: Profile, *, agent: AgentKind, version: str, dataset: Dataset = "smoke"
) -> Task:
    agent_version = version or DEFAULT_VERSIONS[agent]
    return Task(
        name=profile.name,
        dataset=profile.samples(dataset=dataset),
        setup=prepare(),
        solver=coding_agent(agent, version=agent_version),
        scorer=[correctness(), scope()],
        sandbox="hf",
        config=GenerateConfig(cache=False),
        epochs=5,
        message_limit=40,
        token_limit=50_000,
        time_limit=300,
        metadata={
            "profile": profile.name,
            "dataset": dataset,
            "benchmark": humaneval_info().model_dump() if dataset == "humanevalplus" else {},
            "agent": agent,
            "agent_version": agent_version,
            "instructions_sha256": content_hash(GENIUS.instruction_files()),
            "fixtures_sha256": content_hash(
                {path.name: str(path) for path in (*LIBRARY, EXPORTER, RUNNER)}
            ),
            "cases_sha256": cases_hash(dataset),
        },
    )


def cases_hash(dataset: Dataset) -> str:
    return hashlib.sha256(
        "".join(case.model_dump_json() for case in load_cases(dataset=dataset)).encode()
    ).hexdigest()


@task
def baseline(*, agent: AgentKind = "claude", version: str = "", dataset: Dataset = "smoke") -> Task:
    return build_task(BASELINE, agent=agent, version=version, dataset=dataset)


@task
def genius(*, agent: AgentKind = "claude", version: str = "", dataset: Dataset = "smoke") -> Task:
    return build_task(GENIUS, agent=agent, version=version, dataset=dataset)
