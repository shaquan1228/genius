"""Run paired evaluations inside a Hugging Face Job."""

import os
from typing import Any, override

from inspect_ai import eval
from inspect_ai.log import EvalLog, EvalSample
from inspect_ai.model import GenerateConfig, get_model, modelapi
from inspect_ai.model._providers.hf_inference_providers import HFInferenceProvidersAPI

import evals.python.integrations.hugging_face.sandbox  # noqa: F401 - provider registration belongs to HF
from evals.python.contracts import Experiment, RunOverrides
from evals.python.integrations.datasets.catalog import experiment
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
    return experiment(RunOverrides(epochs=int(value) if value else None))


def run() -> int:
    agent = os.environ.get("EVAL_AGENT", "claude")
    version = os.environ.get("EVAL_VERSION", "")
    dataset = os.environ.get("EVAL_DATASET", "smoke")
    model_name = os.environ["EVAL_MODEL"]
    if model_name.startswith("hf-inference-providers/"):
        model = get_model(
            model_name.replace("hf-inference-providers/", "genius-hf/", 1),
            strict_tools=False,
        )
    else:
        model = get_model(model_name)
    spec = run_specification()
    logs = eval(
        [
            build_task(
                request=TaskRequest(
                    profile=profile.name,
                    agent=agent,
                    version=version,
                    dataset=dataset,
                    sandbox="hf",
                    experiment=spec,
                )
            )
            for profile in spec.profiles
        ],
        model=model,
        epochs=spec.epochs,
        sandbox="hf",
        max_samples=1,
        limit=sample_limit(),
        log_dir=os.environ.get("EVAL_LOG_DIR", "/results/live"),
    )
    for log in logs:
        print(f"{log.eval.task}: {log.status} ({log.location})", flush=True)
        print(crash_summary(log), flush=True)
    return int(any(log.status != "success" for log in logs))
