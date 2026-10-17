# Generated from compiled OCaml interfaces; do not edit.
from ._bridge import bind as _bind
from ._bridge import native as _native

required_names = _native.Grader.required_names
grade = _bind(
    operation=_native.Grader.grade,
    arguments={"task": False, "response": False, "outcome": False},
    failure="grading_failure",
)
word_count = _bind(operation=_native.Grader.word_count, arguments={"text": False}, failure=None)
trim = _bind(operation=_native.Grader.trim, arguments={"text": False}, failure=None)

__all__ = ["grade", "required_names", "trim", "word_count"]
