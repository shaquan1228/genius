"""Exercise stable values across new datasets and interchangeable execution adapters."""

from collections.abc import Callable
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from kernel import SourceFile
from pydantic import ValidationError

from evals.python import datasets, evaluation
from evals.python.datasets import Case, Dataset
from evals.python.evaluation import Experiment, resolve_settings
from evals.python.integrations.evalplus import benchmarks
from evals.python.integrations.inspect import profiles
from evals.python.integrations.inspect.tasks import build_task
from evals.python.tests.projections import reference
from evals.python.tests.support import choice_case as _choice_case


@pytest.fixture
def third_dataset(*, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Dataset:
    (tmp_path / "third.py").write_text(
        "from evals.python.tests.support import choice_case\ninfo = None\n"
        "def cases():\n    return (choice_case(case_id='third-case', a=1, b=2),)\n"
    )
    monkeypatch.setattr(datasets, "__path__", [str(tmp_path), *datasets.__path__])
    return datasets.load_dataset(selection="third")


def third_dataset_requires_only_python_declarations(third_dataset: Dataset) -> None:
    cases = datasets.list_cases(selection=third_dataset)
    assert cases[0].case_id == "third-case"
    task = build_task(
        profile=profiles.load_profile("baseline", spec=evaluation.resolve_settings()),
        spec=evaluation.resolve_settings(),
        agent="codex",
        dataset="third",
        catalog=datasets.load_dataset(selection=third_dataset),
        documents=profiles.load_documents(evaluation.resolve_settings()),
    )
    assert task.dataset[0].id == "third-case"


def default_sandbox_is_local() -> None:
    task = build_task(
        profile=profiles.load_profile("baseline", spec=evaluation.resolve_settings()),
        spec=evaluation.resolve_settings(),
        agent="codex",
        catalog=datasets.load_dataset(selection="smoke"),
        documents=profiles.load_documents(evaluation.resolve_settings()),
    )
    assert task.sandbox is not None
    assert task.sandbox.type == "local"


def public_projection_contains_no_private_material() -> None:
    for case in datasets.list_cases():
        assert isinstance(case, Case)
        assert (hasattr(case, "reference"), hasattr(case, "criterion")) == (False, False)
        assert "verifier.py" not in {artifact.path: artifact.contents for artifact in case.files}


def public_projection_includes_visible_tools() -> None:
    case = datasets.list_cases()[0]
    assert "test_receipt.py" in {
        artifact.path: artifact.contents for artifact in case.files
    }  # The visible helper remains available to the agent.


def all_contract_collections_are_immutable() -> None:
    case_id = "clear-task"
    expected = reference(case_id)
    info = datasets.describe_dataset(selection="humanevalplus")
    assert info is not None
    with pytest.raises(TypeError):
        info.attributes["new"] = "value"  # type: ignore[index]
    with pytest.raises(TypeError):
        expected.edits[0] = SourceFile(path="new", contents="value")  # type: ignore[index]
    spec = evaluation.resolve_settings()
    with pytest.raises(ValidationError, match="frozen"):
        spec.profiles[0].preamble = "changed"
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
def experiment_rejects_invalid_run_overrides(field: str, *, value: int) -> None:
    operation = cast(Callable[..., Experiment], resolve_settings)
    with pytest.raises(ValidationError, match=field):
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
        patch("evals.python.datasets.describe_dataset", return_value=None),
        pytest.raises(ValueError, match="provenance"),
    ):
        benchmarks.benchmark_info()


def typed_dataset_compilation_rejects_duplicate_ids() -> None:
    records = (_choice_case(case_id="duplicate", a=1, b=2),) * 2
    with pytest.raises(ValueError, match="unique"):
        datasets.compile_dataset(cases=records)
