"""Exercise typed remote sandbox operations without hosted calls."""

import asyncio
import subprocess
from collections.abc import Iterator
from contextlib import nullcontext
from pathlib import Path
from threading import Event
from unittest.mock import Mock, patch

import pytest
from huggingface_hub import Sandbox, SandboxCommandResult
from inspect_ai.util import SandboxUserUnsupportedError
from inspect_ai.util._sandbox.events import SandboxEnvironmentProxy

from evals.python import commands
from evals.python.integrations.hugging_face import sandbox as backend
from evals.python.integrations.inspect import environments
from evals.python.integrations.inspect.remote import HfSandboxEnvironment


def _result(code: int | None = 0, *, timed_out: bool = False) -> SandboxCommandResult:
    return SandboxCommandResult(exit_code=code, stdout="done", stderr="", timed_out=timed_out)


@pytest.fixture
def client() -> Mock:
    value = Mock()
    value.id = "sandbox-id"
    value.run.return_value = _result()
    return value


def _adapter() -> HfSandboxEnvironment:
    return HfSandboxEnvironment(backend.environment("sandbox-id"), backend.runtime())


@pytest.fixture(autouse=True)
def remote_commands(client: Mock) -> Iterator[None]:
    with (
        patch.object(Sandbox, "create", return_value=client),
        patch.object(Sandbox, "connect", return_value=client),
    ):
        yield


def lifecycle(client: Mock) -> None:
    environment = asyncio.run(HfSandboxEnvironment.sample_init("eval", None, {}))["default"]
    assert isinstance(environment, HfSandboxEnvironment)
    assert environments.environment(environment) is environment.environment
    assert environments.runtime(environment) is environment.runtime
    client.files.mkdir.assert_called_once_with("/eval")
    client.close.assert_not_called()
    asyncio.run(
        HfSandboxEnvironment.sample_cleanup(
            "eval", None, {"default": environment}, interrupted=False
        )
    )
    client.kill.assert_called_once_with()
    assert client.close.call_count == 1


@pytest.mark.parametrize("failure", ["exit", "mkdir"])
def setup_failure_kills_sandbox(failure: str, *, client: Mock) -> None:
    if failure == "exit":
        client.run.return_value = _result(1)
    else:
        client.files.mkdir.side_effect = RuntimeError("mkdir failed")
    with pytest.raises(RuntimeError):
        asyncio.run(HfSandboxEnvironment.sample_init("eval", None, {}))
    client.kill.assert_called_once_with()
    client.close.assert_called_once_with()


@pytest.mark.parametrize(("code", "expected"), [(0, 0), (7, 7), (None, 1)])
def exec(code: int | None, *, expected: int, client: Mock) -> None:
    client.run.return_value = _result(code)
    completion = asyncio.run(
        _adapter().exec(
            ["python", "-V"], input="hello", cwd="workspace", env={"KEY": "value"}, timeout=3
        )
    )
    assert (completion.returncode, completion.success, completion.stdout) == (
        expected,
        expected == 0,
        "done",
    )
    assert client.run.call_args.kwargs == {
        "shell": False,
        "stdin": "hello",
        "cwd": "/eval/workspace",
        "env": {"KEY": "value"},
        "timeout": 3,
        "check": False,
    }
    client.close.assert_called_once_with()


@pytest.mark.parametrize("contents", [b"\x00\xff\r\n", b""])
def binary_stdin(contents: bytes, *, client: Mock) -> None:
    def invoke(cmd: list[str], **kwargs: object) -> SandboxCommandResult:
        assert kwargs["stdin"] is None
        done = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return SandboxCommandResult(
            exit_code=done.returncode, stdout=done.stdout, stderr=done.stderr
        )

    client.run.side_effect = invoke
    client.files.write.side_effect = lambda file, data, **_options: Path(file).write_bytes(data)
    client.files.delete.side_effect = lambda file: Path(file).unlink()
    completion = asyncio.run(
        _adapter().exec(
            [
                "python3",
                "-c",
                "import sys; print(sys.stdin.buffer.read().hex()); print(sys.argv[1]); sys.exit(7)",
                "literal ; $HOME '",
            ],
            input=contents,
        )
    )
    assert (completion.returncode, completion.stdout) == (
        7,
        contents.hex() + "\nliteral ; $HOME '\n",
    )
    file = client.files.write.call_args.args[0]
    client.files.delete.assert_called_once_with(file)
    assert not Path(file).exists()


@pytest.mark.parametrize("failure", ["timeout", "exception"])
def exec_failure_cleans_binary_input(failure: str, *, client: Mock) -> None:
    if failure == "timeout":
        client.run.return_value = _result(timed_out=True)
    else:
        client.run.side_effect = TimeoutError("SDK timeout")
    with pytest.raises(TimeoutError):
        asyncio.run(_adapter().exec(["sleep", "10"], input=b""))
    client.files.delete.assert_called_once_with(client.files.write.call_args.args[0])
    client.close.assert_called_once_with()


def unsupported_user_precedes_command(client: Mock) -> None:
    with pytest.raises(SandboxUserUnsupportedError):
        asyncio.run(_adapter().exec(["id"], user="nobody"))
    client.run.assert_not_called()


@pytest.mark.parametrize("contents", ["line\r\n", b"\x00\xff"])
def file_io(contents: str | bytes, *, client: Mock) -> None:
    environment = _adapter()
    asyncio.run(environment.write_file("workspace/file", contents))
    data = contents.encode() if isinstance(contents, str) else contents
    client.files.write.assert_called_once_with("/eval/workspace/file", data)
    client.files.read.return_value = b"line\r\n"
    assert asyncio.run(environment.read_file("/eval/workspace/file")) == "line\r\n"
    assert asyncio.run(environment.read_file("workspace/file", text=False)) == b"line\r\n"


def creation_cancellation_cleans_eventual_sandbox(client: Mock) -> None:
    started, release = Event(), Event()

    def create(**_options: object) -> Mock:
        started.set()
        assert release.wait(timeout=5)
        return client

    async def cancel() -> None:
        task = asyncio.create_task(HfSandboxEnvironment.sample_init("eval", None, {}))
        assert await asyncio.to_thread(started.wait, 5)
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    with patch.object(Sandbox, "create", side_effect=create):
        asyncio.run(cancel())
    client.kill.assert_called_once_with()


@pytest.mark.parametrize("stdin", [None, "", b""])
def stdin_preserves_absent_text_and_binary(stdin: str | bytes | None, *, client: Mock) -> None:
    async def execute() -> None:
        await backend.environment("sandbox-id").execute(
            commands.Execution(command=("cat",), input=stdin)
        )

    asyncio.run(execute())
    assert client.files.write.called == isinstance(stdin, bytes)
    assert client.run.call_args.kwargs["stdin"] == (None if isinstance(stdin, bytes) else stdin)


@pytest.mark.parametrize("fails", [False, True])
def backend_allocation_owns_eventual_handle_after_repeated_cancellation(
    *, fails: bool, client: Mock
) -> None:
    started, release = Event(), Event()

    def create(**_options: object) -> Mock:
        started.set()
        assert release.wait(timeout=5)
        if fails:
            raise RuntimeError("creation failed")
        return client

    async def cancel() -> None:
        runtime = commands.create_runtime(provider="hf")
        task = asyncio.ensure_future(runtime.create())
        assert await asyncio.to_thread(started.wait, 5)
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    with patch.object(Sandbox, "create", side_effect=create):
        asyncio.run(cancel())
    assert client.kill.call_count == (not fails)


def cleanup_waits_for_eventual_kill_after_repeated_cancellation(client: Mock) -> None:
    started, release = Event(), Event()

    def kill() -> None:
        started.set()
        assert release.wait(timeout=5)

    async def cancel() -> None:
        runtime = commands.create_runtime(provider="hf")
        environment = await runtime.create()
        task = asyncio.create_task(runtime.cleanup(environment, interrupted=False))
        assert await asyncio.to_thread(started.wait, 5)
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    client.kill.side_effect = kill
    asyncio.run(cancel())
    client.kill.assert_called_once_with()
    assert client.close.call_count == 1


def inspect_event_wrapper_reuses_its_canonical_capabilities() -> None:
    sandbox = _adapter()
    wrapped = SandboxEnvironmentProxy(sandbox)
    assert environments.environment(wrapped) is sandbox.environment
    assert environments.runtime(wrapped) is sandbox.runtime


def persistent_runtime_reuses_client(client: Mock) -> None:
    async def exercise() -> None:
        runtime = backend.runtime()
        target = await runtime.create()
        await target.execute(commands.Execution(command=("true",)))
        await target.write_bytes("file", b"data")
        client.files.read.return_value = b"data"
        assert await target.read_bytes("file") == b"data"
        client.close.assert_not_called()
        await runtime.cleanup(target, interrupted=False)

    with patch.object(Sandbox, "connect") as connect:
        asyncio.run(exercise())
    connect.assert_not_called()
    client.close.assert_called_once_with()


@pytest.mark.parametrize("valid", [False, True])
def prepared_runtime_validation(
    *, valid: bool, client: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EVAL_SANDBOX_IMAGE", "private/prepared:fixed")
    monkeypatch.setenv("EVAL_RUN_ID", "run-123")
    monkeypatch.setenv("HF_NAMESPACE", "owner")
    client.run.return_value = _result(0 if valid else 1)
    with patch.object(Sandbox, "create", return_value=client) as create:
        expectation = (
            nullcontext() if valid else pytest.raises(RuntimeError, match="prepare eval tools")
        )
        with expectation:
            created = backend.create()
            backend.destroy(created)
    assert dict(create.call_args.kwargs) == {
        "image": "private/prepared:fixed",
        "idle_timeout": 900,
        "namespace": "owner",
        "forward_hf_token": False,
        "labels": {"genius-run": "run-123"},
    }
    _prepared_setup(client.run.call_args.args[0][2])
    client.close.assert_called_once_with()


def _prepared_setup(setup: str) -> None:
    assert "apt-get" not in setup
    assert "command -v" in setup


def cleanup_failure_closes_client(client: Mock) -> None:
    client.kill.side_effect = RuntimeError("kill failed")

    async def exercise() -> None:
        runtime = backend.runtime()
        target = await runtime.create()
        with pytest.raises(RuntimeError, match="kill failed"):
            await runtime.cleanup(target, interrupted=False)

    asyncio.run(exercise())
    client.close.assert_called_once_with()


@pytest.mark.parametrize("cancel_operation", [False, True])
def cleanup_settles_pending_operations(*, cancel_operation: bool, client: Mock) -> None:
    started, release = Event(), Event()

    def blocked() -> bytes:
        started.set()
        assert release.wait(timeout=5)
        return b"data"

    async def exercise() -> None:
        runtime = backend.runtime()
        target = await runtime.create()
        client.files.read.side_effect = lambda _file: blocked()
        operation = asyncio.ensure_future(target.read_bytes("file"))
        assert await asyncio.to_thread(started.wait, 5)
        if cancel_operation:
            operation.cancel()
        cleanup = asyncio.create_task(runtime.cleanup(target, interrupted=True))
        await asyncio.sleep(0)
        cleanup.cancel()
        await asyncio.sleep(0)
        cleanup.cancel()
        client.kill.assert_not_called()
        release.set()
        if cancel_operation:
            with pytest.raises(asyncio.CancelledError):
                await operation
        else:
            assert await operation == b"data"
        with pytest.raises(asyncio.CancelledError):
            await cleanup

    asyncio.run(exercise())
    client.kill.assert_called_once_with()
    client.close.assert_called_once_with()


@pytest.mark.parametrize("missing", [None, "python", "ocamlfind"])
def prepared_check_requires_every_tool(missing: str | None, *, tmp_path: Path) -> None:
    for tool in ("python", "bash", "curl", "git", "ocaml", "ocamlfind", "rg"):
        if tool != missing:
            (tmp_path / tool).symlink_to("/bin/sh")
    checked = subprocess.run(
        ["/bin/sh", "-c", backend.prepared_check()],
        env={"PATH": str(tmp_path)},
        capture_output=True,
        check=False,
    )
    assert (checked.returncode == 0) == (missing is None)
