"""Direct public queries preserve validation and canonical results."""

from collections.abc import Callable
from typing import assert_type
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from evals.python import commands, datasets, query
from kernel import Ast, Projection


def public_queries_preserve_canonical_objects() -> None:
    dataset = assert_type(query.LoadDataset(), query.Dataset)
    assert query.LoadDataset(selection=dataset) is dataset
    cases = assert_type(query.Cases(), tuple[Ast.case, ...])
    assert cases[0] is dataset.cases[cases[0].id]
    assert all(isinstance(case, Ast.case) for case in cases)


def public_queries_select_canonical_projections() -> None:
    assert query.Cases(selection=query.CompileDataset(cases=())) == ()
    assert assert_type(query.DescribeDataset(), query.DatasetInfo | None) is None
    with patch("evals.python.datasets.humanevalplus.download") as download:
        info = query.DescribeDataset(selection="humanevalplus")
    assert isinstance(info, query.DatasetInfo)
    download.assert_not_called()


def public_experiment_resolves_canonical_overrides() -> None:
    spec = assert_type(query.ExperimentSettings(epochs=2), Ast.experiment)
    assert spec.epochs == 2


def public_hashes_match_existing_provenance() -> None:
    provenance = assert_type(query.Provenance(), query.DatasetProvenance)
    assert provenance.info is None
    assert provenance.source_hash == datasets.fingerprint(query.LoadDataset().sources)
    assert provenance.cases_hash == datasets.cases_hash(query.LoadDataset())


def public_grade_preserves_input_and_result() -> None:
    verification = Ast.Passed()
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
    assert isinstance(grade.call_args.kwargs["outcome"].verification, Ast.Passed)
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


@pytest.mark.parametrize("response", ['{"":"x"}', '{"answer": 1}', "not json"])
def malformed_candidates_receive_incorrect_scores(response: str) -> None:
    scores = query.GradeCase(case_id="small-decision", response=response, changed_files=())
    assert not scores["correctness"]


def reference_query_returns_canonical_reference() -> None:
    dataset = query.LoadDataset()
    expected = Projection.reference(dataset.records["small-decision"])
    with patch("kernel.Projection.reference", return_value=expected) as project:
        actual = query.Reference(case_id="small-decision", selection=dataset)
    assert actual is expected
    project.assert_called_once_with(dataset.records["small-decision"])
