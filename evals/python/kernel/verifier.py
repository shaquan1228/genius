# Generated from compiled OCaml interfaces; do not edit.
from ._bridge import bind as _bind
from ._bridge import native as _native

create = _bind(
    operation=_native.Verifier.create,
    arguments={
        "inputs": False,
        "files": False,
        "tools": False,
        "command": False,
        "stdin": False,
        "timeout_seconds": False,
    },
    failure="validation_failure",
)
resolve_resources = _bind(
    operation=_native.Verifier.resolve_resources,
    arguments={"verifier": False, "resources": False},
    failure="validation_failure",
)

__all__ = ["create", "resolve_resources"]
