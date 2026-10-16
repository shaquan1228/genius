"""Offline reference validation makes no provider or model requests."""

import asyncio
import json
import os
import platform
import runpy
import sys
from unittest.mock import AsyncMock, patch

import pytest

from evals.python import commands
from evals.python.integrations.evalplus import benchmarks
from evals.python.paths import EVALS_ROOT
from evals.python.tests.humaneval import _record
from evals.python.tests.support import import_records as _import_records


def info(capsys: pytest.CaptureFixture[str]) -> None:
    assert benchmarks.main(["info"]) == 0
    assert json.loads(capsys.readouterr().out)["count"] == 164


@pytest.mark.parametrize("status", ["passed", "failed", "harness_error"])
def validate_reports_real_status(*, status: str, capsys: pytest.CaptureFixture[str]) -> None:
    case = _import_records((_record(),))[0]
    with (
        patch("evals.python.catalog.load_cases", return_value=(case,)),
        patch.object(benchmarks, "validate_case", new=AsyncMock(return_value={"status": status})),
    ):
        assert benchmarks.main(["validate", "--limit", "1"]) == int(status != "passed")
    assert json.loads(capsys.readouterr().out)["results"] == [{"status": status}]


def invalid_limit() -> None:
    with pytest.raises(ValueError, match="positive"):
        benchmarks.main(["validate", "--limit", "0"])


def memory_workaround_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
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


def reference_validation_uses_public_operation_and_thaws_only_cli_output() -> None:
    case = _import_records((_record(),))[0]
    canonical = commands.VerificationResult(
        verification=commands.Verification(status="passed"), metadata={"test": {"items": (True,)}}
    )
    with patch.object(
        commands, "ValidateReference", new_callable=AsyncMock, return_value=canonical
    ) as execute:
        result = asyncio.run(benchmarks.validate_case(case))
    execute.assert_awaited_once_with(case_id=case.id, selection="humanevalplus")
    assert result == {
        "case_id": case.id,
        "status": "passed",
        "detail": "",
        "metadata": {"test": {"items": [True]}},
    }
    assert canonical.metadata == {"test": {"items": (True,)}}


def benchmark_entrypoint(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(sys, "argv", ["benchmarks", "info"]),
        pytest.raises(SystemExit) as exited,
    ):
        runpy.run_path(
            str(EVALS_ROOT / "python/integrations/evalplus/benchmarks.py"), run_name="__main__"
        )
    assert exited.value.code == 0
    assert json.loads(capsys.readouterr().out)["count"] == 164
