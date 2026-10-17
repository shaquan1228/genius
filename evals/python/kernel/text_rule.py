# Generated from compiled OCaml interfaces; do not edit.
from ._bridge import bind as _bind
from ._bridge import native as _native

create = _bind(
    operation=_native.Text_rule.create,
    arguments={"field": False, "min_words": False, "max_words": False},
    failure="validation_failure",
)

__all__ = ["create"]
