import asyncio
import json
import os
from collections.abc import Mapping

from evals.python import commands


def optional_int(value: str | None) -> int | None:
    return int(value) if value else None


def optional_json(value: str | None) -> tuple[object, ...] | None:
    if not value:
        return None
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise ValueError("Selection must be a JSON list")
    return tuple(parsed)


def configuration(environment: Mapping[str, str]) -> commands.EvaluationSettings:
    return commands.EvaluationSettings.model_validate(
        {
            "model": environment["EVAL_MODEL"],
            "agent": environment.get("EVAL_AGENT", "claude"),
            "version": environment.get("EVAL_VERSION", ""),
            "dataset": environment.get("EVAL_DATASET", "smoke"),
            "sandbox": "hf",
            "instruction_root": "/eval/instructions",
            "epochs": optional_int(environment.get("EVAL_EPOCHS")),
            "token_limit": optional_int(environment.get("EVAL_TOKEN_LIMIT")),
            "limit": optional_int(environment.get("EVAL_LIMIT")),
            "sample_ids": optional_json(environment.get("EVAL_SAMPLE_IDS")),
            "instruction_delivery": environment.get("EVAL_INSTRUCTION_DELIVERY", "files"),
            "deliveries": optional_json(environment.get("EVAL_DELIVERIES")),
            "log_dir": environment.get("EVAL_LOG_DIR", "/results/live"),
        }
    )


def run() -> int:
    operation = configuration(dict(os.environ))
    return asyncio.run(commands.Evaluate(**operation.model_dump()))


if __name__ == "__main__":
    raise SystemExit(run())
