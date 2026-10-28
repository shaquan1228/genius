"""Plain JSON views and stable fingerprints of kernel values, models and tuples.

One generic traversal reads every field a type exposes, after Lämmel and Peyton Jones,
"Scrap Your Boilerplate" (TLDI 2003), so a new kernel field needs no edit here.
A kernel variant, such as Predicate.All, also names its constructor as "kind",
so variants with the same fields, such as All and Any, do not share a fingerprint.
"""

import hashlib
import json
import re
from inspect import getmembers, isgetsetdescriptor

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
    match value:
        case Value.List(items):
            return plain(items)
        case Value.Record(fields):
            # Like the kernel, read the first of repeated names.
            return {name: plain(value.get(path=[name])) for name, _ in fields}
        case Value.Bool(scalar) | Value.Int(scalar) | Value.Float(scalar) | Value.String(scalar):
            return scalar
        case _:
            return None


def _object(value: object) -> dict[str, JsonValue]:
    """Every present field of a model or native type; None and () mark absent fields."""
    fields = dict(value) if isinstance(value, BaseModel) else _getters(value)
    return {name: plain(item) for name, item in fields.items() if item not in (None, ())}


def _getters(value: object) -> dict[str, object]:
    """Public getters of the type and its bases; a variant derives from its sum type."""
    kind = type(value)
    getters = {
        name: getattr(value, name)
        for name, _ in getmembers(kind, isgetsetdescriptor)
        if not name.startswith("_")
    }
    if len(kind.__mro__) > 2:
        getters["kind"] = re.sub(r"(?<!^)(?=[A-Z])", "_", kind.__name__).lower()
    if not getters:
        raise TypeError(f"Unsupported value: {kind.__name__}")
    return getters


def fingerprint(value: object) -> str:
    """Hash the sorted JSON view, so values the kernel treats as equal hash alike."""
    return hashlib.sha256(json.dumps(plain(value), sort_keys=True).encode()).hexdigest()
