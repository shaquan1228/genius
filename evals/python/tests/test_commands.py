"""Commands exchange JSON projections; vendor SDKs and private inputs stay at their owners."""

import json
import runpy
import sys
from unittest.mock import patch

import pytest

from evals.python.command import command
from evals.python.contracts import GradeRequest, Verification
from evals.python.integrations.datasets import catalog
from evals.python.integrations.evalplus import benchmarks
from evals.python.integrations.inspect import kernel
from evals.python.paths import EVALS_ROOT


@pytest.mark.parametrize(
    "name", ["missing.action", "dataset.missing", "inspect.missing", "missing"]
)
def test_unknown_commands_fail_closed(name: str) -> None:
    with pytest.raises((KeyError, ValueError), match=r"missing|Unknown|unpack"):
        command(name)


def test_invalid_json_cannot_cross_the_boundary() -> None:
    with pytest.raises(ValueError, match="Expecting"):
        command("dataset.cases", payload="invalid")
    with patch("evals.python.command.importlib.import_module") as module:
        module.return_value.execute.return_value = "SDK object repr"
        with pytest.raises(ValueError, match="Expecting"):
            command("dataset.cases")


def test_public_case_command_excludes_trusted_projections() -> None:
    values = json.loads(command("dataset.cases"))
    assert all(set(value) == {"id", "skill", "prompt", "files"} for value in values)
    assert kernel.load_cases() == catalog.load_cases() == benchmarks.load_cases(selection="smoke")
    assert "canonical_solution" not in json.dumps(values)


def test_typed_client_keeps_private_channels_separate() -> None:
    case = kernel.load_cases()[0]
    assert kernel.reference(case.id) == catalog.reference(case.id)
    assert kernel.verifier(case.id) == catalog.verifier(case.id)
    request = GradeRequest(
        case_id=case.id, response="", changed_files=(), verification=Verification(status="failed")
    )
    assert kernel.grade(request=request) == catalog.grade(request=request)


def test_local_suite_selection_survives_json_roundtrip() -> None:
    assert kernel.load_cases(selection=EVALS_ROOT / "ocaml/suite.ml") == catalog.load_cases()


def test_missing_dataset_metadata_is_explicit() -> None:
    assert json.loads(command("dataset.metadata")) is None
    assert kernel.benchmark_metadata("smoke") == {}
    with patch.object(catalog, "dataset_info", return_value=None):
        assert (
            json.loads(command("dataset.metadata", payload='{"selection":"humanevalplus"}')) is None
        )


def test_runner_entrypoint_validates_before_allocating_sandboxes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EVAL_MODEL", "openai/test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("EVAL_DELIVERIES", '["typo"]')
    with (
        patch.object(sys, "argv", ["job"]),
        pytest.raises(ValueError, match="validation error"),
    ):
        runpy.run_path(str(EVALS_ROOT / "python/integrations/inspect/job.py"), run_name="__main__")
