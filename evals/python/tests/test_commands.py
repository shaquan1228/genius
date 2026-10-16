"""Commands exchange JSON projections; vendor SDKs and private inputs stay at their owners."""

import json
import runpy
import sys
from unittest.mock import patch

import pytest

from evals.python import catalog, commands
from evals.python.command import command
from evals.python.contracts import DatasetInfo, Experiment, GradeRequest, RunOverrides, Verification
from evals.python.integrations.evalplus import benchmarks
from evals.python.integrations.inspect import datasets
from evals.python.paths import EVALS_ROOT


def test_public_commands_preserve_canonical_objects() -> None:
    case = commands.load_cases()[0]
    assert case is catalog.load_cases()[0]
    assert commands.verifier(case.id) is catalog.verifier(case.id)
    expected = catalog.reference(case.id)
    with patch("evals.python.transport.reference", return_value=expected):
        assert commands.reference(case.id) is expected


def test_public_commands_select_canonical_projections() -> None:
    assert commands.verifier("small-decision") is None
    assert commands.load_cases(selection=EVALS_ROOT / "ocaml/suite.ml") == catalog.load_cases()
    assert commands.dataset_info("smoke") is None
    assert isinstance(commands.dataset_info("humanevalplus"), DatasetInfo)


def test_public_experiment_resolves_canonical_overrides() -> None:
    overrides = RunOverrides(epochs=2)
    spec = commands.experiment(overrides)
    assert isinstance(spec, Experiment)
    assert spec.epochs == overrides.epochs


def test_public_hashes_match_existing_provenance() -> None:
    assert commands.source_hash("smoke") == datasets.source_hash("smoke")
    assert commands.cases_hash("smoke") == catalog.cases_hash("smoke")


def test_public_grade_preserves_request_and_result() -> None:
    request = GradeRequest(
        case_id="clear-task",
        response="",
        changed_files=(),
        verification=Verification(status="passed"),
    )
    with patch("evals.python.transport.grade", return_value={"correctness": True}) as grade:
        result = commands.grade(request=request)
    assert grade.call_args.kwargs["request"] is request
    assert result is grade.return_value


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
    assert datasets.load_cases() == catalog.load_cases() == benchmarks.load_cases(selection="smoke")
    assert "canonical_solution" not in json.dumps(values)


def test_typed_client_keeps_private_channels_separate() -> None:
    case = datasets.load_cases()[0]
    assert datasets.reference(case.id) == catalog.reference(case.id)
    assert datasets.verifier(case.id) == catalog.verifier(case.id)
    request = GradeRequest(
        case_id=case.id, response="", changed_files=(), verification=Verification(status="failed")
    )
    assert datasets.grade(request=request) == catalog.grade(request=request)


def test_local_suite_selection_survives_json_roundtrip() -> None:
    assert datasets.load_cases(selection=EVALS_ROOT / "ocaml/suite.ml") == catalog.load_cases()


def test_missing_dataset_metadata_is_explicit() -> None:
    assert json.loads(command("dataset.metadata")) is None
    assert datasets.benchmark_metadata("smoke") == {}
    with patch(
        "evals.python.integrations.datasets.commands.catalog.dataset_info", return_value=None
    ):
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
        runpy.run_path(
            str(EVALS_ROOT / "python/integrations/hugging_face/job.py"), run_name="__main__"
        )
