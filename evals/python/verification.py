"""Runner-independent verification policy over immutable execution capabilities."""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from secrets import token_hex
from types import MappingProxyType
from typing import Protocol

from pydantic import BaseModel, JsonValue, ValidationError

from evals.python._kernel import FROZEN, ExecutableChecks, Verification, VerificationStatus

type Diagnostic = (
    str | int | float | bool | tuple[Diagnostic, ...] | Mapping[str, Diagnostic] | None
)


def _freeze(value: Diagnostic | JsonValue) -> Diagnostic:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True, kw_only=True)
class Execution:
    command: tuple[str, ...]
    input: str | bytes | None = None
    cwd: str | None = None
    env: Mapping[str, str] = field(default_factory=dict)
    timeout: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "env", MappingProxyType(dict(self.env)))


@dataclass(frozen=True, kw_only=True)
class Completion:
    returncode: int
    stdout: str
    stderr: str = ""


@dataclass(frozen=True, kw_only=True, eq=False)
class Environment:
    execute: Callable[[Execution], Awaitable[Completion]]
    read_bytes: Callable[[str], Awaitable[bytes]]
    write_bytes: Callable[[str, bytes], Awaitable[None]]


class Cleanup(Protocol):
    async def __call__(self, environment: Environment, /, *, interrupted: bool) -> None: ...


@dataclass(frozen=True, kw_only=True)
class Runtime:
    create: Callable[[], Awaitable[Environment]]
    cleanup: Cleanup


@dataclass(frozen=True, kw_only=True)
class VerificationResult:
    verification: Verification
    metadata: Mapping[str, Diagnostic] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType({key: _freeze(value) for key, value in self.metadata.items()}),
        )


@dataclass(frozen=True, kw_only=True)
class Assessment(VerificationResult):
    scores: Mapping[str, bool]

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(self, "scores", MappingProxyType(dict(self.scores)))


class _Evidence(BaseModel):
    model_config = FROZEN
    marker: str
    status: VerificationStatus
    detail: str
    metadata: dict[str, JsonValue] | None = None


def completion(result: Completion, *, marker: str) -> VerificationResult:
    try:
        evidence = _Evidence.model_validate_json(result.stdout.strip().splitlines()[-1])
    except (ValidationError, IndexError) as error:
        return VerificationResult(
            verification=Verification(
                status="harness_error", detail=f"Invalid verifier evidence: {error}"
            )
        )
    if not all((evidence.marker == marker, result.returncode == 0, evidence.status != "unchecked")):
        return VerificationResult(
            verification=Verification(
                status="harness_error", detail="Verifier completion was not authenticated"
            )
        )
    return VerificationResult(
        verification=Verification(status=evidence.status, detail=evidence.detail),
        metadata=MappingProxyType(
            {key: _freeze(value) for key, value in (evidence.metadata or {}).items()}
        ),
    )


async def _inputs(checks: ExecutableChecks, *, agent: Environment) -> dict[str, bytes]:
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


async def _execute(
    checks: ExecutableChecks, *, grader: Environment, inputs: dict[str, bytes]
) -> VerificationResult:
    setup = await grader.execute(Execution(command=("mkdir", "-p", "workspace")))
    if setup.returncode != 0:
        raise RuntimeError(f"Could not create verifier workspace: {setup.stderr}")
    artifacts = {
        **inputs,
        **{name: value.encode() for name, value in {**checks.tools, **checks.files}.items()},
    }
    for name, contents in artifacts.items():
        await grader.write_bytes(f"workspace/{name}", contents)
    marker = token_hex(32)
    try:
        result = await grader.execute(
            Execution(
                command=checks.command,
                input=checks.stdin,
                cwd="workspace",
                env={"GENIUS_VERIFIER_MARKER": marker},
                timeout=checks.timeout_seconds,
            )
        )
    except TimeoutError as error:
        return VerificationResult(verification=Verification(status="timed_out", detail=str(error)))
    return completion(result, marker=marker)


async def _settle[T](task: asyncio.Future[T]) -> T:
    """Retain ownership until an effect finishes, including repeated cancellation."""
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


async def verify(
    checks: ExecutableChecks, *, agent: Environment, runtime: Runtime
) -> VerificationResult:
    try:
        try:
            inputs = await _inputs(checks, agent=agent)
        except FileNotFoundError as error:
            return VerificationResult(
                verification=Verification(
                    status="invalid_submission", detail=f"Missing required input: {error}"
                )
            )
        async with allocated(runtime, candidate=agent) as grader:
            return await _execute(checks, grader=grader, inputs=inputs)
    except Exception as error:
        return VerificationResult(
            verification=Verification(status="harness_error", detail=str(error))
        )


async def stage_reference(files: Mapping[str, str], *, agent: Environment) -> None:
    result = await agent.execute(Execution(command=("mkdir", "-p", "workspace")))
    if result.returncode != 0:
        raise RuntimeError(f"Could not create reference workspace: {result.stderr}")
    for name, contents in files.items():
        await agent.write_bytes(f"workspace/{name}", contents.encode())
