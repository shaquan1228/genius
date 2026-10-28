import asyncio
import json
import sys

from kernel import Task

from evals.python import datasets, verification


async def validate(task: Task) -> bool:
    result = await verification.validate_reference(task)
    scores: dict[str, bool] = {}
    if result.verification.status != "harness_error":
        scores = dict(task.grade_reference(verification=result.verification))

    print(
        json.dumps(
            {
                "id": task.id,
                "verification": result.verification.status,
                "scores": scores,
            }
        )
    )
    return result.verification.status in {"passed", "unchecked"} and all(scores.values())


async def main() -> int:
    dataset = datasets.load_dataset()
    results = [await validate(record.task) for record in dataset.records.values()]
    return int(not all(results))


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
