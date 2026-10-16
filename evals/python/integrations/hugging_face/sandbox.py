"""Adapt Hugging Face Sandbox effects to canonical execution capabilities."""

import asyncio
from contextlib import suppress
from pathlib import PurePosixPath
from uuid import uuid4

from huggingface_hub import Sandbox, SandboxCommandResult

from evals.python import commands

IMAGE = "python:3.12-slim-bookworm"
WORKDIR = PurePosixPath("/eval")
INSTALL_TOOLS = (
    "apt-get update -qq && apt-get install -y --no-install-recommends "
    "bash ca-certificates curl git ocaml-nox ripgrep && rm -rf /var/lib/apt/lists/*"
)


def create() -> str:
    client = Sandbox.create(image=IMAGE, idle_timeout=900)
    try:
        result = client.run(["sh", "-c", INSTALL_TOOLS], timeout=240, check=False)
        if result.exit_code != 0:
            raise RuntimeError("Could not install eval tools in Hugging Face Sandbox")
        client.files.mkdir(str(WORKDIR))
        return client.id
    except BaseException:
        client.kill()
        raise
    finally:
        client.close()


def run(client: Sandbox, *, request: commands.Execution) -> commands.Completion:
    cmd, stdin = list(request.command), request.input
    stdin_path: str | None = None
    try:
        if isinstance(stdin, bytes):
            stdin_path = f"/tmp/genius-stdin-{uuid4().hex}"
            client.files.write(stdin_path, stdin, mode="0600")
            cmd = ["/bin/sh", "-c", 'stdin=$1; shift; exec "$@" < "$stdin"', "sh", stdin_path, *cmd]
            stdin = None
        result = client.run(
            cmd,
            shell=False,
            stdin=stdin,
            cwd=str(WORKDIR / (request.cwd or ".")),
            env=dict(request.env),
            timeout=request.timeout,
            check=False,
        )
        return completion(result, command=request.command)
    finally:
        if stdin_path is not None:
            client.files.delete(stdin_path)


def completion(result: SandboxCommandResult, *, command: tuple[str, ...]) -> commands.Completion:
    if result.timed_out:
        raise TimeoutError(f"Sandbox command timed out: {command[0]}")
    return commands.Completion(
        returncode=result.exit_code if result.exit_code is not None else 1,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def environment(handle: str) -> commands.Environment:
    async def execute(request: commands.Execution) -> commands.Completion:
        def invoke() -> commands.Completion:
            client = Sandbox.connect(handle)
            try:
                return run(client, request=request)
            finally:
                client.close()

        return await asyncio.to_thread(invoke)

    async def read(file: str) -> bytes:
        def invoke() -> bytes:
            client = Sandbox.connect(handle)
            try:
                return client.files.read(str(WORKDIR / file))
            finally:
                client.close()

        return await asyncio.to_thread(invoke)

    async def write(file: str, contents: bytes) -> None:  # noqa: PLR0917 - capability write port
        def invoke() -> None:
            client = Sandbox.connect(handle)
            try:
                client.files.write(str(WORKDIR / file), contents)
            finally:
                client.close()

        await asyncio.to_thread(invoke)

    return commands.Environment(execute=execute, read_bytes=read, write_bytes=write)


def kill(handle: str) -> None:
    client = Sandbox.connect(handle)
    try:
        client.kill()
    finally:
        client.close()


async def _settle[T](task: asyncio.Task[T]) -> T:
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            continue
    return task.result()


async def _kill(handle: str) -> None:
    pending = asyncio.create_task(asyncio.to_thread(kill, handle))
    try:
        await asyncio.shield(pending)
    except asyncio.CancelledError:
        with suppress(Exception):
            await _settle(pending)
        raise


def runtime() -> commands.Runtime:
    owned: dict[commands.Environment, str] = {}

    async def allocate() -> commands.Environment:
        pending = asyncio.create_task(asyncio.to_thread(create))
        try:
            handle = await asyncio.shield(pending)
        except asyncio.CancelledError:
            with suppress(Exception):
                handle = await _settle(pending)
                await _kill(handle)
            raise
        result = environment(handle)
        owned[result] = handle
        return result

    async def cleanup(target: commands.Environment, *, interrupted: bool) -> None:
        await _kill(owned.pop(target))

    return commands.Runtime(create=allocate, cleanup=cleanup)
