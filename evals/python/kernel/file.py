# Generated from compiled OCaml interfaces; do not edit.
from ._bridge import bind as _bind
from ._bridge import native as _native

create = _bind(
    operation=_native.File.create,
    arguments={"path": False, "contents": False},
    failure="validation_failure",
)
valid_path = _bind(operation=_native.File.valid_path, arguments={"path": False}, failure=None)
path_issues = _bind(
    operation=_native.File.path_issues, arguments={"field": False, "paths": False}, failure=None
)

__all__ = ["create", "path_issues", "valid_path"]
