# Generated from compiled OCaml interfaces; do not edit.
from functools import cache
from types import SimpleNamespace

from ._bridge import bind as _bind
from ._bridge import native as _native

case = SimpleNamespace(
    resolve_resources=_bind(
        operation=_native.Case.resolve_resources,
        arguments={"task": False, "resources": False},
        failure="validation_failure",
    ),
)

construct = SimpleNamespace(
    file=_bind(
        operation=_native.Construct.file,
        arguments={"path": False, "contents": False},
        failure="validation_failure",
    ),
    artifact=_bind(
        operation=_native.Construct.artifact,
        arguments={"path": False, "content": False},
        failure="validation_failure",
    ),
    resource_binding=_bind(
        operation=_native.Construct.resource_binding,
        arguments={"key": False, "contents": False},
        failure=None,
    ),
    fixture=_bind(
        operation=_native.Construct.fixture,
        arguments={"files": False},
        failure="validation_failure",
    ),
    response_field=_bind(
        operation=_native.Construct.response_field,
        arguments={"name": False, "value": False},
        failure="validation_failure",
    ),
    response=_bind(
        operation=_native.Construct.response,
        arguments={"fields": False},
        failure="validation_failure",
    ),
    instruction=_bind(
        operation=_native.Construct.instruction,
        arguments={"skill": False, "prompt": False},
        failure="validation_failure",
    ),
    text_rule=_bind(
        operation=_native.Construct.text_rule,
        arguments={"field": False, "min_words": False, "max_words": False},
        failure="validation_failure",
    ),
    rubric=_bind(
        operation=_native.Construct.rubric,
        arguments={"expected": False, "text_rule": False},
        failure="validation_failure",
    ),
    verifier=_bind(
        operation=_native.Construct.verifier,
        arguments={
            "inputs": False,
            "files": False,
            "tools": False,
            "command": False,
            "stdin": False,
            "timeout_seconds": False,
        },
        failure="validation_failure",
    ),
    task=_bind(
        operation=_native.Construct.task,
        arguments={
            "id": False,
            "fixture": False,
            "instruction": False,
            "criterion": False,
            "allowed_files": False,
            "reference": False,
        },
        failure="validation_failure",
    ),
    experiment=_bind(
        operation=_native.Construct.experiment,
        arguments={
            "profiles": False,
            "epochs": False,
            "message_limit": False,
            "cost_limit": False,
            "time_limit": False,
            "cache": False,
        },
        failure="validation_failure",
    ),
)

experiment = SimpleNamespace(
    default=_native.Experiment.default,
    resolve=_bind(
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
    ),
)

fixture = SimpleNamespace(
    empty=_native.Fixture.empty,
    add=_bind(
        operation=_native.Fixture.add,
        arguments={"fixture": False, "file": False},
        failure="validation_failure",
    ),
    overlay=_bind(
        operation=_native.Fixture.overlay,
        arguments={"base": False, "overrides": False},
        failure=None,
    ),
    files=_bind(operation=_native.Fixture.files, arguments={"fixture": False}, failure=None),
)

grader = SimpleNamespace(
    required_names=_native.Grader.required_names,
    grade=_bind(
        operation=_native.Grader.grade,
        arguments={"task": False, "response": False, "outcome": False},
        failure="grading_failure",
    ),
    word_count=_bind(operation=_native.Grader.word_count, arguments={"text": False}, failure=None),
    trim=_bind(operation=_native.Grader.trim, arguments={"text": False}, failure=None),
)

projection = SimpleNamespace(
    case=_bind(operation=_native.Projection.case, arguments={"task": False}, failure=None),
    verifier=_bind(operation=_native.Projection.verifier, arguments={"task": False}, failure=None),
    reference=_bind(
        operation=_native.Projection.reference, arguments={"task": False}, failure=None
    ),
)


@cache
def sources() -> tuple[tuple[str, str], ...]:
    return tuple((str(name), str(contents)) for name, contents in _native.sources)


__all__ = ["case", "construct", "experiment", "fixture", "grader", "projection", "sources"]
