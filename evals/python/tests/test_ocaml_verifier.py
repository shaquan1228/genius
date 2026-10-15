"""Trusted OCaml driver reports execution evidence without exposing the generic marker."""

import json
import runpy
import subprocess
import sys
from unittest.mock import patch

import pytest

from evals.python.paths import EVALS_ROOT
from evals.python.verifier import Compilation, Invocation, Result, classify, execute, main


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
    assert classify(compilation=Compilation(result=result, marker="done")) == status


def test_missing_compiler_is_harness_error() -> None:
    with patch("evals.python.verifier.shutil.which", return_value=None):
        assert execute(invocation=Invocation(mode="ocaml")) == Result(
            status="harness_error", detail="OCaml compiler is unavailable"
        )


def test_trusted_driver_uses_separate_inner_marker() -> None:
    result = subprocess.CompletedProcess([], 0, stdout="inner\n", stderr="")
    with (
        patch("evals.python.verifier.shutil.which", return_value="compiler"),
        patch("evals.python.verifier.secrets.token_hex", return_value="inner"),
        patch("evals.python.verifier.sys.stdin.read", return_value="assert true"),
        patch("evals.python.verifier.subprocess.run", return_value=result) as process,
    ):
        assert execute(invocation=Invocation(mode="ocaml")) == Result(
            status="passed", detail="inner\n"
        )
    assert "inner" in process.call_args.kwargs["input"]


@pytest.mark.parametrize("failure", [None, RuntimeError("driver failed")])
def test_main_emits_generic_envelope(
    *, failure: Exception | None, capsys: pytest.CaptureFixture[str]
) -> None:
    with (
        patch(
            "evals.python.verifier.execute",
            return_value=Result(status="passed", detail="done"),
            side_effect=failure,
        ),
        patch.dict("os.environ", {"GENIUS_VERIFIER_MARKER": "outer"}),
        patch.object(sys, "argv", ["verifier", "ocaml"]),
    ):
        main()
    evidence = json.loads(capsys.readouterr().out)
    assert evidence == {
        "marker": "outer",
        "status": "harness_error" if failure else "passed",
        "detail": str(failure) if failure else "done",
        "metadata": {},
    }


@pytest.mark.parametrize("mode", ["ocaml", "unknown"])
def test_driver_entrypoint_emits_evidence(*, mode: str, capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch("shutil.which", return_value=None),
        patch.dict("os.environ", {"GENIUS_VERIFIER_MARKER": "entrypoint"}),
        patch.object(sys, "argv", ["verifier", mode]),
    ):
        runpy.run_path(str(EVALS_ROOT / "python/verifier.py"), run_name="__main__")
    evidence = json.loads(capsys.readouterr().out)
    assert evidence["status"] == "harness_error"
    assert (
        evidence["detail"]
        == {
            "ocaml": "OCaml compiler is unavailable",
            "unknown": "Expected verifier mode: ocaml <sources...> or evalplus",
        }[mode]
    )
