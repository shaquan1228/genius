"""A Python-owned dataset exercises the real kernel and generic verifier."""

import json
import runpy
from typing import cast
from unittest.mock import AsyncMock, patch

import pytest
from kernel import Reference, Verification

from evals.python import datasets, verification
from evals.python.datasets import Case
from evals.python.datasets import smoke as declarations
from evals.python.integrations.smoke import __main__ as cli
from evals.python.tests.declarations import _copy_case, _files, _reference_files
from evals.python.verification import VerificationResult


def python_smoke_compiles_to_public_cases() -> None:
    definitions = declarations.cases()
    dataset = datasets.compile_dataset(cases=definitions)
    cases = datasets.list_cases(selection=dataset)
    assert tuple(case.case_id for case in cases) == tuple(record.task.id for record in definitions)
    assert all(isinstance(case, Case) for case in cases)


def default_smoke_uses_python_owned_cases() -> None:
    definitions = declarations.cases()
    dataset = datasets.load_dataset()
    assert dataset is datasets.compile_dataset(cases=definitions)
    assert tuple(dataset.cases) == (
        "clear-task",
        "known-preflight",
        "small-decision",
        "decision-review",
    )
    assert tuple(_files(dataset.cases["clear-task"].files)) == ("receipt.py", "test_receipt.py")


@pytest.mark.parametrize(("initial", "requested"), [(15, 15), (0, 30), (-1, 30), (15, 0), (15, -1)])
def timeout_variants_require_a_real_positive_change(initial: int, *, requested: int) -> None:
    with pytest.raises(ValueError, match="distinct positive"):
        declarations.timeout(initial=initial, requested=requested)


def python_smoke_keeps_checks_and_references_private() -> None:
    definitions = declarations.cases()
    dataset = datasets.compile_dataset(cases=definitions)
    cases = datasets.list_cases(selection=dataset)
    code = definitions[0].task
    checks = code.checks()
    assert checks is not None
    assert checks.stdin not in json.dumps(_files(cases[0].files))
    assert _reference_files(code.reference)["receipt.py"] not in _files(cases[0].files).values()
    assert "verifier.py" not in _files(cases[0].files)


def _run_cli() -> int:
    with pytest.raises(SystemExit) as exited:
        runpy.run_path(cli.__file__, run_name="__main__")
    return cast(int, exited.value.code)


def offline_cli_validates_real_references(*, capsys: pytest.CaptureFixture[str]) -> None:
    assert _run_cli() == 0
    output = capsys.readouterr().out
    rows = [json.loads(line) for line in output.splitlines()]
    assert rows == [
        {"id": case_id, "verification": status, "scores": {"correctness": True, "scope": True}}
        for case_id, status in (
            ("clear-task", "passed"),
            ("known-preflight", "passed"),
            ("small-decision", "unchecked"),
            ("decision-review", "unchecked"),
        )
    ]


def offline_cli_exits_nonzero_on_grading_failure(*, capsys: pytest.CaptureFixture[str]) -> None:
    case = _copy_case(
        declarations.cases()[2],
        reference=Reference(edits=[], completion={}),
    )
    dataset = datasets.compile_dataset(cases=(case,))
    with patch.object(datasets, "load_dataset", return_value=dataset):
        assert _run_cli() == 1
    assert all(
        not json.loads(line)["scores"]["correctness"]
        for line in capsys.readouterr().out.splitlines()
    )


def offline_cli_reports_harness_failure_without_success(
    *, capsys: pytest.CaptureFixture[str]
) -> None:
    result = VerificationResult(verification=Verification.HarnessError(detail="private diagnostic"))
    with patch.object(verification, "validate_reference", new=AsyncMock(return_value=result)):
        assert _run_cli() == 1
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert all(row["verification"] == "harness_error" and row["scores"] == {} for row in rows)
    assert "private diagnostic" not in json.dumps(rows)
