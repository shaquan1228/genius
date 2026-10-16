"""Direct public queries preserve validation and canonical results."""

from collections.abc import Callable
from typing import assert_type
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from evals.python import commands, datasets, queries
from kernel import Case, Experiment, Passed
from kernel._operations import projection as projection_ops


def public_queries_preserve_canonical_objects() -> None:
    dataset = assert_type(queries.load_dataset(), queries.Dataset)
    assert queries.load_dataset(selection=dataset) is dataset
    cases = assert_type(queries.list_cases(), tuple[Case, ...])
    assert cases[0] is dataset.cases[cases[0].id]
    assert all(isinstance(case, Case) for case in cases)


def public_queries_select_canonical_projections() -> None:
    assert queries.list_cases(selection=queries.compile_dataset(cases=())) == ()
    assert assert_type(queries.describe_dataset(), queries.DatasetInfo | None) is None
    with patch("evals.python.datasets.humanevalplus.download") as download:
        info = queries.describe_dataset(selection="humanevalplus")
    assert isinstance(info, queries.DatasetInfo)
    download.assert_not_called()


def public_experiment_resolves_canonical_overrides() -> None:
    spec = assert_type(queries.resolve_settings(epochs=2), Experiment)
    assert spec.epochs == 2


def public_hashes_match_existing_provenance() -> None:
    provenance = assert_type(queries.get_provenance(), queries.DatasetProvenance)
    assert provenance.info is None
    assert provenance.source_hash == datasets.fingerprint(queries.load_dataset().sources)
    assert provenance.cases_hash == datasets.cases_hash(queries.load_dataset())


def public_grade_preserves_input_and_result() -> None:
    verification = Passed()
    with patch(
        "kernel._operations.grader.grade", return_value=[("correctness", True), ("scope", True)]
    ) as grade:
        result = assert_type(
            queries.score_case(
                case_id="clear-task",
                response="answer",
                changed_files=("receipt.py",),
                verification=verification,
            ),
            queries.Scores,
        )
    assert grade.call_args.args[0] is queries.load_dataset().records["clear-task"]
    assert isinstance(grade.call_args.kwargs["outcome"].verification, Passed)
    assert result == dict(grade.return_value)


@pytest.mark.parametrize(
    "operation",
    [queries.load_dataset, queries.list_cases, queries.describe_dataset, queries.get_provenance],
)
@pytest.mark.parametrize("arguments", [{"selection": None}, {"unknown": "smoke"}])
def query_arguments_are_strict(
    operation: Callable[..., object], *, arguments: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        operation(**arguments)


def queries_are_separate_from_commands() -> None:
    assert not {"queries", "execute"} & vars(commands).keys()
    assert not {"create_runtime", "Runtime"} & vars(queries).keys()
    assert set(queries.__all__).isdisjoint(commands.__all__)


@pytest.mark.parametrize("response", ['{"":"x"}', '{"answer": 1}', "not json"])
def malformed_candidates_receive_incorrect_scores(response: str) -> None:
    scores = queries.score_case(case_id="small-decision", response=response, changed_files=())
    assert not scores["correctness"]


def reference_query_returns_canonical_reference() -> None:
    dataset = queries.load_dataset()
    expected = projection_ops.reference(dataset.records["small-decision"])
    with patch("kernel._operations.projection.reference", return_value=expected) as project:
        actual = queries.get_reference(case_id="small-decision", selection=dataset)
    assert actual is expected
    project.assert_called_once_with(dataset.records["small-decision"])
