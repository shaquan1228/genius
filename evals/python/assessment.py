"""Assessment coordinates verification and grading over one dataset snapshot."""

from dataclasses import dataclass
from types import MappingProxyType

from pydantic import InstanceOf, validate_call

from evals.python import datasets, grading, verification
from evals.python.datasets import Selection
from evals.python.execution import Environment, Runtime
from evals.python.grading import Scores
from evals.python.schema import FROZEN
from evals.python.verification import VerificationResult
from kernel import Assessment as NativeAssessment
from kernel import Verification

__all__ = ["AssessmentResult", "assess"]


@dataclass(frozen=True, kw_only=True)
class AssessmentResult:
    evidence: VerificationResult
    assessment: NativeAssessment.Value

    @property
    def scores(self) -> Scores:
        return MappingProxyType(dict(NativeAssessment.scores(assessment=self.assessment)))


@validate_call(config=FROZEN)
async def assess(
    *,
    case_id: str,
    response: str,
    changed_files: tuple[str, ...],
    selection: Selection = "smoke",
    agent: InstanceOf[Environment],
    runtime: InstanceOf[Runtime],
) -> AssessmentResult:
    selection = datasets.load_dataset(selection=selection)
    result = await verification.verify_case(
        case_id=case_id, selection=selection, agent=agent, runtime=runtime
    )
    if isinstance(result.verification, Verification.HarnessError):
        raise RuntimeError(f"Verification harness error: {result.verification.detail}")
    assessment = grading.assess_case(
        case_id=case_id,
        response=response,
        changed_files=changed_files,
        verification=result.verification,
        selection=selection,
    )
    return AssessmentResult(evidence=result, assessment=assessment)
