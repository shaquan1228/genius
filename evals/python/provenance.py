"""Stable fingerprints preserve native value ordering and the saved-run encoding."""

import hashlib
from collections.abc import Mapping

from kernel import (
    Criterion,
    File,
    Instruction,
    Predicate,
    Reference,
    Rubric,
    Task,
    TextRule,
    Value,
    Verifier,
    source_hash,
)
from pydantic import BaseModel

_FIELDS: Mapping[type, tuple[str, ...]] = {
    Criterion: ("kind", "verifier", "rubric", "predicate"),
    File: ("path", "contents"),
    Instruction: ("prompt",),
    Predicate: (
        "kind",
        "path",
        "expected",
        "item",
        "allowed",
        "min_words",
        "max_words",
        "checks",
        "check",
    ),
    Reference: ("edits", "completion"),
    Rubric: ("expected", "text_rule"),
    Task: ("id", "fixture", "instruction", "criterion", "allowed_files", "reference"),
    TextRule: ("field", "min_words", "max_words"),
    Verifier: ("inputs", "files", "tools", "command", "stdin", "timeout_seconds"),
}


def fingerprint(*, resources: tuple[tuple[str, str], ...] = ()) -> str:
    return hashlib.sha256(repr((source_hash(), resources)).encode()).hexdigest()


def _value(value: Value) -> object:
    match value.kind:
        case "list":
            return ("list", tuple(map(_value, value.items)))
        case "record":
            return ("record", tuple((name, _value(item)) for name, item in value.fields))
        case _:
            return value.scalar


def _names(value: object) -> tuple[str, ...]:
    return tuple(type(value).model_fields) if isinstance(value, BaseModel) else _FIELDS[type(value)]


def _canonical(value: object) -> object:
    match value:
        case None | str() | bool() | int() | float():
            return value
        case tuple():
            return tuple(map(_canonical, value))
        case Value():
            return _value(value)
        case _:
            return (
                type(value).__name__,
                tuple((name, _canonical(getattr(value, name))) for name in _names(value)),
            )


def value_fingerprint(value: object) -> str:
    return hashlib.sha256(repr(_canonical(value)).encode()).hexdigest()
