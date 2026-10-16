"""Temporary aliases for callers migrating to the public operation namespace."""

from evals.python._kernel import (
    FROZEN,
    Attributes,
    Case,
    DatasetInfo,
    ExecutableChecks,
    Experiment,
    FileName,
    Files,
    ProfileSpec,
    Reference,
    Verification,
    VerificationStatus,
)
from evals.python.commands import ExperimentSettings as RunOverrides
from evals.python.commands import GradeCase as GradeRequest
from evals.python.transport import VERSION, Program, Sources

__all__ = [
    "FROZEN",
    "VERSION",
    "Attributes",
    "Case",
    "DatasetInfo",
    "ExecutableChecks",
    "Experiment",
    "FileName",
    "Files",
    "GradeRequest",
    "ProfileSpec",
    "Program",
    "Reference",
    "RunOverrides",
    "Sources",
    "Verification",
    "VerificationStatus",
]
