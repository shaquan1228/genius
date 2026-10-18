"""Inspect pinned datasets and validate reference code without model calls."""

import argparse
import asyncio
import json
from collections.abc import Sequence
from typing import Literal, assert_never

from pydantic import BaseModel, ConfigDict

from evals.python import datasets, verification
from kernel import Task


class BenchmarkInfo(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    source: str
    revision: str
    sha256: str
    count: int
    evaluator_commit: str
    numpy_version: str
    psutil_version: str


def benchmark_info() -> BenchmarkInfo:
    info = datasets.describe_dataset(selection="humanevalplus")
    if info is None:
        raise ValueError("Benchmark adapter must declare provenance")
    return BenchmarkInfo.model_validate(
        {**info.model_dump(exclude={"attributes"}), **info.attributes}
    )


async def validate_case(task: Task) -> dict[str, object]:
    result = await verification.validate_reference(task)
    return {
        "case_id": task.id,
        "status": type(result.verification).__name__.lower(),
        "detail": result.detail,
        "metadata": result.metadata_json(),
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("command", choices=("info", "validate"))
    result.add_argument("--limit", type=int, default=None)
    return result


class Options(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    command: Literal["info", "validate"] = "validate"
    limit: int | None = None


def validate(arguments: Options) -> int:
    if arguments.limit is not None and arguments.limit < 1:
        raise ValueError("--limit must be positive")
    dataset = datasets.load_dataset(selection="humanevalplus")
    results = [
        asyncio.run(validate_case(task))
        for task in list(dataset.records.values())[: arguments.limit]
    ]
    print(json.dumps({"provenance": benchmark_info().model_dump(), "results": results}, indent=2))
    return int(any(result["status"] != "passed" for result in results))


def main(arguments: Sequence[str] | None = None) -> int:
    options = Options.model_validate(vars(parser().parse_args(arguments)))
    match options.command:
        case "info":
            print(json.dumps(benchmark_info().model_dump(), indent=2))
            return 0
        case "validate":
            return validate(arguments=options)
        case _ as unreachable:
            assert_never(unreachable)


if __name__ == "__main__":
    raise SystemExit(main())
