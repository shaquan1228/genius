"""Direct public commands validate inputs and own adapter composition."""

import asyncio
import runpy
import sys
from collections.abc import Awaitable, Callable
from typing import assert_type
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from evals.python import assessment, evaluation, execution, verification
from evals.python.evaluation import EvaluationSettings
from evals.python.execution import Runtime
from evals.python.paths import EVALS_ROOT


def runner_entrypoint_validates_before_allocating_sandboxes(
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
    ("operation", "arguments"),
    [
        (verification.verify_case, {"case_id": "case", "agent": object(), "runtime": object()}),
        (
            assessment.assess,
            {
                "case_id": "case",
                "response": "",
                "changed_files": (),
                "agent": object(),
                "runtime": object(),
            },
        ),
        (verification.validate_reference, {"case_id": "case", "runtime": object()}),
        (evaluation.evaluate, {"settings": object()}),
        (evaluation.evaluate, {"settings": {"model": "openai/test"}}),
    ],
)
def capability_commands_reject_non_capabilities(
    operation: Callable[..., Awaitable[object]], *, arguments: dict[str, object]
) -> None:
    async def execute() -> None:
        with pytest.raises(ValidationError):
            await operation(**arguments)

    asyncio.run(execute())


def public_evaluation_preserves_validated_settings_at_the_sdk_edge() -> None:
    settings = EvaluationSettings(model="openai/test", sample_ids=("clear-task",))
    with patch(
        "evals.python.integrations.inspect.evaluation.evaluate_async",
        new_callable=AsyncMock,
        return_value=3,
    ) as evaluate:

        async def execute() -> int:
            return assert_type(await evaluation.evaluate(settings), int)

        assert asyncio.run(execute()) == 3
    assert evaluate.await_args is not None
    assert evaluate.await_args.args[0] is settings
    assert (settings.model, settings.sample_ids) == ("openai/test", ("clear-task",))
    with pytest.raises(ValidationError):
        settings.model = "changed"


@pytest.mark.parametrize(
    "arguments", [{"limit": 0}, {"sample_ids": ()}, {"deliveries": ("files", "files")}]
)
def direct_evaluation_validates_before_sdk_execution(arguments: dict[str, object]) -> None:
    async def execute() -> None:
        await evaluation.evaluate(
            EvaluationSettings.model_validate({"model": "openai/test", **arguments})
        )

    with (
        patch("evals.python.integrations.inspect.evaluation.evaluate_async") as evaluate,
        pytest.raises(ValidationError),
    ):
        asyncio.run(execute())
    evaluate.assert_not_called()


def public_surface_has_no_legacy_function_aliases() -> None:
    for name in (
        "GradeRequest",
        "RunOverrides",
        "load_cases",
        "grade",
        "VerifyCase",
        "AssessCase",
        "ValidateReference",
        "Evaluate",
    ):
        assert not any(
            hasattr(module, name) for module in (assessment, evaluation, execution, verification)
        )


@pytest.mark.parametrize("provider", ["hf", "local"])
def runtime_factory_returns_canonical_capability(provider: str) -> None:
    runtime_factory: Callable[..., Runtime] = execution.create_runtime
    runtime = assert_type(runtime_factory(provider=provider), Runtime)
    assert isinstance(runtime, Runtime)
    with pytest.raises(ValidationError):
        runtime_factory(provider="unknown")
