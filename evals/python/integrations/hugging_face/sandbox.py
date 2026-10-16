"""Hugging Face sandbox operations behind a JSON command boundary."""

import base64
import json
from pathlib import PurePosixPath
from uuid import uuid4

from huggingface_hub import Sandbox
from pydantic import BaseModel, ConfigDict, Field

IMAGE = "python:3.12-slim-bookworm"
WORKDIR = PurePosixPath("/eval")
INSTALL_TOOLS = (
    "apt-get update -qq && apt-get install -y --no-install-recommends "
    "bash ca-certificates curl git ocaml-nox ripgrep && rm -rf /var/lib/apt/lists/*"
)


class Request(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    id: str = ""
    cmd: list[str] = Field(default_factory=list)
    input: str | None = None
    binary: bool = False
    cwd: str = "."
    env: dict[str, str] | None = None
    timeout: int | None = None
    file: str = ""
    contents: str = ""


def create() -> dict[str, str]:
    client = Sandbox.create(image=IMAGE, idle_timeout=900)
    try:
        result = client.run(["sh", "-c", INSTALL_TOOLS], timeout=240, check=False)
        if result.exit_code != 0:
            raise RuntimeError("Could not install eval tools in Hugging Face Sandbox")
        client.files.mkdir(str(WORKDIR))
        return {"id": client.id}
    except BaseException:
        client.kill()
        raise
    finally:
        client.close()


def run(client: Sandbox, *, request: Request) -> dict[str, object]:
    cmd, stdin = request.cmd, request.input
    stdin_path: str | None = None
    try:
        if request.binary:
            stdin_path = f"/tmp/genius-stdin-{uuid4().hex}"
            client.files.write(
                stdin_path, base64.b64decode(stdin or "", validate=True), mode="0600"
            )
            cmd = ["/bin/sh", "-c", 'stdin=$1; shift; exec "$@" < "$stdin"', "sh", stdin_path, *cmd]
            stdin = None
        result = client.run(
            cmd,
            shell=False,
            stdin=stdin,
            cwd=str(WORKDIR / request.cwd),
            env=request.env,
            timeout=request.timeout,
            check=False,
        )
        return {
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": result.timed_out,
        }
    finally:
        if stdin_path is not None:
            client.files.delete(stdin_path)


def read(client: Sandbox, *, request: Request) -> dict[str, str]:
    contents = client.files.read(str(WORKDIR / request.file))
    return {"contents": base64.b64encode(contents).decode()}


def write(client: Sandbox, *, request: Request) -> None:
    client.files.write(
        str(WORKDIR / request.file), base64.b64decode(request.contents, validate=True)
    )


def mkdir(client: Sandbox, *, request: Request) -> None:
    client.files.mkdir(str(WORKDIR / request.file))


def kill(client: Sandbox, *, request: Request) -> None:
    client.kill()


def execute(operation: str, *, payload: str) -> str:
    request = Request.model_validate_json(payload)
    if operation == "create":
        return json.dumps(create())
    handler = {"kill": kill, "exec": run, "read": read, "write": write, "mkdir": mkdir}[operation]
    client = Sandbox.connect(request.id)
    try:
        return json.dumps(handler(client, request=request))
    finally:
        client.close()
