"""Inspect pinned datasets and validate reference code without model calls."""

import argparse
import asyncio
import json
import os
import platform
from collections.abc import Mapping, Sequence
from typing import Literal, assert_never

from pydantic import BaseModel, ConfigDict

from evals.python import commands, queries
from kernel import Case


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
    info = queries.describe_dataset(selection="humanevalplus")
    if info is None:
        raise ValueError("Benchmark adapter must declare provenance")
    return BenchmarkInfo.model_validate(
        {**info.model_dump(exclude={"attributes"}), **info.attributes}
    )


async def validate_case(case: Case, *, dataset: queries.Dataset) -> dict[str, object]:
    result = await commands.validate_reference(case_id=case.id, selection=dataset)
    return {
        "case_id": case.id,
        "status": type(result.verification).__name__.lower(),
        "detail": result.detail,
        "metadata": diagnostic(result.metadata),
    }


def diagnostic(value: commands.Diagnostic) -> object:
    if isinstance(value, Mapping):
        return {key: diagnostic(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [diagnostic(item) for item in value]
    return value


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("command", choices=("info", "validate"))
    result.add_argument("--limit", type=int, default=None)
    result.add_argument(
        "--trusted-macos-memory-workaround",
        action="store_true",
        help="Disable EvalPlus's incompatible macOS memory guard for trusted references only",
    )
    return result


class Options(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    command: Literal["info", "validate"] = "validate"
    limit: int | None = None
    trusted_macos_memory_workaround: bool = False


def configure_memory(arguments: Options) -> None:
    if not arguments.trusted_macos_memory_workaround:
        return
    if platform.system() != "Darwin":
        raise ValueError("Memory workaround is only supported for trusted macOS validation")
    os.environ["EVALPLUS_MAX_MEMORY_BYTES"] = "-1"


def validate(arguments: Options) -> int:
    if arguments.limit is not None and arguments.limit < 1:
        raise ValueError("--limit must be positive")
    configure_memory(arguments=arguments)
    dataset = queries.load_dataset(selection="humanevalplus")
    results = [
        asyncio.run(validate_case(case=case, dataset=dataset))
        for case in queries.list_cases(selection=dataset)[: arguments.limit]
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
