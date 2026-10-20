# Generated from compiled OCaml interfaces; do not edit.
from ._bridge import GradingError as GradingError
from ._bridge import ValidationError as ValidationError
from ._bridge import bind as _bind
from ._bridge import named as _named
from ._bridge import native as _native

Assessment = _native.Assessment.t
Case = _named(constructor=_native.Task.case)
Criterion = _native.Task.criterion
Experiment = _named(constructor=_native.Experiment.t)
File = _named(constructor=_native.Task.file)
GradingFailure = _native.Failure.grading_failure
Instruction = _named(constructor=_native.Task.instruction)
Issue = _named(constructor=_native.Failure.issue)
Kernel = _named(constructor=_native.Kernel.t)
Outcome = _named(constructor=_native.Outcome.t)
Predicate = _native.Predicate.t
Profile = _named(constructor=_native.Profile.t)
Reference = _named(constructor=_native.Task.reference)
Rubric = _named(constructor=_native.Task.rubric)
Score = _native.Assessment.score
Task = _named(constructor=_native.Task.t)
TextRule = _named(constructor=_native.Task.text_rule)
ValidationFailure = _named(constructor=_native.Failure.validation_failure)
Value = _native.Value.t
Verification = _native.Outcome.verification
Verifier = _named(constructor=_native.Task.verifier)
GradingFailure.Value = GradingFailure
GradingFailure.VerificationHarnessError = _named(
    constructor=_native.Failure.Verification_harness_error
)
Value.Value = Value
Value.Null = _named(constructor=_native.Value.Null)
Value.Bool = _named(constructor=_native.Value.Bool)
Value.Int = _named(constructor=_native.Value.Int)
Value.Float = _named(constructor=_native.Value.Float)
Value.String = _named(constructor=_native.Value.String)
Value.List = _named(constructor=_native.Value.List)
Value.Record = _named(constructor=_native.Value.Record)
Value.strings = staticmethod(
    _bind(operation=_native.Value.strings, arguments={"values": False}, failure=None)
)
Value.get = staticmethod(
    _bind(operation=_native.Value.get, arguments={"value": False, "path": False}, failure=None)
)
Value.equal = staticmethod(
    _bind(operation=_native.Value.equal, arguments={"left": False, "right": False}, failure=None)
)
Predicate.Value = Predicate
Predicate.Present = _named(constructor=_native.Predicate.Present)
Predicate.Equals = _named(constructor=_native.Predicate.Equals)
Predicate.Within = _named(constructor=_native.Predicate.Within)
Predicate.Contains = _named(constructor=_native.Predicate.Contains)
Predicate.Words = _named(constructor=_native.Predicate.Words)
Predicate.All = _named(constructor=_native.Predicate.All)
Predicate.Any = _named(constructor=_native.Predicate.Any)
Predicate.Not = _named(constructor=_native.Predicate.Not)
Predicate.holds = staticmethod(
    _bind(
        operation=_native.Predicate.holds,
        arguments={"predicate": False, "observation": False},
        failure=None,
    )
)
Verification.Value = Verification
Verification.Unchecked = _named(constructor=_native.Outcome.Unchecked)
Verification.Passed = _named(constructor=_native.Outcome.Passed)
Verification.Failed = _named(constructor=_native.Outcome.Failed)
Verification.InvalidSubmission = _named(constructor=_native.Outcome.Invalid_submission)
Verification.TimedOut = _named(constructor=_native.Outcome.Timed_out)
Verification.HarnessError = _named(constructor=_native.Outcome.Harness_error)
Outcome.status = staticmethod(
    _bind(operation=_native.Outcome.status, arguments={"verification": False}, failure=None)
)
Outcome.create = staticmethod(
    _bind(
        operation=_native.Outcome.create,
        arguments={"response": True, "facts": True, "changed_files": False, "verification": False},
        failure=None,
    )
)
Outcome.observation = staticmethod(
    _bind(operation=_native.Outcome.observation, arguments={"outcome": False}, failure=None)
)
Assessment.Value = Assessment
Assessment.Check = _named(constructor=_native.Assessment.Check)
Assessment.All = _named(constructor=_native.Assessment.All)
Assessment.create = staticmethod(
    _bind(
        operation=_native.Assessment.create,
        arguments={"predicate": False, "observation": False},
        failure=None,
    )
)
Assessment.passed = staticmethod(
    _bind(operation=_native.Assessment.passed, arguments={"assessment": False}, failure=None)
)
Assessment.observed = staticmethod(
    _bind(operation=_native.Assessment.observed, arguments={"assessment": False}, failure=None)
)
Assessment.scores = staticmethod(
    _bind(operation=_native.Assessment.scores, arguments={"assessment": False}, failure=None)
)
Criterion.Value = Criterion
Criterion.Code = _named(constructor=_native.Task.Code)
Criterion.Answer = _named(constructor=_native.Task.Answer)
Criterion.State = _named(constructor=_native.Task.State)
Task.required_scores = _native.Task.required_scores
Task.paths = staticmethod(
    _bind(operation=_native.Task.paths, arguments={"files": False}, failure=None)
)
Task.checks = staticmethod(
    _bind(operation=_native.Task.checks, arguments={"task": False}, failure=None)
)
Task.project = staticmethod(
    _bind(operation=_native.Task.project, arguments={"task": False}, failure=None)
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
Task.condition = staticmethod(
    _bind(operation=_native.Task.condition, arguments={"criterion": False}, failure=None)
)
Task.assess = staticmethod(
    _bind(
        operation=_native.Task.assess,
        arguments={"task": False, "outcome": False},
        failure="grading_failure",
    )
)
Task.grade = staticmethod(
    _bind(
        operation=_native.Task.grade,
        arguments={"task": False, "outcome": False},
        failure="grading_failure",
    )
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
Kernel.current = _native.Kernel.current

__all__ = [
    "Assessment",
    "Case",
    "Criterion",
    "Experiment",
    "File",
    "GradingError",
    "GradingFailure",
    "Instruction",
    "Issue",
    "Kernel",
    "Outcome",
    "Predicate",
    "Profile",
    "Reference",
    "Rubric",
    "Score",
    "Task",
    "TextRule",
    "ValidationError",
    "ValidationFailure",
    "Value",
    "Verification",
    "Verifier",
]
