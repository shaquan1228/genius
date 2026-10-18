"""Direct public queries preserve validation and canonical results."""

from collections.abc import Callable
from typing import assert_type
from unittest.mock import PropertyMock, patch

import pytest
from pydantic import ValidationError

from evals.python import datasets, evaluation
from evals.python.datasets import Dataset, DatasetProvenance
from evals.python.schema import DatasetInfo
from kernel import Case, Experiment, Task


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


def reference_query_returns_canonical_reference() -> None:
    dataset = datasets.load_dataset()
    expected = (dataset.records["small-decision"]).reference
    with patch.object(
        Task, "reference", new_callable=PropertyMock, return_value=expected
    ) as project:
        actual = datasets.get_reference(case_id="small-decision", selection=dataset)
    assert actual is expected
    project.assert_called_once_with()
