from typing import Literal, overload, override

from inspect_ai.util import (
    ExecResult,
    SandboxEnvironment,
    SandboxUserUnsupportedError,
    sandboxenv,
)

from evals.python import execution
from evals.python.execution import Environment, Execution, Runtime


@sandboxenv(name="hf")
class HfSandboxEnvironment(SandboxEnvironment):
    @override
    def __init__(self, environment: Environment, runtime: Runtime) -> None:
        super().__init__()
        self.environment = environment
        self.runtime = runtime

    @override
    @classmethod
    async def sample_init(
        cls, task_name: str, config: object, metadata: dict[str, str]
    ) -> dict[str, SandboxEnvironment]:
        runtime = execution.create_runtime(provider="hf")
        environment = await runtime.create()
        return {"default": cls(environment, runtime)}

    @override
    @classmethod
    async def sample_cleanup(
        cls,
        task_name: str,
        config: object,
        environments: dict[str, SandboxEnvironment],
        interrupted: bool,
    ) -> None:
        for value in environments.values():
            adapter = value.as_type(cls)
            await adapter.runtime.cleanup(adapter.environment, interrupted=interrupted)

    @override
    async def exec(
        self,
        cmd: list[str],
        input: str | bytes | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        user: str | None = None,
        timeout: int | None = None,
        timeout_retry: bool = True,
        concurrency: bool = True,
    ) -> ExecResult[str]:
        if user not in (None, "root", "0"):
            raise SandboxUserUnsupportedError(f"Hugging Face Sandbox cannot execute as {user!r}")
        result = await self.environment.execute(
            Execution(command=tuple(cmd), input=input, cwd=cwd, env=env or {}, timeout=timeout)
        )
        return ExecResult(
            success=result.returncode == 0,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    @override
    async def write_file(self, file: str, contents: str | bytes) -> None:
        await self.environment.write_bytes(
            file, contents.encode() if isinstance(contents, str) else contents
        )

    @overload
    async def read_file(self, file: str, text: Literal[True] = True) -> str: ...  # noqa: FBT002

    @overload
    async def read_file(self, file: str, text: Literal[False]) -> bytes: ...

    @override
    async def read_file(self, file: str, text: bool = True) -> str | bytes:
        contents = await self.environment.read_bytes(file)
        return contents.decode() if text else contents
