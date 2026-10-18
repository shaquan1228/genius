import asyncio
import json
import os
from collections.abc import Mapping

from evals.python import evaluation
from evals.python.evaluation import EvaluationSettings


def optional_int(value: str | None) -> int | None:
    return int(value) if value else None


def optional_float(value: str | None) -> float | None:
    return float(value) if value else None


def optional_cost(value: str | None) -> object:
    return json.loads(value) if value else None


def optional_json(value: str | None) -> tuple[object, ...] | None:
    if not value:
        return None
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise ValueError("Selection must be a JSON list")
    return tuple(parsed)


def configuration(environment: Mapping[str, str]) -> EvaluationSettings:
    return EvaluationSettings.model_validate_json(
        json.dumps(
            {
                "model": environment["EVAL_MODEL"],
                "run_id": environment.get("EVAL_RUN_ID") or None,
                "agent": environment.get("EVAL_AGENT")
                or ("claude" if environment["EVAL_MODEL"].startswith("anthropic/") else "codex"),
                "version": environment.get("EVAL_VERSION", ""),
                "variant": optional_cost(environment.get("EVAL_VARIANT")),
                "dataset": environment.get("EVAL_DATASET", "smoke"),
                "sandbox": "hf",
                "sandbox_image": environment.get("EVAL_SANDBOX_IMAGE", ""),
                "instruction_root": "/eval/instructions",
                "epochs": optional_int(environment.get("EVAL_EPOCHS")),
                "cost_limit": optional_float(environment.get("EVAL_COST_LIMIT")),
                "time_limit": optional_int(environment.get("EVAL_TIME_LIMIT")),
                "message_limit": optional_int(environment.get("EVAL_MESSAGE_LIMIT")),
                "cache": optional_cost(environment.get("EVAL_CACHE")),
                "model_cost": optional_cost(environment.get("EVAL_MODEL_COST")),
                "max_samples": int(environment.get("EVAL_MAX_SAMPLES") or "1"),
                "limit": optional_int(environment.get("EVAL_LIMIT")),
                "sample_ids": optional_json(environment.get("EVAL_SAMPLE_IDS")),
                "instruction_delivery": environment.get("EVAL_INSTRUCTION_DELIVERY", "files"),
                "deliveries": optional_json(environment.get("EVAL_DELIVERIES")),
                "log_dir": environment.get("EVAL_LOG_DIR", "/results/live"),
            }
        )
    )


def run() -> int:
    return asyncio.run(evaluation.evaluate(configuration(os.environ)))


if __name__ == "__main__":
    raise SystemExit(run())
