# Generated from compiled OCaml interfaces; do not edit.
from ._bridge import GradingError as GradingError
from ._bridge import ValidationError as ValidationError
from ._bridge import named as _named
from ._bridge import native as _native
from ._operations import construct as _construct

Artifact = _named(constructor=_native.artifact)
Case = _named(constructor=_native.case)
Completion = _native.completion
Content = _native.content
Criterion = _native.criterion
Experiment = _named(constructor=_native.experiment)
File = _named(constructor=_native.file)
Fixture = _native.fixture
GradingFailure = _native.grading_failure
Instruction = _named(constructor=_native.instruction)
Outcome = _named(constructor=_native.outcome)
Profile = _named(constructor=_native.profile)
Reference = _named(constructor=_native.reference)
ResourceBinding = _named(constructor=_native.resource_binding)
Response = _named(constructor=_native.response)
ResponseField = _named(constructor=_native.response_field)
ResponseValue = _native.response_value
Rubric = _named(constructor=_native.rubric)
Score = _native.score
Task = _named(constructor=_native.task)
TextRule = _named(constructor=_native.text_rule)
ValidationCode = _native.validation_code
ValidationFailure = _named(constructor=_native.validation_failure)
ValidationIssue = _named(constructor=_native.validation_issue)
Verification = _native.verification
Verifier = _named(constructor=_native.verifier)

ResponseValue.Value = ResponseValue
Content.Value = Content
Criterion.Value = Criterion
Completion.Value = Completion
Verification.Value = Verification
ValidationCode.Value = ValidationCode
GradingFailure.Value = GradingFailure
ResponseValue.String = _named(constructor=_native.String)
ResponseValue.Bool = _named(constructor=_native.Bool)
Content.Inline = _named(constructor=_native.Inline)
Content.Resource = _named(constructor=_native.Resource)
Criterion.Code = _named(constructor=_native.Code)
Criterion.Answer = _named(constructor=_native.Answer)
Completion.Plain = _named(constructor=_native.Plain)
Completion.Structured = _named(constructor=_native.Structured)
Verification.Unchecked = _named(constructor=_native.Unchecked)
Verification.Passed = _named(constructor=_native.Passed)
Verification.Failed = _named(constructor=_native.Failed)
Verification.InvalidSubmission = _named(constructor=_native.Invalid_submission)
Verification.TimedOut = _named(constructor=_native.Timed_out)
Verification.HarnessError = _named(constructor=_native.Harness_error)
ValidationCode.InvalidIdentity = _named(constructor=_native.Invalid_identity)
ValidationCode.InvalidPath = _named(constructor=_native.Invalid_path)
ValidationCode.DuplicatePath = _named(constructor=_native.Duplicate_path)
ValidationCode.EmptyInputs = _named(constructor=_native.Empty_inputs)
ValidationCode.OverlappingPaths = _named(constructor=_native.Overlapping_paths)
ValidationCode.InvalidCommand = _named(constructor=_native.Invalid_command)
ValidationCode.NonpositiveTimeout = _named(constructor=_native.Nonpositive_timeout)
ValidationCode.InvalidResponseField = _named(constructor=_native.Invalid_response_field)
ValidationCode.InvalidTextRule = _named(constructor=_native.Invalid_text_rule)
ValidationCode.OverlappingTextField = _named(constructor=_native.Overlapping_text_field)
ValidationCode.EmptyAnswer = _named(constructor=_native.Empty_answer)
ValidationCode.MissingFixtureInputs = _named(constructor=_native.Missing_fixture_inputs)
ValidationCode.ArtifactOverlap = _named(constructor=_native.Artifact_overlap)
ValidationCode.ReferenceOutsideScope = _named(constructor=_native.Reference_outside_scope)
ValidationCode.InvalidExperimentSetting = _named(constructor=_native.Invalid_experiment_setting)
ValidationCode.MissingResource = _named(constructor=_native.Missing_resource)
GradingFailure.VerificationHarnessError = _named(constructor=_native.Verification_harness_error)

File.create = staticmethod(_construct.file)
Artifact.create = staticmethod(_construct.artifact)
ResourceBinding.create = staticmethod(_construct.resource_binding)
Fixture.create = staticmethod(_construct.fixture)
ResponseField.create = staticmethod(_construct.response_field)
Response.create = staticmethod(_construct.response)
Instruction.create = staticmethod(_construct.instruction)
TextRule.create = staticmethod(_construct.text_rule)
Rubric.create = staticmethod(_construct.rubric)
Verifier.create = staticmethod(_construct.verifier)
Task.create = staticmethod(_construct.task)
Experiment.create = staticmethod(_construct.experiment)

__all__ = [
    "Artifact",
    "Case",
    "Completion",
    "Content",
    "Criterion",
    "Experiment",
    "File",
    "Fixture",
    "GradingError",
    "GradingFailure",
    "Instruction",
    "Outcome",
    "Profile",
    "Reference",
    "ResourceBinding",
    "Response",
    "ResponseField",
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
