"""Inspect pinned datasets and validate reference code without model calls."""

import argparse
import asyncio
import json
import os
import platform
from collections.abc import Sequence

from inspect_ai.util._sandbox.local import LocalSandboxEnvironment

from evals.python.transport import Case, ExecutableChecks, humaneval_info, load_cases
from evals.python.verification import verify


async def validate_case(case: Case) -> dict[str, object]:
    if not isinstance(case.checks, ExecutableChecks):
        raise ValueError("Reference validation requires executable checks")
    agent = LocalSandboxEnvironment()
    try:
        await agent.exec(["mkdir", "workspace"])
        for name, contents in case.solution.items():
            await agent.write_file(f"workspace/{name}", contents)
        evidence, metadata = await verify(case.checks, agent=agent)
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


def configure_memory(arguments: argparse.Namespace) -> None:
    if not arguments.trusted_macos_memory_workaround:
        return
    if platform.system() != "Darwin":
        raise ValueError("Memory workaround is only supported for trusted macOS validation")
    os.environ["EVALPLUS_MAX_MEMORY_BYTES"] = "-1"


def validate(arguments: argparse.Namespace) -> int:
    if arguments.limit is not None and arguments.limit < 1:
        raise ValueError("--limit must be positive")
    configure_memory(arguments)
    results = [
        asyncio.run(validate_case(case))
        for case in load_cases(dataset="humanevalplus")[: arguments.limit]
    ]
    print(json.dumps({"provenance": humaneval_info().model_dump(), "results": results}, indent=2))
    return int(any(result["status"] != "passed" for result in results))


def main(arguments: Sequence[str] | None = None) -> int:
    options = parser().parse_args(arguments)
    if options.command == "info":
        print(json.dumps(humaneval_info().model_dump(), indent=2))
        return 0
    return validate(options)


if __name__ == "__main__":
    raise SystemExit(main())
