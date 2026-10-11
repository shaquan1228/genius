"""Registered Inspect tasks: identical agents and limits, different instructions."""

from inspect_ai import Task, task
from inspect_ai.model import GenerateConfig

from genius_evals.agents import DEFAULT_VERSIONS, AgentKind, coding_agent
from genius_evals.cases import EVALS_ROOT, Profile
from genius_evals.profiles import content_hash, directory_files, instruction_files, samples
from genius_evals.scoring import correctness, scope
from genius_evals.workspace import prepare


def build_task(profile: Profile, agent: AgentKind, version: str) -> Task:
    agent_version = version or DEFAULT_VERSIONS[agent]
    return Task(
        name=profile,
        dataset=samples(profile),
        setup=prepare(),
        solver=coding_agent(agent, agent_version),
        scorer=[correctness(), scope()],
        sandbox=("docker", str(EVALS_ROOT / "Dockerfile")),
        config=GenerateConfig(cache=False),
        epochs=3,
        message_limit=40,
        token_limit=50_000,
        time_limit=300,
        metadata={
            "profile": profile,
            "agent": agent,
            "agent_version": agent_version,
            "instructions_sha256": content_hash(instruction_files()),
            "fixtures_sha256": content_hash(directory_files(EVALS_ROOT / "fixtures", "fixtures")),
            "cases_sha256": content_hash({"cases.json": str(EVALS_ROOT / "cases.json")}),
        },
    )


@task
def baseline(agent: AgentKind = "claude", version: str = "") -> Task:
    return build_task("baseline", agent, version)


@task
def genius(agent: AgentKind = "claude", version: str = "") -> Task:
    return build_task("genius", agent, version)
