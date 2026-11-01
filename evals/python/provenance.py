"""Stable fingerprints of JSON data, models and kernel objects."""

import hashlib
import json
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class _Native(Protocol):
    def to_python(self) -> object: ...


def _encode(value: object) -> object:
    match value:
        case BaseModel():
            return dict(value)
        case _Native():
            return value.to_python()
        case _:
            raise TypeError(f"Unsupported value: {type(value).__name__}")


def fingerprint(value: object) -> str:
    """Hash the sorted JSON view, so values the kernel treats as equal hash alike."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=_encode).encode()).hexdigest()
