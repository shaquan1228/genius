"""Run each Inspect sample in a dedicated Hugging Face Sandbox VM."""

import asyncio
from pathlib import PurePosixPath
from typing import Literal, cast, overload, override
from uuid import uuid4

from huggingface_hub import Sandbox, SandboxCommandResult
from inspect_ai.util import (
    ExecResult,
    SandboxEnvironment,
    SandboxUserUnsupportedError,
    sandboxenv,
)

IMAGE = "python:3.12-slim-bookworm"
WORKDIR = PurePosixPath("/eval")
INSTALL_TOOLS = (
    "apt-get update -qq && apt-get install -y --no-install-recommends "
    "bash ca-certificates curl git ocaml-nox ripgrep && rm -rf /var/lib/apt/lists/*"
)


def completed(result: SandboxCommandResult, *, cmd: list[str]) -> ExecResult[str]:
    if result.timed_out:
        raise TimeoutError(f"Sandbox command timed out: {cmd[0]}")
    returncode = result.exit_code if result.exit_code is not None else 1
    return ExecResult(
        success=returncode == 0,
        returncode=returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


@sandboxenv(name="hf")
class HfSandboxEnvironment(SandboxEnvironment):
    @override
    def __init__(self, client: Sandbox) -> None:
        super().__init__()
        self.client = client

    @override
    @classmethod
    async def sample_init(
        cls, task_name: str, config: object, metadata: dict[str, str]
    ) -> dict[str, SandboxEnvironment]:
        creation = asyncio.create_task(
            asyncio.to_thread(Sandbox.create, image=IMAGE, idle_timeout=900)
        )
        try:
            client = await asyncio.shield(creation)
        except asyncio.CancelledError:
            client = await creation
            await asyncio.to_thread(client.kill)
            raise
        try:
            result = cast(
                SandboxCommandResult,
                await asyncio.to_thread(
                    client.run,
                    ["sh", "-c", INSTALL_TOOLS],
                    timeout=240,
                    check=False,
                ),
            )
            if result.exit_code != 0:
                raise RuntimeError("Could not install eval tools in Hugging Face Sandbox")
            await asyncio.to_thread(client.files.mkdir, str(WORKDIR))
        except BaseException:
            await asyncio.to_thread(client.kill)
            raise
        return {"default": cls(client)}

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
            await asyncio.to_thread(environment.as_type(cls).client.kill)

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
        stdin_path: str | None = None
        try:
            if isinstance(input, bytes):
                stdin_path = f"/tmp/genius-stdin-{uuid4().hex}"
                await asyncio.to_thread(self.client.files.write, stdin_path, input, mode="0600")
                cmd = [
                    "/bin/sh",
                    "-c",
                    'stdin=$1; shift; exec "$@" < "$stdin"',
                    "sh",
                    stdin_path,
                    *cmd,
                ]
                input = None
            result = cast(
                SandboxCommandResult,
                await asyncio.to_thread(
                    self.client.run,
                    cmd,
                    shell=False,
                    stdin=input,
                    cwd=self._path(cwd or "."),
                    env=env,
                    timeout=timeout,
                    check=False,
                ),
            )
            return completed(result, cmd=cmd)
        finally:
            if stdin_path is not None:
                await asyncio.to_thread(self.client.files.delete, stdin_path)

    @override
    async def write_file(self, file: str, contents: str | bytes) -> None:
        await asyncio.to_thread(self.client.files.write, self._path(file), contents)

    @overload
    async def read_file(self, file: str, text: Literal[True] = True) -> str: ...  # noqa: FBT002 - Inspect's signature

    @overload
    async def read_file(self, file: str, text: Literal[False]) -> bytes: ...

    @override
    async def read_file(self, file: str, text: bool = True) -> str | bytes:
        contents = await asyncio.to_thread(self.client.files.read, self._path(file))
        return contents.decode() if text else contents

    @staticmethod
    def _path(file: str) -> str:
        return str(WORKDIR / file)
