# Generated from compiled OCaml interfaces; do not edit.
"""Private native operations used by the Python implementation."""

from functools import cache

from ._bridge import native as _native

case = _native.Case
criterion = _native.Criterion
experiment = _native.Experiment
fixture = _native.Fixture
grader = _native.Grader
projection = _native.Projection
reference = _native.Reference
response = _native.Response
verifier = _native.Verifier


@cache
def sources() -> tuple[tuple[str, str], ...]:
    return tuple((str(name), str(contents)) for name, contents in _native.sources)


__all__ = [
    "case",
    "criterion",
    "experiment",
    "fixture",
    "grader",
    "projection",
    "reference",
    "response",
    "sources",
    "verifier",
]
