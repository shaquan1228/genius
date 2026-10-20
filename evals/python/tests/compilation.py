"""Public compilation retains trusted declarations and canonical dataset identity."""

from collections.abc import Callable
from dataclasses import FrozenInstanceError, replace
from typing import assert_type, cast
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from evals.python import datasets
from evals.python.dataset import DatasetInfo
from evals.python.datasets import Dataset
from evals.python.provenance import fingerprint, value_fingerprint
from evals.python.tests.declarations import (
    _copy_case,
    _copy_verifier,
    _declaration,
    _public_snapshot,
    _reference_files,
)
from evals.python.tests.projections import reference, verifier
from kernel import Case, Criterion, File, Kernel, Reference, Task, Value
from kernel import (
    ValidationError as DomainValidationError,
)


def compile_dataset_exposes_canonical_public_cases() -> None:
    definition = _declaration()
    dataset = assert_type(datasets.compile_dataset(cases=(definition,)), Dataset)
    assert isinstance(dataset, Dataset)
    cases = assert_type(datasets.list_cases(selection=dataset), tuple[Case, ...])
    assert cases[0] is dataset.cases[definition.id]


def compiled_cases_separate_construction_from_public_projection() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(),))
    (case,) = datasets.list_cases(selection=dataset)
    assert not isinstance(case, Task)
    assert isinstance(case, Case)
    assert not hasattr(case, "reference")
    assert "verify.py" not in {artifact.path: artifact.contents for artifact in case.files}


def compiled_selection_reuses_the_compilation_snapshot() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(),))
    assert datasets.load_dataset(selection=dataset) is dataset


def compiled_records_retain_canonical_values() -> None:
    definition = _declaration()
    dataset = datasets.compile_dataset(cases=(definition,))
    assert value_fingerprint(dataset.records[definition.id]) == value_fingerprint(definition)
    assert datasets.list_cases(selection=dataset) == tuple(dataset.cases.values())


def _independent_datasets() -> tuple[Dataset, Dataset]:
    first = _declaration()
    assert isinstance(first.criterion, Criterion.Code)
    checks = _copy_verifier(first.criterion.verifier, stdin="different private stdin")
    second = _copy_case(
        first,
        criterion=Criterion.Code(verifier=checks),
        reference=Reference(
            edits=[File(path="main.py", contents="another fixed solution")],
            completion=Value.String(value="another answer"),
        ),
    )
    return datasets.compile_dataset(cases=(first,)), datasets.compile_dataset(cases=(second,))


def compilation_preserves_independent_public_inputs() -> None:
    a, b = _independent_datasets()
    assert _public_snapshot(datasets.list_cases(selection=a)) == _public_snapshot(
        datasets.list_cases(selection=b)
    )


def compilation_preserves_independent_private_inputs() -> None:
    a, b = _independent_datasets()
    first_checks = verifier("external", selection=a)
    second_checks = verifier("external", selection=b)
    assert first_checks is not None
    assert second_checks is not None
    assert (first_checks.stdin, second_checks.stdin) == ("private stdin", "different private stdin")
    assert (
        _reference_files(reference("external", selection=a)),
        _reference_files(reference("external", selection=b)),
    ) == ({"main.py": "fixed"}, {"main.py": "another fixed solution"})


def compiled_metadata_queries_do_not_download() -> None:
    a, b = _independent_datasets()
    with patch("evals.python.datasets.humanevalplus._download") as download:
        assert datasets.describe_dataset(selection=a) is None
        a_provenance = datasets.load_dataset(selection=a)
        b_provenance = datasets.load_dataset(selection=b)
    download.assert_not_called()
    assert a_provenance.info is None
    assert b_provenance.info is None


def compiled_provenance_retains_python_metadata() -> None:
    definition = _declaration()
    info = DatasetInfo(
        source="python://external", revision="one", sha256="digest", count=1, attributes={}
    )
    original = datasets.compile_dataset(cases=(definition,), info=info)
    changed = datasets.compile_dataset(
        cases=(definition,), info=info.model_copy(update={"revision": "two"})
    )
    assert datasets.describe_dataset(selection=original) == info
    assert _public_snapshot(datasets.list_cases(selection=original)) == _public_snapshot(
        datasets.list_cases(selection=changed)
    )
    assert (
        datasets.load_dataset(selection=original).cases_hash
        != datasets.load_dataset(selection=changed).cases_hash
    )
    with pytest.raises(ValueError, match="count"):
        datasets.compile_dataset(cases=(), info=info)


def compilation_provenance_retains_sources_and_private_records() -> None:
    a, b = _independent_datasets()
    a_provenance = datasets.load_dataset(selection=a)
    b_provenance = datasets.load_dataset(selection=b)
    assert a_provenance.source_hash == b_provenance.source_hash
    assert a_provenance.cases_hash != b_provenance.cases_hash
    assert a_provenance.source_hash == fingerprint(Kernel.current.sources)


def compiled_dataset_is_immutable() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(),))
    with pytest.raises(FrozenInstanceError):
        dataset.records = {}  # type: ignore[misc]
    with pytest.raises(TypeError):
        cast(dict[str, object], dataset.records)["external"] = "changed"
    with pytest.raises(TypeError):
        cast(dict[str, Case], dataset.cases)["external"] = dataset.cases["external"]
    with pytest.raises(TypeError):
        dataset.cases["external"].files[0] = File(path="main.py", contents="changed")  # type: ignore[index]


def empty_and_duplicate_compilation() -> None:
    dataset = datasets.compile_dataset(cases=())
    assert datasets.list_cases(selection=dataset) == ()
    assert dataset.records == {}
    with pytest.raises(ValueError, match="unique"):
        datasets.compile_dataset(cases=(_declaration(), _declaration()))


def compile_query_validates_its_boundary_without_bypassing_kernel() -> None:
    compile_dataset: Callable[..., Dataset] = datasets.compile_dataset
    with pytest.raises(ValidationError):
        compile_dataset(cases=[_declaration()])
    public_case = datasets.list_cases()[0]
    with pytest.raises(ValidationError):
        compile_dataset(cases=(public_case,))
    with pytest.raises(DomainValidationError, match="outside allowed_files"):
        _copy_case(_declaration(), allowed_files=())


def unknown_case_in_compiled_dataset_fails_closed() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(),))
    with pytest.raises(KeyError):
        datasets.load_dataset(selection=dataset).records["absent"]


def mismatched_record_identity_is_rejected() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(),))
    with pytest.raises(ValueError, match="record ID"):
        replace(dataset, records={"wrong-id": dataset.records["external"]})


def direct_dataset_construction_derives_public_cases_and_copies_records() -> None:
    definition = _declaration()
    records = {definition.id: definition}
    dataset = Dataset(records=records)
    before = (dataset.source_hash, dataset.cases_hash)
    records.clear()
    assert datasets.list_cases(selection=dataset)[0].prompt == definition.instruction.prompt
    assert (dataset.source_hash, dataset.cases_hash) == before
    with patch("evals.python.datasets._module", side_effect=AssertionError("reload")):
        assert datasets.load_dataset(selection=dataset) is dataset
        assert (
            cast(
                Value.String,
                datasets.get_reference(case_id=definition.id, selection=dataset).completion,
            ).value
            == "done"
        )


def direct_dataset_construction_validates_metadata_count() -> None:
    info = DatasetInfo(
        source="python://external", revision="one", sha256="digest", count=1, attributes={}
    )
    with pytest.raises(ValueError, match="count"):
        Dataset(records={}, info=info)


def direct_dataset_construction_validates_native_records() -> None:
    with pytest.raises(DomainValidationError, match="outside allowed_files"):
        _copy_case(_declaration(), allowed_files=())


def metadata_order_preserves_cached_provenance() -> None:
    case = _declaration()
    info = DatasetInfo(
        source="python://external",
        revision="one",
        sha256="digest",
        count=1,
        attributes={"first": "a", "second": "b"},
    )
    before = datasets.compile_dataset(cases=(case,), info=info)
    after = datasets.compile_dataset(
        cases=(case,),
        info=DatasetInfo(
            source=info.source,
            revision=info.revision,
            sha256=info.sha256,
            count=info.count,
            attributes={"second": "b", "first": "a"},
        ),
    )
    assert after is before
    assert after.cases_hash == before.cases_hash
