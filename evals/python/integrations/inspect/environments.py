from collections.abc import Callable
from typing import cast

from inspect_ai.util import SandboxEnvironment
from inspect_ai.util._sandbox.local import LocalSandboxEnvironment

from evals.python import verification
from evals.python.integrations.inspect import remote


def environment(sandbox: SandboxEnvironment) -> verification.Environment:
    unwrap = cast(Callable[[object], SandboxEnvironment], sandbox.as_type)
    underlying = unwrap(SandboxEnvironment)
    if isinstance(underlying, remote.HfSandboxEnvironment):
        return underlying.environment

    async def execute(request: verification.Execution) -> verification.Completion:
        result = await sandbox.exec(
            list(request.command),
            input=request.input,
            cwd=request.cwd,
            env=dict(request.env),
            timeout=request.timeout,
        )
        return verification.Completion(
            returncode=result.returncode, stdout=result.stdout, stderr=result.stderr
        )

    async def read(path: str) -> bytes:
        return await sandbox.read_file(path, text=False)

    async def write(path: str, contents: bytes) -> None:  # noqa: PLR0917 - SDK write port
        await sandbox.write_file(path, contents)

    return verification.Environment(execute=execute, read_bytes=read, write_bytes=write)


def runtime(sandbox: SandboxEnvironment | None = None) -> verification.Runtime:
    provider: type[SandboxEnvironment]
    if sandbox is None:
        provider = LocalSandboxEnvironment
    else:
        unwrap = cast(Callable[[object], SandboxEnvironment], sandbox.as_type)
        underlying = unwrap(SandboxEnvironment)
        if isinstance(underlying, remote.HfSandboxEnvironment):
            return underlying.runtime
        provider = type(underlying)
    owned: dict[verification.Environment, dict[str, SandboxEnvironment]] = {}

    async def create() -> verification.Environment:
        sandboxes = await provider.sample_init("genius-verification", None, {})
        result = environment(sandboxes["default"])
        owned[result] = sandboxes
        return result

    async def cleanup(target: verification.Environment, *, interrupted: bool) -> None:
        sandboxes = owned.pop(target)
        await provider.sample_cleanup(
            "genius-verification", None, sandboxes, interrupted=interrupted
        )

    return verification.Runtime(create=create, cleanup=cleanup)
