"""Public compilation retains trusted declarations and canonical dataset identity."""

import asyncio
from collections.abc import Callable
from dataclasses import FrozenInstanceError, replace
from typing import assert_type, cast
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from evals.python import commands, datasets, queries
from evals.python.tests.declarations import (
    _copy_case,
    _copy_verifier,
    _declaration,
    _files,
    _public_snapshot,
    _reference_files,
)
from evals.python.tests.projections import reference, verifier
from kernel import Ast, Fixture, InvalidArgument


def compile_dataset_exposes_canonical_public_cases() -> None:
    definition = _declaration()
    dataset = assert_type(queries.compile_dataset(cases=(definition,)), queries.Dataset)
    assert isinstance(dataset, datasets.Dataset)
    cases = assert_type(queries.list_cases(selection=dataset), tuple[Ast.case, ...])
    assert cases[0] is dataset.cases[definition.id]


def compiled_cases_separate_construction_from_public_projection() -> None:
    dataset = queries.compile_dataset(cases=(_declaration(),))
    (case,) = queries.list_cases(selection=dataset)
    assert not isinstance(case, Ast.task)
    assert isinstance(case, Ast.case)
    assert not hasattr(case, "reference")
    assert "verify.py" not in dict(case.files)


def compiled_selection_reuses_the_compilation_snapshot() -> None:
    dataset = queries.compile_dataset(cases=(_declaration(),))
    assert datasets.load_dataset(dataset) is dataset


def compile_query_forwards_canonical_values_and_results() -> None:
    definition = _declaration()
    dataset = queries.compile_dataset(cases=(definition,))
    with patch("evals.python.datasets.compile_declarations", return_value=dataset) as compile_cases:
        assert queries.compile_dataset(cases=(definition,)) is dataset
    assert compile_cases.call_args.args[0][0] is definition
    assert queries.list_cases(selection=dataset) == tuple(dataset.cases.values())


def _independent_datasets() -> tuple[queries.Dataset, queries.Dataset]:
    first = _declaration()
    assert isinstance(first.criterion, Ast.Code)
    checks = _copy_verifier(first.criterion[0], stdin="different private stdin")
    second = _copy_case(
        first,
        criterion=Ast.Code(checks),
        reference=Ast.reference(
            edits=Fixture.of_files([("main.py", "another fixed solution")]),
            completion=Ast.Plain("another answer"),
        ),
    )
    return queries.compile_dataset(cases=(first,)), queries.compile_dataset(cases=(second,))


def compilation_preserves_independent_public_inputs() -> None:
    a, b = _independent_datasets()
    assert _public_snapshot(queries.list_cases(selection=a)) == _public_snapshot(
        queries.list_cases(selection=b)
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
    with patch("evals.python.datasets.humanevalplus.download") as download:
        assert queries.describe_dataset(selection=a) is None
        a_provenance = queries.get_provenance(selection=a)
        b_provenance = queries.get_provenance(selection=b)
    download.assert_not_called()
    assert a_provenance.info is None
    assert b_provenance.info is None


def compiled_provenance_retains_python_metadata() -> None:
    definition = _declaration()
    info = queries.DatasetInfo(
        source="python://external", revision="one", sha256="digest", count=1, attributes={}
    )
    original = queries.compile_dataset(cases=(definition,), info=info)
    changed = queries.compile_dataset(
        cases=(definition,), info=info.model_copy(update={"revision": "two"})
    )
    assert queries.describe_dataset(selection=original) == info
    assert _public_snapshot(queries.list_cases(selection=original)) == _public_snapshot(
        queries.list_cases(selection=changed)
    )
    assert (
        queries.get_provenance(selection=original).cases_hash
        != queries.get_provenance(selection=changed).cases_hash
    )
    with pytest.raises(ValueError, match="count"):
        queries.compile_dataset(cases=(), info=info)


@pytest.mark.parametrize("resource_name", ["checker.py", "ast.ml", "ast.cmo", "case.cmi", "kernel"])
def compiled_datasets_supply_independent_evaluator_resources(resource_name: str) -> None:
    definition = _declaration()
    assert isinstance(definition.criterion, Ast.Code)
    checks = _copy_verifier(
        definition.criterion[0], files=[("verify.py", Ast.Resource(resource_name))]
    )
    definition = _copy_case(definition, criterion=Ast.Code(checks))
    first = queries.compile_dataset(cases=(definition,), resources={resource_name: "first checker"})
    second = queries.compile_dataset(
        cases=(definition,), resources={resource_name: "second checker"}
    )
    a = cast(Ast.verifier, verifier("external", selection=first))
    b = cast(Ast.verifier, verifier("external", selection=second))
    assert _files(a.files)["verify.py"] == "first checker"
    assert _files(b.files)["verify.py"] == "second checker"
    assert (
        queries.get_provenance(selection=first).cases_hash
        != queries.get_provenance(selection=second).cases_hash
    )


def compilation_provenance_retains_sources_and_private_records() -> None:
    a, b = _independent_datasets()
    a_provenance = queries.get_provenance(selection=a)
    b_provenance = queries.get_provenance(selection=b)
    assert a_provenance.source_hash == b_provenance.source_hash
    assert a_provenance.cases_hash != b_provenance.cases_hash
    assert a_provenance.source_hash == datasets.fingerprint(a.sources)
    assert a_provenance.cases_hash == datasets.cases_hash(a)


def compilation_hashes_include_trusted_source_changes() -> None:
    dataset = queries.compile_dataset(cases=(_declaration(),))
    changed = replace(
        dataset,
        sources=replace(
            dataset.sources, resources=(*dataset.sources.resources, ("extra.txt", "changed"))
        ),
    )
    original = queries.get_provenance(selection=dataset)
    updated = queries.get_provenance(selection=changed)
    assert original.source_hash != updated.source_hash
    assert original.cases_hash != updated.cases_hash


def _grade(*, dataset: queries.Dataset, verification: Ast.verification) -> queries.Scores:
    return queries.score_case(
        case_id="external",
        response="done",
        changed_files=("workspace/main.py",),
        verification=verification,
        selection=dataset,
    )


def compiled_cases_use_existing_grading_policy() -> None:
    dataset = queries.compile_dataset(cases=(_declaration(),))
    assert _grade(dataset=dataset, verification=Ast.Passed()) == {
        "correctness": True,
        "scope": True,
    }


def compiled_grading_preserves_canonical_inputs_and_results() -> None:
    dataset = queries.compile_dataset(cases=(_declaration(),))
    verification = Ast.Passed()
    with patch(
        "kernel.Grader.grade", return_value=[("correctness", True), ("scope", True)]
    ) as kernel_grade:
        assert _grade(dataset=dataset, verification=verification) == dict(kernel_grade.return_value)
    assert kernel_grade.call_args.args[0] is dataset.records["external"]
    assert isinstance(kernel_grade.call_args.kwargs["outcome"].verification, Ast.Passed)


def compiled_dataset_is_immutable() -> None:
    dataset = queries.compile_dataset(cases=(_declaration(),))
    with pytest.raises(FrozenInstanceError):
        dataset.records = {}  # type: ignore[misc]
    with pytest.raises(TypeError):
        cast(dict[str, object], dataset.records)["external"] = "changed"
    with pytest.raises(TypeError):
        cast(dict[str, Ast.case], dataset.cases)["external"] = dataset.cases["external"]
    with pytest.raises(TypeError):
        dataset.cases["external"].files[0] = ("main.py", Ast.Inline("changed"))  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        dataset.sources.modules = ()  # type: ignore[misc]
    with pytest.raises(TypeError):
        dataset.sources.resources[0] = ("changed", "changed")  # type: ignore[index]


def empty_and_duplicate_compilation() -> None:
    dataset = queries.compile_dataset(cases=())
    assert queries.list_cases(selection=dataset) == ()
    assert dataset.records == {}
    with pytest.raises(ValueError, match="unique"):
        queries.compile_dataset(cases=(_declaration(), _declaration()))


def compile_query_validates_its_boundary_without_bypassing_kernel() -> None:
    compile_dataset: Callable[..., queries.Dataset] = queries.compile_dataset
    with pytest.raises(ValidationError):
        compile_dataset(cases=[_declaration()])
    public_case = Ast.case(id="public", skill="reasoning", prompt="", files=[])
    with pytest.raises(ValidationError):
        compile_dataset(cases=(public_case,))
    invalid = _copy_case(_declaration(), allowed_files=())
    with pytest.raises(InvalidArgument, match="outside allowed_files"):
        queries.compile_dataset(cases=(invalid,))


def unknown_case_in_compiled_dataset_fails_closed() -> None:
    dataset = queries.compile_dataset(cases=(_declaration(),))
    with pytest.raises(KeyError):
        datasets.record("absent", selection=dataset)
    with pytest.raises(KeyError):
        queries.score_case(case_id="absent", response="", changed_files=(), selection=dataset)


def compiled_selection_flows_through_all_verification_commands() -> None:
    dataset = queries.compile_dataset(cases=(_declaration(code=False),))
    agent = commands.Environment(
        execute=AsyncMock(), read_bytes=AsyncMock(), write_bytes=AsyncMock()
    )
    runtime = commands.Runtime(create=AsyncMock(), cleanup=AsyncMock())

    async def execute() -> None:
        verification = assert_type(
            await commands.verify(
                case_id="external", selection=dataset, agent=agent, runtime=runtime
            ),
            commands.VerificationResult,
        )
        assert isinstance(verification.verification, Ast.Unchecked)
        assessment = assert_type(
            await commands.assess(
                case_id="external",
                response='{"choice":"B","safe":true,"reason":"clear"}',
                changed_files=("workspace/main.py",),
                selection=dataset,
                agent=agent,
                runtime=runtime,
            ),
            commands.Assessment,
        )
        assert assessment.scores == {"correctness": True, "scope": True}
        reference = assert_type(
            await commands.validate_reference(
                case_id="external", selection=dataset, runtime=runtime
            ),
            commands.VerificationResult,
        )
        assert isinstance(reference.verification, Ast.Unchecked)

    asyncio.run(execute())
    cast(AsyncMock, runtime.create).assert_not_awaited()
    cast(AsyncMock, runtime.cleanup).assert_not_awaited()


def compilation_rejects_a_foreign_kernel_source_snapshot() -> None:
    foreign = replace(datasets.kernel_sources(), modules=())
    with (
        patch("evals.python.datasets.kernel_sources", return_value=foreign),
        pytest.raises(ValueError, match="Kernel sources differ"),
    ):
        queries.compile_dataset(cases=(_copy_case(_declaration(), id="foreign-kernel"),))


def mismatched_record_identity_is_rejected() -> None:
    dataset = queries.compile_dataset(cases=(_declaration(),))
    mismatched = replace(dataset, records={"wrong-id": dataset.records["external"]})
    with pytest.raises(ValueError, match="Unknown case: wrong-id"):
        queries.get_reference(case_id="wrong-id", selection=mismatched)
