"""Inspect pinned datasets and validate reference code without model calls."""

import argparse
import asyncio
import json
from collections.abc import Sequence

from kernel import Task

from evals.python import datasets, verification


def benchmark_info() -> dict[str, object]:
    info = datasets.describe_dataset(selection="humanevalplus")
    if info is None:
        raise ValueError("Benchmark adapter must declare provenance")
    return {**info.model_dump(exclude={"attributes"}), **info.attributes}


async def validate_case(task: Task) -> dict[str, object]:
    result = await verification.validate_reference(task)
    return {
        "case_id": task.id,
        "status": result.verification.status,
        "detail": result.detail,
        "metadata": result.metadata_json(),
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("command", choices=("info", "validate"))
    result.add_argument("--limit", type=int, default=None)
    return result


def validate(arguments: argparse.Namespace) -> int:
    if arguments.limit is not None and arguments.limit < 1:
        raise ValueError("--limit must be positive")
    dataset = datasets.load_dataset(selection="humanevalplus")
    results = [
        asyncio.run(validate_case(record.task))
        for record in list(dataset.records.values())[: arguments.limit]
    ]
    print(json.dumps({"provenance": benchmark_info(), "results": results}, indent=2))
    return int(any(result["status"] != "passed" for result in results))


def main(arguments: Sequence[str] | None = None) -> int:
    options = parser().parse_args(arguments)
    if options.command == "info":
        print(json.dumps(benchmark_info(), indent=2))
        return 0
    return validate(options)


if __name__ == "__main__":
    raise SystemExit(main())
