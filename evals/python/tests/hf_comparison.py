"""Keep the paid boundary mocked while exercising the complete launch sequence."""

import json
import runpy
import subprocess
from collections.abc import Mapping
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from huggingface_hub import HfApi

from evals.python import comparison, evaluation
from evals.python.comparison import (
    ComparisonReport,
    ComparisonRequest,
    Measurement,
    RunSummary,
    VariantRequest,
)
from evals.python.evaluation import EvaluationSettings, ModelPricing, VariantSettings
from evals.python.integrations.hugging_face import compare, dispatch, source


def _request(names: tuple[str, ...] = ("control", "treatment")) -> ComparisonRequest:
    return ComparisonRequest(
        comparison_id="request",
        shared=EvaluationSettings(
            model="openai/test",
            model_cost=ModelPricing(input=0, output=0, input_cache_write=0, input_cache_read=0),
        ),
        baseline=names[0],
        variants=tuple(
            VariantRequest(variant=VariantSettings(name=name, instructions=(), preamble=""))
            for name in names
        ),
    )


def _prepared(settings: EvaluationSettings) -> EvaluationSettings:
    return settings.model_copy(
        update={
            "run_id": settings.run_id or f"{cast(VariantSettings, settings.variant).name}-run",
            "version": "pinned",
            "epochs": 1,
        }
    )


def _report(
    runs: Mapping[str, Path], *, baseline: str, measurement: Measurement
) -> ComparisonReport:
    return comparison.compare_summaries(
        {name: RunSummary(metrics={}, created_at="test") for name in runs},
        baseline=baseline,
        measurement=measurement,
    )


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    client = MagicMock(spec=HfApi)
    client.upload_folder.return_value = SimpleNamespace(oid="immutable-revision")
    client.run_job.side_effect = [
        SimpleNamespace(id="control-job"),
        SimpleNamespace(id="treatment-job"),
    ]
    client.wait_for_job.return_value = SimpleNamespace(status=SimpleNamespace(stage="COMPLETED"))
    monkeypatch.setattr(dispatch, "HfApi", lambda: client)
    monkeypatch.setattr(dispatch, "committed_harness", lambda: None)
    monkeypatch.setattr(source, "trusted_snapshot", lambda *args, **kwargs: "trusted")
    monkeypatch.setattr(source, "instructions", lambda variant, **kwargs: variant)
    monkeypatch.setattr(evaluation, "prepare_run", _prepared)
    monkeypatch.setattr(evaluation, "validate_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(comparison, "compare_runs", _report)
    monkeypatch.setattr(comparison, "render_report", lambda report: "summary")
    monkeypatch.setenv("HF_TOKEN", "private-token")
    monkeypatch.setenv("OPENAI_API_KEY", "private-key")
    return client


def runs_independent_jobs_with_pinned_inputs(api: MagicMock, *, tmp_path: Path) -> None:
    compare.execute(_request(), output=tmp_path, namespace="owner")
    calls = [call[0] for call in api.mock_calls]
    assert calls.index("wait_for_job") > max(i for i, name in enumerate(calls) if name == "run_job")
    _assert_volumes(api)
    assert "private-token" not in (tmp_path / "jobs.json").read_text()
    assert (tmp_path / "summary.md").read_text() == "summary"


def _assert_volumes(api: MagicMock) -> None:
    for call in api.run_job.call_args_list:
        assert call.kwargs["command"] == ["bash", "/source/evals/scripts/huggingface-bootstrap.sh"]
        assert call.kwargs["volumes"][0].revision == "immutable-revision"
        assert call.kwargs["volumes"][1].path.startswith("runs/")
        assert json.loads(call.kwargs["env"]["EVAL_VARIANT"])["source_dir"].startswith(
            "/source/.variants/"
        )


@pytest.mark.parametrize("roles", [("control",), ("control", "treatment")])
def saved_runs_skip_only_the_requested_jobs(
    api: MagicMock, *, tmp_path: Path, roles: tuple[str, ...]
) -> None:
    request = _request()
    variants = tuple(
        selected.model_copy(update={"result_ref": f"prior-{selected.variant.name}"})
        if selected.variant.name in roles
        else selected
        for selected in request.variants
    )
    compare.execute(
        request.model_copy(update={"variants": variants}), output=tmp_path, namespace="owner"
    )
    assert api.run_job.call_count == 2 - len(roles)


def incompatible_control_prevents_paid_dispatch(api: MagicMock, *, tmp_path: Path) -> None:
    request = _request().model_copy(
        update={
            "variants": (
                _request().variants[0].model_copy(update={"result_ref": "prior"}),
                _request().variants[1],
            )
        }
    )
    with (
        patch.object(evaluation, "validate_run", side_effect=ValueError("wrong control")),
        pytest.raises(ValueError, match="wrong control"),
    ):
        compare.execute(request, output=tmp_path, namespace="owner")
    api.run_job.assert_not_called()


@pytest.mark.parametrize("error", [RuntimeError("submission failed"), KeyboardInterrupt()])
def submission_failure_cancels_saved_job_ids(
    api: MagicMock, *, tmp_path: Path, error: BaseException
) -> None:
    api.run_job.side_effect = [SimpleNamespace(id="first-job"), error]
    with pytest.raises(type(error)):
        compare.execute(_request(), output=tmp_path, namespace="owner")
    api.cancel_job.assert_called_once_with(job_id="first-job", namespace="owner")
    assert json.loads((tmp_path / "jobs.json").read_text())["jobs"] == {"control": "first-job"}


def failed_remote_job_cancels_the_remaining_work(api: MagicMock, *, tmp_path: Path) -> None:
    api.wait_for_job.return_value = SimpleNamespace(status=SimpleNamespace(stage="ERROR"))
    with pytest.raises(RuntimeError, match="did not complete"):
        compare.execute(_request(), output=tmp_path, namespace="owner")
    assert api.cancel_job.call_count == 2


def cancellation_failure_preserves_the_original_error(api: MagicMock, *, tmp_path: Path) -> None:
    api.wait_for_job.side_effect = TimeoutError("deadline")
    api.cancel_job.side_effect = RuntimeError("network")
    with pytest.raises(TimeoutError, match="deadline"):
        compare.execute(_request(), output=tmp_path, namespace="owner")
    assert (tmp_path / "jobs.json").exists()


def existing_dispatch_state_is_preserved(api: MagicMock, *, tmp_path: Path) -> None:
    (tmp_path / "jobs.json").write_text("existing")
    with pytest.raises(ValueError, match="already contains"):
        compare.execute(_request(), output=tmp_path, namespace="owner")
    assert (tmp_path / "jobs.json").read_text() == "existing"


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def request_uses_existing_environment_configuration(provider: str) -> None:
    with patch.dict(
        "os.environ",
        {"EVAL_MODEL": f"{provider}/test", "CONTROL_REF": "base", "TREATMENT_REF": "head"},
        clear=True,
    ):
        request = compare.request_from_environment()
    assert tuple(v.variant.source_ref for v in request.variants) == (
        "base",
        "head",
    )


def explicit_request_json_is_preserved() -> None:
    with patch.dict("os.environ", {"COMPARISON_REQUEST": _request().model_dump_json()}, clear=True):
        assert compare.request_from_environment() == _request()


def _repository(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    for name in ("README.md", "docs/identity.md", "skills/reasoning/SKILL.md", "evals/code.py"):
        file = path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("committed data")
    source.git("add", ".", repository=path)
    source.git(
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-qm",
        "snapshot",
        repository=path,
    )


def instruction_export_uses_committed_bytes(tmp_path: Path) -> None:
    repo, output = tmp_path / "repo", tmp_path / "snapshot"
    _repository(repo)
    (repo / "skills/reasoning/SKILL.md").write_text("uncommitted")
    variant = source.instructions(
        VariantSettings(name="test", instructions=("skills",)), destination=output, repository=repo
    )
    assert (output / "skills/reasoning/SKILL.md").read_text() == "committed data"
    assert variant.source_ref == source.resolve("HEAD", repository=repo)


def unsafe_instruction_entries_are_rejected(tmp_path: Path) -> None:
    for entry in (b"120000 blob object\tlink", b"100644 blob object\t../escape"):
        with pytest.raises(ValueError, match=r"regular instruction|escapes"):
            source.export_blob(entry, destination=tmp_path, repository=tmp_path)


def trusted_snapshot_preserves_its_revision(tmp_path: Path) -> None:
    repo, output = tmp_path / "repo", tmp_path / "snapshot"
    _repository(repo)
    revision = source.trusted_snapshot(output, repository=repo)
    assert revision == source.resolve("HEAD", repository=repo)
    assert (output / "evals/code.py").read_text() == "committed data"


@pytest.mark.parametrize("ref", ["--help", "missing"])
def bad_instruction_refs_fail_closed(tmp_path: Path, *, ref: str) -> None:
    _repository(tmp_path / "repo")
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        source.resolve(ref, repository=tmp_path / "repo")


@pytest.mark.parametrize("failed_role", ["control", "treatment"])
def either_failure_cancels_without_waiting_for_its_peer(
    api: MagicMock, *, tmp_path: Path, failed_role: str
) -> None:
    cancelled = Event()
    api.cancel_job.side_effect = lambda **kwargs: cancelled.set()

    def waiting(job_id: str, **kwargs: object) -> SimpleNamespace:
        if job_id == f"{failed_role}-job":
            return SimpleNamespace(status=SimpleNamespace(stage="ERROR"))
        assert cancelled.wait(timeout=5), "peer cancellation was blocked behind its wait"
        return SimpleNamespace(status=SimpleNamespace(stage="CANCELLED"))

    api.wait_for_job.side_effect = waiting
    with pytest.raises(RuntimeError, match="did not complete"):
        compare.execute(_request(), output=tmp_path, namespace="owner")
    assert cancelled.is_set()


@pytest.mark.parametrize("provider", ["unsupported", "openai"])
def invalid_credentials_fail_before_dispatch(provider: str) -> None:
    with (
        patch.dict("os.environ", {"HF_TOKEN": "", "OPENAI_API_KEY": ""}, clear=True),
        pytest.raises(ValueError, match=r"model|credentials"),
    ):
        dispatch.credentials(EvaluationSettings(model=f"{provider}/test"))


@pytest.mark.parametrize("changed", [b"", b" M evals/python/evaluation.py"])
def dispatch_requires_a_committed_harness(changed: bytes) -> None:
    with patch.object(source, "git", return_value=changed):
        if changed:
            with pytest.raises(ValueError, match="Commit the trusted"):
                dispatch.committed_harness()
        else:
            dispatch.committed_harness()


@pytest.mark.parametrize("from_file", [False, True])
def cli_uses_the_same_request_and_execution_path(
    api: MagicMock, *, tmp_path: Path, from_file: bool
) -> None:
    request = tmp_path / "input.json"
    request.write_text(_request().model_dump_json())
    arguments = [str(compare.__file__), "--output", str(tmp_path), "--namespace", "owner"]
    arguments.extend([str(request)] if from_file else [])
    with (
        patch("sys.argv", arguments),
        patch("huggingface_hub.HfApi", return_value=api),
        patch.object(source, "git", return_value=b""),
        patch.dict("os.environ", {"COMPARISON_REQUEST": request.read_text()}),
    ):
        runpy.run_path(str(compare.__file__), run_name="__main__")
    assert (tmp_path / "comparison.json").exists()


def cli_requires_namespace() -> None:
    with (
        patch("sys.argv", [str(compare.__file__), "--output", "unused"]),
        patch.dict("os.environ", {}, clear=True),
        pytest.raises(SystemExit, match="2"),
    ):
        compare.main()


@pytest.mark.parametrize(
    "variant",
    [
        VariantSettings(name="local", source_dir="."),
        VariantSettings(name="missing", instructions=("missing",)),
    ],
)
def hosted_sources_require_committed_instruction_paths(
    tmp_path: Path, *, variant: VariantSettings
) -> None:
    _repository(tmp_path / "repo")
    with pytest.raises(ValueError, match=r"source_ref|not found"):
        source.instructions(variant, destination=tmp_path / "output", repository=tmp_path / "repo")


@pytest.mark.parametrize(
    ("reuse", "expected_jobs"),
    [(False, {"plain", "concise", "detailed"}), (True, {"plain", "detailed"})],
)
def three_variants_share_one_execution_path(
    api: MagicMock, *, tmp_path: Path, reuse: bool, expected_jobs: set[str]
) -> None:
    request = _request(("plain", "concise", "detailed"))
    selections = list(request.variants)
    if reuse:
        selections[1] = selections[1].model_copy(update={"result_ref": "saved"})
    request = request.model_copy(update={"variants": tuple(selections), "baseline": "concise"})
    api.run_job.side_effect = [
        SimpleNamespace(id="job-0"),
        SimpleNamespace(id="job-1"),
        SimpleNamespace(id="job-2"),
    ]
    compare.execute(request, output=tmp_path, namespace="owner")
    state = json.loads((tmp_path / "jobs.json").read_text())
    assert (set(state["runs"]), set(state["jobs"]), api.run_job.call_count) == (
        {"plain", "concise", "detailed"},
        expected_jobs,
        len(expected_jobs),
    )
    persisted = ComparisonRequest.model_validate_json((tmp_path / "request.json").read_text())
    assert (persisted.baseline, persisted.variants) == ("concise", request.variants)
    assert json.loads((tmp_path / "comparison.json").read_text())["baseline"] == "concise"
    _assert_volumes(api)


def third_submission_failure_cancels_every_started_variant(
    api: MagicMock, *, tmp_path: Path
) -> None:
    api.run_job.side_effect = [
        SimpleNamespace(id="first"),
        SimpleNamespace(id="second"),
        RuntimeError("third"),
    ]
    with pytest.raises(RuntimeError, match="third"):
        compare.execute(
            _request(("plain", "concise", "detailed")), output=tmp_path, namespace="owner"
        )
    assert {call.kwargs["job_id"] for call in api.cancel_job.call_args_list} == {"first", "second"}
