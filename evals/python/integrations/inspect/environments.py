"""Convert Inspect sandbox effects to the public execution capability interface."""

from collections.abc import Callable
from typing import cast

from inspect_ai.util import SandboxEnvironment
from inspect_ai.util._sandbox.local import LocalSandboxEnvironment

from evals.python.verification import Completion, Environment, Execution, Runtime


def environment(sandbox: SandboxEnvironment) -> Environment:
    async def execute(request: Execution) -> Completion:
        result = await sandbox.exec(
            list(request.command),
            input=request.input,
            cwd=request.cwd,
            env=dict(request.env),
            timeout=request.timeout,
        )
        return Completion(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)

    async def exists(path: str) -> bool:
        result = await execute(Execution(command=("test", "-f", path)))
        match result.returncode:
            case 0:
                return True
            case 1:
                return False
            case _:
                raise RuntimeError(f"Could not inspect candidate input: {result.stderr}")

    async def read(path: str) -> bytes:
        return await sandbox.read_file(path, text=False)

    async def write(path: str, contents: bytes) -> None:  # noqa: PLR0917 - SDK write port
        await sandbox.write_file(path, contents)

    return Environment(execute=execute, exists=exists, read_bytes=read, write_bytes=write)


def runtime(sandbox: SandboxEnvironment | None = None) -> Runtime:
    provider: type[SandboxEnvironment]
    if sandbox is None:
        provider = LocalSandboxEnvironment
    else:
        unwrap = cast(Callable[[object], SandboxEnvironment], sandbox.as_type)
        provider = type(unwrap(SandboxEnvironment))
    owned: dict[Environment, dict[str, SandboxEnvironment]] = {}

    async def create() -> Environment:
        sandboxes = await provider.sample_init("genius-verification", None, {})
        result = environment(sandboxes["default"])
        owned[result] = sandboxes
        return result

    async def cleanup(target: Environment, *, interrupted: bool) -> None:
        sandboxes = owned.pop(target)
        await provider.sample_cleanup(
            "genius-verification", None, sandboxes, interrupted=interrupted
        )

    return Runtime(create=create, cleanup=cleanup)
