"""Execution capabilities and provider composition."""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, Protocol, assert_never, runtime_checkable

from pydantic import validate_call

from evals.python.schema import FROZEN

__all__ = ["Cleanup", "Completion", "Environment", "Execution", "Runtime", "create_runtime"]


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
def create_runtime(*, provider: Literal["local", "hf"] = "local") -> Runtime:
    match provider:
        case "local":
            from evals.python.integrations.inspect import environments  # noqa: PLC0415 - lazy local SDK composition

            return environments.runtime()
        case "hf":
            from evals.python.integrations.hugging_face import sandbox  # noqa: PLC0415 - lazy HF SDK composition

            return sandbox.runtime()
        case _ as unreachable:
            assert_never(unreachable)
