# Generated from compiled OCaml interfaces; do not edit.
from ._bridge import GradingError as GradingError
from ._bridge import ValidationError as ValidationError
from ._bridge import bind as _bind
from ._bridge import named as _named
from ._bridge import native as _native

Artifact = _named(constructor=_native.Artifact.t)
Assessment = _native.Assessment.t
Case = _named(constructor=_native.Case.t)
Comparison = _named(constructor=_native.Comparison.t)
Completion = _native.Completion.t
Content = _native.Content.t
Criterion = _native.Criterion.t
Evidence = _native.Assessment.evidence
Experiment = _named(constructor=_native.Experiment.t)
FieldComparison = _named(constructor=_native.Response_comparison.field_comparison)
File = _named(constructor=_native.File.t)
Fixture = _native.Fixture.t
FixtureComparison = _named(constructor=_native.Fixture_comparison.t)
GradingFailure = _native.Grading_failure.t
Instruction = _named(constructor=_native.Instruction.t)
Kernel = _named(constructor=_native.Kernel.t)
Outcome = _named(constructor=_native.Outcome.t)
Profile = _named(constructor=_native.Profile.t)
Reference = _named(constructor=_native.Reference.t)
ResourceBinding = _named(constructor=_native.Resource_binding.t)
Response = _named(constructor=_native.Response.t)
ResponseComparison = _named(constructor=_native.Response_comparison.t)
ResponseField = _named(constructor=_native.Response_field.t)
ResponseValue = _native.Response_value.t
Rubric = _named(constructor=_native.Rubric.t)
Score = _native.Score.t
Task = _named(constructor=_native.Task.t)
TaskComparison = _named(constructor=_native.Task_comparison.t)
TextRule = _named(constructor=_native.Text_rule.t)
ValidationCode = _native.Validation_code.t
ValidationFailure = _named(constructor=_native.Validation_failure.t)
ValidationIssue = _named(constructor=_native.Validation_issue.t)
Verification = _native.Verification.t
Verifier = _named(constructor=_native.Verifier.t)
Comparison.create = staticmethod(
    _bind(operation=_native.Comparison.create, arguments={"fields": False}, failure=None)
)
Comparison.combine = staticmethod(
    _bind(operation=_native.Comparison.combine, arguments={"comparisons": False}, failure=None)
)
GradingFailure.Value = GradingFailure
GradingFailure.VerificationHarnessError = _named(
    constructor=_native.Grading_failure.Verification_harness_error
)
Profile.create = staticmethod(
    _bind(
        operation=_native.Profile.create,
        arguments={"name": False, "preamble": False, "instructions": False},
        failure=None,
    )
)
Profile.compare = staticmethod(
    _bind(
        operation=_native.Profile.compare, arguments={"before": False, "after": False}, failure=None
    )
)
ResourceBinding.create = staticmethod(
    _bind(
        operation=_native.Resource_binding.create,
        arguments={"key": False, "contents": False},
        failure=None,
    )
)
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
Verification.Value = Verification
Verification.Unchecked = _named(constructor=_native.Verification.Unchecked)
Verification.Passed = _named(constructor=_native.Verification.Passed)
Verification.Failed = _named(constructor=_native.Verification.Failed)
Verification.InvalidSubmission = _named(constructor=_native.Verification.Invalid_submission)
Verification.TimedOut = _named(constructor=_native.Verification.Timed_out)
Verification.HarnessError = _named(constructor=_native.Verification.Harness_error)
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
ResponseComparison.create = staticmethod(
    _bind(
        operation=_native.Response_comparison.create,
        arguments={"before": False, "after": False},
        failure=None,
    )
)
Response.create = staticmethod(
    _bind(
        operation=_native.Response.create, arguments={"fields": False}, failure="validation_failure"
    )
)
Response.empty = _native.Response.empty
Response.compare = staticmethod(
    _bind(
        operation=_native.Response.compare,
        arguments={"before": False, "after": False},
        failure=None,
    )
)
Outcome.create = staticmethod(
    _bind(
        operation=_native.Outcome.create,
        arguments={"changed_files": False, "verification": False},
        failure=None,
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
Instruction.compare = staticmethod(
    _bind(
        operation=_native.Instruction.compare,
        arguments={"before": False, "after": False},
        failure=None,
    )
)
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
Completion.compare = staticmethod(
    _bind(
        operation=_native.Completion.compare,
        arguments={"before": False, "after": False},
        failure=None,
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
FixtureComparison.create = staticmethod(
    _bind(
        operation=_native.Fixture_comparison.create,
        arguments={"before": False, "after": False},
        failure=None,
    )
)
Kernel.current = _native.Kernel.current
TaskComparison.create = staticmethod(
    _bind(
        operation=_native.Task_comparison.create,
        arguments={
            "id": False,
            "fixture": False,
            "instruction": False,
            "criterion": False,
            "allowed_files": False,
            "reference": False,
        },
        failure=None,
    )
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
Verifier.compare = staticmethod(
    _bind(
        operation=_native.Verifier.compare,
        arguments={"before": False, "after": False},
        failure=None,
    )
)
Rubric.create = staticmethod(
    _bind(
        operation=_native.Rubric.create,
        arguments={"expected": False, "text_rule": False},
        failure="validation_failure",
    )
)
Rubric.compare = staticmethod(
    _bind(
        operation=_native.Rubric.compare, arguments={"before": False, "after": False}, failure=None
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
Fixture.compare = staticmethod(
    _bind(
        operation=_native.Fixture.compare, arguments={"before": False, "after": False}, failure=None
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
Criterion.compare = staticmethod(
    _bind(
        operation=_native.Criterion.compare,
        arguments={"before": False, "after": False},
        failure=None,
    )
)
Reference.create = staticmethod(
    _bind(
        operation=_native.Reference.create,
        arguments={"edits": False, "completion": False},
        failure=None,
    )
)
Reference.compare = staticmethod(
    _bind(
        operation=_native.Reference.compare,
        arguments={"before": False, "after": False},
        failure=None,
    )
)
Evidence.Value = Evidence
Evidence.Present = _named(constructor=_native.Assessment.Present)
Evidence.Present._default_type = ()
Evidence.Field = _named(constructor=_native.Assessment.Field)
Evidence.Field._default_type = ()
Evidence.Text = _named(constructor=_native.Assessment.Text)
Evidence.Text._default_type = ()
Evidence.Verified = _named(constructor=_native.Assessment.Verified)
Evidence.Verified._default_type = ()
Evidence.Scope = _named(constructor=_native.Assessment.Scope)
Evidence.Scope._default_type = ()
Assessment.Value = Assessment
Assessment.Check = _named(constructor=_native.Assessment.Check)
Assessment.Check._default_type = ()
Assessment.All = _named(constructor=_native.Assessment.All)
Assessment.All._default_type = ()
Assessment.present = staticmethod(
    _bind(operation=_native.Assessment.present, arguments={"response": False}, failure=None)
)
Assessment.field = staticmethod(
    _bind(operation=_native.Assessment.field, arguments={"comparison": False}, failure=None)
)
Assessment.text = staticmethod(
    _bind(
        operation=_native.Assessment.text, arguments={"rule": False, "value": False}, failure=None
    )
)
Assessment.verified = staticmethod(
    _bind(
        operation=_native.Assessment.verified,
        arguments={"verification": False},
        failure="grading_failure",
    )
)
Assessment.scope = staticmethod(
    _bind(
        operation=_native.Assessment.scope,
        arguments={"allowed_files": False, "changed_files": False},
        failure=None,
    )
)
Assessment.all = staticmethod(
    _bind(
        operation=_native.Assessment.all, arguments={"checks": False}, failure="validation_failure"
    )
)
Assessment.rubric = staticmethod(
    _bind(
        operation=_native.Assessment.rubric,
        arguments={"rubric": False, "response": False},
        failure=None,
    )
)
Assessment.criterion = staticmethod(
    _bind(
        operation=_native.Assessment.criterion,
        arguments={"criterion": False, "response": False, "verification": False},
        failure="grading_failure",
    )
)
Assessment.passed = staticmethod(
    _bind(operation=_native.Assessment.passed, arguments={"assessment": False}, failure=None)
)
Assessment.word_count = staticmethod(
    _bind(operation=_native.Assessment.word_count, arguments={"value": False}, failure=None)
)
Assessment.unexpected_files = staticmethod(
    _bind(
        operation=_native.Assessment.unexpected_files, arguments={"assessment": False}, failure=None
    )
)
Assessment.scores = staticmethod(
    _bind(operation=_native.Assessment.scores, arguments={"assessment": False}, failure=None)
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
Task.compare = staticmethod(
    _bind(operation=_native.Task.compare, arguments={"before": False, "after": False}, failure=None)
)
Task.assess = staticmethod(
    _bind(
        operation=_native.Task.assess,
        arguments={"task": False, "response": False, "outcome": False},
        failure="grading_failure",
    )
)
Case.create = staticmethod(
    _bind(operation=_native.Case.create, arguments={"task": False}, failure=None)
)

__all__ = [
    "Artifact",
    "Assessment",
    "Case",
    "Comparison",
    "Completion",
    "Content",
    "Criterion",
    "Evidence",
    "Experiment",
    "FieldComparison",
    "File",
    "Fixture",
    "FixtureComparison",
    "GradingError",
    "GradingFailure",
    "Instruction",
    "Kernel",
    "Outcome",
    "Profile",
    "Reference",
    "ResourceBinding",
    "Response",
    "ResponseComparison",
    "ResponseField",
    "ResponseValue",
    "Rubric",
    "Score",
    "Task",
    "TaskComparison",
    "TextRule",
    "ValidationCode",
    "ValidationError",
    "ValidationFailure",
    "ValidationIssue",
    "Verification",
    "Verifier",
]
