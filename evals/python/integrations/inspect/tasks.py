"""Registered Inspect tasks: identical agents and limits, different instructions."""

from inspect_ai import Task, task
from inspect_ai.model import GenerateConfig
from pydantic import BaseModel, ConfigDict

from evals.python.contracts import Experiment
from evals.python.integrations.datasets.catalog import (
    benchmark_metadata,
    cases_hash,
    experiment,
    sources,
)
from evals.python.integrations.inspect.agents import DEFAULT_VERSIONS, AgentKind, contained_agent
from evals.python.integrations.inspect.profiles import content_hash, load_profile
from evals.python.integrations.inspect.scoring import evaluation
from evals.python.integrations.inspect.workspace import prepare
from evals.python.transport import fingerprint


class TaskRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    profile: str
    agent: AgentKind
    version: str = ""
    dataset: str = "smoke"
    sandbox: str = "local"
    experiment: Experiment | None = None


def build_task(*, request: TaskRequest) -> Task:
    spec = request.experiment or experiment()
    profile = load_profile(name=request.profile, spec=spec)
    agent, version, dataset = request.agent, request.version, request.dataset
    agent_version = version or DEFAULT_VERSIONS[agent]
    return Task(
        name=profile.name,
        dataset=profile.samples(dataset=dataset),
        setup=prepare(),
        solver=contained_agent(agent, version=agent_version),
        scorer=evaluation(),
        sandbox=request.sandbox,
        config=GenerateConfig(cache=spec.cache),
        epochs=spec.epochs,
        message_limit=spec.message_limit,
        token_limit=spec.token_limit,
        time_limit=spec.time_limit,
        metadata={
            "profile": profile.name,
            "dataset": str(dataset),
            "benchmark": benchmark_metadata(dataset=dataset),
            "agent": agent,
            "agent_version": agent_version,
            "instructions_sha256": content_hash(
                files=load_profile(name="genius", spec=spec).instruction_files()
            ),
            "fixtures_sha256": fingerprint(sources(dataset)),
            "cases_sha256": cases_hash(dataset=dataset),
        },
    )


@task
def baseline(*, agent: AgentKind = "claude", version: str = "", dataset: str = "smoke") -> Task:
    return build_task(
        request=TaskRequest(profile="baseline", agent=agent, version=version, dataset=dataset)
    )


@task
def genius(*, agent: AgentKind = "claude", version: str = "", dataset: str = "smoke") -> Task:
    return build_task(
        request=TaskRequest(profile="genius", agent=agent, version=version, dataset=dataset)
    )
