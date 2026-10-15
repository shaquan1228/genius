"""Offline reference validation makes no provider or model requests."""

import asyncio
import json
import os
import platform
import runpy
import sys
from unittest.mock import AsyncMock, patch

import pytest

from evals.python.contracts import Verification
from evals.python.integrations.datasets.catalog import load_cases
from evals.python.integrations.evalplus import benchmarks
from evals.python.integrations.inspect.verification import Verifier
from evals.python.paths import EVALS_ROOT
from evals.python.tests.support import import_records, imported_reference, imported_verifier
from evals.python.tests.test_humaneval import record


def test_info(capsys: pytest.CaptureFixture[str]) -> None:
    assert benchmarks.main(["info"]) == 0
    assert json.loads(capsys.readouterr().out)["count"] == 164


@pytest.mark.parametrize("status", ["passed", "failed", "harness_error"])
def test_validate_reports_real_status(*, status: str, capsys: pytest.CaptureFixture[str]) -> None:
    case = import_records((record(),))[0]
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
    benchmarks.configure_memory(benchmarks.Options())
    assert "EVALPLUS_MAX_MEMORY_BYTES" not in os.environ
    args = benchmarks.Options(trusted_macos_memory_workaround=True)
    with (
        patch.object(platform, "system", return_value="Linux"),
        pytest.raises(ValueError, match="macOS"),
    ):
        benchmarks.configure_memory(args)
    with patch.object(platform, "system", return_value="Darwin"):
        benchmarks.configure_memory(args)
    assert os.environ["EVALPLUS_MAX_MEMORY_BYTES"] == "-1"


def test_reference_workspace_cleanup() -> None:
    case = import_records((record(),))[0]
    with (
        patch.object(
            Verifier,
            "verify",
            new=AsyncMock(return_value=(Verification(status="passed"), {"test": True})),
        ),
        patch.object(benchmarks, "verifier", return_value=imported_verifier(record())),
        patch.object(benchmarks, "reference", return_value=imported_reference(record())),
    ):
        result = asyncio.run(benchmarks.validate_case(case))
    assert result == {
        "case_id": case.id,
        "status": "passed",
        "detail": "",
        "metadata": {"test": True},
    }
    with (
        patch.object(benchmarks, "verifier", return_value=None),
        pytest.raises(ValueError, match="executable"),
    ):
        asyncio.run(benchmarks.validate_case(load_cases()[2]))


def test_benchmark_entrypoint(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(sys, "argv", ["benchmarks", "info"]),
        pytest.raises(SystemExit) as exited,
    ):
        runpy.run_path(
            str(EVALS_ROOT / "python/integrations/evalplus/benchmarks.py"), run_name="__main__"
        )
    assert exited.value.code == 0
    assert json.loads(capsys.readouterr().out)["count"] == 164
