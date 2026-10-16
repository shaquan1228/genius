"""Run scripted agents through Inspect for integration tests."""

import json
import shutil
from pathlib import Path

from inspect_ai import Task, eval
from inspect_ai.log import EvalLog, EvalSample
from inspect_ai.model import get_model

from evals.python import catalog, transport
from evals.python._kernel import Case, ExecutableChecks, Reference
from evals.python.paths import EVALS_ROOT
from evals.python.tests.scenarios import Mode, echo_model, scripted


def offline_run(
    tasks: list[Task], *, mode: Mode | None, directory: Path, epochs: int = 1
) -> list[EvalLog]:
    """Mode None keeps each task's own agent solver."""
    model = get_model("mockllm/model", custom_outputs=echo_model)
    logs = eval(
        tasks,
        model=model,
        solver=None if mode is None else scripted(mode),
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
    value = sample.scores["evaluation"].value
    assert isinstance(value, dict)
    return (str(sample.id), value["correctness"], value["scope"])


def crash_evidence(sample: EvalSample) -> tuple[str, object, object]:
    assert sample.scores is not None
    score = sample.scores["evaluation"]
    assert score.metadata is not None
    headline = str(score.explanation).splitlines()[0]
    return (headline, score.metadata["agent_failure"], score.metadata["verification"]["status"])


def results(log: EvalLog) -> list[tuple[str, object, object]]:
    return sorted(sample_result(sample) for sample in log.samples or [])


def ocaml_timeout_case(*, id_expression: str, initial: str, requested: str) -> str:
    return f"""Case.make ~id:({id_expression})
  ~fixture:(Fixtures.Preflight.fixture ~timeout:({initial}))
  ~instruction:(Scenarios.Preflight.change_timeout ~initial:({initial}) ~requested:({requested}))
  ~criterion:(Scenarios.Preflight.defaults ~timeout:({requested}))
  ~allowed_files:["config.ml"; "client.ml"]
  ~reference:(Scenarios.Preflight.reference ~timeout:({requested}))"""


def ocaml_choice_case(*, case_id: str, a: int, b: int) -> str:
    choice = "A" if a < b else "B"
    return f"""Case.make ~id:{json.dumps(case_id)} ~fixture:Fixture.empty
  ~instruction:(Scenarios.Decision.cheaper ~a:{a} ~b:{b})
  ~criterion:(Scenarios.Decision.choice {choice}) ~allowed_files:[]
  ~reference:(Scenarios.Decision.choice_reference {choice} ~reason:"The cost is lower.")"""


# Synthetic benchmark import never downloads datasets or calls a model.
def import_records(records: tuple[str, ...]) -> tuple[Case, ...]:
    return transport.cases(sources=catalog.sources("humanevalplus"), records=records)


def imported_verifier(raw: str) -> ExecutableChecks | None:
    case = import_records((raw,))[0]
    return transport.verifier(sources=catalog.sources("humanevalplus"), case_id=case.id, record=raw)


def imported_reference(raw: str) -> Reference:
    case = import_records((raw,))[0]
    return transport.reference(
        sources=catalog.sources("humanevalplus"), case_id=case.id, record=raw
    )
