# Generated from compiled OCaml interfaces; do not edit.
from ._bridge import bind as _bind
from ._bridge import native as _native

case = _bind(operation=_native.Projection.case, arguments={"task": False}, failure=None)
verifier = _bind(operation=_native.Projection.verifier, arguments={"task": False}, failure=None)
reference = _bind(operation=_native.Projection.reference, arguments={"task": False}, failure=None)

__all__ = ["case", "reference", "verifier"]
