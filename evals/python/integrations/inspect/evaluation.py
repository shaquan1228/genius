"""Prepare explicit evaluation requests and execute them with Inspect."""

import asyncio
from contextlib import suppress
from functools import partial
from pathlib import Path
from typing import Any, override
from uuid import uuid4

from inspect_ai import Task, eval_async
from inspect_ai.log import EvalLog
from inspect_ai.model import GenerateConfig, get_model, modelapi
from inspect_ai.model._providers.hf_inference_providers import HFInferenceProvidersAPI

import evals.python.integrations.inspect.completeness as completeness_adapter
import evals.python.integrations.inspect.pricing as pricing_adapter
import evals.python.integrations.inspect.profiles as profile_adapter
import evals.python.integrations.inspect.progress as progress_adapter
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


# A scored crash still counts as success, so name crashes apart from clean zeros.
def crash_summary(log: EvalLog) -> str:
    samples = log.samples or []
    crashes = sum(completeness_adapter.crashed(sample) for sample in samples)
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
    spec = query.ExperimentSettings(epochs=request.epochs, cost_limit=request.cost_limit)
    tasks = evaluation_tasks(spec, request=request)
    selected_samples(tasks[0], request=request)
    if request.model.startswith("hf-inference-providers/"):
        model = get_model(
            request.model.replace("hf-inference-providers/", "genius-hf/", 1),
            strict_tools=False,
            stream=False,
        )
    else:
        model = get_model(request.model)
    pricing = pricing_adapter.configure(model, request=request)
    state = progress_adapter.Progress(run=request.run_id or uuid4().hex)
    token = progress_adapter.current.set(state)
    heartbeat = asyncio.create_task(state.heartbeat())
    try:
        state.emit(
            "run_start",
            settings=request.model_dump(mode="json"),
            model_cost=pricing,
            cost_limit=spec.cost_limit,
        )
        return await execute(tasks, request=request, spec=spec, model=model, state=state)
    finally:
        try:
            heartbeat.cancel()
            try:
                with suppress(asyncio.CancelledError):
                    await heartbeat
            finally:
                state.finish()
        finally:
            progress_adapter.current.reset(token)


async def execute(
    tasks: list[Task],
    *,
    request: commands.EvaluationSettings,
    spec: commands.Experiment,
    model: Any,
    state: progress_adapter.Progress,
) -> int:
    epochs = 1 if request.deliveries else spec.epochs
    expected = completeness_adapter.expected_pairs(tasks, request=request, epochs=epochs)
    state.emit("expected", tuples=sorted(expected))
    logs = await eval_async(
        tasks,
        model=model,
        epochs=epochs,
        sandbox=request.sandbox,
        max_samples=1 if request.deliveries else request.max_samples,
        max_tasks=1,
        sample_id=selected_samples(tasks[0], request=request),
        limit=request.limit,
        log_dir=str(Path(request.log_dir) / state.run),
    )
    for log in logs:
        print(f"{log.eval.task}: {log.status} ({log.location})", flush=True)
        print(crash_summary(log), flush=True)
    summary = completeness_adapter.report(logs, expected=expected)
    summary["telemetry_errors"] = state.telemetry_errors
    summary["lifecycle_missing"] = len(expected) - state.completed
    state.emit("completeness", **summary)
    return int(completeness_adapter.failed(summary))
