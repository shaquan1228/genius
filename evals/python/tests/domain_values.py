"""Validated domain values and typed failures cross the native bridge directly."""

from collections.abc import Callable
from typing import cast
from unittest.mock import patch

import pytest

from evals.python import datasets, grading
from evals.python.tests.support import choice_case
from kernel import (
    Criterion,
    GradingError,
    Outcome,
    Task,
    ValidationCode,
    ValidationError,
    Verification,
    Verifier,
)
from kernel._bridge import native


def checked_factories_preserve_native_identity() -> None:
    task = choice_case(case_id="validated", a=1, b=2)
    assert isinstance(task, Task)
    assert Task is native.task
    with pytest.raises((AttributeError, TypeError)):
        task.id = ""  # type: ignore[misc]


def raw_native_construction_cannot_bypass_validation() -> None:
    task = choice_case(case_id="validated", a=1, b=2)
    with pytest.raises((RuntimeError, TypeError)):
        native.task(
            id="",
            fixture=task.fixture,
            instruction=task.instruction,
            criterion=task.criterion,
            allowed_files=task.allowed_files,
            reference=task.reference,
        )


def validation_errors_retain_native_issues() -> None:
    with pytest.raises(ValidationError) as caught:
        Verifier.create(
            inputs=("missing/path.py",),
            files=(),
            tools=(),
            command=(),
            stdin="",
            timeout_seconds=0,
        )
    issues = caught.value.issues
    assert issues
    codes = {type(issue.code) for issue in issues}
    assert {
        ValidationCode.InvalidPath,
        ValidationCode.InvalidCommand,
        ValidationCode.NonpositiveTimeout,
    } <= codes
    assert all(isinstance(issue, native.validation_issue) for issue in issues)


def harness_failures_have_a_distinct_error_contract() -> None:
    with pytest.raises(GradingError) as caught:
        grading.score_case(
            case_id="clear-task",
            response="",
            changed_files=(),
            verification=Verification.HarnessError("verifier unavailable"),
        )
    assert "verifier unavailable" in str(caught.value)
    assert caught.value.error[0] == "verifier unavailable"


def construction_and_grading_do_not_serialize_domain_values() -> None:
    task = choice_case(case_id="native-only", a=1, b=2)
    with patch("json.dumps", side_effect=AssertionError("Unexpected domain serialization")):
        dataset = datasets.compile_dataset(cases=(task,))
        assert grading.score_case(
            case_id=task.id,
            selection=dataset,
            response='{"choice":"A","reason":"Less"}',
            changed_files=(),
        )["correctness"]


@pytest.mark.parametrize("consumer", ["grader", "task", "criterion", "response"])
def implicit_dictionary_conversion_cannot_bypass_factories(consumer: str) -> None:
    task = choice_case(case_id="validated", a=1, b=2)
    fields = {
        name: getattr(task, name)
        for name in ("id", "fixture", "instruction", "criterion", "allowed_files", "reference")
    }
    create = cast(Callable[..., Task], Task.create)
    operations: dict[str, Callable[[], object]] = {
        "grader": lambda: native.Grader.grade(
            fields,
            response=None,
            outcome=Outcome(changed_files=(), verification=Verification.Unchecked()),
        ),
        "task": lambda: create(
            **{**fields, "instruction": {"skill": "reasoning", "prompt": "raw"}}
        ),
        "criterion": lambda: create(
            **{
                **fields,
                "criterion": cast(Callable[..., object], Criterion.Code)(
                    {
                        "inputs": ("solution.py",),
                        "files": (),
                        "tools": (),
                        "command": ("checker",),
                        "stdin": "",
                        "timeout_seconds": 5,
                    }
                ),
            }
        ),
        "response": lambda: native.Response.fields({"fields": [("x", True), ("x", False)]}),
    }
    with pytest.raises(TypeError):
        operations[consumer]()
