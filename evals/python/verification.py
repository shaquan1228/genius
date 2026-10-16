"""Runner-independent verification policy over immutable execution capabilities."""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from secrets import token_hex
from types import MappingProxyType
from typing import Literal, Protocol, cast, runtime_checkable

from pydantic import BaseModel, JsonValue, ValidationError

from evals.python.schema import FROZEN
from kernel import Ast

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


@runtime_checkable
class Cleanup(Protocol):
    async def __call__(self, environment: Environment, /, *, interrupted: bool) -> None: ...


@dataclass(frozen=True, kw_only=True)
class Runtime:
    create: Callable[[], Awaitable[Environment]]
    cleanup: Cleanup


@dataclass(frozen=True, kw_only=True)
class VerificationResult:
    verification: Ast.verification
    detail: str = ""
    metadata: Mapping[str, Diagnostic] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.verification, Ast.Harness_error) and not self.detail:
            object.__setattr__(self, "detail", self.verification[0])
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
            verification=Ast.Harness_error(f"Invalid verifier evidence: {error}")
        )
    if not all((evidence.marker == marker, result.returncode == 0, evidence.status != "unchecked")):
        return VerificationResult(
            verification=Ast.Harness_error("Verifier completion was not authenticated")
        )
    return VerificationResult(
        verification=(
            Ast.Harness_error(evidence.detail)
            if evidence.status == "harness_error"
            else cast(Ast.verification, getattr(Ast, evidence.status.capitalize())())
        ),
        detail=evidence.detail,
        # The constructor normalizes validated wire JSON into immutable diagnostics.
        metadata=cast(Mapping[str, Diagnostic], evidence.metadata or {}),
    )


async def _inputs(checks: Ast.verifier, *, agent: Environment) -> dict[str, bytes]:
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


def _contents(value: Ast.content) -> str:
    if not isinstance(value, Ast.Inline):
        raise ValueError("Verifier resources must be resolved before execution")
    return value[0]


async def _execute(
    checks: Ast.verifier, *, grader: Environment, inputs: dict[str, bytes]
) -> VerificationResult:
    setup = await grader.execute(Execution(command=("mkdir", "-p", "workspace")))
    if setup.returncode != 0:
        raise RuntimeError(f"Could not create verifier workspace: {setup.stderr}")
    artifacts = {
        **inputs,
        **{name: _contents(value).encode() for name, value in (*checks.tools, *checks.files)},
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
        return VerificationResult(verification=Ast.Timed_out(), detail=str(error))
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


async def verify(
    checks: Ast.verifier, *, agent: Environment, runtime: Runtime
) -> VerificationResult:
    try:
        try:
            inputs = await _inputs(checks, agent=agent)
        except FileNotFoundError as error:
            return VerificationResult(
                verification=Ast.Invalid_submission(), detail=f"Missing required input: {error}"
            )
        async with allocated(runtime, candidate=agent) as grader:
            return await _execute(checks, grader=grader, inputs=inputs)
    except Exception as error:
        return VerificationResult(verification=Ast.Harness_error(str(error)))


async def stage_reference(files: Mapping[str, str], *, agent: Environment) -> None:
    result = await agent.execute(Execution(command=("mkdir", "-p", "workspace")))
    if result.returncode != 0:
        raise RuntimeError(f"Could not create reference workspace: {result.stderr}")
    for name, contents in files.items():
        await agent.write_bytes(f"workspace/{name}", contents.encode())
