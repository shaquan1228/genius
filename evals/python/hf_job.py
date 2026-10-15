"""Run paired evaluations inside a Hugging Face Job."""

import os

from inspect_ai import eval

from evals.python.tasks import baseline, genius


def run() -> int:
    agent = os.environ.get("EVAL_AGENT", "claude")
    version = os.environ.get("EVAL_VERSION", "")
    logs = eval(
        [baseline(agent=agent, version=version), genius(agent=agent, version=version)],
        model=os.environ["EVAL_MODEL"],
        epochs=int(os.environ.get("EVAL_EPOCHS", "5")),
        sandbox="hf",
        max_samples=1,
        log_dir=os.environ.get("EVAL_LOG_DIR", "/results/live"),
    )
    for log in logs:
        print(f"{log.eval.task}: {log.status} ({log.location})", flush=True)
    return int(any(log.status != "success" for log in logs))
