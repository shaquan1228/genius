"""Prepare explicit evaluation requests and execute them with Inspect."""

import asyncio
from contextlib import suppress
from functools import partial
from pathlib import Path
from typing import Any, override
from uuid import uuid4

from inspect_ai import Task, eval_async
from inspect_ai.log import EvalLog
from inspect_ai.model import GenerateConfig, Model, get_model, modelapi
from inspect_ai.model._providers.hf_inference_providers import HFInferenceProvidersAPI

import evals.python.integrations.inspect.completeness as completeness_adapter
import evals.python.integrations.inspect.pricing as pricing_adapter
import evals.python.integrations.inspect.profiles as profile_adapter
import evals.python.integrations.inspect.progress as progress_adapter
import evals.python.integrations.inspect.remote  # noqa: F401 - register the HF sandbox
import evals.python.integrations.inspect.results as results_adapter
import evals.python.integrations.inspect.tasks as task_adapter
from evals.python import datasets, evaluation
from evals.python.evaluation import EvaluationSettings, Experiment, ModelPricing


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


def selected_samples(task: Task, *, request: EvaluationSettings) -> list[str] | None:
    selected = request.sample_ids
    if selected is None:
        return None
    if request.limit is not None:
        raise ValueError("Choose EVAL_SAMPLE_IDS or EVAL_LIMIT, not both")
    available = {str(sample.id) for sample in task.dataset}
    if unknown := set(selected) - available:
        raise ValueError(f"Unknown sample IDs: {sorted(unknown)}")
    return list(selected)


def variant_experiment(spec: Experiment, *, request: EvaluationSettings) -> Experiment:
    if variant := request.variant:
        if request.deliveries:
            raise ValueError("Choose a variant or delivery diagnostics")
        spec = Experiment.model_validate({**dict(spec), "profiles": (variant,)})
    return spec


def evaluation_tasks(spec: Experiment, *, request: EvaluationSettings) -> list[Task]:
    spec = variant_experiment(spec, request=request)
    source_dir = request.variant.source_dir if request.variant else None
    catalog = datasets.load_dataset(selection=request.dataset)
    documents = (
        profile_adapter.load_documents(spec)
        if source_dir is None
        else profile_adapter.load_documents(spec, source_dir=source_dir)
    )
    build = partial(
        task_adapter.build_task,
        spec=spec,
        catalog=catalog,
        documents=documents,
        agent=request.agent,
        version=request.version,
        dataset=request.dataset,
        sandbox=request.sandbox,
        instruction_root=request.instruction_root,
        harness_sha256=results_adapter.harness_hash(),
        sandbox_image=request.sandbox_image,
    )
    if request.deliveries:
        return diagnostic_tasks(spec, request=request, build=build)
    return [
        build(profile=profile, instruction_delivery=request.instruction_delivery)
        for profile in spec.profiles
    ]


def diagnostic_tasks(
    spec: Experiment, *, request: EvaluationSettings, build: partial[Task]
) -> list[Task]:
    modes = request.deliveries or ()
    single = Experiment.model_validate({**dict(spec), "epochs": 1})
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


async def evaluate_async(request: EvaluationSettings) -> int:
    spec = evaluation.resolve_experiment(request)
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
    request = request.model_copy(update={"model_cost": ModelPricing.model_validate(pricing)})
    if request.variant is not None:
        request = results_adapter.record(tasks[0], request=request, spec=spec)
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
    request: EvaluationSettings,
    spec: Experiment,
    model: Model,
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
