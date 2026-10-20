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
    from . import GradingFailure, Issue, ValidationFailure

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
    raise ImportError(
        "OCaml kernel is not installed; run make -C evals setup-kernel "
        "from the source checkout, using the matching opam switch"
    ) from error

native = cast(ModuleType, _ocaml.Genius_evals_kernel)


class ValidationError(ValueError):
    """A rejected declaration, retaining native validation issues."""

    def __init__(self, *, failure: ValidationFailure) -> None:
        self.issues: tuple[Issue, ...] = tuple(failure.issues)
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


Node = Mapping[str, Any]
Coercer = Callable[[Any], Any]


def value(data: object) -> Any:
    """Encode JSON-shaped Python as a native value; other objects become their text."""
    kinds: dict[type, Coercer] = {
        type(None): lambda _: native.Value.Null(),
        bool: lambda data: native.Value.Bool(value=data),
        int: lambda data: native.Value.Int(value=data),
        float: lambda data: native.Value.Float(value=data),
        str: lambda data: native.Value.String(value=data),
        list: lambda data: native.Value.List(items=[value(item) for item in data]),
        tuple: lambda data: native.Value.List(items=[value(item) for item in data]),
        dict: lambda data: native.Value.Record(
            fields=[(str(key), value(item)) for key, item in data.items()]
        ),
    }
    if isinstance(data, native.Value.t):
        return data
    return kinds.get(type(data), lambda data: native.Value.String(value=str(data)))(data)


def plain(data: Any) -> Any:
    """Decode a native value into JSON-shaped Python."""
    if isinstance(data, native.Value.List):
        return [plain(item) for item in data.items]
    if isinstance(data, native.Value.Record):
        return {name: plain(item) for name, item in data.fields}
    return None if isinstance(data, native.Value.Null) else data.value


def coercer(node: Node) -> Coercer:
    """Convert plain Python wherever the native type expects a value."""
    if node["kind"] == "tuple":
        items = [coercer(item) for item in node["items"]]
        return lambda data: tuple(convert(item) for convert, item in zip(items, data, strict=True))
    if node["name"] == "value":
        return value
    if node["name"] == "list":
        convert = coercer(node["args"][0])
        return lambda data: [
            convert(item) for item in (data.items() if isinstance(data, Mapping) else data)
        ]
    return lambda data: data


def coerced(fields: Mapping[str, Any], *, coerce: Mapping[str, Node]) -> dict[str, Any]:
    converters = {name: coercer(node) for name, node in coerce.items()}
    return {
        name: converters[name](item) if name in converters else item
        for name, item in fields.items()
    }


def named(*, constructor: type[Any], coerce: Mapping[str, Node] | None = None) -> type[Any]:
    initializer = constructor.__init__
    contract = signature(dict.fromkeys(constructor._field_names or (), False))

    def initialize(self: Any, **fields: Any) -> None:
        if "__capsule" not in fields:
            contract.bind(**fields)
            fields = coerced(fields, coerce=coerce or {})
        initializer(self, **fields)

    constructor.__init__ = initialize
    constructor.__signature__ = contract
    return constructor


errors = {"validation_failure": ValidationError, "grading_failure": GradingError}


def bind(
    *,
    operation: Callable[..., Any],
    arguments: Mapping[str, bool],
    failure: str | None,
    coerce: Mapping[str, Node] | None = None,
) -> Callable[..., Any]:
    contract = signature(arguments)

    @wraps(operation)
    def call(**kwargs: Any) -> Any:
        contract.bind(**kwargs)
        result = operation(**coerced(kwargs, coerce=coerce or {}))
        if failure is None:
            return result
        if isinstance(result, _ocaml.Ok):
            return result[0]
        raise errors[failure](failure=result[0])

    cast(Any, call).__signature__ = contract
    return call
