"""Registered Inspect tasks built directly from canonical experiment values."""

from inspect_ai import Task, task
from inspect_ai.model import GenerateConfig

import evals.python.integrations.inspect.agents as agent_adapter
import evals.python.integrations.inspect.profiles as profile_adapter
import evals.python.integrations.inspect.scoring as scoring_adapter
import evals.python.integrations.inspect.workspace as workspace_adapter
from evals.python import commands


def build_task(  # noqa: PLR0913 - canonical values and native Inspect options
    *,
    profile: commands.ProfileSpec,
    spec: commands.Experiment,
    agent: str,
    version: str = "",
    dataset: str = "smoke",
    sandbox: str = "local",
    instruction_delivery: commands.InstructionDelivery = "files",
    instruction_root: str = "../instructions",
    task_name: str | None = None,
    diagnostic_epoch: int | None = None,
) -> Task:
    agent_version = version or agent_adapter.AGENT_REGISTRY[agent].default_version
    provenance = commands.query(commands.Provenance(selection=dataset))
    return Task(
        name=task_name or profile.name,
        dataset=profile_adapter.samples(
            profile,
            cases=commands.query(commands.Cases(selection=dataset)),
            dataset=dataset,
            delivery=instruction_delivery,
            instruction_root=instruction_root,
        ),
        setup=workspace_adapter.prepare(),
        solver=agent_adapter.contained_agent(agent, version=agent_version),
        scorer=scoring_adapter.evaluation(),
        sandbox=sandbox,
        config=GenerateConfig(cache=spec.cache),
        epochs=spec.epochs,
        message_limit=spec.message_limit,
        token_limit=spec.token_limit,
        time_limit=spec.time_limit,
        metadata={
            **({"diagnostic_epoch": diagnostic_epoch} if diagnostic_epoch else {}),
            "profile": profile.name,
            "dataset": dataset,
            "benchmark": provenance.info.model_dump() if provenance.info else {},
            "agent": agent,
            "agent_version": agent_version,
            "instruction_delivery": instruction_delivery,
            "instructions_sha256": profile_adapter.content_hash(
                files=profile_adapter.instruction_files(
                    profile_adapter.load_profile(name="genius", spec=spec)
                )
            ),
            "fixtures_sha256": provenance.source_hash,
            "cases_sha256": provenance.cases_hash,
        },
    )


@task
def baseline(*, agent: str = "claude", version: str = "", dataset: str = "smoke") -> Task:
    spec = commands.query(commands.ExperimentSettings())
    return build_task(
        profile=profile_adapter.load_profile("baseline", spec=spec),
        spec=spec,
        agent=agent,
        version=version,
        dataset=dataset,
    )


@task
def genius(*, agent: str = "claude", version: str = "", dataset: str = "smoke") -> Task:
    spec = commands.query(commands.ExperimentSettings())
    return build_task(
        profile=profile_adapter.load_profile("genius", spec=spec),
        spec=spec,
        agent=agent,
        version=version,
        dataset=dataset,
    )
