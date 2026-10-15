"""Offline reference validation makes no provider or model requests."""

import argparse
import asyncio
import json
import os
import platform
import runpy
import sys
from unittest.mock import AsyncMock, patch

import pytest

from evals.python import benchmarks
from evals.python.paths import EVALS_ROOT
from evals.python.tests.test_humaneval import record
from evals.python.transport import Verification, import_humaneval, load_cases


def options(**updates: object) -> argparse.Namespace:
    return argparse.Namespace(limit=1, trusted_macos_memory_workaround=False, **updates)


def test_info(capsys: pytest.CaptureFixture[str]) -> None:
    assert benchmarks.main(["info"]) == 0
    assert json.loads(capsys.readouterr().out)["count"] == 164


@pytest.mark.parametrize("status", ["passed", "failed", "harness_error"])
def test_validate_reports_real_status(*, status: str, capsys: pytest.CaptureFixture[str]) -> None:
    case = import_humaneval((record(),))[0]
    with (
        patch.object(benchmarks, "load_cases", return_value=(case,)),
        patch.object(benchmarks, "validate_case", new=AsyncMock(return_value={"status": status})),
    ):
        assert benchmarks.main(["validate", "--limit", "1"]) == int(status != "passed")
    assert json.loads(capsys.readouterr().out)["results"] == [{"status": status}]


def test_invalid_limit() -> None:
    with pytest.raises(ValueError, match="positive"):
        benchmarks.main(["validate", "--limit", "0"])


def test_memory_workaround_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EVALPLUS_MAX_MEMORY_BYTES", raising=False)
    benchmarks.configure_memory(options())
    assert "EVALPLUS_MAX_MEMORY_BYTES" not in os.environ
    args = argparse.Namespace(trusted_macos_memory_workaround=True)
    with (
        patch.object(platform, "system", return_value="Linux"),
        pytest.raises(ValueError, match="macOS"),
    ):
        benchmarks.configure_memory(args)
    with patch.object(platform, "system", return_value="Darwin"):
        benchmarks.configure_memory(args)
    assert os.environ["EVALPLUS_MAX_MEMORY_BYTES"] == "-1"


def test_reference_workspace_cleanup() -> None:
    case = import_humaneval((record(),))[0]
    with patch.object(
        benchmarks,
        "verify",
        new=AsyncMock(return_value=(Verification(status="passed"), {"test": True})),
    ):
        result = asyncio.run(benchmarks.validate_case(case))
    assert result == {
        "case_id": case.id,
        "status": "passed",
        "detail": "",
        "metadata": {"test": True},
    }
    with pytest.raises(ValueError, match="executable"):
        asyncio.run(benchmarks.validate_case(load_cases()[2]))


def test_benchmark_entrypoint(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(sys, "argv", ["benchmarks", "info"]),
        pytest.raises(SystemExit) as exited,
    ):
        runpy.run_path(str(EVALS_ROOT / "python/benchmarks.py"), run_name="__main__")
    assert exited.value.code == 0
    assert json.loads(capsys.readouterr().out)["count"] == 164
