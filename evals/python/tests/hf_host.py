"""Check the hosted runner without creating paid Hugging Face Jobs."""

import asyncio
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import assert_type
from unittest.mock import AsyncMock, patch

import pytest
from inspect_ai.model import GenerateConfig, get_model
from inspect_ai.model._providers.hf_inference_providers import HFInferenceProvidersAPI
from inspect_ai.scorer import Score

from evals.python import commands, query
from evals.python.integrations.hugging_face.job import configuration, run
from evals.python.integrations.inspect.evaluation import HfChatAPI
from evals.python.paths import REPO_ROOT


def _configured_request() -> commands.EvaluationSettings:
    environment = {"EVAL_MODEL": "openai/test-model", **os.environ}
    return configuration(environment)


def hf_job_calls_evaluation_with_validated_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVAL_MODEL", "openai/test-model")
    monkeypatch.setenv("EVAL_SAMPLE_IDS", '["clear-task"]')
    monkeypatch.setenv("EVAL_DELIVERIES", '["files", "manifest"]')
    monkeypatch.setenv("EVAL_EPOCHS", "2")
    monkeypatch.setenv("EVAL_TOKEN_LIMIT", "50000")
    before = dict(os.environ)
    with patch.object(commands, "Evaluate", new_callable=AsyncMock, return_value=7) as execute:
        assert run() == 7
    request = commands.EvaluationSettings.model_validate(execute.call_args.kwargs)
    assert isinstance(request, commands.EvaluationSettings)
    assert (request.sample_ids, request.deliveries, request.epochs, request.token_limit) == (
        ("clear-task",),
        ("files", "manifest"),
        2,
        50000,
    )
    assert (request.sandbox, request.instruction_root, dict(os.environ)) == (
        "hf",
        "/eval/instructions",
        before,
    )


def inspect_evaluation_uses_request_without_reading_job_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = commands.EvaluationSettings(model="openai/explicit")
    monkeypatch.setenv("EVAL_MODEL", "invalid-environment-model")
    monkeypatch.setenv("EVAL_AGENT", "invalid-environment-agent")
    monkeypatch.setenv("EVAL_SAMPLE_IDS", "invalid")
    monkeypatch.setenv("EVAL_DELIVERIES", "invalid")
    with (
        patch("evals.python.integrations.inspect.evaluation.get_model") as model,
        patch(
            "evals.python.integrations.inspect.evaluation.eval_async", return_value=[]
        ) as evaluate,
    ):

        async def execute() -> int:
            return assert_type(await commands.Evaluate(**request.model_dump()), int)

        assert asyncio.run(execute()) == 1
        assert evaluate.call_args.args[0] is not None
    model.assert_called_once_with("openai/explicit")
    tasks = evaluate.call_args.args[0]
    assert [
        (task.name, task.metadata["agent"], task.metadata["instruction_delivery"]) for task in tasks
    ] == [
        ("baseline", "claude", "files"),
        ("genius", "claude", "files"),
    ]
    assert evaluate.call_args.kwargs["sandbox"] == "local"


@pytest.mark.parametrize("provider", ["openai", "hf-inference-providers"])
def hf_job_runs_both_profiles(provider: str, *, monkeypatch: pytest.MonkeyPatch) -> None:
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
        "evals.python.integrations.inspect.evaluation.eval_async", return_value=logs
    ) as inspect_eval:
        assert run() == 1
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
    _hf_nonstreaming(model.api)


def _hf_nonstreaming(api: object) -> None:
    if isinstance(api, HFInferenceProvidersAPI):
        assert api.stream is False


@pytest.mark.parametrize("extra_body", [None, {"prompt_cache_key": "codex-session", "top_k": 5}])
def hf_chat_omits_codex_cache_key(extra_body: dict[str, object] | None) -> None:
    api = HfChatAPI(model_name="openai/gpt-oss-20b", api_key="hf_test")
    config = GenerateConfig(extra_body=extra_body)
    params = api.completion_params(config, tools=False)
    assert params.get("extra_body", {}) == ({"top_k": 5} if extra_body else {})
    assert config.extra_body == extra_body


def hf_job_reports_failed_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVAL_MODEL", "openai/test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    logs = [
        SimpleNamespace(
            eval=SimpleNamespace(task="baseline"), status="error", location="log", samples=None
        )
    ]
    with patch("evals.python.integrations.inspect.evaluation.eval_async", return_value=logs):
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
def hf_job_counts_crashed_samples(
    failures: tuple[str | None, ...],
    *,
    summary: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("EVAL_MODEL", "openai/test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    scored = [
        SimpleNamespace(
            id=str(index),
            epoch=1,
            error=None,
            limit=None,
            scores={"evaluation": Score(value={}, metadata={"agent_failure": failure})},
        )
        for index, failure in enumerate(failures)
    ]
    samples = [
        *scored,
        SimpleNamespace(id="unscored", epoch=1, error=None, limit=None, scores=None),
    ]  # A sample error leaves no score.
    log = SimpleNamespace(
        eval=SimpleNamespace(task="baseline"), status="success", location="log", samples=samples
    )
    with patch("evals.python.integrations.inspect.evaluation.eval_async", return_value=[log]):
        assert run() == 1
    assert summary in capsys.readouterr().out.splitlines()


@pytest.mark.parametrize("job_exit", [0, 7])
def host_script_launches_job_without_exposing_key(
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
        ["sh", "evals/bin/hf_host.sh"],
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        check=False,
    )
    commands = calls.read_text()
    assert (result.returncode, commands.count("--from huggingface_hub==2.2.0 hf")) == (job_exit, 4)
    assert (
        "hf://datasets/example/genius-evals:/source:ro" in commands,
        "hf://buckets/example/genius-eval-results:/results:rw" in commands,
        "sh /source/evals/bin/hf_bootstrap.sh" in commands,
        "--repo-type dataset --delete * --commit-message" in commands,
    ) == (True, True, True, True)
    assert (
        "private-test-key" in commands,
        "--env EVAL_VERSION=test-pinned-version" in commands,
        "--detach" in commands,
    ) == (False, True, False)


def host_script_uses_hf_model_without_provider_key(
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
        ["sh", "evals/bin/hf_host.sh"],
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


def host_script_rejects_empty_provider_key(
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
        ["sh", "evals/bin/hf_host.sh"],
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        check=False,
    )
    assert (result.returncode, calls.exists()) == (2, False)
    assert b"Set OPENAI_API_KEY" in result.stderr


def hf_inference_provider_initializes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HF_TOKEN", "hf_test")
    model = get_model("genius-hf/openai/gpt-oss-20b:nscale")
    assert (model.name, model.api.canonical_name()) == (
        "openai/gpt-oss-20b:nscale",
        "openai/gpt-oss-20b",
    )


@pytest.mark.parametrize(("value", "expected"), [("3", 3), ("", None), (None, None)])
def hf_sample_limit(
    *, monkeypatch: pytest.MonkeyPatch, value: str | None, expected: int | None
) -> None:
    monkeypatch.delenv("EVAL_LIMIT", raising=False)
    if value is not None:
        monkeypatch.setenv("EVAL_LIMIT", value)
    assert _configured_request().limit == expected


@pytest.mark.parametrize("value", ["0", "-1", "invalid"])
def hf_sample_limit_rejects_invalid(*, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("EVAL_LIMIT", value)
    with pytest.raises(ValueError, match=r"greater than 0|invalid literal"):
        _configured_request()


def hf_epoch_override_is_shared_with_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVAL_MODEL", "openai/test-model")
    monkeypatch.setenv("EVAL_EPOCHS", "3")
    with (
        patch("evals.python.integrations.inspect.evaluation.get_model"),
        patch(
            "evals.python.integrations.inspect.evaluation.eval_async", return_value=[]
        ) as inspect_eval,
    ):
        assert run() == 1
    tasks = inspect_eval.call_args.args[0]
    assert ([task.epochs for task in tasks], inspect_eval.call_args.kwargs["epochs"]) == (
        [3, 3],
        3,
    )


@pytest.mark.parametrize("value", ["[]", '["x", "x"]', "[1]", '"x"', "invalid"])
def explicit_cohort_rejects_invalid_json_or_duplicates(
    value: str, *, monkeypatch: pytest.MonkeyPatch
) -> None:

    monkeypatch.setenv("EVAL_SAMPLE_IDS", value)
    with pytest.raises(ValueError, match=r"unique|validation error|Expecting|JSON list"):
        _configured_request()


@pytest.mark.parametrize("deliveries", ["[]", '["files"]', '["files", "files"]', '["typo"]'])
def delivery_comparison_rejects_invalid_modes(
    deliveries: str, *, monkeypatch: pytest.MonkeyPatch
) -> None:

    monkeypatch.setenv("EVAL_DELIVERIES", deliveries)
    with pytest.raises(ValueError, match=r"unique|validation error|Expecting"):
        _configured_request()


@pytest.mark.parametrize("setting", ["EVAL_SAMPLE_IDS", "EVAL_DELIVERIES"])
@pytest.mark.parametrize("value", ["null", "{}", '"files"', "1", "true"])
def explicit_non_list_selection_never_reaches_evaluation(
    setting: str, *, value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EVAL_MODEL", "openai/test-model")
    monkeypatch.setenv(setting, value)
    with (
        patch("evals.python.integrations.hugging_face.job.commands.Evaluate") as dispatch,
        patch("evals.python.integrations.inspect.evaluation.get_model") as model,
        patch("evals.python.integrations.inspect.evaluation.eval_async") as evaluate,
        pytest.raises(ValueError, match="JSON list"),
    ):
        run()
    dispatch.assert_not_called()
    model.assert_not_called()
    evaluate.assert_not_called()


@pytest.mark.parametrize("limit", ["", "1"])
def explicit_cohort_validation_precedes_sandbox_allocation(
    limit: str, *, monkeypatch: pytest.MonkeyPatch
) -> None:

    monkeypatch.setenv("EVAL_SAMPLE_IDS", '["missing-case"]')
    monkeypatch.setenv("EVAL_LIMIT", limit)
    monkeypatch.setenv("EVAL_MODEL", "openai/test-model")
    with (
        patch("evals.python.integrations.inspect.evaluation.get_model"),
        patch("evals.python.integrations.inspect.evaluation.eval_async") as evaluate,
        pytest.raises(ValueError, match=r"Unknown sample|Choose EVAL_SAMPLE_IDS"),
    ):
        run()
    evaluate.assert_not_called()


def counterbalanced_delivery_comparison_keeps_limits_and_exact_cohort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    monkeypatch.setenv("EVAL_SAMPLE_IDS", '["clear-task"]')
    monkeypatch.setenv("EVAL_DELIVERIES", '["files", "manifest"]')
    monkeypatch.setenv("EVAL_EPOCHS", "2")
    monkeypatch.setenv("EVAL_TOKEN_LIMIT", "50000")
    monkeypatch.setenv("EVAL_MODEL", "openai/test-model")
    catalog = query.LoadDataset()
    cohort = catalog.model_copy(update={"cases": {"clear-task": catalog.cases["clear-task"]}})
    with (
        patch("evals.python.integrations.inspect.evaluation.get_model"),
        patch("evals.python.query.LoadDataset", return_value=cohort),
        patch(
            "evals.python.integrations.inspect.evaluation.eval_async", return_value=[]
        ) as evaluate,
    ):
        assert run() == 1
    tasks = evaluate.call_args.args[0]
    assert [
        (t.name, t.epochs, t.token_limit, t.time_limit, t.metadata["diagnostic_epoch"])
        for t in tasks
    ] == [
        ("genius-files-r1", 1, 50000, 300, 1),
        ("genius-manifest-r1", 1, 50000, 300, 1),
        ("genius-manifest-r2", 1, 50000, 300, 2),
        ("genius-files-r2", 1, 50000, 300, 2),
    ]
    options = evaluate.call_args.kwargs
    assert {k: options[k] for k in ["sample_id", "epochs", "max_tasks", "max_samples"]} == {
        "sample_id": ["clear-task"],
        "epochs": 1,
        "max_tasks": 1,
        "max_samples": 1,
    }


@pytest.mark.parametrize("value", ["0", "-1", "17", "invalid", "999999999999999999999999999999"])
def host_rejects_invalid_concurrency(value: str, *, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HF_NAMESPACE", "example")
    monkeypatch.setenv("EVAL_MODEL", "mockllm/model")
    monkeypatch.setenv("EVAL_MAX_SAMPLES", value)
    result = subprocess.run(
        ["sh", "evals/bin/hf_host.sh"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert b"EVAL_MAX_SAMPLES must be an integer from 1 to 16" in result.stderr
