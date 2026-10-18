"""Runner-independent verification policy over immutable execution capabilities."""

import asyncio
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from secrets import token_hex
from types import MappingProxyType
from typing import Literal, cast

from pydantic import BaseModel, InstanceOf, JsonValue, ValidationError, validate_call

from evals.python import execution
from evals.python.execution import Completion, Environment, Execution, Runtime
from evals.python.schema import FROZEN
from kernel import Content, Fixture, Task, Verification, Verifier

__all__ = ["Diagnostic", "VerificationResult", "validate_reference", "verify"]

VerificationStatus = Literal[
    "unchecked", "passed", "failed", "invalid_submission", "timed_out", "harness_error"
]

type Diagnostic = (
    str | int | float | bool | tuple[Diagnostic, ...] | Mapping[str, Diagnostic] | None
)


def _freeze(value: Diagnostic | JsonValue) -> Diagnostic:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _json(value: Diagnostic) -> JsonValue:
    if isinstance(value, Mapping):
        return {key: _json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json(item) for item in value]
    return value


@dataclass(frozen=True, kw_only=True)
class VerificationResult:
    verification: Verification.Value
    detail: str = ""
    metadata: Mapping[str, Diagnostic] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.verification, Verification.HarnessError) and not self.detail:
            object.__setattr__(self, "detail", self.verification.detail)
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType({key: _freeze(value) for key, value in self.metadata.items()}),
        )

    def metadata_json(self) -> dict[str, JsonValue]:
        return {key: _json(value) for key, value in self.metadata.items()}


class _Evidence(BaseModel):
    model_config = FROZEN
    marker: str
    status: VerificationStatus
    detail: str
    metadata: dict[str, JsonValue] | None = None


_STATUSES: Mapping[str, Callable[[], Verification.Value]] = {
    "passed": Verification.Passed,
    "failed": Verification.Failed,
    "invalid_submission": Verification.InvalidSubmission,
    "timed_out": Verification.TimedOut,
}


def completion(result: Completion, *, marker: str) -> VerificationResult:
    try:
        evidence = _Evidence.model_validate_json(result.stdout.strip().splitlines()[-1])
    except (ValidationError, IndexError) as error:
        return VerificationResult(
            verification=Verification.HarnessError(detail=f"Invalid verifier evidence: {error}")
        )
    if not all((evidence.marker == marker, result.returncode == 0, evidence.status != "unchecked")):
        return VerificationResult(
            verification=Verification.HarnessError(
                detail="Verifier completion was not authenticated"
            )
        )
    return VerificationResult(
        verification=(
            Verification.HarnessError(detail=evidence.detail)
            if evidence.status == "harness_error"
            else _STATUSES[evidence.status]()
        ),
        detail=evidence.detail,
        metadata=cast(Mapping[str, Diagnostic], evidence.metadata or {}),
    )


async def _inputs(checks: Verifier, *, agent: Environment) -> dict[str, bytes]:
    result = {}
    for name in checks.inputs:
        path = f"workspace/{name}"
        inspection = await agent.execute(Execution(command=("test", "-f", path)))
        if inspection.returncode == 1:
            raise FileNotFoundError(name)
        if inspection.returncode != 0:
            raise RuntimeError(f"Could not inspect candidate input: {inspection.stderr}")
        result[name] = await agent.read_bytes(path)
    return result


def _contents(value: Content.Value) -> str:
    if not isinstance(value, Content.Inline):
        raise ValueError("Verifier resources must be resolved before execution")
    return value.text


async def _execute(
    checks: Verifier, *, grader: Environment, inputs: dict[str, bytes]
) -> VerificationResult:
    setup = await grader.execute(Execution(command=("mkdir", "-p", "workspace")))
    if setup.returncode != 0:
        raise RuntimeError(f"Could not create verifier workspace: {setup.stderr}")
    artifacts = {
        **inputs,
        **{
            artifact.path: _contents(artifact.content).encode()
            for artifact in (*checks.tools, *checks.files)
        },
    }
    for name, contents in artifacts.items():
        await grader.write_bytes(f"workspace/{name}", contents)
    marker = token_hex(32)
    try:
        result = await grader.execute(
            Execution(
                command=tuple(checks.command),
                input=checks.stdin,
                cwd="workspace",
                env={"GENIUS_VERIFIER_MARKER": marker},
                timeout=checks.timeout_seconds,
            )
        )
    except TimeoutError as error:
        return VerificationResult(verification=Verification.TimedOut(), detail=str(error))
    return completion(result, marker=marker)


async def _settle[T](task: asyncio.Future[T]) -> T:
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            continue
    return task.result()


async def _cleanup(runtime: Runtime, *, grader: Environment, interrupted: bool) -> None:
    task = asyncio.create_task(runtime.cleanup(grader, interrupted=interrupted))
    try:
        await asyncio.shield(task)
    except asyncio.CancelledError:
        with suppress(Exception):
            await _settle(task)
        raise
    except Exception:
        if not interrupted:
            raise


async def _allocate(runtime: Runtime, *, candidate: Environment | None) -> Environment:
    allocation = asyncio.ensure_future(runtime.create())
    try:
        return await asyncio.shield(allocation)
    except asyncio.CancelledError:
        with suppress(Exception):
            grader = await _settle(allocation)
            if grader is not candidate:
                await _cleanup(runtime, grader=grader, interrupted=True)
        raise


@asynccontextmanager
async def allocated(
    runtime: Runtime, *, candidate: Environment | None = None
) -> AsyncIterator[Environment]:
    grader = await _allocate(runtime, candidate=candidate)
    if grader is candidate:
        raise RuntimeError("Verification requires a fresh grader environment")
    interrupted = False
    try:
        yield grader
    except asyncio.CancelledError:
        interrupted = True
        raise
    finally:
        await _cleanup(runtime, grader=grader, interrupted=interrupted)


@validate_call(config=FROZEN)
async def verify(
    checks: InstanceOf[Verifier] | None,
    *,
    agent: InstanceOf[Environment],
    runtime: InstanceOf[Runtime],
) -> VerificationResult:
    if checks is None:
        return VerificationResult(verification=Verification.Unchecked())
    try:
        try:
            inputs = await _inputs(checks, agent=agent)
        except FileNotFoundError as error:
            return VerificationResult(
                verification=Verification.InvalidSubmission(),
                detail=f"Missing required input: {error}",
            )
        async with allocated(runtime, candidate=agent) as grader:
            return await _execute(checks, grader=grader, inputs=inputs)
    except Exception as error:
        return VerificationResult(verification=Verification.HarnessError(detail=str(error)))


async def stage_reference(files: Mapping[str, str], *, agent: Environment) -> None:
    result = await agent.execute(Execution(command=("mkdir", "-p", "workspace")))
    if result.returncode != 0:
        raise RuntimeError(f"Could not create reference workspace: {result.stderr}")
    for name, contents in files.items():
        await agent.write_bytes(f"workspace/{name}", contents.encode())


@validate_call(config=FROZEN)
async def validate_reference(
    task: InstanceOf[Task],
    *,
    runtime: InstanceOf[Runtime] | None = None,
) -> VerificationResult:
    checks = Task.verifier(task=task)
    if checks is None:
        return VerificationResult(verification=Verification.Unchecked())
    runtime = runtime or execution.create_runtime()
    try:
        async with allocated(runtime) as agent:
            await stage_reference(
                {file.path: file.contents for file in Fixture.files(fixture=task.reference.edits)},
                agent=agent,
            )
            return await verify(checks, agent=agent, runtime=runtime)
    except Exception as error:
        return VerificationResult(verification=Verification.HarnessError(detail=str(error)))
