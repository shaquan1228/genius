"""Check the hosted runner without creating paid Hugging Face Jobs."""

import asyncio
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from huggingface_hub import SandboxCommandResult
from inspect_ai.model import get_model
from inspect_ai.util import SandboxUserUnsupportedError

from evals.python.hf_job import run
from evals.python.hf_sandbox import HfSandboxEnvironment
from evals.python.paths import REPO_ROOT


def command_result(code: int | None = 0, *, timed_out: bool = False) -> SandboxCommandResult:
    return SandboxCommandResult(exit_code=code, stdout="done", stderr="", timed_out=timed_out)


def test_hf_sample_lifecycle() -> None:
    client = Mock()
    client.run.return_value = command_result()
    with patch("evals.python.hf_sandbox.Sandbox.create", return_value=client):
        environment = asyncio.run(HfSandboxEnvironment.sample_init("genius", None, {}))["default"]
    assert isinstance(environment, HfSandboxEnvironment)
    client.files.mkdir.assert_called_once_with("/eval")
    asyncio.run(
        HfSandboxEnvironment.sample_cleanup("genius", None, {"default": environment}, False)
    )
    client.kill.assert_called_once_with()


def test_hf_sandbox_command_io() -> None:
    client = Mock()
    client.run.return_value = command_result()
    environment = HfSandboxEnvironment(client)
    result = asyncio.run(environment.exec(["python3", "-V"], input=b"hello", cwd="workspace"))
    assert (result.success, result.stdout) == (True, "done")
    assert (client.run.call_args.kwargs["cwd"], client.run.call_args.kwargs["stdin"]) == (
        "/eval/workspace",
        "hello",
    )


def test_hf_sandbox_file_io() -> None:
    client = Mock()
    client.files.read.return_value = b"line\r\n"
    environment = HfSandboxEnvironment(client)
    asyncio.run(environment.write_file("workspace/test.py", "print(1)"))
    client.files.write.assert_called_once_with("/eval/workspace/test.py", "print(1)")
    assert asyncio.run(environment.read_file("/eval/workspace/test.py")) == "line\r\n"
    assert asyncio.run(environment.read_file("workspace/test.py", text=False)) == b"line\r\n"


def test_failed_setup_kills_remote_sandbox() -> None:
    client = Mock()
    client.run.return_value = command_result(1)
    with patch("evals.python.hf_sandbox.Sandbox.create", return_value=client):
        with pytest.raises(RuntimeError, match="Could not install"):
            asyncio.run(HfSandboxEnvironment.sample_init("genius", None, {}))
    client.kill.assert_called_once_with()


def test_exec_failure_timeout_and_unsupported_user() -> None:
    client = Mock()
    environment = HfSandboxEnvironment(client)
    client.run.return_value = command_result(3)
    assert not asyncio.run(environment.exec(["false"])).success
    client.run.return_value = command_result(None)
    assert asyncio.run(environment.exec(["killed"])).returncode == 1
    client.run.return_value = command_result(timed_out=True)
    with pytest.raises(TimeoutError):
        asyncio.run(environment.exec(["sleep", "10"]))
    with pytest.raises(SandboxUserUnsupportedError):
        asyncio.run(environment.exec(["id"], user="nobody"))


def test_hf_job_runs_both_profiles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVAL_MODEL", "openai/test-model")
    monkeypatch.setenv("EVAL_AGENT", "codex")
    logs = [
        SimpleNamespace(
            eval=SimpleNamespace(task=name), status="success", location=f"/results/{name}"
        )
        for name in ("baseline", "genius")
    ]
    with patch("evals.python.hf_job.eval", return_value=logs) as inspect_eval:
        assert run() == 0
    assert (
        [task.name for task in inspect_eval.call_args.args[0]],
        inspect_eval.call_args.kwargs["sandbox"],
        inspect_eval.call_args.kwargs["epochs"],
    ) == (["baseline", "genius"], "hf", 5)


def test_hf_job_reports_failed_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVAL_MODEL", "openai/test-model")
    logs = [SimpleNamespace(eval=SimpleNamespace(task="baseline"), status="error", location="log")]
    with patch("evals.python.hf_job.eval", return_value=logs):
        assert run() == 1


def test_host_script_launches_job_without_exposing_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = tmp_path / "uvx"
    launcher.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$HF_CALLS"\n')
    launcher.chmod(0o755)
    calls = tmp_path / "calls.txt"
    monkeypatch.setenv("HF_CALLS", str(calls))
    monkeypatch.setenv("HF_NAMESPACE", "example")
    monkeypatch.setenv("EVAL_MODEL", "openai/test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "private-test-key")
    monkeypatch.setenv("EVAL_VERSION", "test-pinned-version")
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")

    result = subprocess.run(
        ["sh", "evals/hf_host.sh"], cwd=REPO_ROOT, env=os.environ.copy(), capture_output=True
    )
    commands = calls.read_text()
    assert (result.returncode, commands.count("--from huggingface_hub==2.2.0 hf")) == (0, 4)
    assert "hf://datasets/example/genius-evals:/source:ro" in commands
    assert "hf://buckets/example/genius-eval-results:/results:rw" in commands
    assert (
        "private-test-key" in commands,
        "--env EVAL_VERSION=test-pinned-version" in commands,
    ) == (False, True)


def test_host_script_uses_hf_model_without_provider_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = tmp_path / "uvx"
    launcher.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$HF_CALLS"\n')
    launcher.chmod(0o755)
    calls = tmp_path / "calls.txt"
    monkeypatch.setenv("HF_CALLS", str(calls))
    monkeypatch.setenv("HF_NAMESPACE", "example")
    monkeypatch.setenv("EVAL_MODEL", "hf-inference-providers/openai/gpt-oss-20b")
    monkeypatch.delenv("EVAL_AGENT", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")

    result = subprocess.run(
        ["sh", "evals/hf_host.sh"], cwd=REPO_ROOT, env=os.environ.copy(), capture_output=True
    )
    commands = calls.read_text()
    assert result.returncode == 0
    assert "--secrets HF_TOKEN --env EVAL_AGENT=codex" in commands
    assert "OPENAI_API_KEY" not in commands


def test_host_script_rejects_empty_provider_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = tmp_path / "uvx"
    launcher.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$HF_CALLS"\n')
    launcher.chmod(0o755)
    calls = tmp_path / "calls.txt"
    monkeypatch.setenv("HF_CALLS", str(calls))
    monkeypatch.setenv("HF_NAMESPACE", "example")
    monkeypatch.setenv("EVAL_MODEL", "openai/test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")

    result = subprocess.run(
        ["sh", "evals/hf_host.sh"], cwd=REPO_ROOT, env=os.environ.copy(), capture_output=True
    )
    assert (result.returncode, calls.exists()) == (2, False)
    assert b"Set OPENAI_API_KEY" in result.stderr


def test_hf_inference_provider_initializes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HF_TOKEN", "hf_test")
    model = get_model("hf-inference-providers/openai/gpt-oss-20b")
    assert model.name == "openai/gpt-oss-20b"


def test_cancelled_creation_kills_eventual_sandbox() -> None:
    from threading import Event

    started, release = Event(), Event()
    client = Mock()

    def create(**_kwargs: object) -> Mock:
        started.set()
        assert release.wait(timeout=5)
        return client

    async def cancel_during_creation() -> None:
        task = asyncio.create_task(HfSandboxEnvironment.sample_init("genius", None, {}))
        assert await asyncio.to_thread(started.wait, 5)
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    with patch("evals.python.hf_sandbox.Sandbox.create", side_effect=create):
        asyncio.run(cancel_during_creation())
    client.kill.assert_called_once_with()
