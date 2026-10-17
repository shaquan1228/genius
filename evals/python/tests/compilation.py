"""Public compilation retains trusted declarations and canonical dataset identity."""

import asyncio
from collections.abc import Callable
from dataclasses import FrozenInstanceError, replace
from typing import assert_type, cast
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from evals.python import assessment as assessment_api
from evals.python import datasets, grading, verification
from evals.python.assessment import Assessment
from evals.python.datasets import Dataset, Sources
from evals.python.execution import Environment, Runtime
from evals.python.grading import Scores
from evals.python.schema import DatasetInfo
from evals.python.tests.declarations import (
    _copy_case,
    _copy_verifier,
    _declaration,
    _files,
    _public_snapshot,
    _reference_files,
)
from evals.python.tests.projections import reference, verifier
from evals.python.verification import VerificationResult
from kernel import (
    Artifact,
    Case,
    Completion,
    Content,
    Criterion,
    File,
    Fixture,
    Reference,
    Task,
    Verification,
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


def compile_query_forwards_canonical_values_and_results() -> None:
    definition = _declaration()
    dataset = datasets.compile_dataset(cases=(definition,))
    with patch("evals.python.datasets.compile_declarations", return_value=dataset) as compile_cases:
        assert datasets.compile_dataset(cases=(definition,)) is dataset
    assert compile_cases.call_args.args[0][0] is definition
    assert datasets.list_cases(selection=dataset) == tuple(dataset.cases.values())


def _independent_datasets() -> tuple[Dataset, Dataset]:
    first = _declaration()
    assert isinstance(first.criterion, Criterion.Code)
    checks = _copy_verifier(first.criterion.verifier, stdin="different private stdin")
    second = _copy_case(
        first,
        criterion=Criterion.Code(verifier=checks),
        reference=Reference(
            edits=Fixture.create(
                files=[File.create(path="main.py", contents="another fixed solution")]
            ),
            completion=Completion.Plain(text="another answer"),
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
        a_provenance = datasets.get_provenance(selection=a)
        b_provenance = datasets.get_provenance(selection=b)
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
        datasets.get_provenance(selection=original).cases_hash
        != datasets.get_provenance(selection=changed).cases_hash
    )
    with pytest.raises(ValueError, match="count"):
        datasets.compile_dataset(cases=(), info=info)


@pytest.mark.parametrize("resource_name", ["checker.py", "ast.ml", "ast.cmo", "case.cmi", "kernel"])
def compiled_datasets_supply_independent_evaluator_resources(resource_name: str) -> None:
    definition = _declaration()
    assert isinstance(definition.criterion, Criterion.Code)
    checks = _copy_verifier(
        definition.criterion.verifier,
        files=[Artifact.create(path="verify.py", content=Content.Resource(key=resource_name))],
    )
    definition = _copy_case(definition, criterion=Criterion.Code(verifier=checks))
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
        datasets.get_provenance(selection=first).cases_hash
        != datasets.get_provenance(selection=second).cases_hash
    )


def compilation_provenance_retains_sources_and_private_records() -> None:
    a, b = _independent_datasets()
    a_provenance = datasets.get_provenance(selection=a)
    b_provenance = datasets.get_provenance(selection=b)
    assert a_provenance.source_hash == b_provenance.source_hash
    assert a_provenance.cases_hash != b_provenance.cases_hash
    assert a_provenance.source_hash == datasets.fingerprint(a.sources)
    assert a_provenance.cases_hash == datasets.cases_hash(a)


def compilation_hashes_include_trusted_source_changes() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(),))
    changed = replace(
        dataset,
        sources=replace(
            dataset.sources, resources=(*dataset.sources.resources, ("extra.txt", "changed"))
        ),
    )
    original = datasets.get_provenance(selection=dataset)
    updated = datasets.get_provenance(selection=changed)
    assert original.source_hash != updated.source_hash
    assert original.cases_hash != updated.cases_hash


def _grade(*, dataset: Dataset, verification: Verification.Value) -> Scores:
    return grading.score_case(
        case_id="external",
        response="done",
        changed_files=("workspace/main.py",),
        verification=verification,
        selection=dataset,
    )


def compiled_cases_use_existing_grading_policy() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(),))
    assert _grade(dataset=dataset, verification=Verification.Passed()) == {
        "correctness": True,
        "scope": True,
    }


def compiled_grading_preserves_canonical_inputs_and_results() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(),))
    verification = Verification.Passed()
    with patch(
        "kernel._operations.grader.grade", return_value=[("correctness", True), ("scope", True)]
    ) as kernel_grade:
        assert _grade(dataset=dataset, verification=verification) == dict(kernel_grade.return_value)
    assert kernel_grade.call_args.kwargs["task"] is dataset.records["external"]
    assert isinstance(kernel_grade.call_args.kwargs["outcome"].verification, Verification.Passed)


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
            path="main.py", content=Content.Inline(text="changed")
        )
    with pytest.raises(FrozenInstanceError):
        dataset.sources.modules = ()  # type: ignore[misc]
    with pytest.raises(TypeError):
        dataset.sources.resources[0] = ("changed", "changed")  # type: ignore[index]


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
        datasets.record("absent", selection=dataset)
    with pytest.raises(KeyError):
        grading.score_case(case_id="absent", response="", changed_files=(), selection=dataset)


def compiled_selection_flows_through_all_verification_commands() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(code=False),))
    agent = Environment(execute=AsyncMock(), read_bytes=AsyncMock(), write_bytes=AsyncMock())
    runtime = Runtime(create=AsyncMock(), cleanup=AsyncMock())

    async def execute() -> None:
        result = assert_type(
            await verification.verify_case(
                case_id="external", selection=dataset, agent=agent, runtime=runtime
            ),
            VerificationResult,
        )
        assert isinstance(result.verification, Verification.Unchecked)
        assessment = assert_type(
            await assessment_api.assess(
                case_id="external",
                response='{"choice":"B","safe":true,"reason":"clear"}',
                changed_files=("workspace/main.py",),
                selection=dataset,
                agent=agent,
                runtime=runtime,
            ),
            Assessment,
        )
        assert assessment.scores == {"correctness": True, "scope": True}
        assert isinstance(assessment.evidence.verification, Verification.Unchecked)
        reference = assert_type(
            await verification.validate_reference(
                case_id="external", selection=dataset, runtime=runtime
            ),
            VerificationResult,
        )
        assert isinstance(reference.verification, Verification.Unchecked)

    asyncio.run(execute())
    cast(AsyncMock, runtime.create).assert_not_awaited()
    cast(AsyncMock, runtime.cleanup).assert_not_awaited()


def compilation_rejects_a_foreign_kernel_source_snapshot() -> None:
    foreign = replace(datasets.kernel_sources(), modules=())
    with (
        patch("evals.python.datasets.kernel_sources", return_value=foreign),
        pytest.raises(ValueError, match="Kernel sources differ"),
    ):
        datasets.compile_dataset(cases=(_copy_case(_declaration(), id="foreign-kernel"),))


def mismatched_record_identity_is_rejected() -> None:
    dataset = datasets.compile_dataset(cases=(_declaration(),))
    with pytest.raises(ValueError, match="record ID"):
        replace(dataset, records={"wrong-id": dataset.records["external"]})


def direct_dataset_construction_derives_public_cases_and_copies_records() -> None:
    definition = _declaration()
    records = {definition.id: definition}
    dataset = Dataset(sources=datasets.kernel_sources(), records=records)
    before = datasets.get_provenance(selection=dataset)
    records.clear()
    assert datasets.list_cases(selection=dataset)[0].prompt == definition.instruction.prompt
    assert datasets.get_provenance(selection=dataset) == before
    with patch("evals.python.datasets._module", side_effect=AssertionError("reload")):
        assert datasets.load_dataset(selection=dataset) is dataset
        assert (
            cast(
                Completion.Plain,
                datasets.get_reference(case_id=definition.id, selection=dataset).completion,
            ).text
            == "done"
        )


def direct_dataset_construction_rejects_foreign_sources_even_when_empty() -> None:
    with pytest.raises(ValueError, match="Kernel sources differ"):
        Dataset(sources=replace(datasets.kernel_sources(), modules=()), records={})


def direct_dataset_construction_validates_metadata_count() -> None:
    info = DatasetInfo(
        source="python://external", revision="one", sha256="digest", count=1, attributes={}
    )
    with pytest.raises(ValueError, match="count"):
        Dataset(sources=datasets.kernel_sources(), records={}, info=info)


def direct_dataset_construction_validates_native_records() -> None:
    with pytest.raises(DomainValidationError, match="outside allowed_files"):
        _copy_case(_declaration(), allowed_files=())


def direct_dataset_construction_resolves_resources() -> None:
    definition = _declaration()
    assert isinstance(definition.criterion, Criterion.Code)
    checks = _copy_verifier(
        definition.criterion.verifier,
        files=[Artifact.create(path="verify.py", content=Content.Resource(key="checker"))],
    )
    definition = _copy_case(definition, criterion=Criterion.Code(verifier=checks))
    with pytest.raises(DomainValidationError, match="checker"):
        Dataset(sources=datasets.kernel_sources(), records={definition.id: definition})
    resources = {"checker": "private checker"}
    dataset = Dataset(
        sources=datasets.kernel_sources(resources=resources), records={definition.id: definition}
    )
    resources.clear()
    resolved = verifier(definition.id, selection=dataset)
    assert resolved is not None
    assert _files(resolved.files) == {"verify.py": "private checker"}
    assert "verify.py" not in _files(dataset.cases[definition.id].files)


def direct_sources_retain_owned_immutable_collections() -> None:
    installed = datasets.kernel_sources()
    modules = [list(pair) for pair in installed.modules]
    resources = [["extra", "original"]]
    sources = Sources(
        modules=cast(tuple[tuple[str, str], ...], modules),
        resources=cast(tuple[tuple[str, str], ...], resources),
    )
    dataset = Dataset(sources=sources, records={})
    before = datasets.get_provenance(selection=dataset)
    modules[0][1] = "edited"
    resources[0][1] = "edited"
    modules.clear()
    resources.clear()
    assert dataset.sources.modules == installed.modules
    assert dataset.sources.resources == (("extra", "original"),)
    assert datasets.get_provenance(selection=dataset) == before
