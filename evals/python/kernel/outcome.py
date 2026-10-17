# Generated from compiled OCaml interfaces; do not edit.
from ._bridge import bind as _bind
from ._bridge import native as _native

create = _bind(
    operation=_native.Outcome.create,
    arguments={"changed_files": False, "verification": False},
    failure=None,
)

__all__ = ["create"]
