# Generated from compiled OCaml interfaces; do not edit.
from ._bridge import bind as _bind
from ._bridge import native as _native

create = _bind(
    operation=_native.Criterion.create,
    arguments={"code": True, "answer": True},
    failure="validation_failure",
)

__all__ = ["create"]
