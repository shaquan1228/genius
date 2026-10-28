"""Run scripted agents through Inspect for integration tests."""

from pathlib import Path

from inspect_ai import Task as InspectTask
from inspect_ai import eval
from inspect_ai.log import EvalLog, EvalSample
from inspect_ai.model import ModelCost, ModelInfo, get_model, set_model_info
from kernel import Criterion, Instruction, Reference, Rubric, Task, TextRule, Verifier

from evals.python import datasets
from evals.python.datasets import Case, Dataset, Declaration, humanevalplus, smoke
from evals.python.tests.declarations import _copy_case
from evals.python.tests.projections import reference, verifier
from evals.python.tests.scenarios import Mode
from evals.python.tests.scenarios import echo_model as _echo_model
from evals.python.tests.scenarios import scripted as _scripted

__test__ = False


def offline_run(
    tasks: list[InspectTask],
    *,
    mode: Mode | None,
    directory: Path,
    epochs: int = 1,
    sandbox: str | tuple[str, str] = "local",
) -> list[EvalLog]:
    """Mode None keeps each task's own agent solver."""
    model = get_model("mockllm/model", custom_outputs=_echo_model)
    set_model_info(
        str(model),
        ModelInfo(cost=ModelCost(input=0, output=0, input_cache_write=0, input_cache_read=0)),
    )
    return eval(
        tasks,
        model=model,
        solver=None if mode is None else _scripted(mode),
        sandbox=sandbox,
        epochs=epochs,
        max_samples=1,
        log_dir=str(directory),
        display="none",
        log_format="json",
        ctl_server=False,
    )


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


def timeout_case(*, case_id: str, initial: int, requested: int) -> Declaration:
    task = smoke.timeout(initial=initial, requested=requested)
    return _copy_case(Declaration(skill="preflight", task=task), id=case_id)


def choice_case(*, case_id: str, a: int, b: int) -> Declaration:
    choice = "A" if a < b else "B"
    return Declaration(
        skill="reasoning",
        task=Task(
            id=case_id,
            fixture=[],
            instruction=Instruction(prompt="Choose A or B with a reason"),
            criterion=Criterion.Answer(
                rubric=Rubric(
                    expected=[("choice", choice)],
                    text_rule=TextRule(field="reason", min_words=1, max_words=40),
                )
            ),
            allowed_files=(),
            reference=Reference(
                edits=[],
                completion={"choice": choice, "reason": "The cost is lower."},
            ),
        ),
    )


def import_dataset(records: tuple[str, ...]) -> Dataset:
    return datasets.compile_dataset(cases=humanevalplus.declarations(records))


def import_records(records: tuple[str, ...]) -> tuple[Case, ...]:
    return datasets.list_cases(selection=import_dataset(records))


def imported_verifier(raw: str) -> Verifier | None:
    dataset = import_dataset((raw,))
    return verifier(next(iter(dataset.cases)), selection=dataset)


def imported_reference(raw: str) -> Reference:
    dataset = import_dataset((raw,))
    return reference(next(iter(dataset.cases)), selection=dataset)
