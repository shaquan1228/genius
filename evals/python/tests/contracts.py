"""Exercise stable values across new datasets and interchangeable execution adapters."""

from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from evals.python import datasets, evaluation
from evals.python.datasets import Dataset
from evals.python.evaluation import resolve_settings
from evals.python.grading import Scores, score_case
from evals.python.integrations.evalplus import benchmarks
from evals.python.integrations.inspect import profiles
from evals.python.integrations.inspect.tasks import build_task
from evals.python.tests.declarations import _reference_text
from evals.python.tests.projections import reference, verifier
from evals.python.tests.support import choice_case as _choice_case
from kernel import Case, Experiment, File, Fixture, Task, Verification
from kernel import ValidationError as DomainValidationError


@pytest.fixture
def third_dataset(*, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Dataset:
    (tmp_path / "third.py").write_text(
        "from evals.python.tests.support import choice_case\ninfo = None\n"
        "def cases():\n    return (choice_case(case_id='third-case', a=1, b=2),)\n"
    )
    monkeypatch.setattr(datasets, "__path__", [str(tmp_path), *datasets.__path__])
    return datasets.load_dataset(selection="third")


def _third_grade(*, case_id: str = "third-case", selection: Dataset) -> Scores:
    return score_case(
        case_id=case_id,
        selection=selection,
        response='{"choice":"A","reason":"Less"}',
        changed_files=(),
        verification=Verification.Unchecked(),
    )


def third_dataset_requires_only_python_declarations(third_dataset: Dataset) -> None:
    cases = datasets.list_cases(selection=third_dataset)
    assert cases[0].id == "third-case"
    task = build_task(
        profile=profiles.load_profile("baseline", spec=evaluation.resolve_settings()),
        spec=evaluation.resolve_settings(),
        agent="codex",
        dataset="third",
        catalog=datasets.load_dataset(selection=third_dataset),
        documents=profiles.load_documents(evaluation.resolve_settings()),
        provenance=datasets.get_provenance(selection=third_dataset),
    )
    assert task.dataset[0].id == "third-case"
    assert _third_grade(selection=third_dataset) == {
        "correctness": True,
        "scope": True,
    }


def default_sandbox_is_local() -> None:
    task = build_task(
        profile=profiles.load_profile("baseline", spec=evaluation.resolve_settings()),
        spec=evaluation.resolve_settings(),
        agent="codex",
        catalog=datasets.load_dataset(selection="smoke"),
        documents=profiles.load_documents(evaluation.resolve_settings()),
        provenance=datasets.get_provenance(selection=datasets.load_dataset(selection="smoke")),
    )
    assert task.sandbox is not None
    assert task.sandbox.type == "local"


def third_dataset_imports_and_grades_records(third_dataset: Dataset) -> None:
    imported = datasets.compile_dataset(cases=(_choice_case(case_id="new-case", a=1, b=2),))
    with patch.object(datasets, "load_dataset", return_value=imported):
        assert _third_grade(case_id="new-case", selection=third_dataset)["correctness"]
        assert _reference_text(reference("new-case", selection=imported))
        assert verifier("new-case", selection=imported) is None


def public_projection_contains_no_private_material() -> None:
    for case in datasets.list_cases():
        assert isinstance(case, Case)
        assert (hasattr(case, "reference"), hasattr(case, "criterion")) == (False, False)
        assert "verifier.py" not in {artifact.path: artifact.content for artifact in case.files}


def public_projection_includes_visible_tools() -> None:
    case = datasets.list_cases()[0]
    assert "test_receipt.py" in {
        artifact.path: artifact.content for artifact in case.files
    }  # The visible helper remains available to the agent.


def all_contract_collections_are_immutable() -> None:
    case_id = "clear-task"
    expected = reference(case_id)
    info = datasets.dataset_info("humanevalplus")
    assert info is not None
    with pytest.raises(TypeError):
        info.attributes["new"] = "value"  # type: ignore[index]
    with pytest.raises(TypeError):
        Fixture.files(fixture=expected.edits)[0] = File.create(path="new", contents="value")  # type: ignore[index]
    spec = evaluation.resolve_settings()
    with pytest.raises((AttributeError, TypeError)):
        spec.profiles[0].preamble = "changed"  # type: ignore[misc]
    assert tuple(spec.profiles[0].instructions) == ()


def run_overrides_are_resolved_once_and_shared_with_inspect() -> None:
    original = evaluation.resolve_settings()
    spec = resolve_settings(epochs=2, cost_limit=0.1, cache=True)
    task = build_task(
        profile=profiles.load_profile("genius", spec=spec),
        spec=spec,
        agent="codex",
        catalog=datasets.load_dataset(selection="smoke"),
        documents=profiles.load_documents(spec),
        provenance=datasets.get_provenance(selection=datasets.load_dataset(selection="smoke")),
    )
    assert (task.epochs, task.cost_limit, task.time_limit, task.config.cache) == (
        2,
        0.1,
        original.time_limit,
        True,
    )
    assert evaluation.resolve_settings().epochs == original.epochs


@pytest.mark.parametrize("field", ["epochs", "message_limit", "cost_limit", "time_limit"])
@pytest.mark.parametrize("value", [0, -1])
def kernel_rejects_invalid_run_overrides(field: str, *, value: int) -> None:
    operation = cast(Callable[..., Experiment], resolve_settings)
    with pytest.raises(DomainValidationError):
        operation(**{field: value})


@pytest.mark.parametrize("payload", [{"epochs": 1.5}, {"cache": 1}, {"unknown": 1}])
def public_query_rejects_malformed_run_overrides(payload: dict[str, object]) -> None:
    operation = cast(Callable[..., Experiment], resolve_settings)
    with pytest.raises(ValidationError):
        operation(**payload)


def unknown_or_unsafe_dataset_is_rejected() -> None:
    with pytest.raises(ModuleNotFoundError):
        datasets.list_cases(selection="does-not-exist")
    with pytest.raises(ValidationError):
        datasets.list_cases(selection="../outside")


def benchmark_adapter_requires_provenance() -> None:
    with (
        patch("evals.python.datasets.dataset_info", return_value=None),
        pytest.raises(ValueError, match="provenance"),
    ):
        benchmarks.benchmark_info()


def typed_dataset_compilation_rejects_duplicate_ids() -> None:
    records = (_choice_case(case_id="duplicate", a=1, b=2),) * 2
    with pytest.raises(ValueError, match="unique"):
        datasets.compile_dataset(cases=records)


def verifier_projection_and_grading_use_native_values() -> None:
    case_id = "clear-task"
    checks = verifier(case_id)
    grade = partial(
        score_case,
        case_id=case_id,
        response="",
        changed_files=(),
        verification=Verification.Passed(),
    )
    with (
        patch.object(Task, "verifier", wraps=Task.verifier) as projection,
        patch.object(Task, "assess", wraps=Task.assess) as kernel_grade,
    ):
        projected = verifier(case_id)
        assert projected is not None
        assert checks is not None
        projection.assert_called_once_with(task=datasets.record(case_id, selection="smoke"))
        assert (grade()["correctness"], grade()["correctness"]) == (True, True)
        assert (projected.stdin, kernel_grade.call_count) == (checks.stdin, 2)
