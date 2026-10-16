"""Public compilation retains trusted declarations and canonical dataset identity."""

import asyncio
import subprocess
from dataclasses import FrozenInstanceError, replace
from typing import assert_type, cast
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from evals.python import catalog, commands
from evals.python.tests.test_declarations import declaration


def test_compile_dataset_exposes_canonical_public_cases() -> None:
    definition = declaration()
    operation = commands.CompileDataset(cases=(definition,))
    dataset = assert_type(commands.query(operation), commands.Dataset)
    assert operation.cases[0] is definition
    assert isinstance(dataset, catalog.Catalog)
    cases = assert_type(
        commands.query(commands.Cases(selection=dataset)), tuple[commands.Case, ...]
    )
    assert cases[0] is dataset.cases[definition.id]


def test_compiled_cases_separate_construction_from_public_projection() -> None:
    dataset = commands.query(commands.CompileDataset(cases=(declaration(),)))
    (case,) = commands.query(commands.Cases(selection=dataset))
    assert not isinstance(case, commands.CaseDefinition)
    assert set(case.model_dump()) == {"id", "skill", "prompt", "files"}
    assert "verify.py" not in case.files


def test_compiled_selection_reuses_the_compilation_snapshot() -> None:
    dataset = commands.query(commands.CompileDataset(cases=(declaration(),)))
    assert catalog.sources(dataset) is dataset.sources
    assert catalog._selected(dataset) is dataset


def test_compile_query_forwards_canonical_values_and_results() -> None:
    operation = commands.CompileDataset(cases=(declaration(),))
    dataset = commands.query(operation)
    with patch("evals.python.catalog.compile_declarations", return_value=dataset) as compile_cases:
        assert commands.query(operation) is dataset
    assert compile_cases.call_args.args[0] is operation.cases
    with patch("evals.python.catalog.load_cases", return_value=()) as load:
        commands.query(commands.Cases(selection=dataset))
    assert load.call_args.kwargs["selection"] is dataset


def independent_datasets() -> tuple[commands.Dataset, commands.Dataset]:
    first = declaration()
    assert isinstance(first.criterion, commands.CodeCriterion)
    verifier = first.criterion.verifier.model_copy(update={"stdin": "different private stdin"})
    second = first.model_copy(
        update={
            "criterion": commands.CodeCriterion(verifier=verifier),
            "reference": commands.ReferenceDefinition(
                edits={"main.py": "another fixed solution"},
                completion=commands.PlainCompletion(text="another answer"),
            ),
        }
    )
    a = commands.query(commands.CompileDataset(cases=(first,)))
    b = commands.query(commands.CompileDataset(cases=(second,)))
    return a, b


def test_compilation_preserves_independent_private_inputs() -> None:
    a, b = independent_datasets()
    assert commands.query(commands.Cases(selection=a)) == commands.query(
        commands.Cases(selection=b)
    )
    assert catalog.verifier("external", selection=a) != catalog.verifier("external", selection=b)
    assert catalog.reference("external", selection=a).solution == {"main.py": "fixed"}
    assert catalog.reference("external", selection=b).solution == {
        "main.py": "another fixed solution"
    }


def test_compiled_metadata_queries_do_not_download() -> None:
    a, b = independent_datasets()
    with patch("evals.python.catalog.download") as download:
        assert commands.query(commands.DescribeDataset(selection=a)) is None
        a_provenance = commands.query(commands.Provenance(selection=a))
        b_provenance = commands.query(commands.Provenance(selection=b))
    download.assert_not_called()
    assert a_provenance.info is None
    assert b_provenance.info is None


def test_compilation_provenance_retains_sources_and_private_records() -> None:
    a, b = independent_datasets()
    a_provenance = commands.query(commands.Provenance(selection=a))
    b_provenance = commands.query(commands.Provenance(selection=b))
    assert a_provenance.source_hash == b_provenance.source_hash
    assert a_provenance.cases_hash != b_provenance.cases_hash
    assert a_provenance.source_hash == catalog.source_hash(a)
    assert a_provenance.cases_hash == catalog.cases_hash(a)


def test_compilation_hashes_include_trusted_source_changes() -> None:
    dataset = commands.query(commands.CompileDataset(cases=(declaration(),)))
    changed = dataset.model_copy(
        update={
            "sources": replace(
                dataset.sources, resources=(*dataset.sources.resources, ("extra.txt", "changed"))
            )
        }
    )
    original = commands.query(commands.Provenance(selection=dataset))
    updated = commands.query(commands.Provenance(selection=changed))
    assert original.source_hash != updated.source_hash
    assert original.cases_hash != updated.cases_hash


def grading_operation() -> commands.GradeCase:
    dataset = commands.query(commands.CompileDataset(cases=(declaration(),)))
    return commands.GradeCase(
        case_id="external",
        response="done",
        changed_files=("workspace/main.py",),
        verification=commands.Verification(status="passed"),
        selection=dataset,
    )


def test_compiled_cases_use_existing_grading_policy() -> None:
    assert commands.query(grading_operation()) == {"correctness": True, "scope": True}


def test_compiled_grading_preserves_canonical_inputs_and_results() -> None:
    operation = grading_operation()
    dataset = cast(commands.Dataset, operation.selection)
    with patch("evals.python.transport.grade", return_value={"correctness": True}) as grade:
        assert commands.query(operation) is grade.return_value
    assert grade.call_args.kwargs["sources"] is dataset.sources
    assert grade.call_args.kwargs["record"] is dataset.records["external"]
    assert grade.call_args.kwargs["verification"] is operation.verification


def test_compiled_dataset_is_immutable() -> None:
    dataset = commands.query(commands.CompileDataset(cases=(declaration(),)))
    with pytest.raises(ValidationError):
        dataset.records = {}
    with pytest.raises(TypeError):
        cast(dict[str, str], dataset.records)["external"] = "changed"
    with pytest.raises(TypeError):
        cast(dict[str, commands.Case], dataset.cases)["external"] = dataset.cases["external"]
    with pytest.raises(TypeError):
        cast(dict[str, str], dataset.cases["external"].files)["main.py"] = "changed"
    with pytest.raises(FrozenInstanceError):
        dataset.sources.modules = ()  # type: ignore[misc]
    with pytest.raises(TypeError):
        dataset.sources.resources[0] = ("changed", "changed")  # type: ignore[index]


def test_empty_and_duplicate_compilation() -> None:
    dataset = commands.query(commands.CompileDataset(cases=()))
    assert commands.query(commands.Cases(selection=dataset)) == ()
    assert dataset.records == {}
    with pytest.raises(subprocess.CalledProcessError):
        commands.query(commands.CompileDataset(cases=(declaration(), declaration())))


def test_compile_operation_validates_its_boundary_without_bypassing_kernel() -> None:
    operation = commands.CompileDataset(cases=(declaration(),))
    with pytest.raises(ValidationError):
        operation.cases = ()
    with pytest.raises(ValidationError):
        commands.CompileDataset.model_validate({"cases": [declaration()]})
    public_case = commands.Case(id="public", skill="reasoning", prompt="", files={})
    with pytest.raises(ValidationError):
        commands.CompileDataset.model_validate({"cases": (public_case,)})
    invalid = declaration().model_copy(update={"allowed_files": ()})
    with pytest.raises(subprocess.CalledProcessError):
        commands.query(commands.CompileDataset(cases=(invalid,)))


def test_unknown_case_in_compiled_dataset_fails_closed() -> None:
    dataset = commands.query(commands.CompileDataset(cases=(declaration(),)))
    with pytest.raises(KeyError):
        catalog.case("absent", selection=dataset)
    with pytest.raises(subprocess.CalledProcessError):
        commands.query(
            commands.GradeCase(case_id="absent", response="", changed_files=(), selection=dataset)
        )


def test_compiled_selection_flows_through_all_verification_commands() -> None:
    dataset = commands.query(commands.CompileDataset(cases=(declaration(code=False),)))
    agent = commands.Environment(
        execute=AsyncMock(), read_bytes=AsyncMock(), write_bytes=AsyncMock()
    )
    runtime = commands.Runtime(create=AsyncMock(), cleanup=AsyncMock())

    async def execute() -> None:
        verification = assert_type(
            await commands.execute(
                commands.VerifyCase(
                    case_id="external", selection=dataset, agent=agent, runtime=runtime
                )
            ),
            commands.VerificationResult,
        )
        assert verification.verification.status == "unchecked"
        assessment = assert_type(
            await commands.execute(
                commands.AssessCase(
                    case_id="external",
                    response='{"choice":"B","safe":true,"reason":"clear"}',
                    changed_files=("workspace/main.py",),
                    selection=dataset,
                    agent=agent,
                    runtime=runtime,
                )
            ),
            commands.Assessment,
        )
        assert assessment.scores == {"correctness": True, "scope": True}
        reference = assert_type(
            await commands.execute(
                commands.ValidateReference(case_id="external", selection=dataset, runtime=runtime)
            ),
            commands.VerificationResult,
        )
        assert reference.verification.status == "unchecked"

    asyncio.run(execute())
    cast(AsyncMock, runtime.create).assert_not_awaited()
    cast(AsyncMock, runtime.cleanup).assert_not_awaited()
