"""Generic execution keeps private verification separate from candidate work."""

import asyncio
import json
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from inspect_ai.util import ExecResult
from inspect_ai.util._sandbox.local import LocalSandboxEnvironment
from pydantic import ValidationError

from evals.python.transport import (
    ExecutableChecks,
    Verification,
    grade,
    load_cases,
    workspace_files,
)
from evals.python.verification import cleanup, completion, run_verifier, verify

DRIVER = """import json, os, subprocess, sys
result = subprocess.run([sys.executable, 'solution.py'], capture_output=True, text=True)
print(json.dumps({'marker': os.environ['GENIUS_VERIFIER_MARKER'],
 'status': 'passed' if result.stdout.strip() == sys.stdin.read().strip() else 'failed',
 'detail': result.stderr, 'metadata': {'raw': result.stdout}}))
"""


def checks(**updates: object) -> ExecutableChecks:
    return ExecutableChecks.model_validate(
        {
            "inputs": ("solution.py",),
            "files": {"grader.py": DRIVER},
            "tools": {"visible.py": "raise Exception()"},
            "command": ("python3", "grader.py"),
            "stdin": "42",
            "timeout_seconds": 30,
            **updates,
        }
    )


def output(*, stdout: str, code: int = 0) -> ExecResult[str]:
    return ExecResult(success=code == 0, returncode=code, stdout=stdout, stderr="")


def envelope(**updates: object) -> str:
    return json.dumps({"marker": "secret", "status": "passed", "detail": "", **updates})


@pytest.mark.parametrize("source", ["print(42)", "print(0)"])
def test_python_inputs_execute_in_fresh_workspace(source: str) -> None:
    async def execute() -> None:
        agent = LocalSandboxEnvironment()
        agent_directory = Path(agent.directory.name)
        try:
            await agent.exec(["mkdir", "workspace"])
            await agent.write_file("workspace/solution.py", source)
            await agent.write_file("workspace/grader.py", "raise Exception('tampered')")
            with patch.object(
                LocalSandboxEnvironment,
                "sample_init",
                wraps=LocalSandboxEnvironment.sample_init,
            ) as create:
                result, metadata = await verify(checks(), agent=agent)
            assert result.status == ("passed" if source == "print(42)" else "failed")
            assert metadata == {"raw": "42\n" if source == "print(42)" else "0\n"}
            assert create.call_count == 1
            assert (agent_directory / "workspace/grader.py").read_text().endswith("tampered')")
        finally:
            await LocalSandboxEnvironment.sample_cleanup(
                "test", None, {"default": agent}, interrupted=False
            )
        assert not agent_directory.exists()

    asyncio.run(execute())


@pytest.mark.parametrize(
    ("stdout", "code"),
    [
        ("", 0),
        ("not json", 0),
        (envelope(marker="forged"), 0),
        (envelope(), 1),
        (envelope(status="unchecked"), 0),
        (envelope(status="unknown"), 0),
        (envelope(detail=True), 0),
        (envelope(metadata=[]), 0),
    ],
)
def test_invalid_completion_is_harness_error(*, stdout: str, code: int) -> None:
    result, metadata = completion(output(stdout=stdout, code=code), marker="secret")
    assert result.status == "harness_error"
    assert metadata == {}


def test_valid_completion_allows_prior_stdout() -> None:
    result, metadata = completion(output(stdout="candidate output\n" + envelope()), marker="secret")
    assert result == Verification(status="passed")
    assert metadata == {}


def test_missing_candidate_is_invalid_submission() -> None:
    async def execute() -> None:
        agent = AsyncMock(spec=LocalSandboxEnvironment)
        agent.read_file.side_effect = FileNotFoundError("solution.py")
        result, _ = await verify(checks(), agent=agent)
        assert result.status == "invalid_submission"

    asyncio.run(execute())


@pytest.mark.parametrize("error", [TimeoutError("slow"), RuntimeError("server")])
def test_cleanup_runs_when_verifier_fails(error: Exception) -> None:
    async def execute() -> None:
        agent = LocalSandboxEnvironment()
        environment = AsyncMock(spec=LocalSandboxEnvironment)
        environment.exec.side_effect = error
        try:
            await agent.exec(["mkdir", "workspace"])
            await agent.write_file("workspace/solution.py", "print(42)")
            with (
                patch.object(
                    LocalSandboxEnvironment, "sample_init", return_value={"default": environment}
                ),
                patch.object(LocalSandboxEnvironment, "sample_cleanup") as cleanup,
                patch(
                    "evals.python.verification.candidate_files", return_value={"solution.py": b""}
                ),
            ):
                result, _ = await verify(checks(), agent=agent)
            assert result.status == "harness_error"
            cleanup.assert_awaited_once()
        finally:
            await LocalSandboxEnvironment.sample_cleanup(
                "test", None, {"default": agent}, interrupted=False
            )

    asyncio.run(execute())


def test_workspace_creation_failure_is_reported() -> None:
    async def execute() -> None:
        environment = AsyncMock(spec=LocalSandboxEnvironment)
        environment.exec.return_value = output(stdout="", code=1)
        with pytest.raises(RuntimeError, match="create verifier workspace"):
            await run_verifier(checks(), environment=environment, inputs={})

    asyncio.run(execute())


def test_cancellation_cleans_created_environment() -> None:
    async def execute() -> None:
        agent = LocalSandboxEnvironment()
        environment = AsyncMock(spec=LocalSandboxEnvironment)
        environment.exec.side_effect = asyncio.CancelledError()
        try:
            await agent.exec(["mkdir", "workspace"])
            await agent.write_file("workspace/solution.py", "")
            with (
                patch.object(
                    LocalSandboxEnvironment, "sample_init", return_value={"default": environment}
                ),
                patch.object(LocalSandboxEnvironment, "sample_cleanup") as cleanup,
                patch(
                    "evals.python.verification.candidate_files", return_value={"solution.py": b""}
                ),
                pytest.raises(asyncio.CancelledError),
            ):
                await verify(checks(), agent=agent)
            assert cleanup.call_args.kwargs["interrupted"]
        finally:
            await LocalSandboxEnvironment.sample_cleanup(
                "test", None, {"default": agent}, interrupted=False
            )

    asyncio.run(execute())


@pytest.mark.parametrize(
    "updates",
    [
        {"inputs": ("../bad.py",)},
        {"inputs": ("/bad.py",)},
        {"inputs": ("solution.py", "solution.py")},
        {"files": {"solution.py": "bad"}},
        {"command": ("",)},
        {"timeout_seconds": 0},
    ],
)
def test_invalid_executable_contract_is_rejected(updates: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        checks(**updates)


@pytest.mark.parametrize(
    "status", ["unchecked", "passed", "failed", "invalid_submission", "timed_out"]
)
def test_typed_status_reaches_kernel(status: str) -> None:
    scores = grade(
        "clear-task",
        response="",
        changed_files=(),
        verification=Verification.model_validate({"status": status}),
    )
    assert scores["correctness"] == (status == "passed")


def test_kernel_refuses_harness_error() -> None:

    with pytest.raises(subprocess.CalledProcessError):
        grade(
            "clear-task",
            response="",
            changed_files=(),
            verification=Verification(status="harness_error", detail="server failed"),
        )


def test_private_artifacts_are_excluded_from_public_files() -> None:

    for case in load_cases():
        if isinstance(case.checks, ExecutableChecks):
            assert not case.checks.files.keys() & workspace_files(case).keys()


def test_candidate_inspection_failure_is_harness_error() -> None:
    async def execute() -> None:
        agent = AsyncMock(spec=LocalSandboxEnvironment)
        agent.exec.return_value = output(stdout="", code=2)
        result, _ = await verify(checks(), agent=agent)
        assert result.status == "harness_error"

    asyncio.run(execute())


def test_cleanup_finishes_when_cancelled() -> None:
    async def execute() -> None:
        agent = LocalSandboxEnvironment()
        started = asyncio.Event()
        finished = asyncio.Event()

        async def finish(*args: object, **kwargs: object) -> None:
            started.set()
            await asyncio.sleep(0)
            finished.set()

        try:
            with patch.object(LocalSandboxEnvironment, "sample_cleanup", side_effect=finish):
                pending = asyncio.create_task(
                    cleanup(agent, environments={"default": agent}, interrupted=False)
                )
                await started.wait()
                pending.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await pending
            assert finished.is_set()
        finally:
            await LocalSandboxEnvironment.sample_cleanup(
                "test", None, {"default": agent}, interrupted=False
            )

    asyncio.run(execute())


def test_missing_file_check_works_for_remote_read_implementations() -> None:
    async def execute() -> None:
        agent = AsyncMock(spec=LocalSandboxEnvironment)
        agent.exec.return_value = output(stdout="", code=1)
        result, _ = await verify(checks(), agent=agent)
        assert result.status == "invalid_submission"
        agent.read_file.assert_not_awaited()

    asyncio.run(execute())


@pytest.mark.parametrize("stage", ["read", "provision", "transfer"])
def test_infrastructure_timeouts_are_harness_errors(stage: str) -> None:
    async def execute() -> None:
        agent = LocalSandboxEnvironment()
        environment = AsyncMock(spec=LocalSandboxEnvironment)
        environment.exec.return_value = output(stdout="")
        failures = {
            "read": patch.object(agent, "read_file", side_effect=TimeoutError("read")),
            "provision": patch.object(
                LocalSandboxEnvironment, "sample_init", side_effect=TimeoutError("provision")
            ),
            "transfer": patch.object(
                environment, "write_file", side_effect=TimeoutError("transfer")
            ),
        }
        try:
            await agent.exec(["mkdir", "workspace"])
            await agent.write_file("workspace/solution.py", "print(42)")
            with (
                patch.object(
                    LocalSandboxEnvironment, "sample_init", return_value={"default": environment}
                ),
                patch.object(LocalSandboxEnvironment, "sample_cleanup"),
                failures[stage],
            ):
                result, _ = await verify(checks(), agent=agent)
            assert result.status == "harness_error"
        finally:
            await LocalSandboxEnvironment.sample_cleanup(
                "test", None, {"default": agent}, interrupted=False
            )

    asyncio.run(execute())


def test_verifier_execution_deadline_is_preserved() -> None:
    async def execute() -> None:
        agent = LocalSandboxEnvironment()
        environment = AsyncMock(spec=LocalSandboxEnvironment)
        environment.exec.side_effect = [output(stdout=""), TimeoutError("command deadline")]
        try:
            with (
                patch.object(
                    LocalSandboxEnvironment, "sample_init", return_value={"default": environment}
                ),
                patch.object(LocalSandboxEnvironment, "sample_cleanup") as finish,
                patch(
                    "evals.python.verification.candidate_files", return_value={"solution.py": b""}
                ),
            ):
                result, _ = await verify(checks(), agent=agent)
            assert result.status == "timed_out"
            finish.assert_awaited_once()
        finally:
            await LocalSandboxEnvironment.sample_cleanup(
                "test", None, {"default": agent}, interrupted=False
            )

    asyncio.run(execute())
