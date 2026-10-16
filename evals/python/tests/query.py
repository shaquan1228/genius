"""Direct public queries preserve validation and canonical results."""

from collections.abc import Callable
from typing import assert_type
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from evals.python import commands, datasets, query


def public_queries_preserve_canonical_objects() -> None:
    dataset = assert_type(query.LoadDataset(), query.Dataset)
    assert query.LoadDataset(selection=dataset) is dataset
    cases = assert_type(query.Cases(), tuple[query.Ast.public_case, ...])
    assert cases[0] is dataset.cases[cases[0].id]
    assert all(isinstance(case, query.Ast.public_case) for case in cases)


def public_queries_select_canonical_projections() -> None:
    assert query.Cases(selection=query.CompileDataset(cases=())) == ()
    assert assert_type(query.DescribeDataset(), query.DatasetInfo | None) is None
    with patch("evals.python.datasets.humanevalplus.download") as download:
        info = query.DescribeDataset(selection="humanevalplus")
    assert isinstance(info, query.DatasetInfo)
    download.assert_not_called()


def public_experiment_resolves_canonical_overrides() -> None:
    spec = assert_type(query.ExperimentSettings(epochs=2), query.Ast.experiment)
    assert spec.epochs == 2


def public_hashes_match_existing_provenance() -> None:
    provenance = assert_type(query.Provenance(), query.DatasetProvenance)
    assert provenance.info is None
    assert provenance.source_hash == datasets.fingerprint(query.LoadDataset().sources)
    assert provenance.cases_hash == datasets.cases_hash(query.LoadDataset())


def public_grade_preserves_input_and_result() -> None:
    verification = query.Ast.Passed()
    with patch(
        "kernel.Grader.grade", return_value=[("correctness", True), ("scope", True)]
    ) as grade:
        result = assert_type(
            query.GradeCase(
                case_id="clear-task",
                response="answer",
                changed_files=("receipt.py",),
                verification=verification,
            ),
            query.Scores,
        )
    assert grade.call_args.args[0] is query.LoadDataset().records["clear-task"]
    assert isinstance(grade.call_args.kwargs["outcome"].verification, query.Ast.Passed)
    assert result == dict(grade.return_value)


@pytest.mark.parametrize(
    "operation", [query.LoadDataset, query.Cases, query.DescribeDataset, query.Provenance]
)
@pytest.mark.parametrize("arguments", [{"selection": None}, {"unknown": "smoke"}])
def query_arguments_are_strict(
    operation: Callable[..., object], *, arguments: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        operation(**arguments)


@pytest.mark.parametrize("provider", ["hf", "local"])
def runtime_query_returns_canonical_capability(provider: str) -> None:
    runtime_query: Callable[..., query.Runtime] = query.ExecutionRuntime
    runtime = assert_type(runtime_query(provider=provider), query.Runtime)
    assert isinstance(runtime, commands.Runtime)
    with pytest.raises(ValidationError):
        runtime_query(provider="unknown")


def queries_are_separate_from_commands() -> None:
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
