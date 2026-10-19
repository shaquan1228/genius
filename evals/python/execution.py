"""Execution capabilities and provider composition."""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, Protocol, assert_never, runtime_checkable

from pydantic import validate_call

from evals.python import FROZEN

__all__ = [
    "Cleanup",
    "Completion",
    "Environment",
    "Execution",
    "Runtime",
    "allocated",
    "create_runtime",
    "settle",
]


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


@validate_call(config=FROZEN)
def create_runtime(
    *, provider: Literal["local", "hf"] = "local", image: str | None = None
) -> Runtime:
    match provider:
        case "local":
            from evals.python.integrations.inspect import environments  # noqa: PLC0415 - lazy local SDK composition

            return environments.runtime()
        case "hf":
            from evals.python.integrations.hugging_face import sandbox  # noqa: PLC0415 - lazy HF SDK composition

            return sandbox.runtime(image=image)
        case _ as unreachable:
            assert_never(unreachable)


async def settle[T](task: asyncio.Future[T]) -> T:
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
            await settle(task)
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
            grader = await settle(allocation)
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
