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
    Fixture,
    GradingError,
    Outcome,
    Response,
    Task,
    ValidationCode,
    ValidationError,
    Verification,
    Verifier,
)
from kernel._bridge import native


def public_factories_name_their_collection_arguments() -> None:
    fixture = Fixture.create(files=[])
    response = Response.create(fields=[])
    assert isinstance(fixture, Fixture)
    assert tuple(response.fields) == ()


def checked_factories_preserve_native_identity() -> None:
    task = choice_case(case_id="validated", a=1, b=2)
    assert isinstance(task, Task)
    assert Task is native.Task.t
    assert unwrap(Task.create) is native.Task.create
    with pytest.raises((AttributeError, TypeError)):
        task.id = ""  # type: ignore[misc]


def raw_native_construction_cannot_bypass_validation() -> None:
    task = choice_case(case_id="validated", a=1, b=2)
    with pytest.raises((RuntimeError, TypeError)):
        native.Task.t(
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
            files=[],
            tools=[],
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
    assert all(isinstance(issue, native.Validation_issue.t) for issue in issues)


def harness_failures_have_a_distinct_error_contract() -> None:
    with pytest.raises(GradingError) as caught:
        Task.grade(
            task=datasets.record("clear-task", selection="smoke"),
            response=None,
            outcome=Outcome.create(
                changed_files=(),
                verification=Verification.HarnessError(detail="verifier unavailable"),
            ),
        )
    assert "verifier unavailable" in str(caught.value)
    assert caught.value.error.detail == "verifier unavailable"


@pytest.mark.parametrize("consumer", ["grader", "task", "criterion", "response"])
def implicit_dictionary_conversion_cannot_bypass_factories(consumer: str) -> None:
    task = choice_case(case_id="validated", a=1, b=2)
    fields = {
        name: getattr(task, name)
        for name in ("id", "fixture", "instruction", "criterion", "allowed_files", "reference")
    }
    create = cast(Callable[..., Task], Task.create)
    operations: dict[str, Callable[[], object]] = {
        "grader": lambda: native.Task.grade(
            task=fields,
            response=None,
            outcome=Outcome.create(changed_files=(), verification=Verification.Unchecked()),
        ),
        "task": lambda: create(
            **{**fields, "instruction": {"skill": "reasoning", "prompt": "raw"}}
        ),
        "criterion": lambda: create(
            **{
                **fields,
                "criterion": cast(Callable[..., object], Criterion.create)(
                    code={
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
        "response": lambda: native.Rubric.create(expected={"fields": []}, text_rule=None),
    }
    with pytest.raises(TypeError):
        operations[consumer]()


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
        domain.Outcome,
        domain.Profile,
        domain.ResponseValue.String,
        domain.ResponseValue.Bool,
        domain.Content.Inline,
        domain.Content.Resource,
        domain.Criterion.Code,
        domain.Criterion.Answer,
        domain.Completion.Plain,
        domain.Completion.Structured,
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


@pytest.mark.parametrize("fields", [{}, {"values": []}, {"fields": [], "extra": True}])
def factory_calls_reject_missing_or_unknown_names(fields: dict[str, object]) -> None:
    create = cast(Callable[..., Response], Response.create)
    with pytest.raises(TypeError):
        create(**fields)


@pytest.mark.parametrize("fields", [{}, {"value": "x"}, {"text": "x", "extra": True}])
def variant_calls_reject_missing_or_unknown_names(fields: dict[str, object]) -> None:
    constructor = cast(Callable[..., object], domain.Content.Inline)
    with pytest.raises(TypeError):
        constructor(**fields)


@pytest.mark.parametrize(
    ("constructor", "fields"),
    [
        (Fixture.create, {"files": [("main.py", "text")]}),
        (Response.create, {"fields": [("choice", domain.ResponseValue.create(string="B"))]}),
        (
            Verifier.create,
            {
                "inputs": ["main.py"],
                "files": [("verify.py", domain.Content.create(inline="check"))],
                "tools": [],
                "command": ["python3", "verify.py"],
                "stdin": "",
                "timeout_seconds": 5,
            },
        ),
    ],
)
def collections_require_named_domain_entries(
    constructor: Callable[..., object], *, fields: dict[str, object]
) -> None:
    with pytest.raises(TypeError):
        constructor(**fields)


@pytest.mark.parametrize("owner", ["Content", "Completion", "Criterion", "ResponseValue"])
def alternative_factories_require_one_named_choice(owner: str) -> None:
    with pytest.raises(ValidationError, match="exactly one") as caught:
        getattr(domain, owner).create()
    assert isinstance(caught.value.issues[0].code, ValidationCode.InvalidAlternative)


@pytest.mark.parametrize(
    ("owner", "fields"),
    [
        ("Content", {"inline": "", "resource": "checker"}),
        ("Completion", {"plain": "", "structured": Response.create(fields=[])}),
        ("ResponseValue", {"string": "", "bool": False}),
    ],
)
def alternative_factories_reject_multiple_named_choices(
    owner: str, *, fields: dict[str, object]
) -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        getattr(domain, owner).create(**fields)


@pytest.mark.parametrize(
    ("constructor", "fields"),
    [
        (domain.Content.Inline, {"text": "unchecked"}),
        (domain.Content.Resource, {"key": "unchecked"}),
        (domain.Completion.Plain, {"text": "unchecked"}),
        (domain.ResponseValue.String, {"value": "unchecked"}),
    ],
)
def private_alternatives_require_the_owner_factory(
    constructor: Callable[..., object], *, fields: dict[str, object]
) -> None:
    with pytest.raises(RuntimeError, match="private type"):
        constructor(**fields)
