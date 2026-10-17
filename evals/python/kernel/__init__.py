# Generated from compiled OCaml interfaces; do not edit.
from functools import cache

from . import artifact as artifact
from . import case as case
from . import completion as completion
from . import content as content
from . import criterion as criterion
from . import experiment as experiment
from . import file as file
from . import fixture as fixture
from . import grader as grader
from . import instruction as instruction
from . import outcome as outcome
from . import profile as profile
from . import projection as projection
from . import reference as reference
from . import resource_binding as resource_binding
from . import response as response
from . import response_field as response_field
from . import response_value as response_value
from . import rubric as rubric
from . import task as task
from . import text_rule as text_rule
from . import verifier as verifier
from ._bridge import GradingError as GradingError
from ._bridge import ValidationError as ValidationError
from ._bridge import named as _named
from ._bridge import native as _native

Artifact = _named(constructor=_native.Artifact.t)
Case = _named(constructor=_native.Case.t)
Completion = _native.Completion.t
Content = _native.Content.t
Criterion = _native.Criterion.t
Experiment = _named(constructor=_native.Experiment.t)
File = _named(constructor=_native.File.t)
Fixture = _native.Fixture.t
GradingFailure = _native.Grading_failure.t
Instruction = _named(constructor=_native.Instruction.t)
Outcome = _named(constructor=_native.Outcome.t)
Profile = _named(constructor=_native.Profile.t)
Reference = _named(constructor=_native.Reference.t)
ResourceBinding = _named(constructor=_native.Resource_binding.t)
Response = _named(constructor=_native.Response.t)
ResponseField = _named(constructor=_native.Response_field.t)
ResponseValue = _native.Response_value.t
Rubric = _named(constructor=_native.Rubric.t)
Score = _native.Score.t
Task = _named(constructor=_native.Task.t)
TextRule = _named(constructor=_native.Text_rule.t)
ValidationCode = _native.Validation_code.t
ValidationFailure = _named(constructor=_native.Validation_failure.t)
ValidationIssue = _named(constructor=_native.Validation_issue.t)
Verification = _native.Verification.t
Verifier = _named(constructor=_native.Verifier.t)
ValidationCode.Value = ValidationCode
ValidationCode.InvalidIdentity = _named(constructor=_native.Validation_code.Invalid_identity)
ValidationCode.InvalidPath = _named(constructor=_native.Validation_code.Invalid_path)
ValidationCode.DuplicatePath = _named(constructor=_native.Validation_code.Duplicate_path)
ValidationCode.EmptyInputs = _named(constructor=_native.Validation_code.Empty_inputs)
ValidationCode.OverlappingPaths = _named(constructor=_native.Validation_code.Overlapping_paths)
ValidationCode.InvalidCommand = _named(constructor=_native.Validation_code.Invalid_command)
ValidationCode.NonpositiveTimeout = _named(constructor=_native.Validation_code.Nonpositive_timeout)
ValidationCode.InvalidResponseField = _named(
    constructor=_native.Validation_code.Invalid_response_field
)
ValidationCode.InvalidTextRule = _named(constructor=_native.Validation_code.Invalid_text_rule)
ValidationCode.OverlappingTextField = _named(
    constructor=_native.Validation_code.Overlapping_text_field
)
ValidationCode.EmptyAnswer = _named(constructor=_native.Validation_code.Empty_answer)
ValidationCode.MissingFixtureInputs = _named(
    constructor=_native.Validation_code.Missing_fixture_inputs
)
ValidationCode.ArtifactOverlap = _named(constructor=_native.Validation_code.Artifact_overlap)
ValidationCode.ReferenceOutsideScope = _named(
    constructor=_native.Validation_code.Reference_outside_scope
)
ValidationCode.InvalidExperimentSetting = _named(
    constructor=_native.Validation_code.Invalid_experiment_setting
)
ValidationCode.MissingResource = _named(constructor=_native.Validation_code.Missing_resource)
ValidationCode.InvalidAlternative = _named(constructor=_native.Validation_code.Invalid_alternative)
File.create = staticmethod(file.create)
Fixture.create = staticmethod(fixture.create)
ResponseValue.Value = ResponseValue
ResponseValue.String = _named(constructor=_native.Response_value.String)
ResponseValue.String._default_type = ()
ResponseValue.Bool = _named(constructor=_native.Response_value.Bool)
ResponseValue.Bool._default_type = ()
ResponseValue.create = staticmethod(response_value.create)
ResponseField.create = staticmethod(response_field.create)
Response.create = staticmethod(response.create)
ResourceBinding.create = staticmethod(resource_binding.create)
Content.Value = Content
Content.Inline = _named(constructor=_native.Content.Inline)
Content.Inline._default_type = ()
Content.Resource = _named(constructor=_native.Content.Resource)
Content.Resource._default_type = ()
Content.create = staticmethod(content.create)
Artifact.create = staticmethod(artifact.create)
Instruction.create = staticmethod(instruction.create)
TextRule.create = staticmethod(text_rule.create)
Rubric.create = staticmethod(rubric.create)
Verifier.create = staticmethod(verifier.create)
Criterion.Value = Criterion
Criterion.Code = _named(constructor=_native.Criterion.Code)
Criterion.Code._default_type = ()
Criterion.Answer = _named(constructor=_native.Criterion.Answer)
Criterion.Answer._default_type = ()
Criterion.create = staticmethod(criterion.create)
Completion.Value = Completion
Completion.Plain = _named(constructor=_native.Completion.Plain)
Completion.Plain._default_type = ()
Completion.Structured = _named(constructor=_native.Completion.Structured)
Completion.Structured._default_type = ()
Completion.create = staticmethod(completion.create)
Reference.create = staticmethod(reference.create)
Task.create = staticmethod(task.create)
Verification.Value = Verification
Verification.Unchecked = _named(constructor=_native.Verification.Unchecked)
Verification.Passed = _named(constructor=_native.Verification.Passed)
Verification.Failed = _named(constructor=_native.Verification.Failed)
Verification.InvalidSubmission = _named(constructor=_native.Verification.Invalid_submission)
Verification.TimedOut = _named(constructor=_native.Verification.Timed_out)
Verification.HarnessError = _named(constructor=_native.Verification.Harness_error)
Outcome.create = staticmethod(outcome.create)
GradingFailure.Value = GradingFailure
GradingFailure.VerificationHarnessError = _named(
    constructor=_native.Grading_failure.Verification_harness_error
)
Profile.create = staticmethod(profile.create)
Experiment.create = staticmethod(experiment.create)
Case.create = staticmethod(case.create)


@cache
def sources() -> tuple[tuple[str, str], ...]:
    return tuple((str(name), str(contents)) for name, contents in _native.sources)


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
    "artifact",
    "case",
    "completion",
    "content",
    "criterion",
    "experiment",
    "file",
    "fixture",
    "grader",
    "instruction",
    "outcome",
    "profile",
    "projection",
    "reference",
    "resource_binding",
    "response",
    "response_field",
    "response_value",
    "rubric",
    "sources",
    "task",
    "text_rule",
    "verifier",
]
