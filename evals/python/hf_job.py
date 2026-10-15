"""Run paired evaluations inside a Hugging Face Job."""

import os
from typing import Any, override

from inspect_ai import eval
from inspect_ai.model import GenerateConfig, get_model, modelapi
from inspect_ai.model._providers.hf_inference_providers import HFInferenceProvidersAPI

from evals.python.tasks import baseline, genius


@modelapi(name="genius-hf")
class HfChatAPI(HFInferenceProvidersAPI):
    @override
    def completion_params(self, config: GenerateConfig, tools: bool) -> dict[str, Any]:
        params = super().completion_params(config, tools)
        if body := params.get("extra_body"):
            body.pop("prompt_cache_key", None)
        return params


def run() -> int:
    agent = os.environ.get("EVAL_AGENT", "claude")
    version = os.environ.get("EVAL_VERSION", "")
    model_name = os.environ["EVAL_MODEL"]
    if model_name.startswith("hf-inference-providers/"):
        model = get_model(
            model_name.replace("hf-inference-providers/", "genius-hf/", 1),
            strict_tools=False,
        )
    else:
        model = get_model(model_name)
    logs = eval(
        [baseline(agent=agent, version=version), genius(agent=agent, version=version)],
        model=model,
        epochs=int(os.environ.get("EVAL_EPOCHS", "5")),
        sandbox="hf",
        max_samples=1,
        log_dir=os.environ.get("EVAL_LOG_DIR", "/results/live"),
    )
    for log in logs:
        print(f"{log.eval.task}: {log.status} ({log.location})", flush=True)
    return int(any(log.status != "success" for log in logs))
