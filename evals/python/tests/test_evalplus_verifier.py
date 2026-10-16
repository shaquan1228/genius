"""The adapter delegates correctness to EvalPlus and returns explicit evidence."""

import importlib
import io
import json
import os
import runpy
import subprocess
import sys
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from typing import cast
from unittest.mock import Mock, patch

import pytest

from evals.python.integrations.evalplus import evalplus_verifier as driver
from evals.python.integrations.evalplus.benchmarks import benchmark_info
from evals.python.paths import EVALS_ROOT
from evals.python.tests.test_humaneval import record


def payload() -> driver.Payload:
    return {"manifest": cast(driver.Manifest, benchmark_info().model_dump()), "record": record()}


@pytest.mark.parametrize("memory_limit", [None, "1"])
@pytest.mark.parametrize(
    ("source", "status"),
    [
        ("def identity(x):\n    return x\n", "passed"),
        ("def identity(x):\n    return 0\n", "failed"),
        # Pinned EvalPlus treats per-input timeouts as failed checks.
        ("def identity(x):\n    while True:\n        pass\n", "failed"),
        ("not valid python!", "invalid_submission"),
        ("import os\nos._exit(0)\ndef identity(x):\n    return x\n", "timed_out"),
    ],
)
def test_official_checker(
    *, tmp_path: Path, source: str, status: str, memory_limit: str | None
) -> None:
    (tmp_path / "solution.py").write_text(source)
    environment = {
        **os.environ,
        "GENIUS_VERIFIER_MARKER": "private",
    }
    environment.pop("EVALPLUS_MAX_MEMORY_BYTES", None)
    if memory_limit is not None:
        environment["EVALPLUS_MAX_MEMORY_BYTES"] = memory_limit
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(EVALS_ROOT / "python/integrations/evalplus/evalplus_verifier.py"),
            "evalplus",
        ],
        input=json.dumps(payload()),
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=environment,
        timeout=30,
        check=True,
    )
    evidence = json.loads(result.stdout.splitlines()[-1])
    assert evidence["status"] == status, evidence
    assert evidence["marker"] == "private"
    assert evidence["metadata"]["dataset"]["sha256"] == benchmark_info().sha256


def test_installed_revision() -> None:
    distribution = Mock()
    distribution.read_text.return_value = '{"vcs_info":{"commit_id":"abc"}}'
    with patch("importlib.metadata.distribution", return_value=distribution):
        assert driver.installed("abc")
        assert not driver.installed("other")
        distribution.read_text.return_value = None
        assert not driver.installed("abc")
    with patch("importlib.metadata.distribution", side_effect=PackageNotFoundError):
        assert not driver.installed("abc")


def test_dependency_bootstrap_uses_private_target() -> None:
    manifest = payload()["manifest"]
    with (
        patch.object(driver, "installed", return_value=False),
        patch.object(subprocess, "run") as install,
        patch.object(sys, "path", []),
    ):
        driver.dependencies(
            request=driver.Dependencies(manifest=manifest, destination="private-target")
        )
        assert sys.path == ["private-target"]
    command = install.call_args.args[0]
    assert command[-3:] == [
        "git+https://github.com/evalplus/evalplus.git@" + benchmark_info().evaluator_commit,
        "numpy==2.5.4",
        "psutil==7.2.2",
    ]
    assert "--no-deps" in command
    with (
        patch.object(driver, "installed", return_value=True),
        patch.object(subprocess, "run") as install,
    ):
        driver.dependencies(request=driver.Dependencies(manifest=manifest, destination="unused"))
    install.assert_not_called()


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ({"base": "pass", "plus": "pass"}, "passed"),
        ({"base": "pass", "plus": "fail"}, "failed"),
        ({"base": "timeout", "plus": "fail"}, "timed_out"),
    ],
)
def test_phase_statuses(
    *, statuses: dict[driver.PhaseName, driver.PhaseStatus], expected: str
) -> None:
    assert driver.outcome(statuses) == expected


def test_unknown_upstream_status_rejected() -> None:
    reference, evaluator = (Mock(), Mock())
    reference.trusted_exec.return_value = ([1], [0.1])
    evaluator.untrusted_check.return_value = ("unknown", [])
    with (
        patch.object(importlib, "import_module", side_effect=[reference, evaluator]),
        pytest.raises(RuntimeError, match="Unexpected EvalPlus"),
    ):
        driver.phase(
            request=driver.Phase(
                record=cast(driver.Problem, json.loads(record())), name="base", code="candidate"
            )
        )
    reference.trusted_exec.assert_called_once()
    assert evaluator.untrusted_check.call_args.kwargs["fast_check"] is True


def test_driver_reports_json_errors(
    *, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("GENIUS_VERIFIER_MARKER", "marker")
    with (
        patch.object(driver, "execute", side_effect=ValueError("bad JSON")),
        patch.object(sys, "argv", ["verifier", "evalplus"]),
    ):
        driver.main()
    evidence = json.loads(capsys.readouterr().out)
    assert evidence == {
        "marker": "marker",
        "status": "harness_error",
        "detail": "bad JSON",
        "metadata": {},
    }


def test_encoding_error_invalid_submission() -> None:
    data = payload()
    with patch.object(Path, "read_text", side_effect=UnicodeError("encoding")):
        evidence = driver.evaluate(data)
    assert (evidence.status, evidence.detail) == ("invalid_submission", "encoding")


def test_phase_exception_retains_provenance() -> None:
    metadata: dict[str, object] = {"dataset": {"sha256": "digest"}}
    with patch.object(driver, "phase", side_effect=["pass", RuntimeError("reference failed")]):
        evidence = driver.evaluate_phases(
            request=driver.Evaluation(
                record=cast(driver.Problem, json.loads(record())),
                code="candidate",
                metadata=metadata,
            )
        )
    assert evidence.status == "harness_error"
    assert evidence.detail == "EvalPlus plus phase: reference failed"
    assert evidence.metadata == {"dataset": {"sha256": "digest"}, "phases": {"base": "pass"}}


@pytest.mark.parametrize("dependency", ["numpy", "psutil"])
def test_missing_runtime_dependency(dependency: str) -> None:
    manifest = payload()["manifest"]
    versions = {"numpy": manifest["numpy_version"], "psutil": manifest["psutil_version"]}

    def version(name: str) -> str:
        if name == dependency:
            raise PackageNotFoundError(name)
        return str(versions[name])

    with (
        patch.object(driver, "installed", return_value=True),
        patch("importlib.metadata.version", side_effect=version),
    ):
        assert not driver.installed_runtime(manifest)


def test_evaluate_preserves_upstream_evidence(
    *, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("EVALPLUS_MAX_MEMORY_BYTES", raising=False)
    (tmp_path / "solution.py").write_text("def identity(x):\n    return x\n")
    evidence = driver.evaluate(payload())
    assert evidence.status == "passed", evidence.detail
    assert evidence.metadata["dataset"] == benchmark_info().model_dump()
    assert evidence.metadata["task_id"] == "HumanEval/0"
    assert (
        json.loads(evidence.detail)
        == evidence.metadata["phases"]
        == {"base": "pass", "plus": "pass"}
    )
    assert_runtime_evidence(evidence.metadata)


def test_syntax_error_retains_provenance(
    *, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "solution.py").write_text("invalid python!")
    evidence = driver.evaluate(payload())
    assert evidence.status == "invalid_submission"
    assert "invalid syntax" in evidence.detail
    assert evidence.metadata == {"dataset": benchmark_info().model_dump(), "task_id": "HumanEval/0"}


def assert_runtime_evidence(metadata: dict[str, object]) -> None:
    assert metadata["test_counts"] == {"base": 1, "plus": 1}
    assert metadata["python_version"] == sys.version
    assert metadata["runtime"] == {
        name: importlib.metadata.version(name) for name in ("evalplus", "numpy", "psutil")
    }


@pytest.mark.parametrize("missing", [True, False])
def test_invalid_phase_inputs_are_harness_errors(
    *, missing: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("EVALPLUS_MAX_MEMORY_BYTES", raising=False)
    data = cast(driver.Problem, json.loads(record()))
    data["plus_input"] = cast(list[object], None)
    if missing:
        cast(dict[str, object], data).pop("plus_input", None)
    evidence = driver.evaluate_phases(
        request=driver.Evaluation(record=data, code="def identity(x):\n    return x\n", metadata={})
    )
    assert evidence.status == "harness_error"
    assert evidence.detail.startswith("EvalPlus plus phase:")
    assert evidence.metadata["phases"] == {"base": "pass"}


def test_execute_cleans_private_dependencies(
    *, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("EVALPLUS_MAX_MEMORY_BYTES", raising=False)
    (tmp_path / "solution.py").write_text("def identity(x):\n    return x\n")
    with (
        patch.object(sys, "stdin", io.StringIO(json.dumps(payload()))),
        patch.object(driver, "dependencies") as dependencies,
    ):
        evidence = driver.execute()
    assert evidence.status == "passed", evidence.detail
    assert evidence.metadata["phases"] == {"base": "pass", "plus": "pass"}
    destination = Path(dependencies.call_args.kwargs["request"].destination)
    assert (destination.parent, destination.exists(), tuple(tmp_path.iterdir())) == (
        tmp_path,
        False,
        (tmp_path / "solution.py",),
    )


@pytest.mark.parametrize(
    ("arguments", "expected_error"),
    [
        (["evalplus"], "Expecting value"),
        ([], "Expected verifier mode: evalplus"),
        (["ocaml"], "Expected verifier mode: evalplus"),
    ],
)
def test_driver_entrypoint(
    *,
    arguments: list[str],
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("GENIUS_VERIFIER_MARKER", "entrypoint")
    with (
        patch.object(sys, "stdin", io.StringIO("invalid JSON")),
        patch.object(sys, "argv", ["verifier", *arguments]),
    ):
        runpy.run_path(
            str(EVALS_ROOT / "python/integrations/evalplus/evalplus_verifier.py"),
            run_name="__main__",
        )
    evidence = json.loads(capsys.readouterr().out)
    assert evidence["status"] == "harness_error"
    assert evidence["marker"] == "entrypoint"
    assert evidence["metadata"] == {}
    assert expected_error in evidence["detail"]


def test_expanded_inputs_can_fail_after_base_passes(
    *, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("EVALPLUS_MAX_MEMORY_BYTES", raising=False)
    (tmp_path / "solution.py").write_text(
        f"def identity(x):\n    return x if x > {2**200} else 0\n"
    )
    evidence = driver.evaluate(payload())
    assert (evidence.status, evidence.metadata["phases"]) == (
        "failed",
        {"base": "pass", "plus": "fail"},
    )
