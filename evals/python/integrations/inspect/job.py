"""Run Inspect evaluations; hosting and remote execution use command boundaries."""

import os
from typing import Any, override

from inspect_ai import Task, eval
from inspect_ai.log import EvalLog, EvalSample
from inspect_ai.model import GenerateConfig, get_model, modelapi
from inspect_ai.model._providers.hf_inference_providers import HFInferenceProvidersAPI
from pydantic import TypeAdapter

import evals.python.integrations.inspect.remote  # noqa: F401 - register the command-backed sandbox
from evals.python.contracts import Experiment, RunOverrides
from evals.python.integrations.inspect.kernel import experiment
from evals.python.integrations.inspect.profiles import InstructionDelivery
from evals.python.integrations.inspect.tasks import TaskRequest, build_task


@modelapi(name="genius-hf")
class HfChatAPI(HFInferenceProvidersAPI):
    @override
    def completion_params(self, config: GenerateConfig, tools: bool) -> dict[str, Any]:
        params = super().completion_params(config, tools)
        if body := params.get("extra_body"):
            body.pop("prompt_cache_key", None)
        return params


def sample_limit() -> int | None:
    value = os.environ.get("EVAL_LIMIT")
    if not value:
        return None
    limit = int(value)
    if limit < 1:
        raise ValueError("EVAL_LIMIT must be positive")
    return limit


def crashed(sample: EvalSample) -> bool:
    scores = sample.scores or {}
    return any((score.metadata or {}).get("agent_failure") for score in scores.values())


# A scored crash still counts as success, so name crashes apart from clean zeros.
def crash_summary(log: EvalLog) -> str:
    samples = log.samples or []
    crashes = sum(crashed(sample) for sample in samples)
    return f"{log.eval.task}: {crashes} of {len(samples)} samples had an agent crash"


def run_specification() -> Experiment:
    value = os.environ.get("EVAL_EPOCHS")
    tokens = os.environ.get("EVAL_TOKEN_LIMIT")
    return experiment(
        RunOverrides(
            epochs=int(value) if value else None,
            token_limit=int(tokens) if tokens else None,
        )
    )


def sample_ids() -> list[str] | None:
    value = os.environ.get("EVAL_SAMPLE_IDS")
    if not value:
        return None
    ids = TypeAdapter(list[str]).validate_json(value, strict=True)
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("EVAL_SAMPLE_IDS must contain unique case IDs")
    return ids


def selected_samples(task: Task) -> list[str] | None:
    selected = sample_ids()
    if selected:
        if sample_limit() is not None:
            raise ValueError("Choose EVAL_SAMPLE_IDS or EVAL_LIMIT, not both")
        available = {str(sample.id) for sample in task.dataset}
        if unknown := set(selected) - available:
            raise ValueError(f"Unknown sample IDs: {sorted(unknown)}")
    return selected


def job_tasks(spec: Experiment) -> list[Task]:
    deliveries = os.environ.get("EVAL_DELIVERIES")
    if deliveries:
        modes = TypeAdapter(list[InstructionDelivery]).validate_json(deliveries, strict=True)
        if len(modes) < 2 or len(set(modes)) != len(modes):
            raise ValueError("EVAL_DELIVERIES requires at least two unique delivery modes")
        return diagnostic_tasks(spec, modes=modes)
    mode = TypeAdapter(InstructionDelivery).validate_python(
        os.environ.get("EVAL_INSTRUCTION_DELIVERY", "files")
    )
    return [make_task(spec, profile=profile.name, delivery=mode) for profile in spec.profiles]


def make_task(
    spec: Experiment, *, profile: str, delivery: InstructionDelivery, task_name: str | None = None
) -> Task:
    return build_task(
        request=TaskRequest(
            profile=profile,
            agent=os.environ.get("EVAL_AGENT", "claude"),
            version=os.environ.get("EVAL_VERSION", ""),
            dataset=os.environ.get("EVAL_DATASET", "smoke"),
            sandbox="hf",
            experiment=spec,
            instruction_delivery=delivery,
            instruction_root="/eval/instructions",
            task_name=task_name,
        )
    )


def diagnostic_tasks(spec: Experiment, *, modes: list[InstructionDelivery]) -> list[Task]:
    tasks = []
    single = spec.model_copy(update={"epochs": 1})
    for epoch in range(1, spec.epochs + 1):
        for mode in modes if epoch % 2 else list(reversed(modes)):
            task = make_task(
                single, profile="genius", delivery=mode, task_name=f"genius-{mode}-r{epoch}"
            )
            assert task.metadata is not None
            task.metadata["diagnostic_epoch"] = epoch
            tasks.append(task)
    return tasks


def run() -> int:
    model_name = os.environ["EVAL_MODEL"]
    if model_name.startswith("hf-inference-providers/"):
        model = get_model(
            model_name.replace("hf-inference-providers/", "genius-hf/", 1),
            strict_tools=False,
        )
    else:
        model = get_model(model_name)
    spec = run_specification()
    tasks = job_tasks(spec)
    selected = selected_samples(tasks[0])
    logs = eval(
        tasks,
        model=model,
        epochs=1 if os.environ.get("EVAL_DELIVERIES") else spec.epochs,
        sandbox="hf",
        max_samples=1,
        max_tasks=1,
        sample_id=selected,
        limit=sample_limit(),
        log_dir=os.environ.get("EVAL_LOG_DIR", "/results/live"),
    )
    for log in logs:
        print(f"{log.eval.task}: {log.status} ({log.location})", flush=True)
        print(crash_summary(log), flush=True)
    return int(any(log.status != "success" for log in logs))


if __name__ == "__main__":
    raise SystemExit(run())
