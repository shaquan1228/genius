"""Direct public queries preserve validation and canonical results."""

from collections.abc import Callable
from typing import assert_type
from unittest.mock import PropertyMock, patch

import pytest
from pydantic import ValidationError

from evals.python import datasets, evaluation, grading
from evals.python.datasets import Dataset, DatasetProvenance
from evals.python.grading import Scores
from evals.python.schema import DatasetInfo
from kernel import Case, Experiment, Task, Verification


def public_queries_preserve_canonical_objects() -> None:
    dataset = assert_type(datasets.load_dataset(), Dataset)
    assert datasets.load_dataset(selection=dataset) is dataset
    cases = assert_type(datasets.list_cases(), tuple[Case, ...])
    assert cases[0] is dataset.cases[cases[0].id]
    assert all(isinstance(case, Case) for case in cases)


def public_queries_select_canonical_projections() -> None:
    assert datasets.list_cases(selection=datasets.compile_dataset(cases=())) == ()
    assert assert_type(datasets.describe_dataset(), DatasetInfo | None) is None
    with patch("evals.python.datasets.humanevalplus._download") as download:
        info = datasets.describe_dataset(selection="humanevalplus")
    assert isinstance(info, DatasetInfo)
    download.assert_not_called()


def public_experiment_resolves_canonical_overrides() -> None:
    spec = assert_type(evaluation.resolve_settings(epochs=2), Experiment)
    assert spec.epochs == 2


def public_hashes_match_existing_provenance() -> None:
    provenance = assert_type(datasets.get_provenance(), DatasetProvenance)
    assert provenance.info is None
    assert provenance.source_hash == datasets.fingerprint(datasets.load_dataset().sources)
    assert provenance.cases_hash == datasets.cases_hash(datasets.load_dataset())


def public_grade_preserves_input_and_result() -> None:
    verification = Verification.Passed()
    with patch("kernel.Task.grade", return_value=[("correctness", True), ("scope", True)]) as grade:
        result = assert_type(
            grading.score_case(
                case_id="clear-task",
                response="answer",
                changed_files=("receipt.py",),
                verification=verification,
            ),
            Scores,
        )
    assert grade.call_args.kwargs["task"] is datasets.load_dataset().records["clear-task"]
    assert isinstance(grade.call_args.kwargs["outcome"].verification, Verification.Passed)
    assert result == dict(grade.return_value)


@pytest.mark.parametrize(
    "operation",
    [
        datasets.load_dataset,
        datasets.list_cases,
        datasets.describe_dataset,
        datasets.get_provenance,
    ],
)
@pytest.mark.parametrize("arguments", [{"selection": None}, {"unknown": "smoke"}])
def query_arguments_are_strict(
    operation: Callable[..., object], *, arguments: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        operation(**arguments)


def query_concerns_expose_only_their_own_operations() -> None:
    assert not {"create_runtime", "assess", "verify_case", "evaluate"} & set(datasets.__all__)
    assert grading.__all__ == ["Scores", "score_case"]
    assert set(evaluation.__all__) == {
        "EvaluationSettings",
        "InstructionDelivery",
        "ModelPricing",
        "VariantSettings",
        "evaluate",
        "prepare_run",
        "validate_run",
        "resolve_settings",
        "resolve_experiment",
    }


@pytest.mark.parametrize("response", ['{"":"x"}', '{"answer": 1}', "not json"])
def malformed_candidates_receive_incorrect_scores(response: str) -> None:
    scores = grading.score_case(case_id="small-decision", response=response, changed_files=())
    assert not scores["correctness"]


def reference_query_returns_canonical_reference() -> None:
    dataset = datasets.load_dataset()
    expected = (dataset.records["small-decision"]).reference
    with patch.object(
        Task, "reference", new_callable=PropertyMock, return_value=expected
    ) as project:
        actual = datasets.get_reference(case_id="small-decision", selection=dataset)
    assert actual is expected
    project.assert_called_once_with()
