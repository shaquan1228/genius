"""Check the hosted runner without creating paid Hugging Face Jobs."""

import asyncio
import os
import subprocess
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from huggingface_hub import SandboxCommandResult
from inspect_ai.model import GenerateConfig, get_model
from inspect_ai.model._providers.hf_inference_providers import HFInferenceProvidersAPI
from inspect_ai.scorer import Score
from inspect_ai.util import SandboxUserUnsupportedError

from evals.python.integrations.hugging_face.job import HfChatAPI, run, sample_limit
from evals.python.integrations.hugging_face.sandbox import HfSandboxEnvironment
from evals.python.paths import REPO_ROOT


def command_result(code: int | None = 0, *, timed_out: bool = False) -> SandboxCommandResult:
    return SandboxCommandResult(exit_code=code, stdout="done", stderr="", timed_out=timed_out)


def test_hf_sample_lifecycle() -> None:
    client = Mock()
    client.run.return_value = command_result()
    with patch(
        "evals.python.integrations.hugging_face.sandbox.Sandbox.create", return_value=client
    ):
        environment = asyncio.run(HfSandboxEnvironment.sample_init("genius", None, {}))["default"]
    assert isinstance(environment, HfSandboxEnvironment)
    client.files.mkdir.assert_called_once_with("/eval")
    asyncio.run(
        HfSandboxEnvironment.sample_cleanup(
            task_name="genius",
            config=None,
            environments={"default": environment},
            interrupted=False,
        )
    )
    client.kill.assert_called_once_with()


def test_hf_sandbox_command_io() -> None:
    client = Mock()
    client.run.return_value = command_result()
    environment = HfSandboxEnvironment(client)
    result = asyncio.run(environment.exec(["python3", "-V"], input="hello", cwd="workspace"))
    assert (result.success, result.stdout) == (True, "done")
    assert (client.run.call_args.kwargs["cwd"], client.run.call_args.kwargs["stdin"]) == (
        "/eval/workspace",
        "hello",
    )
    assert client.run.call_args.args[0] == ["python3", "-V"]


@pytest.mark.parametrize("payload", [b"\x1f\x8b\x00\xff\r\n", b""])
def test_hf_sandbox_binary_stdin(payload: bytes) -> None:
    client = Mock()

    def execute(cmd: list[str], **kwargs: object) -> SandboxCommandResult:
        assert kwargs["stdin"] is None
        result = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            check=False,
        )
        return SandboxCommandResult(
            exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr
        )

    client.run.side_effect = execute
    client.files.write.side_effect = lambda path, data, **_kwargs: Path(path).write_bytes(data)
    client.files.delete.side_effect = lambda path: Path(path).unlink()
    environment = HfSandboxEnvironment(client)
    result = asyncio.run(
        environment.exec(
            [
                "python3",
                "-c",
                "import sys; print(sys.stdin.buffer.read().hex()); print(sys.argv[1]); sys.exit(7)",
                "literal ; $HOME ' argument",
            ],
            input=payload,
        )
    )
    assert (result.stdout, result.returncode) == (
        f"{payload.hex()}\nliteral ; $HOME ' argument\n",
        7,
    )
    path = client.files.write.call_args.args[0]
    assert (client.files.write.call_args.args[1], client.files.write.call_args.kwargs) == (
        payload,
        {"mode": "0600"},
    )
    client.files.delete.assert_called_once_with(path)
    assert not Path(path).exists()


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
    with (
        patch("evals.python.integrations.hugging_face.sandbox.Sandbox.create", return_value=client),
        pytest.raises(RuntimeError, match="Could not install"),
    ):
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
        asyncio.run(environment.exec(["sleep", "10"], input=b"binary"))
    client.files.delete.assert_called_once_with(client.files.write.call_args.args[0])
    with pytest.raises(SandboxUserUnsupportedError):
        asyncio.run(environment.exec(["id"], user="nobody"))


@pytest.mark.parametrize("provider", ["openai", "hf-inference-providers"])
def test_hf_job_runs_both_profiles(provider: str, *, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVAL_MODEL", f"{provider}/test-model")
    monkeypatch.setenv("HF_TOKEN", "hf_test")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("EVAL_AGENT", "codex")
    logs = [
        SimpleNamespace(
            eval=SimpleNamespace(task=name),
            status="success",
            location=f"/results/{name}",
            samples=[],
        )
        for name in ("baseline", "genius")
    ]
    with patch(
        "evals.python.integrations.hugging_face.job.eval", return_value=logs
    ) as inspect_eval:
        assert run() == 0
    assert (
        [task.name for task in inspect_eval.call_args.args[0]],
        inspect_eval.call_args.kwargs["sandbox"],
        inspect_eval.call_args.kwargs["epochs"],
    ) == (["baseline", "genius"], "hf", 5)
    model = inspect_eval.call_args.kwargs["model"]
    assert (
        isinstance(model.api, HFInferenceProvidersAPI),
        getattr(model.api, "strict_tools", False),
    ) == (provider == "hf-inference-providers", False)


@pytest.mark.parametrize("extra_body", [None, {"prompt_cache_key": "codex-session", "top_k": 5}])
def test_hf_chat_omits_codex_cache_key(extra_body: dict[str, object] | None) -> None:
    api = HfChatAPI(model_name="openai/gpt-oss-20b", api_key="hf_test")
    config = GenerateConfig(extra_body=extra_body)
    params = api.completion_params(config, tools=False)
    assert params.get("extra_body", {}) == ({"top_k": 5} if extra_body else {})
    assert config.extra_body == extra_body


def test_hf_job_reports_failed_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVAL_MODEL", "openai/test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    logs = [
        SimpleNamespace(
            eval=SimpleNamespace(task="baseline"), status="error", location="log", samples=None
        )
    ]
    with patch("evals.python.integrations.hugging_face.job.eval", return_value=logs):
        assert run() == 1


@pytest.mark.parametrize(
    ("failures", "summary"),
    [
        ((None, None), "baseline: 0 of 3 samples had an agent crash"),
        (
            ("Error executing codex cli agent 1: x", None),
            "baseline: 1 of 3 samples had an agent crash",
        ),
    ],
)
def test_hf_job_counts_crashed_samples(
    failures: tuple[str | None, ...],
    *,
    summary: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("EVAL_MODEL", "openai/test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    scored = [
        SimpleNamespace(scores={"evaluation": Score(value={}, metadata={"agent_failure": failure})})
        for failure in failures
    ]
    samples = [*scored, SimpleNamespace(scores=None)]  # A sample error leaves no score.
    log = SimpleNamespace(
        eval=SimpleNamespace(task="baseline"), status="success", location="log", samples=samples
    )
    with patch("evals.python.integrations.hugging_face.job.eval", return_value=[log]):
        assert run() == 0
    assert capsys.readouterr().out.splitlines() == ["baseline: success (log)", summary]


@pytest.mark.parametrize("job_exit", [0, 7])
def test_host_script_launches_job_without_exposing_key(
    job_exit: int, *, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = tmp_path / "uvx"
    launcher.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$HF_CALLS"\n'
        f'case "$*" in *"hf jobs run"*) exit {job_exit} ;; esac\n'
    )
    launcher.chmod(0o755)
    calls = tmp_path / "calls.txt"
    monkeypatch.setenv("HF_CALLS", str(calls))
    monkeypatch.setenv("HF_NAMESPACE", "example")
    monkeypatch.setenv("EVAL_MODEL", "openai/test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "private-test-key")
    monkeypatch.setenv("EVAL_VERSION", "test-pinned-version")
    monkeypatch.setenv("GIT_TEST_ASSUME_DIFFERENT_OWNER", "1")
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")

    result = subprocess.run(
        ["sh", "evals/hf_host.sh"],
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        check=False,
    )
    commands = calls.read_text()
    assert (result.returncode, commands.count("--from huggingface_hub==2.2.0 hf")) == (job_exit, 4)
    assert "hf://datasets/example/genius-evals:/source:ro" in commands
    assert "hf://buckets/example/genius-eval-results:/results:rw" in commands
    assert (
        "private-test-key" in commands,
        "--env EVAL_VERSION=test-pinned-version" in commands,
        "--detach" in commands,
    ) == (False, True, False)


def test_host_script_uses_hf_model_without_provider_key(
    *, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = tmp_path / "uvx"
    launcher.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$HF_CALLS"\n')
    launcher.chmod(0o755)
    calls = tmp_path / "calls.txt"
    monkeypatch.setenv("HF_CALLS", str(calls))
    monkeypatch.setenv("HF_NAMESPACE", "example")
    monkeypatch.setenv("EVAL_MODEL", "hf-inference-providers/openai/gpt-oss-20b:nscale")
    monkeypatch.delenv("EVAL_AGENT", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")

    result = subprocess.run(
        ["sh", "evals/hf_host.sh"],
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode()
    commands = calls.read_text()
    assert (
        "--secrets HF_TOKEN --env EVAL_AGENT=codex" in commands,
        "--env EVAL_MODEL=hf-inference-providers/openai/gpt-oss-20b:nscale" in commands,
    ) == (True, True)
    assert "OPENAI_API_KEY" not in commands


def test_host_script_rejects_empty_provider_key(
    *, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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
        ["sh", "evals/hf_host.sh"],
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        check=False,
    )
    assert (result.returncode, calls.exists()) == (2, False)
    assert b"Set OPENAI_API_KEY" in result.stderr


def test_hf_inference_provider_initializes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HF_TOKEN", "hf_test")
    model = get_model("genius-hf/openai/gpt-oss-20b:nscale")
    assert (model.name, model.api.canonical_name()) == (
        "openai/gpt-oss-20b:nscale",
        "openai/gpt-oss-20b",
    )


def test_cancelled_creation_kills_eventual_sandbox() -> None:
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

    with patch("evals.python.integrations.hugging_face.sandbox.Sandbox.create", side_effect=create):
        asyncio.run(cancel_during_creation())
    client.kill.assert_called_once_with()


@pytest.mark.parametrize(("value", "expected"), [("3", 3), ("", None), (None, None)])
def test_hf_sample_limit(
    *, monkeypatch: pytest.MonkeyPatch, value: str | None, expected: int | None
) -> None:
    monkeypatch.delenv("EVAL_LIMIT", raising=False)
    if value is not None:
        monkeypatch.setenv("EVAL_LIMIT", value)
    assert sample_limit() == expected


@pytest.mark.parametrize("value", ["0", "-1", "invalid"])
def test_hf_sample_limit_rejects_invalid(*, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("EVAL_LIMIT", value)
    with pytest.raises(ValueError, match=r"positive|invalid literal"):
        sample_limit()


def test_hf_epoch_override_is_shared_with_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVAL_MODEL", "openai/test-model")
    monkeypatch.setenv("EVAL_EPOCHS", "3")
    with (
        patch("evals.python.integrations.hugging_face.job.get_model"),
        patch("evals.python.integrations.hugging_face.job.eval", return_value=[]) as inspect_eval,
    ):
        assert run() == 0
    tasks = inspect_eval.call_args.args[0]
    assert ([task.epochs for task in tasks], inspect_eval.call_args.kwargs["epochs"]) == (
        [3, 3],
        3,
    )
