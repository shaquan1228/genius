from collections.abc import Callable
from typing import cast

from inspect_ai.util import SandboxEnvironment
from inspect_ai.util._sandbox.docker.docker import DockerSandboxEnvironment
from inspect_ai.util._sandbox.local import LocalSandboxEnvironment

from evals.python.execution import Completion, Environment, Execution, Runtime
from evals.python.integrations.inspect import remote


def environment(sandbox: SandboxEnvironment) -> Environment:
    unwrap = cast(Callable[[object], SandboxEnvironment], sandbox.as_type)
    underlying = unwrap(SandboxEnvironment)
    if isinstance(underlying, remote.HfSandboxEnvironment):
        return underlying.environment

    async def execute(request: Execution) -> Completion:
        result = await sandbox.exec(
            list(request.command),
            input=request.input,
            cwd=request.cwd,
            env=dict(request.env),
            timeout=request.timeout,
        )
        return Completion(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)

    async def read(path: str) -> bytes:
        return await sandbox.read_file(path, text=False)

    async def write(path: str, contents: bytes) -> None:  # noqa: PLR0917 - SDK write port
        await sandbox.write_file(path, contents)

    return Environment(execute=execute, read_bytes=read, write_bytes=write)


def runtime(sandbox: SandboxEnvironment | None = None) -> Runtime:
    provider: type[SandboxEnvironment]
    config: str | None = None
    if sandbox is None:
        provider = LocalSandboxEnvironment
    else:
        unwrap = cast(Callable[[object], SandboxEnvironment], sandbox.as_type)
        underlying = unwrap(SandboxEnvironment)
        if isinstance(underlying, remote.HfSandboxEnvironment):
            return underlying.runtime
        provider = type(underlying)
        if isinstance(underlying, DockerSandboxEnvironment):
            config = underlying._project.config
    owned: dict[Environment, dict[str, SandboxEnvironment]] = {}

    async def create() -> Environment:
        sandboxes = await provider.sample_init("genius-verification", config, {})
        result = environment(sandboxes["default"])
        owned[result] = sandboxes
        return result

    async def cleanup(target: Environment, *, interrupted: bool) -> None:
        sandboxes = owned.pop(target)
        await provider.sample_cleanup(
            "genius-verification", config, sandboxes, interrupted=interrupted
        )

    return Runtime(create=create, cleanup=cleanup)
