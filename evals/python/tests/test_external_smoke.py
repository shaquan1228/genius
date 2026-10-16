"""A Python-owned dataset exercises the real kernel and generic verifier."""

import asyncio
import json
import runpy
from typing import cast
from unittest.mock import AsyncMock, patch

import pytest

from evals.python import commands, query
from evals.python.integrations.smoke import __main__ as cli
from evals.python.integrations.smoke import declarations


def test_python_smoke_compiles_to_public_cases() -> None:
    definitions = declarations.cases()
    dataset = query.CompileDataset(cases=definitions)
    cases = query.Cases(selection=dataset)
    assert tuple(case.id for case in cases) == tuple(case.id for case in definitions)
    assert all(set(case.model_dump()) == {"id", "skill", "prompt", "files"} for case in cases)


def test_default_smoke_uses_python_owned_cases() -> None:
    definitions = declarations.cases()
    dataset = query.LoadDataset()
    assert dataset is query.CompileDataset(cases=definitions)
    assert tuple(dataset.cases) == (
        "clear-task",
        "known-preflight",
        "small-decision",
        "decision-review",
    )
    assert tuple(dataset.cases["clear-task"].files) == ("receipt.py", "test_receipt.py")


@pytest.mark.parametrize(("initial", "requested"), [(15, 15), (0, 30), (-1, 30), (15, 0), (15, -1)])
def test_timeout_variants_require_a_real_positive_change(initial: int, *, requested: int) -> None:
    with pytest.raises(ValueError, match="distinct positive"):
        declarations.timeout(initial=initial, requested=requested)


def test_python_smoke_keeps_checks_and_references_private() -> None:
    definitions = declarations.cases()
    dataset = query.CompileDataset(cases=definitions)
    cases = query.Cases(selection=dataset)
    code = definitions[0]
    assert isinstance(code.criterion, query.CodeCriterion)
    assert code.criterion.verifier.stdin not in cases[0].model_dump_json()
    assert code.reference.edits["receipt.py"] not in cases[0].files.values()
    assert "verifier.py" not in cases[0].files


async def assess_code(
    *, dataset: query.Dataset, agent: commands.Environment
) -> tuple[commands.Assessment, ...]:
    runtime = query.ExecutionRuntime()

    async def assess(changed_files: tuple[str, ...]) -> commands.Assessment:
        return await commands.AssessCase(
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
        "workspace/receipt.py", definition.reference.edits["receipt.py"].encode()
    )
    fixed = await assess(("workspace/receipt.py",))
    outside = await assess(("secret",))
    return seed, fixed, outside


def test_external_seed_fails_reference_passes_and_scope_is_enforced() -> None:
    dataset = query.CompileDataset(cases=declarations.cases())
    runtime = query.ExecutionRuntime()

    async def execute() -> tuple[commands.Assessment, ...]:
        agent = await runtime.create()
        try:
            await agent.execute(commands.Execution(command=("mkdir", "workspace")))
            for name, content in query.Cases(selection=dataset)[0].files.items():
                await agent.write_bytes(f"workspace/{name}", content.encode())
            return await assess_code(dataset=dataset, agent=agent)
        finally:
            await runtime.cleanup(agent, interrupted=False)

    results = asyncio.run(execute())
    assert tuple(result.verification.status for result in results) == ("failed", "passed", "passed")
    assert tuple(result.scores for result in results) == (
        {"correctness": False, "scope": True},
        {"correctness": True, "scope": True},
        {"correctness": True, "scope": False},
    )


def test_external_answer_uses_kernel_rules_without_allocating() -> None:
    dataset = query.CompileDataset(cases=declarations.cases())
    agent = commands.Environment(
        execute=AsyncMock(), read_bytes=AsyncMock(), write_bytes=AsyncMock()
    )
    runtime = commands.Runtime(create=AsyncMock(), cleanup=AsyncMock())

    async def assess(response: str) -> commands.Assessment:
        return await commands.AssessCase(
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
    assert result.verification.status == "unchecked"
    assert result.scores == {"correctness": True, "scope": True}
    wrong_type = asyncio.run(assess(response.replace("true", '"true"')))
    assert wrong_type.scores == {"correctness": False, "scope": True}
    cast(AsyncMock, runtime.create).assert_not_awaited()
    cast(AsyncMock, runtime.cleanup).assert_not_awaited()
    cast(AsyncMock, agent.execute).assert_not_awaited()
    cast(AsyncMock, agent.read_bytes).assert_not_awaited()
    cast(AsyncMock, agent.write_bytes).assert_not_awaited()


def run_cli() -> int:
    with pytest.raises(SystemExit) as exited:
        runpy.run_path(cli.__file__, run_name="__main__")
    return cast(int, exited.value.code)


def test_offline_cli_validates_real_references(*, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_cli() == 0
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


def test_offline_cli_exits_nonzero_on_grading_failure(
    *, capsys: pytest.CaptureFixture[str]
) -> None:
    with patch.object(query, "GradeCase", return_value={"correctness": False, "scope": True}):
        assert run_cli() == 1
    assert all(
        not json.loads(line)["scores"]["correctness"]
        for line in capsys.readouterr().out.splitlines()
    )


def test_offline_cli_reports_harness_failure_without_success(
    *, capsys: pytest.CaptureFixture[str]
) -> None:
    result = commands.VerificationResult(
        verification=query.Verification(status="harness_error", detail="private diagnostic")
    )
    with patch.object(commands, "ValidateReference", new=AsyncMock(return_value=result)):
        assert run_cli() == 1
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert all(row["verification"] == "harness_error" and row["scores"] == {} for row in rows)
    assert "private diagnostic" not in json.dumps(rows)
