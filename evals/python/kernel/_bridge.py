"""Load the native library while preserving the caller's process environment."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from functools import wraps
from importlib import import_module
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
InvalidArgument = _ocaml.Invalid_argument


class ValidationError(ValueError):
    """A rejected declaration, retaining native validation issues."""

    def __init__(self, failure: ValidationFailure) -> None:
        self.issues: tuple[ValidationIssue, ...] = tuple(failure.issues)
        self.case_id = failure.case_id
        super().__init__("; ".join(issue.message for issue in self.issues))


class GradingError(RuntimeError):
    """A grading failure, separate from an incorrect candidate answer."""

    def __init__(self, error: GradingFailure.Value) -> None:
        self.error = error
        super().__init__("Verification harness error: " + str(error[0]))


def checked(operation: Callable[..., Any], *, failure: str) -> Callable[..., Any]:
    error = ValidationError if failure == "validation_failure" else GradingError

    @wraps(operation)
    def call(*args: Any, **kwargs: Any) -> Any:
        result = operation(*args, **kwargs)
        if isinstance(result, _ocaml.Ok):
            return result[0]
        raise error(result[0])

    return call
