"""Offline reference validation makes no provider or model requests."""

import asyncio
import json
import runpy
import sys
from unittest.mock import AsyncMock, call, patch

import pytest

from evals.python import datasets, verification
from evals.python.integrations.evalplus import benchmarks
from evals.python.paths import EVALS_ROOT
from evals.python.tests.humaneval import _record
from evals.python.tests.support import import_dataset as _import_dataset
from evals.python.tests.support import import_records as _import_records
from evals.python.verification import VerificationResult
from kernel import Verification


def info(capsys: pytest.CaptureFixture[str]) -> None:
    assert benchmarks.main(["info"]) == 0
    assert json.loads(capsys.readouterr().out)["count"] == 164


@pytest.mark.parametrize("status", ["passed", "failed", "harness_error"])
def validate_reports_real_status(*, status: str, capsys: pytest.CaptureFixture[str]) -> None:
    case = _import_records((_record(),))[0]
    dataset = _import_dataset((_record(),))
    with (
        patch.object(datasets, "load_dataset", return_value=dataset) as load,
        patch.object(
            benchmarks, "validate_case", new=AsyncMock(return_value={"status": status})
        ) as validate,
    ):
        assert benchmarks.main(["validate", "--limit", "1"]) == int(status != "passed")
    assert load.call_args_list == [call(selection="humanevalplus"), call(selection=dataset)]
    validate.assert_awaited_once_with(case=case, dataset=dataset)
    assert json.loads(capsys.readouterr().out)["results"] == [{"status": status}]


def invalid_limit() -> None:
    with pytest.raises(ValueError, match="positive"):
        benchmarks.main(["validate", "--limit", "0"])


def reference_validation_uses_public_operation_and_thaws_only_cli_output() -> None:
    case = _import_records((_record(),))[0]
    dataset = _import_dataset((_record(),))
    canonical = VerificationResult(
        verification=Verification.Passed(), metadata={"test": {"items": (True,)}}
    )
    with patch.object(
        verification, "validate_reference", new_callable=AsyncMock, return_value=canonical
    ) as execute:
        result = asyncio.run(benchmarks.validate_case(case, dataset=dataset))
    execute.assert_awaited_once_with(case_id=case.id, selection=dataset)
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
