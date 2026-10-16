"""Prepare explicit evaluation requests and execute them with Inspect."""

from typing import Annotated, Any, override

from inspect_ai import Task, eval
from inspect_ai.log import EvalLog, EvalSample
from inspect_ai.model import GenerateConfig, get_model, modelapi
from inspect_ai.model._providers.hf_inference_providers import HFInferenceProvidersAPI
from pydantic import AfterValidator, BaseModel, Field

import evals.python.integrations.inspect.remote  # noqa: F401 - register the command-backed sandbox
from evals.python.contracts import FROZEN, Experiment, RunOverrides
from evals.python.integrations.inspect.agents import AgentKind
from evals.python.integrations.inspect.datasets import experiment
from evals.python.integrations.inspect.profiles import InstructionDelivery
from evals.python.integrations.inspect.tasks import TaskRequest, build_task


def unique[T](values: tuple[T, ...]) -> tuple[T, ...]:
    if len(set(values)) != len(values):
        raise ValueError("Selection must contain unique values")
    return values


SampleIds = Annotated[tuple[str, ...], Field(min_length=1), AfterValidator(unique)]
Deliveries = Annotated[tuple[InstructionDelivery, ...], Field(min_length=2), AfterValidator(unique)]


class EvaluationRequest(BaseModel):
    """Immutable launch configuration; Inspect does not read the Job environment."""

    model_config = FROZEN
    model: str
    agent: AgentKind = "claude"
    version: str = ""
    dataset: str = "smoke"
    sandbox: str = "local"
    instruction_root: str = "../instructions"
    epochs: int | None = None
    token_limit: int | None = None
    limit: int | None = Field(default=None, gt=0)
    sample_ids: SampleIds | None = None
    instruction_delivery: InstructionDelivery = "files"
    deliveries: Deliveries | None = None
    log_dir: str = "/results/live"


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


def selected_samples(task: Task, *, request: EvaluationRequest) -> list[str] | None:
    selected = request.sample_ids
    if selected is None:
        return None
    if request.limit is not None:
        raise ValueError("Choose EVAL_SAMPLE_IDS or EVAL_LIMIT, not both")
    available = {str(sample.id) for sample in task.dataset}
    if unknown := set(selected) - available:
        raise ValueError(f"Unknown sample IDs: {sorted(unknown)}")
    return list(selected)


def evaluation_tasks(spec: Experiment, *, request: EvaluationRequest) -> list[Task]:
    if request.deliveries:
        return diagnostic_tasks(spec, request=request)
    return [
        make_task(
            spec, request=request, profile=profile.name, delivery=request.instruction_delivery
        )
        for profile in spec.profiles
    ]


def make_task(
    spec: Experiment,
    *,
    request: EvaluationRequest,
    profile: str,
    delivery: InstructionDelivery,
    diagnostic_epoch: int | None = None,
) -> Task:
    return build_task(
        request=TaskRequest(
            profile=profile,
            agent=request.agent,
            version=request.version,
            dataset=request.dataset,
            sandbox=request.sandbox,
            experiment=spec,
            instruction_delivery=delivery,
            instruction_root=request.instruction_root,
            task_name=f"{profile}-{delivery}-r{diagnostic_epoch}" if diagnostic_epoch else None,
            diagnostic_epoch=diagnostic_epoch,
        )
    )


def diagnostic_tasks(spec: Experiment, *, request: EvaluationRequest) -> list[Task]:
    modes = request.deliveries or ()
    single = spec.model_copy(update={"epochs": 1})
    return [
        make_task(
            single,
            request=request,
            profile="genius",
            delivery=mode,
            diagnostic_epoch=epoch,
        )
        for epoch in range(1, spec.epochs + 1)
        for mode in (modes if epoch % 2 else tuple(reversed(modes)))
    ]


def evaluate(request: EvaluationRequest) -> int:
    spec = experiment(RunOverrides(epochs=request.epochs, token_limit=request.token_limit))
    tasks = evaluation_tasks(spec, request=request)
    selected = selected_samples(tasks[0], request=request)
    if request.model.startswith("hf-inference-providers/"):
        model = get_model(
            request.model.replace("hf-inference-providers/", "genius-hf/", 1),
            strict_tools=False,
        )
    else:
        model = get_model(request.model)
    logs = eval(
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
