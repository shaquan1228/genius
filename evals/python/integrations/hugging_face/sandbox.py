import asyncio
import json
import os
import sys
from collections.abc import Callable
from contextlib import suppress
from pathlib import PurePosixPath
from typing import cast
from uuid import uuid4

from huggingface_hub import Sandbox, SandboxCommandResult

from evals.python import execution

IMAGE = "python:3.12-slim-bookworm"
WORKDIR = PurePosixPath("/eval")
INSTALL_TOOLS = (
    "apt-get update -qq && apt-get install -y --no-install-recommends "
    "bash ca-certificates curl git ocaml-nox ripgrep && rm -rf /var/lib/apt/lists/*"
)


def event(name: str, *, handle: str = "") -> None:
    sys.stdout.write(
        json.dumps({"event": name, "run_id": os.environ.get("EVAL_RUN_ID", ""), "vm_id": handle})
        + "\n"
    )
    sys.stdout.flush()


def prepared_check() -> str:
    return (
        "set -eu; for tool in python bash curl git ocaml ocamlfind rg; do "
        'command -v "$tool" >/dev/null || exit 1; done'
    )


def provision(image: str) -> Sandbox:
    return Sandbox.create(
        image=image or IMAGE,
        idle_timeout=900,
        namespace=os.environ.get("HF_NAMESPACE") or None,
        forward_hf_token=False,
        labels={"genius-run": os.environ.get("EVAL_RUN_ID", "unknown")},
    )


def create() -> Sandbox:
    event("vm_provisioning")
    image = os.environ.get("EVAL_SANDBOX_IMAGE", "")
    client = provision(image)
    try:
        setup = prepared_check() if image else INSTALL_TOOLS
        result = client.run(["sh", "-c", setup], timeout=240, check=False)
        if result.exit_code != 0:
            raise RuntimeError("Could not prepare eval tools in Hugging Face Sandbox")
        client.files.mkdir(str(WORKDIR))
        event("vm_ready", handle=client.id)
        return client
    except BaseException:
        destroy(client)
        raise


def destroy(client: Sandbox) -> None:
    try:
        client.kill()
        event("vm_cleanup", handle=client.id)
    finally:
        client.close()


def run(client: Sandbox, *, request: execution.Execution) -> execution.Completion:
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


def completion(result: SandboxCommandResult, *, command: tuple[str, ...]) -> execution.Completion:
    if result.timed_out:
        raise TimeoutError(f"Sandbox command timed out: {command[0]}")
    return execution.Completion(
        returncode=result.exit_code if result.exit_code is not None else 1,
        stdout=result.stdout,
        stderr=result.stderr,
    )


async def effect[T](
    invoke: Callable[[], T], *, active: set[asyncio.Task[object]] | None = None
) -> T:
    pending = asyncio.create_task(asyncio.to_thread(invoke))
    tracked = cast(asyncio.Task[object], pending)
    if active is not None:
        active.add(tracked)
    try:
        return await asyncio.shield(pending)
    except asyncio.CancelledError:
        with suppress(Exception):
            await _settle(pending)
        raise
    finally:
        if active is not None:
            active.discard(tracked)


def environment(
    handle: str, *, client: Sandbox | None = None, active: set[asyncio.Task[object]] | None = None
) -> execution.Environment:
    async def invoke[T](operation: Callable[[Sandbox], T]) -> T:
        def connected() -> T:
            current = client if client is not None else Sandbox.connect(handle)
            try:
                return operation(current)
            finally:
                if client is None:
                    current.close()

        return await effect(connected, active=active)

    async def execute(request: execution.Execution) -> execution.Completion:
        return await invoke(lambda current: run(current, request=request))

    async def read(file: str) -> bytes:
        return await invoke(lambda current: current.files.read(str(WORKDIR / file)))

    async def write(file: str, contents: bytes) -> None:  # noqa: PLR0917 - capability write port
        await invoke(lambda current: current.files.write(str(WORKDIR / file), contents))

    return execution.Environment(execute=execute, read_bytes=read, write_bytes=write)


async def _settle[T](task: asyncio.Task[T]) -> T:
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            continue
    return task.result()


async def _kill(client: Sandbox) -> None:
    await effect(lambda: destroy(client))


def runtime() -> execution.Runtime:
    owned: dict[execution.Environment, tuple[Sandbox, set[asyncio.Task[object]]]] = {}

    async def allocate() -> execution.Environment:
        pending = asyncio.create_task(asyncio.to_thread(create))
        try:
            client = await asyncio.shield(pending)
        except asyncio.CancelledError:
            with suppress(Exception):
                client = await _settle(pending)
                await _kill(client)
            raise
        active: set[asyncio.Task[object]] = set()
        result = environment(client.id, client=client, active=active)
        owned[result] = client, active
        return result

    async def cleanup(target: execution.Environment, *, interrupted: bool) -> None:
        client, active = owned.pop(target)

        async def finish() -> None:
            for pending in tuple(active):
                with suppress(Exception):
                    await _settle(pending)
            await _kill(client)

        pending = asyncio.create_task(finish())
        try:
            await asyncio.shield(pending)
        except asyncio.CancelledError:
            with suppress(Exception):
                await _settle(pending)
            raise

    return execution.Runtime(create=allocate, cleanup=cleanup)
