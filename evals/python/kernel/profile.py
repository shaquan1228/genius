# Generated from compiled OCaml interfaces; do not edit.
from ._bridge import bind as _bind
from ._bridge import native as _native

create = _bind(
    operation=_native.Profile.create,
    arguments={"name": False, "preamble": False, "instructions": False},
    failure=None,
)

__all__ = ["create"]
