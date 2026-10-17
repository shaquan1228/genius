# Generated from compiled OCaml interfaces; do not edit.
from ._bridge import bind as _bind
from ._bridge import native as _native

create = _bind(
    operation=_native.Fixture.create, arguments={"files": False}, failure="validation_failure"
)
empty = _native.Fixture.empty
add = _bind(
    operation=_native.Fixture.add,
    arguments={"fixture": False, "file": False},
    failure="validation_failure",
)
overlay = _bind(
    operation=_native.Fixture.overlay, arguments={"base": False, "overrides": False}, failure=None
)
files = _bind(operation=_native.Fixture.files, arguments={"fixture": False}, failure=None)

__all__ = ["add", "create", "empty", "files", "overlay"]
