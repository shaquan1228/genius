"""Validate reference code using Inspect-owned environments, without model calls."""

from typing import assert_never

from inspect_ai.util._sandbox.local import LocalSandboxEnvironment

from evals.python.contracts import ExecutableChecks
from evals.python.integrations.inspect.datasets import reference, verifier
from evals.python.integrations.inspect.verification import Verifier


async def validate_case(case_id: str) -> dict[str, object]:
    match verifier(case_id, selection="humanevalplus"):
        case ExecutableChecks() as checks:
            pass
        case None:
            raise ValueError("Reference validation requires executable checks")
        case _ as unreachable:
            assert_never(unreachable)
    agent = LocalSandboxEnvironment()
    try:
        await agent.exec(["mkdir", "workspace"])
        for name, contents in reference(case_id, selection="humanevalplus").solution.items():
            await agent.write_file(f"workspace/{name}", contents)
        evidence, metadata = await Verifier(checks=checks, agent=agent).verify()
        return {"case_id": case_id, **evidence.model_dump(), "metadata": metadata}
    finally:
        await LocalSandboxEnvironment.sample_cleanup(
            "reference-validation", None, {"default": agent}, interrupted=False
        )
