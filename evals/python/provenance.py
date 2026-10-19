"""Stable fingerprints preserve native value ordering and the saved-run encoding."""

import hashlib
from collections.abc import Sequence
from typing import cast

from kernel import File, Fixture, Task


def fingerprint(sources: Sequence[File], *, resources: tuple[tuple[str, str], ...] = ()) -> str:
    modules = tuple((file.path, file.contents) for file in sources)
    return hashlib.sha256(repr((modules, resources)).encode()).hexdigest()


def _canonical(value: object) -> object:
    match value:
        case None | str() | bool() | int() | float():
            return value
        case Fixture():
            return tuple(_canonical(file) for file in Fixture.files(fixture=value))
        case _:
            return (
                type(value).__name__,
                tuple(_canonical(item) for item in cast(Sequence[object], value)),
            )


def value_fingerprint(value: Task) -> str:
    return hashlib.sha256(repr(_canonical(value)).encode()).hexdigest()
