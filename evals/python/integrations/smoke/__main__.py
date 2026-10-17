import asyncio
import json
import sys
from typing import assert_never

from evals.python import datasets, grading, verification
from evals.python.datasets import Dataset
from evals.python.grading import Scores
from kernel import Case, Completion, Verification
from kernel._operations import fixture as fixture_ops


def response(completion: Completion.Value) -> str:
    match completion:
        case Completion.Plain():
            return completion[0]
        case Completion.Structured():
            return json.dumps({name: value[0] for name, value in completion[0]})
        case _ as unreachable:
            assert_never(unreachable)


async def validate(case: Case, *, dataset: Dataset) -> bool:
    reference = datasets.get_reference(case_id=case.id, selection=dataset)
    result = await verification.validate_reference(case_id=case.id, selection=dataset)
    scores: Scores = {}
    if not isinstance(result.verification, Verification.HarnessError):
        scores = grading.score_case(
            case_id=case.id,
            response=response(reference.completion),
            changed_files=tuple(
                f"workspace/{name}" for name, _ in fixture_ops.files(reference.edits)
            ),
            verification=result.verification,
            selection=dataset,
        )
    print(
        json.dumps(
            {
                "id": case.id,
                "verification": type(result.verification).__name__.lower(),
                "scores": dict(scores),
            }
        )
    )
    return isinstance(result.verification, (Verification.Passed, Verification.Unchecked)) and all(
        scores.values()
    )


async def main() -> int:
    dataset = datasets.load_dataset()
    results = [
        await validate(case, dataset=dataset) for case in datasets.list_cases(selection=dataset)
    ]
    return int(not all(results))


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
