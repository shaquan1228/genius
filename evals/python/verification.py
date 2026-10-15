"""Execute private verifier specifications in fresh environments."""

import asyncio
from collections.abc import Callable
from secrets import token_hex
from typing import cast

from inspect_ai.util import ExecResult, SandboxEnvironment
from pydantic import BaseModel, ConfigDict, JsonValue, ValidationError

from evals.python.transport import ExecutableChecks, Verification, VerificationStatus


class Evidence(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    marker: str
    status: VerificationStatus
    detail: str
    metadata: dict[str, JsonValue] | None = None


def authenticated(evidence: Evidence, *, marker: str, returncode: int) -> bool:
    return evidence.marker == marker and returncode == 0 and evidence.status != "unchecked"


def completion(
    result: ExecResult[str], *, marker: str
) -> tuple[Verification, dict[str, JsonValue]]:
    try:
        evidence = Evidence.model_validate_json(result.stdout.strip().splitlines()[-1])
    except (ValidationError, IndexError) as error:
        return Verification(
            status="harness_error", detail=f"Invalid verifier evidence: {error}"
        ), {}
    if not authenticated(evidence, marker=marker, returncode=result.returncode):
        return Verification(
            status="harness_error", detail="Verifier completion was not authenticated"
        ), {}
    return Verification(status=evidence.status, detail=evidence.detail), evidence.metadata or {}


async def candidate_files(
    checks: ExecutableChecks, *, agent: SandboxEnvironment
) -> dict[str, bytes] | Verification:
    try:
        return {name: await read_candidate(name, agent=agent) for name in checks.inputs}
    except FileNotFoundError as error:
        return Verification(status="invalid_submission", detail=f"Missing required input: {error}")


async def read_candidate(name: str, *, agent: SandboxEnvironment) -> bytes:
    exists = await agent.exec(["test", "-f", f"workspace/{name}"])
    if exists.returncode == 1:
        raise FileNotFoundError(name)
    if not exists.success:
        raise RuntimeError(f"Could not inspect candidate input: {exists.stderr}")
    return await agent.read_file(f"workspace/{name}", text=False)


async def run_verifier(
    checks: ExecutableChecks, *, environment: SandboxEnvironment, inputs: dict[str, bytes]
) -> tuple[Verification, dict[str, JsonValue]]:
    setup = await environment.exec(["mkdir", "-p", "workspace"])
    if not setup.success:
        raise RuntimeError(f"Could not create verifier workspace: {setup.stderr}")
    artifacts: dict[str, str | bytes] = {**inputs, **checks.tools, **checks.files}
    for name, contents in artifacts.items():
        await environment.write_file(f"workspace/{name}", contents)
    marker = token_hex(32)
    try:
        result = await environment.exec(
            list(checks.command),
            input=checks.stdin,
            cwd="workspace",
            env={"GENIUS_VERIFIER_MARKER": marker},
            timeout=checks.timeout_seconds,
        )
    except TimeoutError as error:
        return Verification(status="timed_out", detail=str(error)), {}
    return completion(result, marker=marker)


def provider(agent: SandboxEnvironment) -> type[SandboxEnvironment]:
    unwrap = cast(Callable[[object], SandboxEnvironment], agent.as_type)
    return type(unwrap(SandboxEnvironment))


async def execute_in_environment(
    checks: ExecutableChecks,
    *,
    agent: SandboxEnvironment,
    environments: dict[str, SandboxEnvironment],
) -> tuple[Verification, dict[str, JsonValue]]:
    inputs = await candidate_files(checks, agent=agent)
    if isinstance(inputs, Verification):
        return inputs, {}
    environments.update(await provider(agent).sample_init("genius-verification", None, {}))
    return await run_verifier(checks, environment=environments["default"], inputs=inputs)


async def cleanup(
    agent: SandboxEnvironment, *, environments: dict[str, SandboxEnvironment], interrupted: bool
) -> None:
    if not environments:
        return
    task = asyncio.create_task(
        provider(agent).sample_cleanup(
            "genius-verification", None, environments, interrupted=interrupted
        )
    )
    try:
        await asyncio.shield(task)
    except asyncio.CancelledError:
        await task
        raise


async def verify(
    checks: ExecutableChecks, *, agent: SandboxEnvironment
) -> tuple[Verification, dict[str, JsonValue]]:
    environments: dict[str, SandboxEnvironment] = {}
    interrupted = False
    try:
        return await execute_in_environment(checks, agent=agent, environments=environments)
    except asyncio.CancelledError:
        interrupted = True
        raise
    except Exception as error:
        return Verification(status="harness_error", detail=str(error)), {}
    finally:
        await cleanup(agent, environments=environments, interrupted=interrupted)
