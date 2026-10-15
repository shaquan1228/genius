"""Run scripted agents through Inspect for integration tests."""

import json
import shutil
from pathlib import Path

from inspect_ai import Task, eval
from inspect_ai.log import EvalLog, EvalSample
from inspect_ai.model import get_model

from evals.python.paths import EVALS_ROOT
from evals.python.tests.scenarios import Mode, echo_model, scripted


def offline_run(tasks: list[Task], mode: Mode, directory: Path, epochs: int = 1) -> list[EvalLog]:
    model = get_model("mockllm/model", custom_outputs=echo_model)
    logs = eval(
        tasks,
        model=model,
        solver=scripted(mode),
        sandbox="local",
        epochs=epochs,
        max_samples=1,
        log_dir=str(directory),
        display="none",
        log_format="json",
        ctl_server=False,
    )
    archive = EVALS_ROOT / "results/offline"
    archive.mkdir(parents=True, exist_ok=True)
    for log in logs:
        shutil.copy2(str(log.location), archive)
    return logs


def sample_result(sample: EvalSample) -> tuple[str, object, object]:
    assert sample.scores is not None
    return (str(sample.id), sample.scores["correctness"].value, sample.scores["scope"].value)


def results(log: EvalLog) -> list[tuple[str, object, object]]:
    return sorted(sample_result(sample) for sample in log.samples or [])


def ocaml_timeout_case(*, id_expression: str, initial: str, requested: str) -> str:
    return f"""Eval.case ~id:({id_expression})
  ~fixture:(Fixtures.Preflight.fixture ~timeout:({initial}))
  ~task:(Task.Preflight.change_timeout ~initial:({initial}) ~requested:({requested}))
  ~checks:(Check.Preflight.defaults ~timeout:({requested}))
  ~allowed_files:["config.ml"; "client.ml"]
  ~reference:(Reference.preflight ~timeout:({requested}))"""


def ocaml_choice_case(*, case_id: str, a: int, b: int) -> str:
    choice = "A" if a < b else "B"
    return f"""Eval.case ~id:{json.dumps(case_id)} ~fixture:Fixture.empty
  ~task:(Task.Decision.cheaper ~a:{a} ~b:{b})
  ~checks:(Check.choice {choice}) ~allowed_files:[]
  ~reference:(Reference.reply ~answer:(Choice {choice}) ~reason:"The cost is lower.")"""
