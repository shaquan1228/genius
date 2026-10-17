# Generated from compiled OCaml interfaces; do not edit.
from ._bridge import bind as _bind
from ._bridge import native as _native

create = _bind(
    operation=_native.Instruction.create,
    arguments={"skill": False, "prompt": False},
    failure="validation_failure",
)
valid_name = _bind(
    operation=_native.Instruction.valid_name, arguments={"name": False}, failure=None
)

__all__ = ["create", "valid_name"]
