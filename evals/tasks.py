"""Registered Inspect tasks: identical agents and limits, different instructions."""

from inspect_ai import Task, task
from inspect_ai.model import GenerateConfig

from evals.agents import DEFAULT_VERSIONS, AgentKind, coding_agent
from evals.cases import EVALS_ROOT, OCAML_SOURCES, Profile
from evals.profiles import content_hash, instruction_files, samples
from evals.scoring import correctness, scope
from evals.workspace import prepare


def build_task(profile: Profile, *, agent: AgentKind, version: str) -> Task:
    agent_version = version or DEFAULT_VERSIONS[agent]
    return Task(
        name=profile,
        dataset=samples(profile),
        setup=prepare(),
        solver=coding_agent(agent, agent_version),
        scorer=[correctness(), scope()],
        sandbox=("docker", str(EVALS_ROOT / "Dockerfile")),
        config=GenerateConfig(cache=False),
        epochs=5,
        message_limit=40,
        token_limit=50_000,
        time_limit=300,
        metadata={
            "profile": profile,
            "agent": agent,
            "agent_version": agent_version,
            "instructions_sha256": content_hash(instruction_files()),
            "fixtures_sha256": content_hash(
                {
                    name: str(EVALS_ROOT / name)
                    for name in (*OCAML_SOURCES, "check.sh")
                    if name != "suite.ml"
                }
            ),
            "cases_sha256": content_hash({"suite.ml": str(EVALS_ROOT / "suite.ml")}),
        },
    )


@task
def baseline(agent: AgentKind = "claude", version: str = "") -> Task:
    return build_task("baseline", agent=agent, version=version)


@task
def genius(agent: AgentKind = "claude", version: str = "") -> Task:
    return build_task("genius", agent=agent, version=version)
