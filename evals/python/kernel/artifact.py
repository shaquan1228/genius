# Generated from compiled OCaml interfaces; do not edit.
from ._bridge import bind as _bind
from ._bridge import native as _native

create = _bind(
    operation=_native.Artifact.create,
    arguments={"path": False, "content": False},
    failure="validation_failure",
)
resolve = _bind(
    operation=_native.Artifact.resolve,
    arguments={"artifact": False, "resources": False},
    failure="validation_failure",
)

__all__ = ["create", "resolve"]
