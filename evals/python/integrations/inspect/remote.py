"""Adapt remote JSON commands to Inspect's sandbox interface."""

import asyncio
import base64
import json
from typing import Literal, overload, override

from inspect_ai.util import (
    ExecResult,
    SandboxEnvironment,
    SandboxUserUnsupportedError,
    sandboxenv,
)
from pydantic import BaseModel, ConfigDict

from evals.python.command import command


class Handle(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    id: str


class Completion(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool


class Contents(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    contents: str


def completed(result: Completion, *, cmd: list[str]) -> ExecResult[str]:
    if result.timed_out:
        raise TimeoutError(f"Sandbox command timed out: {cmd[0]}")
    code = result.exit_code if result.exit_code is not None else 1
    return ExecResult(
        success=code == 0, returncode=code, stdout=result.stdout, stderr=result.stderr
    )


@sandboxenv(name="hf")
class HfSandboxEnvironment(SandboxEnvironment):
    @override
    def __init__(self, handle: str) -> None:
        super().__init__()
        self.handle = handle

    @override
    @classmethod
    async def sample_init(
        cls, task_name: str, config: object, metadata: dict[str, str]
    ) -> dict[str, SandboxEnvironment]:
        creation = asyncio.create_task(asyncio.to_thread(command, "hf.create"))
        try:
            response = await asyncio.shield(creation)
        except asyncio.CancelledError:
            response = await creation
            await asyncio.to_thread(command, "hf.kill", payload=response)
            raise
        return {"default": cls(Handle.model_validate_json(response).id)}

    @override
    @classmethod
    async def sample_cleanup(
        cls,
        task_name: str,
        config: object,
        environments: dict[str, SandboxEnvironment],
        interrupted: bool,
    ) -> None:
        for environment in environments.values():
            await environment.as_type(cls).invoke("kill")

    async def invoke(self, operation: str, **payload: object) -> str:
        return await asyncio.to_thread(
            command, f"hf.{operation}", payload=json.dumps({"id": self.handle, **payload})
        )

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
        binary = isinstance(input, bytes)
        stdin = base64.b64encode(input).decode() if isinstance(input, bytes) else input
        result = Completion.model_validate_json(
            await self.invoke(
                "exec",
                cmd=cmd,
                input=stdin,
                binary=binary,
                cwd=cwd or ".",
                env=env,
                timeout=timeout,
            )
        )
        return completed(result, cmd=cmd)

    @override
    async def write_file(self, file: str, contents: str | bytes) -> None:
        data = contents.encode() if isinstance(contents, str) else contents
        await self.invoke("write", file=file, contents=base64.b64encode(data).decode())

    @overload
    async def read_file(self, file: str, text: Literal[True] = True) -> str: ...  # noqa: FBT002

    @overload
    async def read_file(self, file: str, text: Literal[False]) -> bytes: ...

    @override
    async def read_file(self, file: str, text: bool = True) -> str | bytes:
        response = Contents.model_validate_json(await self.invoke("read", file=file))
        contents = base64.b64decode(response.contents, validate=True)
        return contents.decode() if text else contents
