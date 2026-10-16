"""Exercise stable values across new datasets and interchangeable execution adapters."""

from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from evals.python import datasets, query
from evals.python.integrations.evalplus import benchmarks
from evals.python.integrations.inspect import profiles
from evals.python.integrations.inspect.tasks import build_task
from evals.python.query import ExperimentSettings, GradeCase
from evals.python.tests.declarations import _reference_text
from evals.python.tests.projections import reference, verifier
from evals.python.tests.support import choice_case as _choice_case
from kernel import Ast, InvalidArgument, load


@pytest.fixture
def third_dataset(*, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> query.Dataset:
    (tmp_path / "third.py").write_text(
        "from evals.python.tests.support import choice_case\ninfo = None\n"
        "def cases():\n    return (choice_case(case_id='third-case', a=1, b=2),)\n"
    )
    monkeypatch.setattr(datasets, "__path__", [str(tmp_path), *datasets.__path__])
    return query.LoadDataset(selection="third")


def _third_grade(*, case_id: str = "third-case", selection: query.Dataset) -> query.Scores:
    return GradeCase(
        case_id=case_id,
        selection=selection,
        response='{"choice":"A","reason":"Less"}',
        changed_files=(),
        verification=Ast.Unchecked(),
    )


def third_dataset_requires_only_python_declarations(third_dataset: query.Dataset) -> None:
    cases = query.Cases(selection=third_dataset)
    assert cases[0].id == "third-case"
    task = build_task(
        profile=profiles.load_profile("baseline", spec=query.ExperimentSettings()),
        spec=query.ExperimentSettings(),
        agent="codex",
        dataset="third",
        catalog=query.LoadDataset(selection=third_dataset),
        instructions=profiles.load_instructions(query.ExperimentSettings()),
        provenance=query.Provenance(selection=third_dataset),
    )
    assert task.dataset[0].id == "third-case"
    assert _third_grade(selection=third_dataset) == {
        "correctness": True,
        "scope": True,
    }


def default_sandbox_is_local() -> None:
    task = build_task(
        profile=profiles.load_profile("baseline", spec=query.ExperimentSettings()),
        spec=query.ExperimentSettings(),
        agent="codex",
        catalog=query.LoadDataset(selection="smoke"),
        instructions=profiles.load_instructions(query.ExperimentSettings()),
        provenance=query.Provenance(selection=query.LoadDataset(selection="smoke")),
    )
    assert task.sandbox is not None
    assert task.sandbox.type == "local"


def third_dataset_imports_and_grades_records(third_dataset: query.Dataset) -> None:
    imported = query.CompileDataset(cases=(_choice_case(case_id="new-case", a=1, b=2),))
    with patch.object(datasets, "load_dataset", return_value=imported):
        assert _third_grade(case_id="new-case", selection=third_dataset)["correctness"]
        assert _reference_text(reference("new-case", selection=imported))
        assert verifier("new-case", selection=imported) is None


def public_projection_contains_no_private_material() -> None:
    for case in query.Cases():
        assert isinstance(case, Ast.case)
        assert not hasattr(case, "reference")
        assert not hasattr(case, "criterion")
        assert "verifier.py" not in dict(case.files)


def public_projection_includes_visible_tools() -> None:
    case = query.Cases()[0]
    assert "test_receipt.py" in dict(
        case.files
    )  # The visible helper remains available to the agent.


def all_contract_collections_are_immutable() -> None:
    case_id = "clear-task"
    expected = reference(case_id)
    info = datasets.dataset_info("humanevalplus")
    assert info is not None
    with pytest.raises(TypeError):
        info.attributes["new"] = "value"  # type: ignore[index]
    with pytest.raises(TypeError):
        query.Fixture.files(expected.edits)[0] = ("new", "value")  # type: ignore[index]
    spec = query.ExperimentSettings()
    with pytest.raises((AttributeError, TypeError)):
        spec.profiles[0].preamble = "changed"  # type: ignore[misc]
    assert tuple(spec.profiles[0].instructions) == ()


def run_overrides_are_resolved_once_and_shared_with_inspect() -> None:
    original = query.ExperimentSettings()
    spec = ExperimentSettings(epochs=2, cost_limit=0.1, cache=True)
    task = build_task(
        profile=profiles.load_profile("genius", spec=spec),
        spec=spec,
        agent="codex",
        catalog=query.LoadDataset(selection="smoke"),
        instructions=profiles.load_instructions(spec),
        provenance=query.Provenance(selection=query.LoadDataset(selection="smoke")),
    )
    assert (task.epochs, task.cost_limit, task.time_limit, task.config.cache) == (
        2,
        0.1,
        original.time_limit,
        True,
    )
    assert query.ExperimentSettings().epochs == original.epochs


@pytest.mark.parametrize("field", ["epochs", "message_limit", "cost_limit", "time_limit"])
@pytest.mark.parametrize("value", [0, -1])
def kernel_rejects_invalid_run_overrides(field: str, *, value: int) -> None:
    operation = cast(Callable[..., Ast.experiment], ExperimentSettings)
    with pytest.raises(InvalidArgument):
        operation(**{field: value})


@pytest.mark.parametrize("payload", [{"epochs": 1.5}, {"cache": 1}, {"unknown": 1}])
def public_query_rejects_malformed_run_overrides(payload: dict[str, object]) -> None:
    operation = cast(Callable[..., Ast.experiment], ExperimentSettings)
    with pytest.raises(ValidationError):
        operation(**payload)


def unknown_or_unsafe_dataset_is_rejected() -> None:
    with pytest.raises(ModuleNotFoundError):
        query.Cases(selection="does-not-exist")
    with pytest.raises(ValidationError):
        query.Cases(selection="../outside")


def benchmark_adapter_requires_provenance() -> None:
    with (
        patch("evals.python.datasets.dataset_info", return_value=None),
        pytest.raises(ValueError, match="provenance"),
    ):
        benchmarks.benchmark_info()


def typed_dataset_compilation_rejects_duplicate_ids() -> None:
    records = (_choice_case(case_id="duplicate", a=1, b=2),) * 2
    with pytest.raises(ValueError, match="unique"):
        query.CompileDataset(cases=records)


def verifier_projection_and_grading_use_native_values() -> None:
    case_id = "clear-task"
    checks = verifier(case_id)
    grade = partial(
        GradeCase,
        case_id=case_id,
        response="",
        changed_files=(),
        verification=Ast.Passed(),
    )
    native = load(datasets.kernel_sources().modules)
    with (
        patch.object(native.Projection, "verifier", wraps=native.Projection.verifier) as projection,
        patch.object(native.Grader, "grade", wraps=native.Grader.grade) as kernel_grade,
    ):
        projected = verifier(case_id)
        assert projected is not None
        assert checks is not None
        assert projected.stdin == checks.stdin
        projection.assert_called_once_with(datasets.record(case_id, selection="smoke"))
        assert (grade()["correctness"], grade()["correctness"]) == (True, True)
        assert kernel_grade.call_count == 2
