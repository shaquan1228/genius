"""Plain JSON views and stable fingerprints of kernel values, models and tuples.

One generic traversal reads every field a type exposes, after Lämmel and Peyton Jones,
"Scrap Your Boilerplate" (TLDI 2003), so a new kernel field needs no edit here.
"""

import hashlib
import json
from inspect import isgetsetdescriptor

from kernel import Value
from pydantic import BaseModel, JsonValue


def plain(value: object) -> JsonValue:
    match value:
        case None | str() | bool() | int() | float():
            return value
        case tuple():
            return [plain(item) for item in value]
        case Value():
            return _value(value)
        case _:
            return _object(value)


def _value(value: Value) -> JsonValue:
    match value.kind:
        case "list":
            return plain(value.items)
        case "record":
            # Like the kernel, read the first of repeated names.
            return {name: plain(value.get(path=[name])) for name, _ in value.fields}
        case _:
            return value.scalar


def _object(value: object) -> dict[str, JsonValue]:
    """Every present field of a model or native type; None and () mark absent fields."""
    fields = dict(value) if isinstance(value, BaseModel) else _getters(value)
    return {name: plain(item) for name, item in fields.items() if item not in (None, ())}


def _getters(value: object) -> dict[str, object]:
    kind = type(value)
    getters = {
        name: getattr(value, name)
        for name, member in vars(kind).items()
        if isgetsetdescriptor(member) and not name.startswith("_")
    }
    if not getters:
        raise TypeError(f"Unsupported value: {kind.__name__}")
    return getters


def fingerprint(value: object) -> str:
    """Hash the sorted JSON view, so values the kernel treats as equal hash alike."""
    return hashlib.sha256(json.dumps(plain(value), sort_keys=True).encode()).hexdigest()
