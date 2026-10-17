"""Public verification transformations preserve lifecycle and canonical evidence."""

import asyncio
import json
from collections.abc import Callable
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from typing import assert_type, cast
from unittest.mock import AsyncMock, patch

import pytest
from inspect_ai.util import ExecResult
from inspect_ai.util._sandbox.local import LocalSandboxEnvironment
from pydantic import ValidationError

from evals.python import assessment, datasets, verification
from evals.python.assessment import Assessment
from evals.python.execution import Completion as ProcessCompletion
from evals.python.execution import Environment, Execution, Runtime
from evals.python.grading import score_case
from evals.python.integrations.inspect.environments import environment, runtime
from evals.python.tests.declarations import _copy_case, _declaration, _reference_files
from evals.python.tests.projections import reference, verifier
from evals.python.verification import VerificationResult
from kernel import (
    Artifact,
    Completion,
    Content,
    Criterion,
    File,
    Fixture,
    GradingError,
    Reference,
    Task,
    Verification,
    Verifier,
)
from kernel import (
    ValidationError as DomainValidationError,
)

DRIVER = """import json, os, subprocess, sys
result = subprocess.run([sys.executable, 'solution.py'], capture_output=True, text=True)
print(json.dumps({'marker': os.environ['GENIUS_VERIFIER_MARKER'],
 'status': 'passed' if result.stdout.strip() == sys.stdin.read().strip() else 'failed',
 'detail': result.stderr, 'metadata': {'raw': result.stdout}}))
"""


def _checks(**updates: object) -> Verifier:
    values = {
        "inputs": ("solution.py",),
        "files": [Artifact.create(path="grader.py", content=Content.create(inline=DRIVER))],
        "tools": [
            Artifact.create(path="visible.py", content=Content.create(inline="raise Exception()"))
        ],
        "command": ("python3", "grader.py"),
        "stdin": "42",
        "timeout_seconds": 30,
        **updates,
    }
    constructor = cast(Callable[..., Verifier], Verifier.create)
    return constructor(**values)


def _output(*, stdout: str = "", code: int = 0) -> ProcessCompletion:
    return ProcessCompletion(returncode=code, stdout=stdout)


def _envelope(**updates: object) -> str:
    return json.dumps({"marker": "secret", "status": "passed", "detail": "", **updates})


def _agent_port() -> Environment:
    return Environment(
        execute=AsyncMock(return_value=_output()),
        read_bytes=AsyncMock(return_value=b"print(42)"),
        write_bytes=AsyncMock(),
    )


def _grader_port(*, stdout: str | None = None, code: int = 0) -> Environment:
    result = _agent_port()
    cast(AsyncMock, result.execute).side_effect = [
        _output(),
        _output(stdout=_envelope() if stdout is None else stdout, code=code),
    ]
    return result


def _runtime_port(grader: Environment) -> Runtime:
    return Runtime(create=AsyncMock(return_value=grader), cleanup=AsyncMock())


async def _run(agent: Environment, *, runtime: Runtime) -> VerificationResult:
    with (
        patch("kernel.projection.verifier", return_value=_checks()),
        patch("evals.python.verification.token_hex", return_value="secret"),
    ):
        return assert_type(
            await verification.verify_case(case_id="clear-task", agent=agent, runtime=runtime),
            VerificationResult,
        )


@pytest.mark.parametrize("source", ["print(42)", "print(0)"])
def python_inputs_execute_in_fresh_workspace(source: str) -> None:
    async def execute() -> None:
        agent = LocalSandboxEnvironment()
        directory = Path(agent.directory.name)
        try:
            await agent.exec(["mkdir", "workspace"])
            await agent.write_file("workspace/solution.py", source)
            await agent.write_file("workspace/grader.py", "raise Exception('tampered')")
            with patch("kernel.projection.verifier", return_value=_checks()):
                result = await verification.verify_case(
                    case_id="clear-task", agent=environment(agent), runtime=runtime(agent)
                )
            assert isinstance(
                result.verification,
                Verification.Passed if source == "print(42)" else Verification.Failed,
            )
            assert result.metadata == {"raw": "42\n" if source == "print(42)" else "0\n"}
            assert (directory / "workspace/grader.py").read_text().endswith("tampered')")
        finally:
            await LocalSandboxEnvironment.sample_cleanup(
                "test", None, {"default": agent}, interrupted=False
            )
        assert not directory.exists()

    asyncio.run(execute())


@pytest.mark.parametrize(
    ("stdout", "code"),
    [
        ("", 0),
        ("not json", 0),
        (_envelope(marker="forged"), 0),
        (_envelope(), 1),
        (_envelope(status="unchecked"), 0),
        (_envelope(status="unknown"), 0),
        (_envelope(detail=True), 0),
        (_envelope(metadata=[]), 0),
        (_envelope(marker="forged", metadata={"untrusted": True}), 0),
    ],
)
def invalid_completion_discards_metadata(*, stdout: str, code: int) -> None:
    async def execute() -> None:
        result = await _run(
            _agent_port(), runtime=_runtime_port(_grader_port(stdout=stdout, code=code))
        )
        assert isinstance(result.verification, Verification.HarnessError)
        assert result.metadata == {}

    asyncio.run(execute())


def valid_completion_allows_prior_stdout_and_freezes_nested_metadata() -> None:
    async def execute() -> None:
        result = await _run(
            _agent_port(),
            runtime=_runtime_port(
                _grader_port(
                    stdout="candidate output\n"
                    + _envelope(metadata={"nested": {"items": [True, None, 4.2]}})
                )
            ),
        )
        assert isinstance(result.verification, Verification.Passed)
        assert result.metadata == {"nested": {"items": (True, None, 4.2)}}
        with pytest.raises(TypeError):
            result.metadata["nested"]["items"] = ()  # type: ignore[index]
        with pytest.raises(FrozenInstanceError):
            result.verification = Verification.Failed()  # type: ignore[misc]

    asyncio.run(execute())


@pytest.mark.parametrize("missing", ["inspection", "read"])
def missing_candidate_is_invalid_before_allocation(missing: str) -> None:
    async def execute() -> None:
        agent = _agent_port()
        if missing == "inspection":
            cast(AsyncMock, agent.execute).return_value = _output(code=1)
        else:
            cast(AsyncMock, agent.read_bytes).side_effect = FileNotFoundError("solution.py")
        ports = _runtime_port(_grader_port())
        result = await _run(agent, runtime=ports)
        assert isinstance(result.verification, Verification.InvalidSubmission)
        cast(AsyncMock, ports.create).assert_not_awaited()
        cast(AsyncMock, ports.cleanup).assert_not_awaited()
        if missing == "inspection":
            cast(AsyncMock, agent.read_bytes).assert_not_awaited()

    asyncio.run(execute())


@pytest.mark.parametrize("stage", ["inspection", "read", "provision", "mkdir", "transfer"])
@pytest.mark.parametrize("error", [TimeoutError("slow"), RuntimeError("server")])
def infrastructure_failures_are_harness_errors(*, stage: str, error: Exception) -> None:
    async def execute() -> None:
        agent, grader = _agent_port(), _grader_port()
        ports = _runtime_port(grader)
        effects = {
            "inspection": agent.execute,
            "read": agent.read_bytes,
            "provision": ports.create,
            "mkdir": grader.execute,
            "transfer": grader.write_bytes,
        }
        cast(AsyncMock, effects[stage]).side_effect = error
        result = await _run(agent, runtime=ports)
        assert isinstance(result.verification, Verification.HarnessError)
        assert result.metadata == {}
        assert cast(AsyncMock, ports.cleanup).await_count == (stage in {"mkdir", "transfer"})

    asyncio.run(execute())


def workspace_creation_failure_is_reported_and_cleaned() -> None:
    async def execute() -> None:
        grader = _grader_port()
        cast(AsyncMock, grader.execute).side_effect = [_output(code=1)]
        ports = _runtime_port(grader)
        result = await _run(_agent_port(), runtime=ports)
        assert isinstance(result.verification, Verification.HarnessError)
        assert "create verifier workspace" in result.detail
        cast(AsyncMock, ports.cleanup).assert_awaited_once_with(grader, interrupted=False)

    asyncio.run(execute())


def only_verifier_execution_deadline_is_timed_out() -> None:
    async def execute() -> None:
        grader = _grader_port()
        cast(AsyncMock, grader.execute).side_effect = [_output(), TimeoutError("command deadline")]
        ports = _runtime_port(grader)
        result = await _run(_agent_port(), runtime=ports)
        assert isinstance(result.verification, Verification.TimedOut)
        assert result.detail == "command deadline"
        cast(AsyncMock, ports.cleanup).assert_awaited_once_with(grader, interrupted=False)

    asyncio.run(execute())


def same_environment_is_rejected_without_destroying_candidate() -> None:
    async def execute() -> None:
        agent = _agent_port()
        ports = _runtime_port(agent)
        result = await _run(agent, runtime=ports)
        assert isinstance(result.verification, Verification.HarnessError)
        cast(AsyncMock, ports.cleanup).assert_not_awaited()

    asyncio.run(execute())


def cancellation_cleans_created_environment() -> None:
    async def execute() -> None:
        grader = _grader_port()
        cast(AsyncMock, grader.execute).side_effect = asyncio.CancelledError()
        ports = _runtime_port(grader)
        with pytest.raises(asyncio.CancelledError):
            await _run(_agent_port(), runtime=ports)
        cast(AsyncMock, ports.cleanup).assert_awaited_once_with(grader, interrupted=True)

    asyncio.run(execute())


@pytest.mark.parametrize("fails", [False, True])
def cancelled_allocation_waits_for_eventual_environment(*, fails: bool) -> None:
    async def execute() -> None:
        started, release = asyncio.Event(), asyncio.Event()
        grader = _grader_port()

        async def create() -> Environment:
            started.set()
            await release.wait()
            if fails:
                raise RuntimeError("allocation failed")
            return grader

        ports = Runtime(create=create, cleanup=AsyncMock())
        pending = asyncio.create_task(_run(_agent_port(), runtime=ports))
        await started.wait()
        pending.cancel()
        await asyncio.sleep(0)
        pending.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await pending
        assert cast(AsyncMock, ports.cleanup).await_count == (not fails)
        if not fails:
            cast(AsyncMock, ports.cleanup).assert_awaited_once_with(grader, interrupted=True)

    asyncio.run(execute())


def cleanup_finishes_after_repeated_cancellation() -> None:
    async def execute() -> None:
        started, release, finished = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def cleanup(target: Environment, *, interrupted: bool) -> None:
            started.set()
            await release.wait()
            finished.set()

        ports = Runtime(create=AsyncMock(return_value=_grader_port()), cleanup=cleanup)
        pending = asyncio.create_task(_run(_agent_port(), runtime=ports))
        await started.wait()
        pending.cancel()
        await asyncio.sleep(0)
        pending.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await pending
        assert finished.is_set()

    asyncio.run(execute())


@pytest.mark.parametrize(
    "updates",
    [
        {"inputs": ("../bad.py",)},
        {"inputs": ("/bad.py",)},
        {"command": ("",)},
        {"timeout_seconds": 0},
    ],
)
def invalid_executable_contract_is_rejected(updates: dict[str, object]) -> None:
    case = _declaration()
    with pytest.raises(DomainValidationError):
        datasets.compile_dataset(
            cases=(
                _copy_case(
                    case,
                    fixture=Fixture.create(
                        files=[File.create(path="solution.py", contents="print(42)")]
                    ),
                    criterion=Criterion.create(code=_checks(**updates)),
                    allowed_files=("solution.py",),
                    reference=Reference.create(
                        edits=Fixture.create(files=[]), completion=Completion.create(plain="")
                    ),
                ),
            )
        )


@pytest.mark.parametrize(
    "status",
    [
        Verification.Unchecked(),
        Verification.Passed(),
        Verification.Failed(),
        Verification.InvalidSubmission(),
        Verification.TimedOut(),
    ],
)
def typed_status_reaches_kernel(status: Verification.Value) -> None:
    scores = score_case(
        case_id="clear-task",
        response="",
        changed_files=(),
        verification=status,
    )
    assert scores["correctness"] == isinstance(status, Verification.Passed)


def kernel_refuses_harness_error() -> None:
    with pytest.raises(GradingError):
        score_case(
            case_id="clear-task",
            response="",
            changed_files=(),
            verification=Verification.HarnessError(detail="server failed"),
        )


def private_artifacts_are_excluded_from_public_files() -> None:
    for case in datasets.list_cases():
        executable = verifier(case.id)
        if isinstance(executable, Verifier):
            assert (
                not {artifact.path: artifact.content for artifact in executable.files}.keys()
                & {artifact.path: artifact.content for artifact in case.files}.keys()
            )


def public_answer_only_verification_never_allocates() -> None:
    async def execute() -> None:
        ports = _runtime_port(_grader_port())
        with patch("kernel.projection.verifier", return_value=None):
            result = await verification.verify_case(
                case_id="small-decision", agent=_agent_port(), runtime=ports
            )
        assert isinstance(result.verification, Verification.Unchecked)
        assert result.metadata == {}
        cast(AsyncMock, ports.create).assert_not_awaited()

    asyncio.run(execute())


def assessment_grades_canonical_observation_and_freezes_scores() -> None:
    async def execute() -> None:
        evidence = VerificationResult(verification=Verification.Unchecked())
        expected = score_case(
            case_id="clear-task", response="answer", changed_files=("receipt.py",)
        )
        with patch.object(verification, "verify_case", return_value=evidence):
            result = assert_type(
                await assessment.assess(
                    case_id="clear-task",
                    response="answer",
                    changed_files=("receipt.py",),
                    agent=_agent_port(),
                    runtime=_runtime_port(_grader_port()),
                ),
                Assessment,
            )
        assert isinstance(result.evidence.verification, Verification.Unchecked)
        assert result.evidence is evidence
        assert not isinstance(result, VerificationResult)
        assert result.scores == expected
        with pytest.raises(TypeError):
            result.scores["correctness"] = True  # type: ignore[index]

    asyncio.run(execute())


def assessment_owns_immutable_scores_and_retains_evidence() -> None:
    evidence = VerificationResult(
        verification=Verification.Passed(), metadata={"nested": {"items": (True,)}}
    )
    scores = {"correctness": True}
    result = Assessment(evidence=evidence, scores=scores)
    scores["correctness"] = False
    assert result.scores == {"correctness": True}
    assert result.evidence.metadata == {"nested": {"items": (True,)}}
    for name in ("evidence", "scores"):
        with pytest.raises(FrozenInstanceError):
            setattr(result, name, None)


def assessment_refuses_harness_error_before_grading() -> None:
    async def execute() -> None:
        with (
            patch("kernel.projection.verifier", return_value=_checks()),
            patch("kernel.grader.grade") as grading,
            pytest.raises(RuntimeError, match="Verification harness error"),
        ):
            await assessment.assess(
                case_id="clear-task",
                response="",
                changed_files=(),
                agent=_agent_port(),
                runtime=_runtime_port(_grader_port(stdout="invalid")),
            )
        grading.assert_not_called()

    asyncio.run(execute())


@pytest.mark.parametrize("code", [0, 1, 2])
def candidate_inspection_classifies_missing_and_infrastructure(code: int) -> None:
    async def execute() -> None:
        sandbox = AsyncMock(spec=LocalSandboxEnvironment)
        sandbox.exec.return_value = ExecResult(
            returncode=code, success=code == 0, stdout="", stderr="server"
        )
        sandbox.read_file.return_value = b"print(42)"
        result = await _run(environment(sandbox), runtime=_runtime_port(_grader_port()))
        assert isinstance(
            result.verification,
            {
                0: Verification.Passed,
                1: Verification.InvalidSubmission,
                2: Verification.HarnessError,
            }[code],
        )
        if code == 2:
            assert "inspect candidate" in result.detail

    asyncio.run(execute())


def execution_environment_is_immutable_snapshot() -> None:
    values = {"marker": "original"}
    request = Execution(command=("python3",), env=values)
    values["marker"] = "changed"
    assert request.env == {"marker": "original"}


def reference_uses_default_local_adapter_and_real_ocaml() -> None:
    async def execute() -> VerificationResult:
        return assert_type(
            await verification.validate_reference(case_id="clear-task"),
            VerificationResult,
        )

    result = asyncio.run(execute())
    assert isinstance(result.verification, Verification.Passed), result.detail


def answer_only_reference_never_allocates() -> None:
    ports = _runtime_port(_grader_port())
    with patch("kernel.projection.verifier", return_value=None):
        result = asyncio.run(
            verification.validate_reference(case_id="small-decision", runtime=ports)
        )
    assert isinstance(result.verification, Verification.Unchecked)
    cast(AsyncMock, ports.create).assert_not_awaited()


def reference_candidate_and_grader_are_both_cleaned() -> None:
    async def execute() -> None:
        agent, grader = _agent_port(), _grader_port()
        ports = _runtime_port(grader)
        cast(AsyncMock, ports.create).side_effect = [agent, grader]
        with (
            patch("kernel.projection.verifier", return_value=_checks()),
            patch(
                "kernel.projection.reference",
                return_value=Reference.create(
                    edits=Fixture.create(
                        files=[File.create(path="solution.py", contents="print(42)")]
                    ),
                    completion=Completion.create(plain=""),
                ),
            ),
            patch("evals.python.verification.token_hex", return_value="secret"),
        ):
            result = await verification.validate_reference(case_id="clear-task", runtime=ports)
        assert isinstance(result.verification, Verification.Passed)
        assert cast(AsyncMock, ports.cleanup).await_count == 2
        cast(AsyncMock, agent.write_bytes).assert_awaited_once_with(
            "workspace/solution.py", b"print(42)"
        )
        assert cast(AsyncMock, ports.cleanup).call_args_list[-1].args == (agent,)

    asyncio.run(execute())


@pytest.mark.parametrize("stage", ["allocation", "mkdir", "transfer", "cancel"])
def reference_setup_failures_preserve_lifecycle(stage: str) -> None:
    async def execute() -> None:
        agent = _agent_port()
        ports = _runtime_port(agent)
        effects = {
            "allocation": ports.create,
            "mkdir": agent.execute,
            "transfer": agent.write_bytes,
            "cancel": agent.write_bytes,
        }
        error = asyncio.CancelledError() if stage == "cancel" else TimeoutError("setup")
        cast(AsyncMock, effects[stage]).side_effect = error
        with (
            patch("kernel.projection.verifier", return_value=_checks()),
            patch(
                "kernel.projection.reference",
                return_value=Reference.create(
                    edits=Fixture.create(files=[File.create(path="solution.py", contents="")]),
                    completion=Completion.create(plain=""),
                ),
            ),
        ):
            if stage == "cancel":
                with pytest.raises(asyncio.CancelledError):
                    await verification.validate_reference(case_id="clear-task", runtime=ports)
            else:
                result = await verification.validate_reference(case_id="clear-task", runtime=ports)
                assert isinstance(result.verification, Verification.HarnessError)
        assert cast(AsyncMock, ports.cleanup).await_count == (stage != "allocation")
        if stage != "allocation":
            cast(AsyncMock, ports.cleanup).assert_awaited_once_with(
                agent, interrupted=stage == "cancel"
            )

    asyncio.run(execute())


def reference_nonzero_mkdir_is_harness_error() -> None:
    async def execute() -> None:
        agent = _agent_port()
        cast(AsyncMock, agent.execute).return_value = _output(code=1)
        with (
            patch("kernel.projection.verifier", return_value=_checks()),
            patch(
                "kernel.projection.reference",
                return_value=Reference.create(
                    edits=Fixture.create(files=[]), completion=Completion.create(plain="")
                ),
            ),
        ):
            result = await verification.validate_reference(
                case_id="clear-task", runtime=_runtime_port(agent)
            )
        assert isinstance(result.verification, Verification.HarnessError)
        assert "create reference workspace" in result.detail

    asyncio.run(execute())


def assessment_replaces_untrusted_verification_with_execution() -> None:
    async def execute() -> None:
        untrusted = Verification.Failed()
        prior_scores = score_case(
            case_id="clear-task",
            response="",
            changed_files=(),
            verification=untrusted,
        )
        with (
            patch("kernel.projection.verifier", return_value=_checks()),
            patch("evals.python.verification.token_hex", return_value="secret"),
        ):
            result = await assessment.assess(
                case_id="clear-task",
                response="",
                changed_files=(),
                agent=_agent_port(),
                runtime=_runtime_port(_grader_port()),
            )
        assert isinstance(result.evidence.verification, Verification.Passed)
        assert result.scores["correctness"]
        assert not prior_scores["correctness"]
        assert isinstance(untrusted, Verification.Failed)

    asyncio.run(execute())


def assessment_runs_actual_private_checks_before_grading() -> None:
    async def execute() -> None:
        agent = LocalSandboxEnvironment()
        try:
            await agent.exec(["mkdir", "workspace"])
            for name, contents in _reference_files(reference("clear-task")).items():
                await agent.write_file(f"workspace/{name}", contents)
            result = await assessment.assess(
                case_id="clear-task",
                response="",
                changed_files=(),
                agent=environment(agent),
                runtime=runtime(agent),
            )
            assert isinstance(result.evidence.verification, Verification.Passed)
            assert result.scores["correctness"]
        finally:
            await LocalSandboxEnvironment.sample_cleanup(
                "test", None, {"default": agent}, interrupted=False
            )

    asyncio.run(execute())


@pytest.mark.parametrize("cancelled", [False, True])
def cleanup_failure_preserves_cancellation(*, cancelled: bool) -> None:
    async def execute() -> None:
        grader = _grader_port()
        if cancelled:
            cast(AsyncMock, grader.execute).side_effect = asyncio.CancelledError()
        ports = _runtime_port(grader)
        cast(AsyncMock, ports.cleanup).side_effect = RuntimeError("cleanup failed")
        if cancelled:
            with pytest.raises(asyncio.CancelledError):
                await _run(_agent_port(), runtime=ports)
        else:
            result = await _run(_agent_port(), runtime=ports)
            assert isinstance(result.verification, Verification.HarnessError)
            assert result.detail == "cleanup failed"

    asyncio.run(execute())


def cancelled_cleanup_failure_still_propagates_cancellation() -> None:
    async def execute() -> None:
        started, release = asyncio.Event(), asyncio.Event()

        async def cleanup(target: Environment, *, interrupted: bool) -> None:
            started.set()
            await release.wait()
            raise RuntimeError("cleanup failed")

        ports = Runtime(create=AsyncMock(return_value=_grader_port()), cleanup=cleanup)
        pending = asyncio.create_task(_run(_agent_port(), runtime=ports))
        await started.wait()
        pending.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await pending

    asyncio.run(execute())


def cancelled_allocation_never_cleans_candidate() -> None:
    async def execute() -> None:
        started, release = asyncio.Event(), asyncio.Event()
        agent = _agent_port()

        async def create() -> Environment:
            started.set()
            await release.wait()
            return agent

        ports = Runtime(create=create, cleanup=AsyncMock())
        pending = asyncio.create_task(_run(agent, runtime=ports))
        await started.wait()
        pending.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await pending
        cast(AsyncMock, ports.cleanup).assert_not_awaited()

    asyncio.run(execute())


def unresolved_verifier_resource_is_a_harness_error() -> None:
    agent, grader = _agent_port(), _grader_port()
    ports = _runtime_port(grader)
    checks = _checks(
        files=[Artifact.create(path="grader.py", content=Content.create(resource="unresolved"))]
    )
    with patch("kernel.projection.verifier", return_value=checks):
        result = asyncio.run(
            verification.verify_case(case_id="clear-task", agent=agent, runtime=ports)
        )
    assert isinstance(result.verification, Verification.HarnessError)
    assert result.detail == "Verifier resources must be resolved before execution"
    cast(AsyncMock, grader.write_bytes).assert_not_awaited()
    cast(AsyncMock, ports.cleanup).assert_awaited_once_with(grader, interrupted=False)


def assessment_pins_named_dataset_until_grading_and_next_operation_reloads() -> None:
    async def execute() -> None:
        current = _declaration()
        agent, grader = _agent_port(), _grader_port()

        def cases() -> tuple[Task, ...]:
            return (current,)

        async def create() -> Environment:
            nonlocal current
            current = _declaration(code=False)
            return grader

        ports = Runtime(create=create, cleanup=AsyncMock())
        with (
            patch(
                "evals.python.datasets._module",
                return_value=SimpleNamespace(info=None, cases=cases),
            ),
            patch("evals.python.verification.token_hex", return_value="secret"),
        ):
            first = await assessment.assess(
                case_id="external",
                selection="changing",
                response="done",
                changed_files=(),
                agent=agent,
                runtime=ports,
            )
            second = await assessment.assess(
                case_id="external",
                selection="changing",
                response="done",
                changed_files=(),
                agent=agent,
                runtime=ports,
            )
        assert isinstance(first.evidence.verification, Verification.Passed)
        assert first.scores["correctness"]
        assert isinstance(second.evidence.verification, Verification.Unchecked)
        assert not second.scores["correctness"]
        cast(AsyncMock, ports.cleanup).assert_awaited_once_with(grader, interrupted=False)

    asyncio.run(execute())


def reference_pins_named_dataset_before_awaiting_allocation() -> None:
    async def execute() -> None:
        current = _declaration()
        agent, grader = _agent_port(), _grader_port()
        allocated = 0

        def cases() -> tuple[Task, ...]:
            return (current,)

        async def create() -> Environment:
            nonlocal allocated, current
            await asyncio.sleep(0)
            allocated += 1
            current = _copy_case(
                _declaration(code=False),
                reference=Reference.create(
                    edits=Fixture.create(files=[File.create(path="main.py", contents="changed")]),
                    completion=Completion.create(plain="changed"),
                ),
            )
            return agent if allocated == 1 else grader

        ports = Runtime(create=create, cleanup=AsyncMock())
        with (
            patch(
                "evals.python.datasets._module",
                return_value=SimpleNamespace(info=None, cases=cases),
            ),
            patch("evals.python.verification.token_hex", return_value="secret"),
        ):
            result = await verification.validate_reference(
                case_id="external", selection="changing", runtime=ports
            )
        assert isinstance(result.verification, Verification.Passed)
        cast(AsyncMock, agent.write_bytes).assert_awaited_once_with("workspace/main.py", b"fixed")
        assert cast(AsyncMock, ports.cleanup).await_count == 2

    asyncio.run(execute())


@pytest.mark.parametrize("reference", [False, True])
@pytest.mark.parametrize(
    ("selection", "case_id", "error"),
    [
        ("../outside", "external", ValidationError),
        ("does-not-exist", "external", ModuleNotFoundError),
        ("smoke", "missing", KeyError),
    ],
)
def compound_operations_reject_invalid_selection_before_execution(
    *, reference: bool, selection: str, case_id: str, error: type[Exception]
) -> None:
    async def execute() -> None:
        agent = _agent_port()
        ports = _runtime_port(_grader_port())
        operation = (
            verification.validate_reference(case_id=case_id, selection=selection, runtime=ports)
            if reference
            else assessment.assess(
                case_id=case_id,
                selection=selection,
                response="",
                changed_files=(),
                agent=agent,
                runtime=ports,
            )
        )
        with pytest.raises(error):
            await operation
        cast(AsyncMock, agent.execute).assert_not_awaited()
        cast(AsyncMock, ports.create).assert_not_awaited()
        cast(AsyncMock, ports.cleanup).assert_not_awaited()

    asyncio.run(execute())
