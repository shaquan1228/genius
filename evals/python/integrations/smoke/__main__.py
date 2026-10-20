import asyncio
import json
import sys

from evals.python import datasets, verification
from kernel import Completion, Fixture, Outcome, Task, Verification


async def validate(task: Task) -> bool:
    reference = task.reference
    result = await verification.validate_reference(task)
    scores: dict[str, bool] = {}
    if not isinstance(result.verification, Verification.HarnessError):
        candidate = (
            reference.completion.response
            if isinstance(reference.completion, Completion.Structured)
            else None
        )
        scores = dict(
            Task.grade(
                task=task,
                response=candidate,
                outcome=Outcome.create(
                    changed_files=[file.path for file in Fixture.files(fixture=reference.edits)],
                    verification=result.verification,
                ),
            )
        )

    print(
        json.dumps(
            {
                "id": task.id,
                "verification": Verification.name(status=result.verification),
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
