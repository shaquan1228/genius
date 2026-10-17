# Generated from compiled OCaml interfaces; do not edit.
from ._bridge import bind as _bind
from ._bridge import native as _native

create = _bind(
    operation=_native.Response.create, arguments={"fields": False}, failure="validation_failure"
)
empty = _native.Response.empty

__all__ = ["create", "empty"]
