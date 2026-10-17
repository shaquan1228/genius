# Generated from compiled OCaml interfaces; do not edit.
from ._bridge import bind as _bind
from ._bridge import native as _native

create = _bind(operation=_native.Case.create, arguments={"task": False}, failure=None)

__all__ = ["create"]
