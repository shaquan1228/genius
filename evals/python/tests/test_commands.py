"""Typed public operations preserve canonical values and own adapter composition."""

import asyncio
import runpy
import sys
from typing import assert_type, cast
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from evals.python import catalog, commands
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
    assert grade.call_args.kwargs["case_id"] == operation.case_id
    assert grade.call_args.kwargs["verification"] is operation.verification
    assert result is grade.return_value


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


@pytest.mark.parametrize("provider", ["hf", "local"])
def test_runtime_query_returns_canonical_capability(provider: str) -> None:
    operation = commands.ExecutionRuntime.model_validate({"provider": provider})
    assert isinstance(assert_type(commands.query(operation), commands.Runtime), commands.Runtime)
    with pytest.raises(ValidationError):
        commands.ExecutionRuntime.model_validate({"provider": "unknown"})


def test_public_surface_has_no_legacy_function_aliases() -> None:
    for name in (
        "GradeRequest",
        "RunOverrides",
        "load_cases",
        "grade",
        "verify_case",
        "assess_case",
        "validate_reference",
    ):
        assert not hasattr(commands, name)
