# Generated from compiled OCaml interfaces; do not edit.
from ._bridge import bind as _bind
from ._bridge import native as _native

default = _native.Experiment.default
resolve = _bind(
    operation=_native.Experiment.resolve,
    arguments={
        "profiles": True,
        "epochs": True,
        "message_limit": True,
        "cost_limit": True,
        "time_limit": True,
        "cache": True,
    },
    failure="validation_failure",
)
create = _bind(
    operation=_native.Experiment.create,
    arguments={
        "profiles": False,
        "epochs": False,
        "message_limit": False,
        "cost_limit": False,
        "time_limit": False,
        "cache": False,
    },
    failure="validation_failure",
)

__all__ = ["create", "default", "resolve"]
