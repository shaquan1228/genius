"""Public compilation retains trusted declarations and canonical dataset identity."""

import asyncio
import subprocess
from collections.abc import Callable
from dataclasses import FrozenInstanceError, replace
from typing import assert_type, cast
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from evals.python import catalog, commands, query
from evals.python.tests.declarations import declaration


def compile_dataset_exposes_canonical_public_cases_test() -> None:
    definition = declaration()
    dataset = assert_type(query.CompileDataset(cases=(definition,)), query.Dataset)
    assert isinstance(dataset, catalog.Catalog)
    cases = assert_type(query.Cases(selection=dataset), tuple[query.Case, ...])
    assert cases[0] is dataset.cases[definition.id]


def compiled_cases_separate_construction_from_public_projection_test() -> None:
    dataset = query.CompileDataset(cases=(declaration(),))
    (case,) = query.Cases(selection=dataset)
    assert not isinstance(case, query.CaseDefinition)
    assert set(case.model_dump()) == {"id", "skill", "prompt", "files"}
    assert "verify.py" not in case.files


def compiled_selection_reuses_the_compilation_snapshot_test() -> None:
    dataset = query.CompileDataset(cases=(declaration(),))
    assert catalog.sources(dataset) is dataset.sources
    assert catalog.load_dataset(dataset) is dataset


def compile_query_forwards_canonical_values_and_results_test() -> None:
    definition = declaration()
    dataset = query.CompileDataset(cases=(definition,))
    with patch("evals.python.catalog.compile_declarations", return_value=dataset) as compile_cases:
        assert query.CompileDataset(cases=(definition,)) is dataset
    assert compile_cases.call_args.args[0][0] is definition
    with patch("evals.python.catalog.load_cases", return_value=()) as load:
        query.Cases(selection=dataset)
    assert load.call_args.kwargs["selection"] is dataset


def independent_datasets() -> tuple[query.Dataset, query.Dataset]:
    first = declaration()
    assert isinstance(first.criterion, query.CodeCriterion)
    verifier = first.criterion.verifier.model_copy(update={"stdin": "different private stdin"})
    second = first.model_copy(
        update={
            "criterion": query.CodeCriterion(verifier=verifier),
            "reference": query.ReferenceDefinition(
                edits={"main.py": "another fixed solution"},
                completion=query.PlainCompletion(text="another answer"),
            ),
        }
    )
    a = query.CompileDataset(cases=(first,))
    b = query.CompileDataset(cases=(second,))
    return (a, b)


def compilation_preserves_independent_private_inputs_test() -> None:
    a, b = independent_datasets()
    assert query.Cases(selection=a) == query.Cases(selection=b)
    assert catalog.verifier("external", selection=a) != catalog.verifier("external", selection=b)
    assert catalog.reference("external", selection=a).solution == {"main.py": "fixed"}
    assert catalog.reference("external", selection=b).solution == {
        "main.py": "another fixed solution"
    }


def compiled_metadata_queries_do_not_download_test() -> None:
    a, b = independent_datasets()
    with patch("evals.python.catalog.download") as download:
        assert query.DescribeDataset(selection=a) is None
        a_provenance = query.Provenance(selection=a)
        b_provenance = query.Provenance(selection=b)
    download.assert_not_called()
    assert a_provenance.info is None
    assert b_provenance.info is None


def compilation_provenance_retains_sources_and_private_records_test() -> None:
    a, b = independent_datasets()
    a_provenance = query.Provenance(selection=a)
    b_provenance = query.Provenance(selection=b)
    assert a_provenance.source_hash == b_provenance.source_hash
    assert a_provenance.cases_hash != b_provenance.cases_hash
    assert a_provenance.source_hash == catalog.source_hash(a)
    assert a_provenance.cases_hash == catalog.cases_hash(a)


def compilation_hashes_include_trusted_source_changes_test() -> None:
    dataset = query.CompileDataset(cases=(declaration(),))
    changed = dataset.model_copy(
        update={
            "sources": replace(
                dataset.sources, resources=(*dataset.sources.resources, ("extra.txt", "changed"))
            )
        }
    )
    original = query.Provenance(selection=dataset)
    updated = query.Provenance(selection=changed)
    assert original.source_hash != updated.source_hash
    assert original.cases_hash != updated.cases_hash


def grade(*, dataset: query.Dataset, verification: query.Verification) -> query.Scores:
    return query.GradeCase(
        case_id="external",
        response="done",
        changed_files=("workspace/main.py",),
        verification=verification,
        selection=dataset,
    )


def compiled_cases_use_existing_grading_policy_test() -> None:
    dataset = query.CompileDataset(cases=(declaration(),))
    assert grade(dataset=dataset, verification=query.Verification(status="passed")) == {
        "correctness": True,
        "scope": True,
    }


def compiled_grading_preserves_canonical_inputs_and_results_test() -> None:
    dataset = query.CompileDataset(cases=(declaration(),))
    verification = query.Verification(status="passed")
    with patch("evals.python.transport.grade", return_value={"correctness": True}) as kernel_grade:
        assert grade(dataset=dataset, verification=verification) is kernel_grade.return_value
    assert kernel_grade.call_args.kwargs["sources"] is dataset.sources
    assert kernel_grade.call_args.kwargs["record"] is dataset.records["external"]
    assert kernel_grade.call_args.kwargs["verification"] is verification


def compiled_dataset_is_immutable_test() -> None:
    dataset = query.CompileDataset(cases=(declaration(),))
    with pytest.raises(ValidationError):
        dataset.records = {}
    with pytest.raises(TypeError):
        cast(dict[str, str], dataset.records)["external"] = "changed"
    with pytest.raises(TypeError):
        cast(dict[str, query.Case], dataset.cases)["external"] = dataset.cases["external"]
    with pytest.raises(TypeError):
        cast(dict[str, str], dataset.cases["external"].files)["main.py"] = "changed"
    with pytest.raises(FrozenInstanceError):
        dataset.sources.modules = ()  # type: ignore[misc]
    with pytest.raises(TypeError):
        dataset.sources.resources[0] = ("changed", "changed")  # type: ignore[index]


def empty_and_duplicate_compilation_test() -> None:
    dataset = query.CompileDataset(cases=())
    assert query.Cases(selection=dataset) == ()
    assert dataset.records == {}
    with pytest.raises(subprocess.CalledProcessError):
        query.CompileDataset(cases=(declaration(), declaration()))


def compile_query_validates_its_boundary_without_bypassing_kernel_test() -> None:
    compile_dataset: Callable[..., query.Dataset] = query.CompileDataset
    with pytest.raises(ValidationError):
        compile_dataset(cases=[declaration()])
    public_case = query.Case(id="public", skill="reasoning", prompt="", files={})
    with pytest.raises(ValidationError):
        compile_dataset(cases=(public_case,))
    invalid = declaration().model_copy(update={"allowed_files": ()})
    with pytest.raises(subprocess.CalledProcessError):
        query.CompileDataset(cases=(invalid,))


def unknown_case_in_compiled_dataset_fails_closed_test() -> None:
    dataset = query.CompileDataset(cases=(declaration(),))
    with pytest.raises(KeyError):
        catalog.case("absent", selection=dataset)
    with pytest.raises(subprocess.CalledProcessError):
        query.GradeCase(case_id="absent", response="", changed_files=(), selection=dataset)


def compiled_selection_flows_through_all_verification_commands_test() -> None:
    dataset = query.CompileDataset(cases=(declaration(code=False),))
    agent = commands.Environment(
        execute=AsyncMock(), read_bytes=AsyncMock(), write_bytes=AsyncMock()
    )
    runtime = commands.Runtime(create=AsyncMock(), cleanup=AsyncMock())

    async def execute() -> None:
        verification = assert_type(
            await commands.VerifyCase(
                case_id="external", selection=dataset, agent=agent, runtime=runtime
            ),
            commands.VerificationResult,
        )
        assert verification.verification.status == "unchecked"
        assessment = assert_type(
            await commands.AssessCase(
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
            await commands.ValidateReference(
                case_id="external", selection=dataset, runtime=runtime
            ),
            commands.VerificationResult,
        )
        assert reference.verification.status == "unchecked"

    asyncio.run(execute())
    cast(AsyncMock, runtime.create).assert_not_awaited()
    cast(AsyncMock, runtime.cleanup).assert_not_awaited()
