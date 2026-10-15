"""Trusted OCaml driver reports execution evidence without exposing the generic marker."""

import json
import runpy
import subprocess
from unittest.mock import patch

import pytest

from evals.python.ocaml_verifier import classify, execute, main


@pytest.mark.parametrize(
    ("code", "stdout", "status"),
    [
        (65, "", "invalid_submission"),
        (127, "", "harness_error"),
        (2, "", "failed"),
        (0, "", "failed"),
        (0, "done\n", "passed"),
    ],
)
def test_classification(*, code: int, stdout: str, status: str) -> None:
    result = subprocess.CompletedProcess([], code, stdout=stdout)
    assert classify(result, marker="done") == status


def test_missing_compiler_is_harness_error() -> None:
    with patch("evals.python.ocaml_verifier.shutil.which", return_value=None):
        assert execute() == ("harness_error", "OCaml compiler is unavailable")


def test_trusted_driver_uses_separate_inner_marker() -> None:
    result = subprocess.CompletedProcess([], 0, stdout="inner\n", stderr="")
    with (
        patch("evals.python.ocaml_verifier.shutil.which", return_value="compiler"),
        patch("evals.python.ocaml_verifier.secrets.token_hex", return_value="inner"),
        patch("evals.python.ocaml_verifier.sys.stdin.read", return_value="assert true"),
        patch("evals.python.ocaml_verifier.subprocess.run", return_value=result) as process,
    ):
        assert execute() == ("passed", "inner\n")
    assert "inner" in process.call_args.kwargs["input"]


@pytest.mark.parametrize("failure", [None, RuntimeError("driver failed")])
def test_main_emits_generic_envelope(
    *, failure: Exception | None, capsys: pytest.CaptureFixture[str]
) -> None:
    with (
        patch(
            "evals.python.ocaml_verifier.execute",
            return_value=("passed", "done"),
            side_effect=failure,
        ),
        patch.dict("os.environ", {"GENIUS_VERIFIER_MARKER": "outer"}),
    ):
        main()
    evidence = json.loads(capsys.readouterr().out)
    assert evidence == {
        "marker": "outer",
        "status": "harness_error" if failure else "passed",
        "detail": str(failure) if failure else "done",
    }


def test_driver_entrypoint_emits_evidence(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch("shutil.which", return_value=None),
        patch.dict("os.environ", {"GENIUS_VERIFIER_MARKER": "entrypoint"}),
    ):
        runpy.run_module("evals.python.ocaml_verifier", run_name="__main__")
    assert json.loads(capsys.readouterr().out)["status"] == "harness_error"
