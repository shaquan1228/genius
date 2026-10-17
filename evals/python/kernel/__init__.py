# Generated from compiled OCaml interfaces; do not edit.
from ._bridge import GradingError as GradingError
from ._bridge import ValidationError as ValidationError
from ._bridge import bind as _bind
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
Kernel = _named(constructor=_native.Kernel.t)
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
File.create = staticmethod(
    _bind(
        operation=_native.File.create,
        arguments={"path": False, "contents": False},
        failure="validation_failure",
    )
)
File.valid_path = staticmethod(
    _bind(operation=_native.File.valid_path, arguments={"path": False}, failure=None)
)
File.path_issues = staticmethod(
    _bind(
        operation=_native.File.path_issues, arguments={"field": False, "paths": False}, failure=None
    )
)
Fixture.create = staticmethod(
    _bind(
        operation=_native.Fixture.create, arguments={"files": False}, failure="validation_failure"
    )
)
Fixture.empty = _native.Fixture.empty
Fixture.add = staticmethod(
    _bind(
        operation=_native.Fixture.add,
        arguments={"fixture": False, "file": False},
        failure="validation_failure",
    )
)
Fixture.overlay = staticmethod(
    _bind(
        operation=_native.Fixture.overlay,
        arguments={"base": False, "overrides": False},
        failure=None,
    )
)
Fixture.files = staticmethod(
    _bind(operation=_native.Fixture.files, arguments={"fixture": False}, failure=None)
)
ResponseValue.Value = ResponseValue
ResponseValue.String = _named(constructor=_native.Response_value.String)
ResponseValue.String._default_type = ()
ResponseValue.Bool = _named(constructor=_native.Response_value.Bool)
ResponseValue.Bool._default_type = ()
ResponseValue.create = staticmethod(
    _bind(
        operation=_native.Response_value.create,
        arguments={"string": True, "bool": True},
        failure="validation_failure",
    )
)
ResponseField.create = staticmethod(
    _bind(
        operation=_native.Response_field.create,
        arguments={"name": False, "value": False},
        failure="validation_failure",
    )
)
Response.create = staticmethod(
    _bind(
        operation=_native.Response.create, arguments={"fields": False}, failure="validation_failure"
    )
)
Response.empty = _native.Response.empty
ResourceBinding.create = staticmethod(
    _bind(
        operation=_native.Resource_binding.create,
        arguments={"key": False, "contents": False},
        failure=None,
    )
)
Content.Value = Content
Content.Inline = _named(constructor=_native.Content.Inline)
Content.Inline._default_type = ()
Content.Resource = _named(constructor=_native.Content.Resource)
Content.Resource._default_type = ()
Content.create = staticmethod(
    _bind(
        operation=_native.Content.create,
        arguments={"inline": True, "resource": True},
        failure="validation_failure",
    )
)
Artifact.create = staticmethod(
    _bind(
        operation=_native.Artifact.create,
        arguments={"path": False, "content": False},
        failure="validation_failure",
    )
)
Artifact.resolve = staticmethod(
    _bind(
        operation=_native.Artifact.resolve,
        arguments={"artifact": False, "resources": False},
        failure="validation_failure",
    )
)
Instruction.create = staticmethod(
    _bind(
        operation=_native.Instruction.create,
        arguments={"skill": False, "prompt": False},
        failure="validation_failure",
    )
)
Instruction.valid_name = staticmethod(
    _bind(operation=_native.Instruction.valid_name, arguments={"name": False}, failure=None)
)
TextRule.create = staticmethod(
    _bind(
        operation=_native.Text_rule.create,
        arguments={"field": False, "min_words": False, "max_words": False},
        failure="validation_failure",
    )
)
TextRule.word_count = staticmethod(
    _bind(operation=_native.Text_rule.word_count, arguments={"text": False}, failure=None)
)
Rubric.create = staticmethod(
    _bind(
        operation=_native.Rubric.create,
        arguments={"expected": False, "text_rule": False},
        failure="validation_failure",
    )
)
Verifier.create = staticmethod(
    _bind(
        operation=_native.Verifier.create,
        arguments={
            "inputs": False,
            "files": False,
            "tools": False,
            "command": False,
            "stdin": False,
            "timeout_seconds": False,
        },
        failure="validation_failure",
    )
)
Verifier.resolve_resources = staticmethod(
    _bind(
        operation=_native.Verifier.resolve_resources,
        arguments={"verifier": False, "resources": False},
        failure="validation_failure",
    )
)
Criterion.Value = Criterion
Criterion.Code = _named(constructor=_native.Criterion.Code)
Criterion.Code._default_type = ()
Criterion.Answer = _named(constructor=_native.Criterion.Answer)
Criterion.Answer._default_type = ()
Criterion.create = staticmethod(
    _bind(
        operation=_native.Criterion.create,
        arguments={"code": True, "answer": True},
        failure="validation_failure",
    )
)
Completion.Value = Completion
Completion.Plain = _named(constructor=_native.Completion.Plain)
Completion.Plain._default_type = ()
Completion.Structured = _named(constructor=_native.Completion.Structured)
Completion.Structured._default_type = ()
Completion.create = staticmethod(
    _bind(
        operation=_native.Completion.create,
        arguments={"plain": True, "structured": True},
        failure="validation_failure",
    )
)
Completion.trim = staticmethod(
    _bind(operation=_native.Completion.trim, arguments={"text": False}, failure=None)
)
Reference.create = staticmethod(
    _bind(
        operation=_native.Reference.create,
        arguments={"edits": False, "completion": False},
        failure=None,
    )
)
Verification.Value = Verification
Verification.Unchecked = _named(constructor=_native.Verification.Unchecked)
Verification.Passed = _named(constructor=_native.Verification.Passed)
Verification.Failed = _named(constructor=_native.Verification.Failed)
Verification.InvalidSubmission = _named(constructor=_native.Verification.Invalid_submission)
Verification.TimedOut = _named(constructor=_native.Verification.Timed_out)
Verification.HarnessError = _named(constructor=_native.Verification.Harness_error)
Outcome.create = staticmethod(
    _bind(
        operation=_native.Outcome.create,
        arguments={"changed_files": False, "verification": False},
        failure=None,
    )
)
GradingFailure.Value = GradingFailure
GradingFailure.VerificationHarnessError = _named(
    constructor=_native.Grading_failure.Verification_harness_error
)
Task.create = staticmethod(
    _bind(
        operation=_native.Task.create,
        arguments={
            "id": False,
            "fixture": False,
            "instruction": False,
            "criterion": False,
            "allowed_files": False,
            "reference": False,
        },
        failure="validation_failure",
    )
)
Task.resolve_resources = staticmethod(
    _bind(
        operation=_native.Task.resolve_resources,
        arguments={"task": False, "resources": False},
        failure="validation_failure",
    )
)
Task.required_scores = _native.Task.required_scores
Task.grade = staticmethod(
    _bind(
        operation=_native.Task.grade,
        arguments={"task": False, "response": False, "outcome": False},
        failure="grading_failure",
    )
)
Task.verifier = staticmethod(
    _bind(operation=_native.Task.verifier, arguments={"task": False}, failure=None)
)
Profile.create = staticmethod(
    _bind(
        operation=_native.Profile.create,
        arguments={"name": False, "preamble": False, "instructions": False},
        failure=None,
    )
)
Experiment.default = _native.Experiment.default
Experiment.resolve = staticmethod(
    _bind(
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
)
Experiment.create = staticmethod(
    _bind(
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
)
Case.create = staticmethod(
    _bind(operation=_native.Case.create, arguments={"task": False}, failure=None)
)
Kernel.current = _native.Kernel.current

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
    "Kernel",
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
