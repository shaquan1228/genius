"""Authenticate verifier process evidence and retain immutable diagnostics."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, cast

from pydantic import BaseModel, JsonValue, ValidationError

from evals.python import FROZEN
from evals.python.execution import Completion
from kernel import Verification

VerificationStatus = Literal[
    "unchecked", "passed", "failed", "invalid_submission", "timed_out", "harness_error"
]

type Diagnostic = (
    str | int | float | bool | tuple[Diagnostic, ...] | Mapping[str, Diagnostic] | None
)


def _freeze(value: Diagnostic | JsonValue) -> Diagnostic:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _json(value: Diagnostic) -> JsonValue:
    if isinstance(value, Mapping):
        return {key: _json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json(item) for item in value]
    return value


@dataclass(frozen=True, kw_only=True)
class VerificationResult:
    verification: Verification.Value
    detail: str = ""
    metadata: Mapping[str, Diagnostic] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.verification, Verification.HarnessError) and not self.detail:
            object.__setattr__(self, "detail", self.verification.detail)
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType({key: _freeze(value) for key, value in self.metadata.items()}),
        )

    def metadata_json(self) -> dict[str, JsonValue]:
        return {key: _json(value) for key, value in self.metadata.items()}


class _Evidence(BaseModel):
    model_config = FROZEN
    marker: str
    status: VerificationStatus
    detail: str
    metadata: dict[str, JsonValue] | None = None


_STATUSES: Mapping[str, Callable[[], Verification.Value]] = {
    "passed": Verification.Passed,
    "failed": Verification.Failed,
    "invalid_submission": Verification.InvalidSubmission,
    "timed_out": Verification.TimedOut,
}


def completion(result: Completion, *, marker: str) -> VerificationResult:
    try:
        evidence = _Evidence.model_validate_json(result.stdout.strip().splitlines()[-1])
    except (ValidationError, IndexError) as error:
        return VerificationResult(
            verification=Verification.HarnessError(detail=f"Invalid verifier evidence: {error}")
        )
    if not all((evidence.marker == marker, result.returncode == 0, evidence.status != "unchecked")):
        return VerificationResult(
            verification=Verification.HarnessError(
                detail="Verifier completion was not authenticated"
            )
        )
    return VerificationResult(
        verification=(
            Verification.HarnessError(detail=evidence.detail)
            if evidence.status == "harness_error"
            else _STATUSES[evidence.status]()
        ),
        detail=evidence.detail,
        metadata=cast(Mapping[str, Diagnostic], evidence.metadata or {}),
    )
