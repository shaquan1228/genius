"""Inspect pinned datasets and validate reference code without model calls."""

import argparse
import asyncio
import json
import os
import platform
from collections.abc import Sequence
from typing import Literal, assert_never

from inspect_ai.util._sandbox.local import LocalSandboxEnvironment
from pydantic import BaseModel, ConfigDict

from evals.python.transport import Case, ExecutableChecks, benchmark_info, load_cases
from evals.python.verification import Verifier


async def validate_case(case: Case) -> dict[str, object]:
    match case.checks:
        case ExecutableChecks() as checks:
            pass
        case None:
            raise ValueError("Reference validation requires executable checks")
        case _ as unreachable:
            assert_never(unreachable)
    agent = LocalSandboxEnvironment()
    try:
        await agent.exec(["mkdir", "workspace"])
        for name, contents in case.solution.items():
            await agent.write_file(f"workspace/{name}", contents)
        evidence, metadata = await Verifier(checks=checks, agent=agent).verify()
        return {"case_id": case.id, **evidence.model_dump(), "metadata": metadata}
    finally:
        await LocalSandboxEnvironment.sample_cleanup(
            "reference-validation", None, {"default": agent}, interrupted=False
        )


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
    results = [
        asyncio.run(validate_case(case=case))
        for case in load_cases(selection="humanevalplus")[: arguments.limit]
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
