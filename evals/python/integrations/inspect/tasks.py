import json
from collections.abc import Mapping
from hashlib import sha256

from inspect_ai import Task, task
from inspect_ai.model import GenerateConfig

import evals.python.integrations.inspect.agents as agent_adapter
import evals.python.integrations.inspect.profiles as profile_adapter
import evals.python.integrations.inspect.results as results_adapter
import evals.python.integrations.inspect.scoring as scoring_adapter
import evals.python.integrations.inspect.workspace as workspace_adapter
from evals.python import datasets, evaluation
from evals.python.datasets import Dataset
from evals.python.evaluation import Experiment, InstructionDelivery, Profile


def build_task(  # noqa: PLR0913 - canonical values and native Inspect options
    *,
    profile: Profile,
    spec: Experiment,
    catalog: Dataset,
    documents: Mapping[str, bytes],
    agent: str,
    version: str = "",
    dataset: str = "smoke",
    sandbox: str = "local",
    instruction_delivery: InstructionDelivery = "files",
    instruction_root: str = "../instructions",
    task_name: str | None = None,
    diagnostic_epoch: int | None = None,
    harness_sha256: str | None = None,
    sandbox_image: str | None = None,
) -> Task:
    agent_version = version or agent_adapter.AGENT_REGISTRY[agent].default_version
    return Task(
        name=task_name or profile.name,
        dataset=profile_adapter.samples(
            profile,
            cases=tuple(catalog.cases.values()),
            documents=documents,
            dataset=dataset,
            delivery=instruction_delivery,
            instruction_root=instruction_root,
            sandbox_image=sandbox_image,
        ),
        setup=workspace_adapter.prepare(),
        solver=agent_adapter.contained_agent(agent, version=agent_version),
        scorer=scoring_adapter.bound_evaluation(dataset=catalog),
        sandbox=sandbox,
        config=GenerateConfig(cache=spec.cache),
        epochs=spec.epochs,
        message_limit=spec.message_limit,
        cost_limit=spec.cost_limit,
        time_limit=spec.time_limit,
        metadata={
            "diagnostic_epoch": diagnostic_epoch,
            "profile": profile.name,
            "harness_sha256": harness_sha256 or results_adapter.harness_hash(),
            "dataset": dataset,
            "benchmark": catalog.info.model_dump() if catalog.info else {},
            "agent": agent,
            "agent_version": agent_version,
            "agent_options_sha256": sha256(
                json.dumps(agent_adapter.AGENT_REGISTRY[agent].options, sort_keys=True).encode()
            ).hexdigest(),
            "agent_system_prompt_sha256": sha256(
                agent_adapter.AGENT_REGISTRY[agent].system_prompt.encode()
            ).hexdigest(),
            "instruction_delivery": instruction_delivery,
            "preamble_sha256": sha256(profile.preamble.encode()).hexdigest(),
            "instructions_sha256": profile_adapter.content_hash(
                files=profile_adapter.document_files(
                    profile,
                    documents=documents,
                )
            ),
            "fixtures_sha256": catalog.source_hash,
            "cases_sha256": catalog.cases_hash,
        },
    )


def _task(profile: str, *, agent: str, version: str, dataset: str) -> Task:
    spec = evaluation.resolve_settings()
    catalog = datasets.load_dataset(selection=dataset)
    return build_task(
        profile=profile_adapter.load_profile(profile, spec=spec),
        spec=spec,
        catalog=catalog,
        documents=profile_adapter.load_documents(spec),
        agent=agent,
        version=version,
        dataset=dataset,
    )


@task
def baseline(*, agent: str = "claude", version: str = "", dataset: str = "smoke") -> Task:
    return _task("baseline", agent=agent, version=version, dataset=dataset)


@task
def genius(*, agent: str = "claude", version: str = "", dataset: str = "smoke") -> Task:
    return _task("genius", agent=agent, version=version, dataset=dataset)
