"""Prepare explicit evaluation requests and execute them with Inspect."""

from functools import partial
from typing import Any, override

from inspect_ai import Task, eval_async
from inspect_ai.log import EvalLog, EvalSample
from inspect_ai.model import GenerateConfig, get_model, modelapi
from inspect_ai.model._providers.hf_inference_providers import HFInferenceProvidersAPI

import evals.python.integrations.inspect.profiles as profile_adapter
import evals.python.integrations.inspect.remote  # noqa: F401 - register the HF sandbox
import evals.python.integrations.inspect.tasks as task_adapter
from evals.python import commands, query


@modelapi(name="genius-hf")
class HfChatAPI(HFInferenceProvidersAPI):
    @override
    def completion_params(self, config: GenerateConfig, tools: bool) -> dict[str, Any]:
        params = super().completion_params(config, tools)
        if body := params.get("extra_body"):
            body.pop("prompt_cache_key", None)
        return params


def crashed(sample: EvalSample) -> bool:
    scores = sample.scores or {}
    return any((score.metadata or {}).get("agent_failure") for score in scores.values())


# A scored crash still counts as success, so name crashes apart from clean zeros.
def crash_summary(log: EvalLog) -> str:
    samples = log.samples or []
    crashes = sum(crashed(sample) for sample in samples)
    return f"{log.eval.task}: {crashes} of {len(samples)} samples had an agent crash"


def selected_samples(task: Task, *, request: commands.EvaluationSettings) -> list[str] | None:
    selected = request.sample_ids
    if selected is None:
        return None
    if request.limit is not None:
        raise ValueError("Choose EVAL_SAMPLE_IDS or EVAL_LIMIT, not both")
    available = {str(sample.id) for sample in task.dataset}
    if unknown := set(selected) - available:
        raise ValueError(f"Unknown sample IDs: {sorted(unknown)}")
    return list(selected)


def evaluation_tasks(
    spec: commands.Experiment, *, request: commands.EvaluationSettings
) -> list[Task]:
    catalog = query.LoadDataset(selection=request.dataset)
    instructions = profile_adapter.load_instructions(spec)
    provenance = query.Provenance(selection=catalog)
    build = partial(
        task_adapter.build_task,
        spec=spec,
        catalog=catalog,
        instructions=instructions,
        provenance=provenance,
        agent=request.agent,
        version=request.version,
        dataset=request.dataset,
        sandbox=request.sandbox,
        instruction_root=request.instruction_root,
    )
    if request.deliveries:
        return diagnostic_tasks(spec, request=request, build=build)
    return [
        build(profile=profile, instruction_delivery=request.instruction_delivery)
        for profile in spec.profiles
    ]


def diagnostic_tasks(
    spec: commands.Experiment, *, request: commands.EvaluationSettings, build: partial[Task]
) -> list[Task]:
    modes = request.deliveries or ()
    single = spec.model_copy(update={"epochs": 1})
    profile = profile_adapter.load_profile("genius", spec=spec)
    return [
        build(
            profile=profile,
            spec=single,
            instruction_delivery=mode,
            task_name=f"genius-{mode}-r{epoch}",
            diagnostic_epoch=epoch,
        )
        for epoch in range(1, spec.epochs + 1)
        for mode in (modes if epoch % 2 else tuple(reversed(modes)))
    ]


async def evaluate_async(request: commands.EvaluationSettings) -> int:
    spec = query.ExperimentSettings(epochs=request.epochs, token_limit=request.token_limit)
    tasks = evaluation_tasks(spec, request=request)
    selected = selected_samples(tasks[0], request=request)
    if request.model.startswith("hf-inference-providers/"):
        model = get_model(
            request.model.replace("hf-inference-providers/", "genius-hf/", 1),
            strict_tools=False,
        )
    else:
        model = get_model(request.model)
    logs = await eval_async(
        tasks,
        model=model,
        epochs=1 if request.deliveries else spec.epochs,
        sandbox=request.sandbox,
        max_samples=1,
        max_tasks=1,
        sample_id=selected,
        limit=request.limit,
        log_dir=request.log_dir,
    )
    for log in logs:
        print(f"{log.eval.task}: {log.status} ({log.location})", flush=True)
        print(crash_summary(log), flush=True)
    return int(any(log.status != "success" for log in logs))
