"""Direct public queries preserve validation and canonical results."""

from collections.abc import Callable
from typing import assert_type
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from evals.python import catalog, commands, query
from evals.python.paths import EVALS_ROOT


def test_public_queries_preserve_canonical_objects() -> None:
    dataset = assert_type(query.LoadDataset(), query.Dataset)
    assert query.LoadDataset(selection=dataset) is dataset
    cases = assert_type(query.Cases(), tuple[query.Case, ...])
    assert cases[0] is dataset.cases[cases[0].id]
    assert all(set(case.model_dump()) == {"id", "skill", "prompt", "files"} for case in cases)


def test_public_queries_select_canonical_projections() -> None:
    assert query.Cases(selection=EVALS_ROOT / "ocaml/suite.ml") == catalog.load_cases()
    assert assert_type(query.DescribeDataset(), query.DatasetInfo | None) is None
    with patch("evals.python.catalog.download") as download:
        info = query.DescribeDataset(selection="humanevalplus")
    assert isinstance(info, query.DatasetInfo)
    download.assert_not_called()


def test_public_experiment_resolves_canonical_overrides() -> None:
    spec = assert_type(query.ExperimentSettings(epochs=2), query.Experiment)
    assert spec.epochs == 2


def test_public_hashes_match_existing_provenance() -> None:
    provenance = assert_type(query.Provenance(), query.DatasetProvenance)
    assert provenance.info is None
    assert provenance.source_hash == catalog.source_hash("smoke")
    assert provenance.cases_hash == catalog.cases_hash("smoke")


def test_public_grade_preserves_input_and_result() -> None:
    verification = query.Verification(status="passed")
    with patch("evals.python.transport.grade", return_value={"correctness": True}) as grade:
        result = assert_type(
            query.GradeCase(
                case_id="clear-task",
                response="answer",
                changed_files=("receipt.ml",),
                verification=verification,
            ),
            query.Scores,
        )
    assert grade.call_args.kwargs["case_id"] == "clear-task"
    assert grade.call_args.kwargs["verification"] is verification
    assert result is grade.return_value


@pytest.mark.parametrize(
    "operation", [query.LoadDataset, query.Cases, query.DescribeDataset, query.Provenance]
)
@pytest.mark.parametrize("arguments", [{"selection": None}, {"unknown": "smoke"}])
def test_query_arguments_are_strict(
    operation: Callable[..., object], *, arguments: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        operation(**arguments)


@pytest.mark.parametrize("provider", ["hf", "local"])
def test_runtime_query_returns_canonical_capability(provider: str) -> None:
    runtime_query: Callable[..., query.Runtime] = query.ExecutionRuntime
    runtime = assert_type(runtime_query(provider=provider), query.Runtime)
    assert isinstance(runtime, commands.Runtime)
    with pytest.raises(ValidationError):
        runtime_query(provider="unknown")


def test_queries_are_separate_from_commands() -> None:
    assert not hasattr(commands, "query")
    assert not hasattr(commands, "execute")
    for name in (
        "Cases",
        "LoadDataset",
        "DescribeDataset",
        "Provenance",
        "GradeCase",
        "ExecutionRuntime",
        "ExperimentSettings",
    ):
        assert not hasattr(commands, name)
