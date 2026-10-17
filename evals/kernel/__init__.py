# Generated from compiled OCaml interfaces; do not edit.
"""Native domain types, with alternatives attached to their owners."""

from ._bridge import InvalidArgument as InvalidArgument
from ._bridge import native as _native

Case = _native.case
Completion = _native.completion
Content = _native.content
Criterion = _native.criterion
Experiment = _native.experiment
Fixture = _native.fixture
Instruction = _native.instruction
Outcome = _native.outcome
Profile = _native.profile
Reference = _native.reference
Response = _native.response
ResponseValue = _native.response_value
Rubric = _native.rubric
Score = _native.score
Task = _native.task
TextRule = _native.text_rule
Verification = _native.verification
Verifier = _native.verifier

ResponseValue.Value = ResponseValue
Content.Value = Content
Criterion.Value = Criterion
Completion.Value = Completion
Verification.Value = Verification
ResponseValue.String = _native.String
ResponseValue.Bool = _native.Bool
Content.Inline = _native.Inline
Content.Resource = _native.Resource
Criterion.Code = _native.Code
Criterion.Answer = _native.Answer
Completion.Plain = _native.Plain
Completion.Structured = _native.Structured
Verification.Unchecked = _native.Unchecked
Verification.Passed = _native.Passed
Verification.Failed = _native.Failed
Verification.InvalidSubmission = _native.Invalid_submission
Verification.TimedOut = _native.Timed_out
Verification.HarnessError = _native.Harness_error

__all__ = [
    "Case",
    "Completion",
    "Content",
    "Criterion",
    "Experiment",
    "Fixture",
    "Instruction",
    "InvalidArgument",
    "Outcome",
    "Profile",
    "Reference",
    "Response",
    "ResponseValue",
    "Rubric",
    "Score",
    "Task",
    "TextRule",
    "Verification",
    "Verifier",
]
