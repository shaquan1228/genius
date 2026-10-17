"""A Python-owned dataset exercises the real kernel and generic verifier."""

import asyncio
import json
import runpy
from typing import cast
from unittest.mock import AsyncMock, patch

import pytest

from evals.python import assessment, datasets, execution, grading, verification
from evals.python.assessment import Assessment
from evals.python.datasets import Dataset
from evals.python.datasets import smoke as declarations
from evals.python.execution import Environment, Execution, Runtime
from evals.python.integrations.smoke import __main__ as cli
from evals.python.tests.declarations import _files, _reference_files
from evals.python.verification import VerificationResult
from kernel import Case, Criterion, Verification


def python_smoke_compiles_to_public_cases() -> None:
    definitions = declarations.cases()
    dataset = datasets.compile_dataset(cases=definitions)
    cases = datasets.list_cases(selection=dataset)
    assert tuple(case.id for case in cases) == tuple(case.id for case in definitions)
    assert all(isinstance(case, Case) for case in cases)


def default_smoke_uses_python_owned_cases() -> None:
    definitions = declarations.cases()
    dataset = datasets.load_dataset()
    assert dataset is datasets.compile_dataset(cases=definitions)
    assert tuple(dataset.cases) == (
        "clear-task",
        "known-preflight",
        "small-decision",
        "decision-review",
    )
    assert tuple(dict(dataset.cases["clear-task"].files)) == ("receipt.py", "test_receipt.py")


@pytest.mark.parametrize(("initial", "requested"), [(15, 15), (0, 30), (-1, 30), (15, 0), (15, -1)])
def timeout_variants_require_a_real_positive_change(initial: int, *, requested: int) -> None:
    with pytest.raises(ValueError, match="distinct positive"):
        declarations.timeout(initial=initial, requested=requested)


def python_smoke_keeps_checks_and_references_private() -> None:
    definitions = declarations.cases()
    dataset = datasets.compile_dataset(cases=definitions)
    cases = datasets.list_cases(selection=dataset)
    code = definitions[0]
    assert isinstance(code.criterion, Criterion.Code)
    assert code.criterion[0].stdin not in json.dumps(_files(cases[0].files))
    assert _reference_files(code.reference)["receipt.py"] not in _files(cases[0].files).values()
    assert "verifier.py" not in dict(cases[0].files)


async def _assess_code(*, dataset: Dataset, agent: Environment) -> tuple[Assessment, ...]:
    runtime = execution.create_runtime()

    async def assess(changed_files: tuple[str, ...]) -> Assessment:
        return await assessment.assess(
            case_id="clear-task",
            selection=dataset,
            response="done",
            changed_files=changed_files,
            agent=agent,
            runtime=runtime,
        )

    seed = await assess(("workspace/receipt.py",))
    definition = declarations.cases()[0]
    await agent.write_bytes(
        "workspace/receipt.py", _reference_files(definition.reference)["receipt.py"].encode()
    )
    fixed = await assess(("workspace/receipt.py",))
    outside = await assess(("secret",))
    return seed, fixed, outside


def external_seed_fails_reference_passes_and_scope_is_enforced() -> None:
    dataset = datasets.compile_dataset(cases=declarations.cases())
    runtime = execution.create_runtime()

    async def execute() -> tuple[Assessment, ...]:
        agent = await runtime.create()
        try:
            await agent.execute(Execution(command=("mkdir", "workspace")))
            for name, content in _files(datasets.list_cases(selection=dataset)[0].files).items():
                await agent.write_bytes(f"workspace/{name}", content.encode())
            return await _assess_code(dataset=dataset, agent=agent)
        finally:
            await runtime.cleanup(agent, interrupted=False)

    results = asyncio.run(execute())
    assert isinstance(results[0].verification, Verification.Failed)
    assert all(isinstance(result.verification, Verification.Passed) for result in results[1:])
    assert tuple(result.scores for result in results) == (
        {"correctness": False, "scope": True},
        {"correctness": True, "scope": True},
        {"correctness": True, "scope": False},
    )


def external_answer_uses_kernel_rules_without_allocating() -> None:
    dataset = datasets.compile_dataset(cases=declarations.cases())
    agent = Environment(execute=AsyncMock(), read_bytes=AsyncMock(), write_bytes=AsyncMock())
    runtime = Runtime(create=AsyncMock(), cleanup=AsyncMock())

    async def assess(response: str) -> Assessment:
        return await assessment.assess(
            case_id="decision-review",
            selection=dataset,
            response=response,
            changed_files=(),
            agent=agent,
            runtime=runtime,
        )

    response = (
        '{"decision_was_supported":true,"change_rule":false,"reason":"Check existing behavior"}'
    )
    result = asyncio.run(assess(response))
    assert isinstance(result.verification, Verification.Unchecked)
    assert result.scores == {"correctness": True, "scope": True}
    wrong_type = asyncio.run(assess(response.replace("true", '"true"')))
    assert wrong_type.scores == {"correctness": False, "scope": True}
    cast(AsyncMock, runtime.create).assert_not_awaited()
    cast(AsyncMock, runtime.cleanup).assert_not_awaited()
    cast(AsyncMock, agent.execute).assert_not_awaited()
    cast(AsyncMock, agent.read_bytes).assert_not_awaited()
    cast(AsyncMock, agent.write_bytes).assert_not_awaited()


def _run_cli() -> int:
    with pytest.raises(SystemExit) as exited:
        runpy.run_path(cli.__file__, run_name="__main__")
    return cast(int, exited.value.code)


def offline_cli_validates_real_references(*, capsys: pytest.CaptureFixture[str]) -> None:
    assert _run_cli() == 0
    output = capsys.readouterr().out
    rows = [json.loads(line) for line in output.splitlines()]
    assert rows == [
        {"id": case_id, "verification": status, "scores": {"correctness": True, "scope": True}}
        for case_id, status in (
            ("clear-task", "passed"),
            ("known-preflight", "passed"),
            ("small-decision", "unchecked"),
            ("decision-review", "unchecked"),
        )
    ]


def offline_cli_exits_nonzero_on_grading_failure(*, capsys: pytest.CaptureFixture[str]) -> None:
    with patch.object(grading, "score_case", return_value={"correctness": False, "scope": True}):
        assert _run_cli() == 1
    assert all(
        not json.loads(line)["scores"]["correctness"]
        for line in capsys.readouterr().out.splitlines()
    )


def offline_cli_reports_harness_failure_without_success(
    *, capsys: pytest.CaptureFixture[str]
) -> None:
    result = VerificationResult(verification=Verification.HarnessError("private diagnostic"))
    with patch.object(verification, "validate_reference", new=AsyncMock(return_value=result)):
        assert _run_cli() == 1
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert all(row["verification"] == "harness_error" and row["scores"] == {} for row in rows)
    assert "private diagnostic" not in json.dumps(rows)
