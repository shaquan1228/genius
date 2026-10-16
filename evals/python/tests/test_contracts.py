"""Exercise stable values across new datasets and interchangeable execution adapters."""

import json
import subprocess
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from evals.python import catalog, query, transport
from evals.python._kernel import Verification
from evals.python.integrations.evalplus import benchmarks
from evals.python.integrations.inspect import profiles
from evals.python.integrations.inspect.tasks import build_task
from evals.python.query import ExperimentSettings, GradeCase
from evals.python.tests.support import native_choice_case


@pytest.fixture
def third_dataset(*, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    adapter = tmp_path / "third.ml"
    expression = native_choice_case(case_id="third-case", a=1, b=2)
    adapter.write_text(
        f"let info = None\nlet cases = [{expression}]\n"
        "let import raw = { (List.hd cases) with Ast.id = raw }\n"
    )
    (tmp_path / "suite.ml").write_text((catalog.ADAPTER_ROOT / "suite.ml").read_text())
    (tmp_path / "declarations.ml").write_text(
        (catalog.ADAPTER_ROOT / "declarations.ml").read_text()
    )
    monkeypatch.setattr(catalog, "ADAPTER_ROOT", tmp_path)
    return "third"


def third_grade(*, case_id: str = "third-case", selection: str) -> query.Scores:
    return GradeCase(
        case_id=case_id,
        selection=selection,
        response='{"choice":"A","reason":"Less"}',
        changed_files=(),
        verification=Verification(status="unchecked"),
    )


def test_third_dataset_requires_only_adapter_and_declarations(third_dataset: str) -> None:
    cases = catalog.load_cases(selection=third_dataset)
    assert cases[0].id == "third-case"
    task = build_task(
        profile=profiles.load_profile("baseline", spec=query.ExperimentSettings()),
        spec=query.ExperimentSettings(),
        agent="codex",
        dataset="third",
        catalog=query.LoadDataset(selection="third"),
        instructions=profiles.load_instructions(query.ExperimentSettings()),
        provenance=query.Provenance(selection=query.LoadDataset(selection="third")),
    )
    assert task.dataset[0].id == "third-case"
    assert third_grade(selection=third_dataset) == {
        "correctness": True,
        "scope": True,
    }


def test_default_sandbox_is_local() -> None:
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


def test_third_dataset_imports_and_grades_records(third_dataset: str) -> None:
    imported = catalog.compile_records(sources=catalog.sources("third"), records=("new-case",))
    with patch.object(catalog, "load_dataset", return_value=imported):
        assert third_grade(case_id="new-case", selection=third_dataset)["correctness"]
        assert catalog.reference("new-case", selection="third").answer
        assert catalog.verifier("new-case", selection="third") is None


def test_public_projection_contains_no_private_material() -> None:
    for case in catalog.load_cases():
        assert set(case.model_dump()) == {"id", "skill", "prompt", "files"}
        assert "canonical_solution" not in case.model_dump_json()
        assert "verifier.py" not in case.files


def test_public_projection_includes_visible_tools() -> None:
    case = catalog.load_cases()[0]
    assert "test_receipt.py" in case.files  # The visible helper remains available to the agent.


def test_all_contract_collections_are_immutable() -> None:
    case_id = "clear-task"
    reference = catalog.reference(case_id)
    info = catalog.dataset_info("humanevalplus")
    assert info is not None
    with pytest.raises(TypeError):
        info.attributes["new"] = "value"  # type: ignore[index]
    with pytest.raises(TypeError):
        reference.solution["new"] = "value"  # type: ignore[index]
    spec = catalog.experiment()
    with pytest.raises(ValidationError):
        spec.profiles[0].preamble = "changed"
    assert isinstance(spec.profiles[0].instructions, tuple)


def test_run_overrides_are_resolved_once_and_shared_with_inspect() -> None:
    original = catalog.experiment()
    spec = ExperimentSettings(epochs=2, token_limit=1234, cache=True)
    task = build_task(
        profile=profiles.load_profile("genius", spec=spec),
        spec=spec,
        agent="codex",
        catalog=query.LoadDataset(selection="smoke"),
        instructions=profiles.load_instructions(spec),
        provenance=query.Provenance(selection=query.LoadDataset(selection="smoke")),
    )
    assert (task.epochs, task.token_limit, task.time_limit, task.config.cache) == (
        2,
        1234,
        original.time_limit,
        True,
    )
    assert catalog.experiment() == original


@pytest.mark.parametrize("field", ["epochs", "message_limit", "token_limit", "time_limit"])
@pytest.mark.parametrize("value", [0, -1])
def test_kernel_rejects_invalid_run_overrides(field: str, *, value: int) -> None:
    operation = cast(Callable[..., query.Experiment], ExperimentSettings)
    with pytest.raises(subprocess.CalledProcessError):
        operation(**{field: value})


@pytest.mark.parametrize("payload", [{"epochs": 1.5}, {"cache": 1}, {"unknown": 1}])
def test_protocol_rejects_malformed_run_overrides(payload: dict[str, object]) -> None:
    with pytest.raises(subprocess.CalledProcessError):
        transport.invoke(sources=catalog.sources(), operation="--experiment", payload=payload)


@pytest.mark.parametrize("version", [2, 4, True])
def test_public_projection_requires_exact_protocol_version(version: object) -> None:
    with pytest.raises(ValidationError):
        transport.decode(json.dumps({"version": version, "value": []}))


def test_unknown_or_unsafe_dataset_is_rejected() -> None:
    with pytest.raises(FileNotFoundError):
        query.Cases(selection="does-not-exist")
    with pytest.raises(ValidationError):
        query.Cases(selection="../outside")


def test_benchmark_adapter_requires_provenance() -> None:
    with (
        patch("evals.python.catalog.dataset_info", return_value=None),
        pytest.raises(ValueError, match="provenance"),
    ):
        benchmarks.benchmark_info()


def test_transport_rejects_duplicate_export_ids() -> None:
    case = catalog.load_cases()[0].model_dump()
    with pytest.raises(ValueError, match="unique"):
        transport.decode(json.dumps({"version": 3, "value": [case, case]}))


def test_verifier_projection_is_cached_but_grading_is_not() -> None:
    case_id = "clear-task"
    checks = catalog.verifier(case_id)
    grade = partial(
        GradeCase,
        case_id=case_id,
        response="",
        changed_files=(),
        verification=Verification(status="passed"),
    )
    with patch("evals.python.transport.subprocess.run", wraps=subprocess.run) as process:
        assert (
            catalog.verifier(case_id),
            catalog.verifier(case_id),
            process.call_count,
        ) == (
            checks,
            checks,
            0,
        )
        assert (
            grade()["correctness"],
            grade()["correctness"],
        ) == (True, True)
        assert [call.args[0][1:] for call in process.call_args_list] == [["--grade"], ["--grade"]]
