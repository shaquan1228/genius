"""Validated domain values and typed failures cross the native bridge directly."""

from collections.abc import Callable
from inspect import Parameter, signature, unwrap
from typing import cast

import pytest

import kernel as domain
from evals.python import datasets
from evals.python.tests.support import choice_case
from kernel import (
    Criterion,
    File,
    GradingError,
    Outcome,
    Task,
    ValidationError,
    Value,
    Verification,
    Verifier,
)
from kernel._bridge import native


def checked_factories_preserve_native_identity() -> None:
    task = choice_case(case_id="validated", a=1, b=2)
    assert isinstance(task, Task)
    assert Task is native.Task.t
    assert unwrap(Task.create) is native.Task.create
    with pytest.raises((AttributeError, TypeError)):
        task.id = ""  # type: ignore[misc]


def validation_errors_retain_native_issues() -> None:
    task = choice_case(case_id="validated", a=1, b=2)
    with pytest.raises(ValidationError) as caught:
        Task.create(
            id=task.id,
            fixture=[File(path="main.py", contents="")],
            instruction=task.instruction,
            criterion=Criterion.Code(
                verifier=Verifier(
                    inputs=("missing/path.py",),
                    files=[],
                    tools=[],
                    command=(),
                    stdin="",
                    timeout_seconds=0,
                )
            ),
            allowed_files=[],
            reference=task.reference,
        )
    issues = caught.value.issues
    assert {issue.field for issue in issues} == {
        "verifier.inputs",
        "verifier.command",
        "verifier.timeout_seconds",
    }
    assert caught.value.case_id == "validated"
    assert all(isinstance(issue, native.Failure.issue) for issue in issues)


def harness_failures_have_a_distinct_error_contract() -> None:
    with pytest.raises(GradingError) as caught:
        Task.grade(
            task=datasets.load_dataset(selection="smoke").records["clear-task"],
            outcome=Outcome.create(
                changed_files=(),
                verification=Verification.HarnessError(detail="verifier unavailable"),
            ),
        )
    assert "verifier unavailable" in str(caught.value)
    assert caught.value.error.detail == "verifier unavailable"


def _public_factories() -> list[Callable[..., object]]:
    return [
        value.create
        for name in cast(list[str], vars(domain)["__all__"])
        if hasattr(value := getattr(domain, name), "create")
    ]


@pytest.mark.parametrize(
    "constructor",
    [
        *_public_factories(),
        domain.Reference,
        domain.Profile,
        domain.File,
        domain.Value.String,
        domain.Value.Record,
        domain.Predicate.Equals,
        domain.Criterion.Code,
        domain.Criterion.State,
        domain.Verification.Passed,
        domain.Verification.HarnessError,
    ],
)
def constructors_expose_names_and_reject_positional_inputs(
    constructor: Callable[..., object],
) -> None:
    assert all(
        parameter.kind is Parameter.KEYWORD_ONLY
        for parameter in signature(constructor).parameters.values()
    )
    with pytest.raises(TypeError):
        constructor(object())


@pytest.mark.parametrize(
    "fields", [{}, {"values": []}, {"path": "x", "contents": "", "extra": True}]
)
def record_calls_reject_missing_or_unknown_names(fields: dict[str, object]) -> None:
    constructor = cast(Callable[..., object], File)
    with pytest.raises(TypeError):
        constructor(**fields)


@pytest.mark.parametrize("fields", [{}, {"text": "x"}, {"value": "x", "extra": True}])
def variant_calls_reject_missing_or_unknown_names(fields: dict[str, object]) -> None:
    constructor = cast(Callable[..., object], Value.String)
    with pytest.raises(TypeError):
        constructor(**fields)


def collections_require_named_domain_entries() -> None:
    constructor = cast(Callable[..., object], Verifier)
    with pytest.raises(TypeError):
        constructor(
            inputs=["main.py"],
            files=[("verify.py", "check")],
            tools=[],
            command=["python3", "verify.py"],
            stdin="",
            timeout_seconds=5,
        )
