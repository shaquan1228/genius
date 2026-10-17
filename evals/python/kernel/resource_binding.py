# Generated from compiled OCaml interfaces; do not edit.
from ._bridge import bind as _bind
from ._bridge import native as _native

create = _bind(
    operation=_native.Resource_binding.create,
    arguments={"key": False, "contents": False},
    failure=None,
)

__all__ = ["create"]
