import asyncio
import json
import sys

from evals.python import datasets, verification
from kernel import Outcome, Task, Verification


async def validate(task: Task) -> bool:
    reference = task.reference
    result = await verification.validate_reference(task)
    scores: dict[str, bool] = {}
    if not isinstance(result.verification, Verification.HarnessError):
        scores = dict(
            Task.grade(
                task=task,
                outcome=Outcome.create(
                    changed_files=[file.path for file in reference.edits],
                    verification=result.verification,
                    response=reference.completion,
                ),
            )
        )

    print(
        json.dumps(
            {
                "id": task.id,
                "verification": Outcome.status(verification=result.verification),
                "scores": scores,
            }
        )
    )
    return isinstance(result.verification, (Verification.Passed, Verification.Unchecked)) and all(
        scores.values()
    )


async def main() -> int:
    dataset = datasets.load_dataset()
    results = [await validate(task) for task in dataset.records.values()]
    return int(not all(results))


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
