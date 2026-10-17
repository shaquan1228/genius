# Generated from compiled OCaml interfaces; do not edit.
from ._bridge import bind as _bind
from ._bridge import native as _native

create = _bind(
    operation=_native.Task.create,
    arguments={
        "id": False,
        "fixture": False,
        "instruction": False,
        "criterion": False,
        "allowed_files": False,
        "reference": False,
    },
    failure="validation_failure",
)
resolve_resources = _bind(
    operation=_native.Task.resolve_resources,
    arguments={"task": False, "resources": False},
    failure="validation_failure",
)

__all__ = ["create", "resolve_resources"]
