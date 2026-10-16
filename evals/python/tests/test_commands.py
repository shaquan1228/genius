"""Commands exchange JSON projections; vendor SDKs and private inputs stay at their owners."""

import asyncio
import json
import runpy
import sys
from typing import assert_type, cast
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from evals.python import catalog, commands, contracts
from evals.python.command import command
from evals.python.contracts import GradeRequest, Verification
from evals.python.integrations.evalplus import benchmarks
from evals.python.integrations.inspect import datasets
from evals.python.integrations.inspect.evaluation import EvaluationRequest
from evals.python.paths import EVALS_ROOT


def test_public_commands_preserve_canonical_objects() -> None:
    cases = assert_type(commands.query(commands.Cases()), tuple[commands.Case, ...])
    assert cases[0] is catalog.load_cases()[0]
    assert all(set(case.model_dump()) == {"id", "skill", "prompt", "files"} for case in cases)


def test_public_commands_select_canonical_projections() -> None:
    assert (
        commands.query(commands.Cases(selection=EVALS_ROOT / "ocaml/suite.ml"))
        == catalog.load_cases()
    )
    assert (
        assert_type(commands.query(commands.DescribeDataset()), commands.DatasetInfo | None) is None
    )
    with patch("evals.python.catalog.download") as download:
        info = commands.query(commands.DescribeDataset(selection="humanevalplus"))
    assert isinstance(info, commands.DatasetInfo)
    download.assert_not_called()


def test_public_experiment_resolves_canonical_overrides() -> None:
    spec = assert_type(commands.query(commands.ExperimentSettings(epochs=2)), commands.Experiment)
    assert spec.epochs == 2


def test_public_hashes_match_existing_provenance() -> None:
    provenance = assert_type(commands.query(commands.Provenance()), commands.DatasetProvenance)
    assert provenance.info is None
    assert provenance.source_hash == catalog.source_hash("smoke")
    assert provenance.cases_hash == catalog.cases_hash("smoke")


def test_public_grade_preserves_request_and_result() -> None:
    operation = commands.GradeCase(
        case_id="clear-task",
        response="",
        changed_files=(),
        verification=commands.Verification(status="passed"),
    )
    with patch("evals.python.transport.grade", return_value={"correctness": True}) as grade:
        result = assert_type(commands.query(operation), commands.Scores)
    assert grade.call_args.kwargs["request"]["case_id"] == operation.case_id
    assert grade.call_args.kwargs["request"]["verification"] == {"status": "passed", "detail": ""}
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
    assert datasets.grade(request=request) == commands.grade(request=request)


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


@pytest.mark.parametrize(
    "operation_type", [commands.Cases, commands.DescribeDataset, commands.Provenance]
)
def test_query_selection_is_immutable_and_strict(
    operation_type: type[commands.Cases | commands.DescribeDataset | commands.Provenance],
) -> None:
    operation = operation_type()
    with pytest.raises(ValidationError):
        operation.selection = "changed"
    with pytest.raises(ValidationError):
        operation_type.model_validate({"selection": None})
    with pytest.raises(ValidationError):
        operation_type.model_validate({"unknown": "smoke"})


def test_capability_commands_reject_non_capabilities() -> None:
    with pytest.raises(ValidationError):
        commands.VerifyCase.model_validate(
            {"case_id": "case", "agent": object(), "runtime": object()}
        )
    with pytest.raises(ValidationError):
        commands.AssessCase.model_validate(
            {
                "case_id": "case",
                "response": "",
                "changed_files": (),
                "agent": object(),
                "runtime": object(),
            }
        )
    with pytest.raises(ValidationError):
        commands.ValidateReference.model_validate({"case_id": "case", "runtime": object()})


def test_unknown_query_fails_closed_at_runtime() -> None:
    with pytest.raises(AssertionError):
        commands.query(cast(commands.Cases, commands.Evaluate(model="test")))


def test_unknown_execution_fails_closed_at_runtime() -> None:
    async def execute() -> None:
        with pytest.raises(AssertionError):
            await commands.execute(cast(commands.Evaluate, commands.Cases()))

    asyncio.run(execute())


def test_public_evaluation_preserves_the_command_at_the_sdk_edge() -> None:
    operation = commands.Evaluate(model="openai/test", sample_ids=("clear-task",))
    with patch(
        "evals.python.integrations.inspect.evaluation.evaluate_async",
        new_callable=AsyncMock,
        return_value=3,
    ) as evaluate:
        assert asyncio.run(commands.execute(operation)) == 3
    assert evaluate.await_args is not None
    assert evaluate.await_args.args[0] is operation
    with pytest.raises(ValidationError):
        operation.model = "changed"


def test_legacy_aliases_share_one_canonical_contract() -> None:
    assert (
        contracts.Case,
        contracts.Verification,
        contracts.RunOverrides,
        contracts.GradeRequest,
        EvaluationRequest,
    ) == (
        commands.Case,
        commands.Verification,
        commands.ExperimentSettings,
        commands.GradeCase,
        commands.Evaluate,
    )
