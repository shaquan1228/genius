# Generated from compiled OCaml interfaces; do not edit.
from functools import cache
from types import SimpleNamespace

from ._bridge import checked as _checked
from ._bridge import native as _native

case = SimpleNamespace(
    make=_checked(_native.Case.make, failure="validation_failure"),
    resolve_resources=_checked(_native.Case.resolve_resources, failure="validation_failure"),
)

criterion = SimpleNamespace(
    answer=_checked(_native.Criterion.answer, failure="validation_failure"),
)

construct = SimpleNamespace(
    instruction=_checked(_native.Construct.instruction, failure="validation_failure"),
    text_rule=_checked(_native.Construct.text_rule, failure="validation_failure"),
    rubric=_checked(_native.Construct.rubric, failure="validation_failure"),
    experiment=_checked(_native.Construct.experiment, failure="validation_failure"),
)

experiment = SimpleNamespace(
    default=_native.Experiment.default,
    resolve=_checked(_native.Experiment.resolve, failure="validation_failure"),
)

fixture = SimpleNamespace(
    empty=_native.Fixture.empty,
    of_files=_checked(_native.Fixture.of_files, failure="validation_failure"),
    add=_checked(_native.Fixture.add, failure="validation_failure"),
    overlay=_native.Fixture.overlay,
    files=_native.Fixture.files,
)

grader = SimpleNamespace(
    required_names=_native.Grader.required_names,
    grade=_checked(_native.Grader.grade, failure="grading_failure"),
    word_count=_native.Grader.word_count,
    trim=_native.Grader.trim,
)

projection = SimpleNamespace(
    case=_native.Projection.case,
    verifier=_native.Projection.verifier,
    reference=_native.Projection.reference,
)

reference = SimpleNamespace(
    edits=_native.Reference.edits,
)

response = SimpleNamespace(
    empty=_native.Response.empty,
    of_fields=_checked(_native.Response.of_fields, failure="validation_failure"),
    fields=_native.Response.fields,
)

verifier = SimpleNamespace(
    valid_path=_native.Verifier.valid_path,
    make=_checked(_native.Verifier.make, failure="validation_failure"),
)

_factories = {
    "task": case.make,
    "instruction": construct.instruction,
    "text_rule": construct.text_rule,
    "rubric": construct.rubric,
    "experiment": construct.experiment,
    "fixture": fixture.of_files,
    "response": response.of_fields,
    "verifier": verifier.make,
}


@cache
def sources() -> tuple[tuple[str, str], ...]:
    return tuple((str(name), str(contents)) for name, contents in _native.sources)


__all__ = [
    "case",
    "construct",
    "criterion",
    "experiment",
    "fixture",
    "grader",
    "projection",
    "reference",
    "response",
    "sources",
    "verifier",
]
