# Generated from compiled OCaml interfaces; do not edit.
"""Native domain types, with alternatives attached to their owners."""

from ._bridge import GradingError as GradingError
from ._bridge import InvalidArgument as InvalidArgument
from ._bridge import ValidationError as ValidationError
from ._bridge import native as _native
from ._operations import _factories

Case = _native.case
Completion = _native.completion
Content = _native.content
Criterion = _native.criterion
Experiment = _native.experiment
Fixture = _native.fixture
GradingFailure = _native.grading_failure
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
ValidationCode = _native.validation_code
ValidationFailure = _native.validation_failure
ValidationIssue = _native.validation_issue
Verification = _native.verification
Verifier = _native.verifier

ResponseValue.Value = ResponseValue
Content.Value = Content
Criterion.Value = Criterion
Completion.Value = Completion
Verification.Value = Verification
ValidationCode.Value = ValidationCode
GradingFailure.Value = GradingFailure
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
ValidationCode.InvalidIdentity = _native.Invalid_identity
ValidationCode.InvalidPath = _native.Invalid_path
ValidationCode.DuplicatePath = _native.Duplicate_path
ValidationCode.EmptyInputs = _native.Empty_inputs
ValidationCode.OverlappingPaths = _native.Overlapping_paths
ValidationCode.InvalidCommand = _native.Invalid_command
ValidationCode.NonpositiveTimeout = _native.Nonpositive_timeout
ValidationCode.InvalidResponseField = _native.Invalid_response_field
ValidationCode.InvalidTextRule = _native.Invalid_text_rule
ValidationCode.OverlappingTextField = _native.Overlapping_text_field
ValidationCode.EmptyAnswer = _native.Empty_answer
ValidationCode.MissingFixtureInputs = _native.Missing_fixture_inputs
ValidationCode.ArtifactOverlap = _native.Artifact_overlap
ValidationCode.ReferenceOutsideScope = _native.Reference_outside_scope
ValidationCode.InvalidExperimentSetting = _native.Invalid_experiment_setting
ValidationCode.MissingResource = _native.Missing_resource
GradingFailure.VerificationHarnessError = _native.Verification_harness_error

Task.create = staticmethod(_factories["task"])
Instruction.create = staticmethod(_factories["instruction"])
TextRule.create = staticmethod(_factories["text_rule"])
Rubric.create = staticmethod(_factories["rubric"])
Experiment.create = staticmethod(_factories["experiment"])
Fixture.create = staticmethod(_factories["fixture"])
Response.create = staticmethod(_factories["response"])
Verifier.create = staticmethod(_factories["verifier"])

__all__ = [
    "Case",
    "Completion",
    "Content",
    "Criterion",
    "Experiment",
    "Fixture",
    "GradingError",
    "GradingFailure",
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
    "ValidationCode",
    "ValidationError",
    "ValidationFailure",
    "ValidationIssue",
    "Verification",
    "Verifier",
]
