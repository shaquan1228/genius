"""Load the native library while preserving the caller's process environment."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping
from functools import wraps
from importlib import import_module
from inspect import Parameter, Signature
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from . import GradingFailure, ValidationFailure, ValidationIssue

_environment = {name: os.environ.get(name) for name in ("PATH", "PYTHONHOME", "PYTHONPATH")}
os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + (_environment["PATH"] or "")
try:
    _ocaml = import_module("ocaml")
finally:
    # PyML mutates libc's environment without updating Python's os.environ mapping.
    for _name, _value in _environment.items():
        if _value is None:
            os.unsetenv(_name)
            os.environ.pop(_name, None)
        else:
            os.environ[_name] = _value


try:
    _ocaml.require("genius_evals_kernel")
except ImportError as error:
    raise ImportError("OCaml kernel is not installed; run make -C evals setup-kernel") from error

native = cast(ModuleType, _ocaml.Genius_evals_kernel)


class ValidationError(ValueError):
    """A rejected declaration, retaining native validation issues."""

    def __init__(self, *, failure: ValidationFailure) -> None:
        self.issues: tuple[ValidationIssue, ...] = tuple(failure.issues)
        self.case_id = failure.case_id
        super().__init__("; ".join(issue.message for issue in self.issues))


class GradingError(RuntimeError):
    """A grading failure, separate from an incorrect candidate answer."""

    def __init__(self, *, failure: GradingFailure.Value) -> None:
        self.error = failure
        super().__init__("Verification harness error: " + failure.detail)


def signature(arguments: Mapping[str, bool]) -> Signature:
    return Signature(
        [
            Parameter(name, Parameter.KEYWORD_ONLY, default=... if optional else Parameter.empty)
            for name, optional in arguments.items()
        ]
    )


def named(*, constructor: type[Any]) -> type[Any]:
    initializer = constructor.__init__
    contract = signature(dict.fromkeys(constructor._field_names or (), False))

    def initialize(self: Any, **fields: Any) -> None:
        if "__capsule" not in fields:
            contract.bind(**fields)
        initializer(self, **fields)

    constructor.__init__ = initialize
    constructor.__signature__ = contract
    return constructor


errors = {"validation_failure": ValidationError, "grading_failure": GradingError}


def bind(
    *, operation: Callable[..., Any], arguments: Mapping[str, bool], failure: str | None
) -> Callable[..., Any]:
    contract = signature(arguments)

    @wraps(operation)
    def call(**kwargs: Any) -> Any:
        contract.bind(**kwargs)
        result = operation(**kwargs)
        if failure is None:
            return result
        if isinstance(result, _ocaml.Ok):
            return result[0]
        raise errors[failure](failure=result[0])

    cast(Any, call).__signature__ = contract
    return call
