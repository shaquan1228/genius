"""Hosted comparison safety without network or paid jobs."""

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from evals.python import comparison
from evals.python.comparison import ComparisonRequest, VariantRequest
from evals.python.evaluation import EvaluationSettings, VariantSettings
from evals.python.integrations.hugging_face import compare, source


def _request() -> ComparisonRequest:
    return ComparisonRequest(
        comparison_id="test-comparison",
        shared=EvaluationSettings(model="openai/test", log_dir="/results"),
        control=VariantRequest(variant=VariantSettings(name="control", instructions=())),
        treatment=VariantRequest(variant=VariantSettings(name="treatment", instructions=())),
    )


def _repository(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / "SKILL.md").write_text("instructions")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-qm",
            "instructions",
        ],
        check=True,
    )


def exports_only_instruction_data(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _repository(repo)
    destination = tmp_path / "snapshot"
    result = source.instructions(
        VariantSettings(name="test", instructions=("SKILL.md",)),
        destination=destination,
        repository=repo,
    )
    assert result.source_ref == source.resolve("HEAD", repository=repo)
    assert (destination / "SKILL.md").read_text() == "instructions"
    assert not (destination / ".git").exists()


def rejects_link_instructions(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _repository(repo)
    name = "link.md"
    (repo / name).symlink_to("SKILL.md")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-qm",
            "unsafe",
        ],
        check=True,
    )
    with pytest.raises(ValueError, match="regular instruction data"):
        source.instructions(
            VariantSettings(name="bad", instructions=(name,)),
            destination=tmp_path / "out",
            repository=repo,
        )


def rejects_local_source_and_option_refs(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="local source_dir"):
        source.instructions(
            VariantSettings(name="bad", source_dir="/tmp"),
            destination=tmp_path,
            repository=tmp_path,
        )
    with pytest.raises(ValueError, match="Invalid source"):
        source.resolve("--help", repository=tmp_path)


def _mocked_execute(tmp_path: Path, *, api: MagicMock, candidate: ComparisonRequest) -> None:
    with (
        patch.object(compare, "committed_harness"),
        patch.object(compare, "resolve_request", side_effect=lambda value: value),
        patch.object(compare, "credentials", return_value={"HF_TOKEN": "secret"}),
        patch.object(source, "trusted_snapshot", return_value="harness-sha"),
        patch.object(source, "instructions", side_effect=lambda variant, **_: variant),
        patch.object(comparison, "prepare_run", return_value=object()),
        patch.object(compare, "validate_saved"),
        patch.object(comparison, "compare_runs", return_value={"verdict": "inconclusive"}),
        patch.object(comparison, "render_report", return_value="summary"),
    ):
        api.upload_folder.return_value = SimpleNamespace(oid="immutable-sha")
        compare.execute(candidate, output=tmp_path, namespace="example", api=api)


def submits_both_before_wait_and_pins_source(tmp_path: Path) -> None:
    api = MagicMock()
    api.run_job.side_effect = [
        SimpleNamespace(id="control-job"),
        SimpleNamespace(id="treatment-job"),
    ]
    api.inspect_job.return_value = SimpleNamespace(status=SimpleNamespace(stage="COMPLETED"))
    _mocked_execute(tmp_path, api=api, candidate=_request())
    _assert_dispatch_order(api)
    for call in api.run_job.call_args_list:
        _assert_dispatch_configuration(call.kwargs)
    assert json.loads((tmp_path / "jobs.json").read_text())["jobs"] == {
        "control": "control-job",
        "treatment": "treatment-job",
    }
    assert (tmp_path / "comparison.json").exists()
    assert "secret" not in (tmp_path / "jobs.json").read_text()


def _assert_dispatch_order(api: MagicMock) -> None:
    names = [call[0] for call in api.mock_calls]
    submissions = [index for index, name in enumerate(names) if name == "run_job"]
    assert names.index("inspect_job") > max(submissions)


def _assert_dispatch_configuration(options: dict[str, object]) -> None:
    from typing import Any, cast  # noqa: PLC0415

    data = cast(dict[str, Any], options)
    assert data["volumes"][0].revision == "immutable-sha"
    assert data["volumes"][1].path.startswith("runs/")
    assert data["env"]["EVAL_LOG_DIR"] == "/results"
    assert data["env"]["EVAL_VARIANT"].find("/source/.variants/") > 0


def cancels_outstanding_job_on_failure(tmp_path: Path) -> None:
    api = MagicMock()
    api.run_job.side_effect = [SimpleNamespace(id="first"), RuntimeError("dispatch failed")]
    with pytest.raises(RuntimeError, match="dispatch failed"):
        _mocked_execute(tmp_path, api=api, candidate=_request())
    api.cancel_job.assert_called_once_with(job_id="first", namespace="example")
    assert json.loads((tmp_path / "jobs.json").read_text())["jobs"]["control"] == "first"


def cancels_jobs_on_keyboard_interrupt(tmp_path: Path) -> None:
    api = MagicMock()
    api.run_job.side_effect = [SimpleNamespace(id="first"), KeyboardInterrupt()]
    with pytest.raises(KeyboardInterrupt):
        _mocked_execute(tmp_path, api=api, candidate=_request())
    api.cancel_job.assert_called_once_with(job_id="first", namespace="example")


def saved_mismatch_prevents_paid_dispatch(tmp_path: Path) -> None:
    candidate = _request().model_copy(
        update={"control": _request().control.model_copy(update={"result_ref": "prior-run"})}
    )
    api = MagicMock()
    with (
        patch.object(compare, "committed_harness"),
        patch.object(compare, "resolve_request", side_effect=lambda value: value),
        patch.object(compare, "credentials", return_value={"HF_TOKEN": "secret"}),
        patch.object(source, "trusted_snapshot", return_value="sha"),
        patch.object(source, "instructions", side_effect=lambda variant, **_: variant),
        patch.object(comparison, "prepare_run", return_value=object()),
        patch.object(compare, "validate_saved", side_effect=ValueError("Saved run does not match")),
        pytest.raises(ValueError, match="does not match"),
    ):
        compare.execute(candidate, output=tmp_path, namespace="example", api=api)
    api.run_job.assert_not_called()
    api.upload_folder.assert_not_called()


def _commit(repository: Path) -> None:
    subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-qm",
            "snapshot",
        ],
        check=True,
    )


def _harness_repository(repository: Path) -> None:
    _repository(repository)
    for name in ("README.md", "docs/readme.md", "skills/example/SKILL.md", "evals/python/job.py"):
        path = repository / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name)
    _commit(repository)


@pytest.mark.parametrize("change", ["clean", "dirty", "untracked", "test", "notes"])
def harness_requires_committed_runtime(
    tmp_path: Path, *, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    _harness_repository(tmp_path)
    monkeypatch.setattr(compare, "REPO_ROOT", tmp_path)
    _change_harness(tmp_path, change=change)
    if change in {"dirty", "untracked"}:
        with pytest.raises(ValueError, match="Commit the trusted"):
            compare.committed_harness()
    else:
        compare.committed_harness()


def _change_harness(repository: Path, *, change: str) -> None:
    names = {
        "dirty": "evals/python/job.py",
        "untracked": "evals/python/new.py",
        "test": "evals/python/tests/new.py",
        "notes": "evals/python/notes.md",
    }
    if change in names:
        path = repository / names[change]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("changed")


def trusted_snapshot_exports_exact_committed_tree(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    _harness_repository(repository)
    revision = source.resolve("HEAD", repository=repository)
    (repository / "evals/python/job.py").write_text("dirty")
    destination = tmp_path / "snapshot"
    assert source.trusted_snapshot(destination, repository=repository) == revision
    assert (destination / "evals/python/job.py").read_text() == "evals/python/job.py"
    assert not (destination / "SKILL.md").exists()


def missing_instruction_path_rejected(tmp_path: Path) -> None:
    _repository(tmp_path)
    with pytest.raises(ValueError, match="Instruction path not found"):
        source.instructions(
            VariantSettings(name="missing", instructions=("missing",)),
            destination=tmp_path / "export",
            repository=tmp_path,
        )


def exported_blob_cannot_escape_snapshot(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="escapes snapshot"):
        source.export_blob(
            b"100644 blob 012345\t../escape", destination=tmp_path, repository=tmp_path
        )
    assert not (tmp_path.parent / "escape").exists()


def resolution_freezes_public_run_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    from evals.python.evaluation import ModelPricing  # noqa: PLC0415

    monkeypatch.setenv("EVAL_SANDBOX_IMAGE", "sandbox@sha256:fixed")
    settings = EvaluationSettings(
        model="openai/test",
        agent="codex",
        sample_ids=("clear-task",),
        epochs=2,
        time_limit=23,
        message_limit=7,
        cache=False,
        model_cost=ModelPricing(input=1, output=2, input_cache_write=3, input_cache_read=4),
    )
    resolved = compare.resolve_request(_request().model_copy(update={"shared": settings}))
    assert resolved.shared.version not in {"", "latest", "stable", "next"}
    assert resolved.shared.model_dump(
        include={
            "variant",
            "sample_ids",
            "epochs",
            "time_limit",
            "message_limit",
            "cache",
            "model_cost",
            "sandbox_image",
            "sandbox",
            "log_dir",
        }
    ) == {
        "variant": None,
        "sample_ids": ("clear-task",),
        "epochs": 2,
        "time_limit": 23,
        "message_limit": 7,
        "cache": False,
        "model_cost": settings.model_cost.model_dump() if settings.model_cost else None,
        "sandbox_image": "sandbox@sha256:fixed",
        "sandbox": "hf",
        "log_dir": "/results",
    }


@pytest.mark.parametrize("version", ["", "latest", "stable", "next"])
def resolution_rejects_unpinned_agent(version: str) -> None:
    settings = _request().shared.model_copy(update={"version": version})
    with (
        patch.object(comparison, "prepare_run", return_value=SimpleNamespace(settings=settings)),
        pytest.raises(ValueError, match="exact agent version"),
    ):
        compare.resolve_request(_request())


@pytest.mark.parametrize(
    ("model", "tokens", "message"),
    [
        ("unsupported/test", {"HF_TOKEN": "hf"}, "Choose an"),
        ("hf-inference-providers/test", {"HF_TOKEN": "hf"}, "exact model_cost"),
        ("openai/test", {"HF_TOKEN": "hf", "OPENAI_API_KEY": ""}, "Missing required"),
        ("anthropic/test", {"HF_TOKEN": "", "ANTHROPIC_API_KEY": "key"}, "Missing required"),
    ],
)
def invalid_credentials_fail_before_dispatch(
    *, model: str, tokens: dict[str, str], message: str
) -> None:
    settings = _request().shared.model_copy(update={"model": model})
    with (
        patch.dict("os.environ", tokens, clear=True),
        pytest.raises(ValueError, match=message),
    ):
        compare.credentials(_request().model_copy(update={"shared": settings}))


@pytest.mark.parametrize("provider", ["openai", "anthropic", "hf-inference-providers"])
def provider_credentials_are_minimal(provider: str) -> None:
    from evals.python.evaluation import ModelPricing  # noqa: PLC0415

    settings = _request().shared.model_copy(
        update={
            "model": f"{provider}/test",
            "model_cost": ModelPricing(input=1, output=2, input_cache_write=0, input_cache_read=0),
        }
    )
    available = {"HF_TOKEN": "hf", "OPENAI_API_KEY": "openai", "ANTHROPIC_API_KEY": "anthropic"}
    with patch.dict("os.environ", available, clear=True):
        secrets = compare.credentials(_request().model_copy(update={"shared": settings}))
    expected = {"HF_TOKEN": "hf"}
    expected.update(_provider_key(provider))
    assert secrets == expected


def _provider_key(provider: str) -> dict[str, str]:
    return {
        "openai": {"OPENAI_API_KEY": "openai"},
        "anthropic": {"ANTHROPIC_API_KEY": "anthropic"},
        "hf-inference-providers": {},
    }[provider]


@pytest.mark.parametrize("saved", [("control",), ("control", "treatment")])
def saved_results_only_dispatch_missing_variants(tmp_path: Path, *, saved: tuple[str, ...]) -> None:
    request = _request()
    replacements = {
        role: getattr(request, role).model_copy(update={"result_ref": f"saved-{role}"})
        for role in saved
    }
    request = request.model_copy(update=replacements)
    api = MagicMock()
    api.run_job.return_value = SimpleNamespace(id="treatment-job")
    api.inspect_job.return_value = SimpleNamespace(status=SimpleNamespace(stage="COMPLETED"))
    _mocked_execute(tmp_path, api=api, candidate=request)
    state = json.loads((tmp_path / "jobs.json").read_text())
    assert (
        api.run_job.call_count,
        state["namespace"],
        state["runs"]["control"],
        api.sync_bucket.call_count,
    ) == (2 - len(saved), "example", "saved-control", 2)
    if len(saved) == 1:
        assert api.run_job.call_args.kwargs["name"] == "genius-treatment"


def _host(tmp_path: Path) -> compare.HostedComparison:
    return compare.HostedComparison(
        request=_request(),
        output=tmp_path,
        namespace="example",
        api=MagicMock(),
        timeout="4h",
        secrets={},
        jobs={"control": "first", "treatment": "second"},
        pending={"control", "treatment"},
    )


def polling_waits_for_running_jobs(tmp_path: Path) -> None:
    host = _host(tmp_path)
    with (
        patch.object(
            host.api,
            "inspect_job",
            side_effect=[
                SimpleNamespace(status=SimpleNamespace(stage="RUNNING")),
                SimpleNamespace(status=SimpleNamespace(stage="COMPLETED")),
                SimpleNamespace(status=SimpleNamespace(stage="COMPLETED")),
            ],
        ),
        patch("evals.python.integrations.hugging_face.compare.time.sleep") as sleep,
    ):
        host.wait(seconds=60)
    sleep.assert_called_once_with(10)
    assert not host.pending


def host_timeout_retains_ids_and_cancels_every_job(tmp_path: Path) -> None:
    host = _host(tmp_path)
    with (
        patch.object(
            host.api,
            "inspect_job",
            return_value=SimpleNamespace(status=SimpleNamespace(stage="RUNNING")),
        ),
        patch("evals.python.integrations.hugging_face.compare.time.monotonic", side_effect=[0, 1]),
        pytest.raises(TimeoutError, match="host wait limit"),
    ):
        host.wait(seconds=0)
    with patch.object(host.api, "cancel_job") as cancel:
        host.cancel()
    assert cancel.call_count == 2
    assert host.jobs == {"control": "first", "treatment": "second"}


def terminal_error_cancels_remaining_job(tmp_path: Path) -> None:
    api = MagicMock()
    api.run_job.side_effect = [SimpleNamespace(id="first"), SimpleNamespace(id="second")]
    api.inspect_job.return_value = SimpleNamespace(status=SimpleNamespace(stage="ERROR"))
    with pytest.raises(RuntimeError, match="job ended with ERROR"):
        _mocked_execute(tmp_path, api=api, candidate=_request())
    api.cancel_job.assert_called_once()


def cancellation_failure_preserves_original_error_and_saved_ids(tmp_path: Path) -> None:
    api = MagicMock()
    api.run_job.side_effect = [SimpleNamespace(id="first"), RuntimeError("dispatch failed")]
    api.cancel_job.side_effect = RuntimeError("network failed")
    with pytest.raises(RuntimeError, match="dispatch failed"):
        _mocked_execute(tmp_path, api=api, candidate=_request())
    assert json.loads((tmp_path / "jobs.json").read_text())["jobs"] == {"control": "first"}


def dispatch_state_cannot_be_overwritten(tmp_path: Path) -> None:
    (tmp_path / "jobs.json").write_text("existing")
    api = MagicMock()
    with pytest.raises(ValueError, match="already contains dispatch state"):
        _mocked_execute(tmp_path, api=api, candidate=_request())
    api.run_job.assert_not_called()
    assert (tmp_path / "jobs.json").read_text() == "existing"


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
def prepare_preserves_origin_refs_and_selects_agent(tmp_path: Path, *, provider: str) -> None:
    environment = {
        "EVAL_MODEL": f"{provider}/test",
        "CONTROL_REF": "base-sha",
        "TREATMENT_REF": "head-sha",
        "CONTROL_RESULT_REF": "prior-control",
        "COMPARISON_ID": "pr80-head",
        "GITHUB_REPOSITORY": "example/repo",
        "GITHUB_RUN_ID": "100",
        "PR_NUMBER": "80",
    }
    with patch.dict("os.environ", environment, clear=True):
        compare.prepare(tmp_path)
    request = ComparisonRequest.model_validate_json((tmp_path / "request.json").read_text())
    assert (request.comparison_id, request.origin) == (
        "pr80-head",
        {
            "GITHUB_REPOSITORY": "example/repo",
            "GITHUB_RUN_ID": "100",
            "PR_NUMBER": "80",
        },
    )
    assert (
        request.control.result_ref,
        request.control.variant.source_ref,
        request.treatment.variant.source_ref,
        request.shared.agent,
        request.shared.variant,
    ) == (
        "prior-control",
        "base-sha",
        "head-sha",
        {"anthropic": "claude", "openai": "codex"}[provider],
        None,
    )


def prepare_defaults_head_and_keeps_explicit_agent(tmp_path: Path) -> None:
    with patch.dict(
        "os.environ", {"EVAL_MODEL": "openai/test", "EVAL_AGENT": "claude"}, clear=True
    ):
        compare.prepare(tmp_path)
    request = ComparisonRequest.model_validate_json((tmp_path / "request.json").read_text())
    assert request.control.variant.source_ref == "HEAD"
    assert request.treatment.result_ref is None
    assert request.shared.agent == "claude"


@pytest.mark.parametrize(
    ("error", "verdict"), [(ValueError("invalid"), "incompatible"), (RuntimeError("job"), "failed")]
)
def execute_file_writes_failure_evidence(tmp_path: Path, *, error: Exception, verdict: str) -> None:
    path = tmp_path / "request.json"
    path.write_text(_request().model_dump_json())
    output = tmp_path / "output"
    with patch.object(compare, "execute", side_effect=error), pytest.raises(type(error)):
        compare.execute_file(path, output=output, namespace="example", timeout="2h")
    assert json.loads((output / "comparison.json").read_text()) == {
        "verdict": verdict,
        "error": str(error),
    }
    assert f"**{verdict}**" in (output / "summary.md").read_text()


def execute_file_passes_validated_request(tmp_path: Path) -> None:
    path = tmp_path / "request.json"
    path.write_text(_request().model_dump_json())
    with patch.object(compare, "execute") as execute:
        compare.execute_file(path, output=tmp_path / "out", namespace="example", timeout="2h")
    execute.assert_called_once_with(
        _request(), output=tmp_path / "out", namespace="example", timeout="2h"
    )


@pytest.mark.parametrize("action", ["prepare", "run", "cancel"])
def cli_routes_actions(tmp_path: Path, *, action: str) -> None:
    arguments = [
        "compare",
        action,
        str(tmp_path / "request.json"),
        "--output",
        str(tmp_path),
        "--namespace",
        "example",
        "--timeout",
        "2h",
    ]
    with (
        patch("sys.argv", arguments),
        patch.object(compare, "prepare") as prepare,
        patch.object(compare, "execute_file") as execute,
        patch.object(compare, "HfApi") as api,
    ):
        (tmp_path / "jobs.json").write_text(json.dumps({"jobs": {"control": "first"}}))
        compare.main()
    assert prepare.call_count == int(action == "prepare")
    assert execute.call_count == int(action == "run")
    assert api.return_value.cancel_job.call_count == int(action == "cancel")


@pytest.mark.parametrize("arguments", [[], ["request.json"]])
def cli_requires_request_and_namespace(tmp_path: Path, *, arguments: list[str]) -> None:
    with (
        patch("sys.argv", ["compare", "run", *arguments, "--output", str(tmp_path)]),
        patch.dict("os.environ", {}, clear=True),
        pytest.raises(SystemExit) as error,
    ):
        compare.main()
    assert error.value.code == 2


def saved_validation_uses_public_boundary(tmp_path: Path) -> None:
    settings = _request().shared
    with patch.object(comparison, "validate_run") as validate:
        compare.validate_saved(tmp_path, settings=settings)
    validate.assert_called_once_with(tmp_path, settings=settings)


def module_entrypoint_prepares_request(tmp_path: Path) -> None:
    import runpy  # noqa: PLC0415

    with (
        patch("sys.argv", ["compare", "prepare", "--output", str(tmp_path)]),
        patch.dict("os.environ", {"EVAL_MODEL": "openai/test"}, clear=True),
    ):
        runpy.run_path(str(compare.__file__), run_name="__main__")
    request = ComparisonRequest.model_validate_json((tmp_path / "request.json").read_text())
    assert request.shared.agent == "codex"
