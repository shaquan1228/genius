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
from evals.python.provenance import fingerprint
from evals.python.tests.declarations import (
    _copy_case,
    _copy_verifier,
    _declaration,
    _files,
    _public_snapshot,
    _reference_files,
)
from evals.python.tests.projections import reference, verifier
from kernel import (
    Artifact,
    Case,
    Completion,
    Content,
    Criterion,
    File,
    Fixture,
    Kernel,
    Reference,
    ResourceBinding,
    Task,
    Verifier,
)
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
    assert "verify.py" not in {artifact.path: artifact.content for artifact in case.files}


def compiled_selection_reuses_the_compilation_snapshot() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(),))
    assert datasets.load_dataset(selection=dataset) is dataset


def compiled_records_retain_canonical_values() -> None:
    definition = _declaration()
    dataset = datasets.compile_dataset(cases=(definition,))
    assert Task.compare(before=dataset.records[definition.id], after=definition).equal
    assert datasets.list_cases(selection=dataset) == tuple(dataset.cases.values())


def _independent_datasets() -> tuple[Dataset, Dataset]:
    first = _declaration()
    assert isinstance(first.criterion, Criterion.Code)
    checks = _copy_verifier(first.criterion.verifier, stdin="different private stdin")
    second = _copy_case(
        first,
        criterion=Criterion.create(code=checks),
        reference=Reference.create(
            edits=Fixture.create(
                files=[File.create(path="main.py", contents="another fixed solution")]
            ),
            completion=Completion.create(plain="another answer"),
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


@pytest.mark.parametrize("resource_name", ["checker.py", "ast.ml", "ast.cmo", "case.cmi", "kernel"])
def compiled_datasets_supply_independent_evaluator_resources(resource_name: str) -> None:
    definition = _declaration()
    assert isinstance(definition.criterion, Criterion.Code)
    checks = _copy_verifier(
        definition.criterion.verifier,
        files=[Artifact.create(path="verify.py", content=Content.create(resource=resource_name))],
    )
    definition = _copy_case(definition, criterion=Criterion.create(code=checks))
    first = datasets.compile_dataset(
        cases=(definition,), resources={resource_name: "first checker"}
    )
    second = datasets.compile_dataset(
        cases=(definition,), resources={resource_name: "second checker"}
    )
    a = cast(Verifier, verifier("external", selection=first))
    b = cast(Verifier, verifier("external", selection=second))
    assert _files(a.files)["verify.py"] == "first checker"
    assert _files(b.files)["verify.py"] == "second checker"
    assert (
        datasets.load_dataset(selection=first).cases_hash
        != datasets.load_dataset(selection=second).cases_hash
    )


def compilation_provenance_retains_sources_and_private_records() -> None:
    a, b = _independent_datasets()
    a_provenance = datasets.load_dataset(selection=a)
    b_provenance = datasets.load_dataset(selection=b)
    assert a_provenance.source_hash == b_provenance.source_hash
    assert a_provenance.cases_hash != b_provenance.cases_hash
    assert a_provenance.source_hash == fingerprint(Kernel.current.sources)


def compilation_hashes_include_trusted_source_changes() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(),))
    changed = replace(
        dataset,
        resources=(*dataset.resources, ResourceBinding.create(key="extra.txt", contents="changed")),
    )
    original = datasets.load_dataset(selection=dataset)
    updated = datasets.load_dataset(selection=changed)
    assert original.source_hash != updated.source_hash
    assert original.cases_hash != updated.cases_hash


def compiled_dataset_is_immutable() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(),))
    with pytest.raises(FrozenInstanceError):
        dataset.records = {}  # type: ignore[misc]
    with pytest.raises(TypeError):
        cast(dict[str, object], dataset.records)["external"] = "changed"
    with pytest.raises(TypeError):
        cast(dict[str, Case], dataset.cases)["external"] = dataset.cases["external"]
    with pytest.raises(TypeError):
        dataset.cases["external"].files[0] = Artifact.create(  # type: ignore[index]
            path="main.py", content=Content.create(inline="changed")
        )
    with pytest.raises(TypeError):
        dataset.resources[0] = ResourceBinding.create(key="changed", contents="changed")  # type: ignore[index]


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


def kernel_source_snapshot_cannot_be_forged() -> None:
    with pytest.raises(RuntimeError, match="private type"):
        cast(Callable[..., Kernel], Kernel)(sources=[])


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
                Completion.Plain,
                datasets.get_reference(case_id=definition.id, selection=dataset).completion,
            ).text
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


def direct_dataset_construction_resolves_resources() -> None:
    definition = _declaration()
    assert isinstance(definition.criterion, Criterion.Code)
    checks = _copy_verifier(
        definition.criterion.verifier,
        files=[Artifact.create(path="verify.py", content=Content.create(resource="checker"))],
    )
    definition = _copy_case(definition, criterion=Criterion.create(code=checks))
    with pytest.raises(DomainValidationError, match="checker"):
        Dataset(records={definition.id: definition})
    resources = {"checker": "private checker"}
    dataset = Dataset(
        resources=(ResourceBinding.create(key="checker", contents=resources["checker"]),),
        records={definition.id: definition},
    )
    resources.clear()
    resolved = verifier(definition.id, selection=dataset)
    assert resolved is not None
    assert _files(resolved.files) == {"verify.py": "private checker"}
    assert "verify.py" not in _files(dataset.cases[definition.id].files)


def direct_resources_retain_owned_immutable_collections() -> None:
    resources = [ResourceBinding.create(key="extra", contents="original")]
    dataset = Dataset(records={}, resources=cast(tuple[ResourceBinding, ...], resources))
    before = datasets.load_dataset(selection=dataset).source_hash
    resources.clear()
    assert [(r.key, r.contents) for r in dataset.resources] == [("extra", "original")]
    assert datasets.load_dataset(selection=dataset).source_hash == before


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
