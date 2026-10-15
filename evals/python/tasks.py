"""Registered Inspect tasks: identical agents and limits, different instructions."""

import hashlib

from inspect_ai import Task, task
from inspect_ai.model import GenerateConfig
from pydantic import BaseModel, ConfigDict

import evals.python.hf_sandbox  # noqa: F401 - registers the Hugging Face Sandbox provider
from evals.python.agents import DEFAULT_VERSIONS, AgentKind, coding_agent
from evals.python.profiles import BASELINE, GENIUS, Profile, content_hash
from evals.python.scoring import correctness, scope
from evals.python.transport import (
    EXPORTER,
    LIBRARY,
    RUNNER,
    Dataset,
    benchmark_metadata,
    load_cases,
)
from evals.python.workspace import prepare


class TaskRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    profile: Profile
    agent: AgentKind
    version: str = ""
    dataset: Dataset = "smoke"


def build_task(*, request: TaskRequest) -> Task:
    profile, agent, version, dataset = (
        request.profile,
        request.agent,
        request.version,
        request.dataset,
    )
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
            "benchmark": benchmark_metadata(dataset=dataset),
            "agent": agent,
            "agent_version": agent_version,
            "instructions_sha256": content_hash(files=GENIUS.instruction_files()),
            "fixtures_sha256": content_hash(
                files={path.name: str(path) for path in (*LIBRARY, EXPORTER, RUNNER)}
            ),
            "cases_sha256": cases_hash(dataset=dataset),
        },
    )


def cases_hash(dataset: Dataset) -> str:
    return hashlib.sha256(
        "".join(case.model_dump_json() for case in load_cases(selection=dataset)).encode()
    ).hexdigest()


@task
def baseline(*, agent: AgentKind = "claude", version: str = "", dataset: Dataset = "smoke") -> Task:
    return build_task(
        request=TaskRequest(profile=BASELINE, agent=agent, version=version, dataset=dataset)
    )


@task
def genius(*, agent: AgentKind = "claude", version: str = "", dataset: Dataset = "smoke") -> Task:
    return build_task(
        request=TaskRequest(profile=GENIUS, agent=agent, version=version, dataset=dataset)
    )
