"""Execute private verifier specifications in fresh environments."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from secrets import token_hex
from typing import assert_never, cast

from inspect_ai.util import ExecResult, SandboxEnvironment
from pydantic import BaseModel, ConfigDict, JsonValue, ValidationError

from evals.python.transport import ExecutableChecks, Verification, VerificationStatus


class Evidence(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    marker: str
    status: VerificationStatus
    detail: str
    metadata: dict[str, JsonValue] | None = None


@dataclass(frozen=True, kw_only=True)
class Completion:
    result: ExecResult[str]
    marker: str


def completion(request: Completion) -> tuple[Verification, dict[str, JsonValue]]:
    try:
        evidence = Evidence.model_validate_json(request.result.stdout.strip().splitlines()[-1])
    except (ValidationError, IndexError) as error:
        return Verification(
            status="harness_error", detail=f"Invalid verifier evidence: {error}"
        ), {}
    if not all(
        (
            evidence.marker == request.marker,
            request.result.returncode == 0,
            evidence.status != "unchecked",
        )
    ):
        return Verification(
            status="harness_error", detail="Verifier completion was not authenticated"
        ), {}
    return Verification(status=evidence.status, detail=evidence.detail), evidence.metadata or {}


def provider(agent: SandboxEnvironment) -> type[SandboxEnvironment]:
    unwrap = cast(Callable[[object], SandboxEnvironment], agent.as_type)
    return type(unwrap(SandboxEnvironment))


@dataclass(kw_only=True)
class Verifier:
    checks: ExecutableChecks
    agent: SandboxEnvironment
    environments: dict[str, SandboxEnvironment] = field(default_factory=dict)
    interrupted: bool = False

    async def read_candidate(self, name: str) -> bytes:
        exists = await self.agent.exec(["test", "-f", f"workspace/{name}"])
        match exists.returncode:
            case 1:
                raise FileNotFoundError(name)
            case 0:
                return await self.agent.read_file(f"workspace/{name}", text=False)
            case _:
                raise RuntimeError(f"Could not inspect candidate input: {exists.stderr}")

    async def candidate_files(self) -> dict[str, bytes] | Verification:
        try:
            return {name: await self.read_candidate(name=name) for name in self.checks.inputs}
        except FileNotFoundError as error:
            return Verification(
                status="invalid_submission", detail=f"Missing required input: {error}"
            )

    async def run_verifier(
        self, inputs: dict[str, bytes]
    ) -> tuple[Verification, dict[str, JsonValue]]:
        environment = self.environments["default"]
        setup = await environment.exec(["mkdir", "-p", "workspace"])
        if not setup.success:
            raise RuntimeError(f"Could not create verifier workspace: {setup.stderr}")
        artifacts: dict[str, str | bytes] = {**inputs, **self.checks.tools, **self.checks.files}
        for name, contents in artifacts.items():
            await environment.write_file(f"workspace/{name}", contents)
        marker = token_hex(32)
        try:
            result = await environment.exec(
                list(self.checks.command),
                input=self.checks.stdin,
                cwd="workspace",
                env={"GENIUS_VERIFIER_MARKER": marker},
                timeout=self.checks.timeout_seconds,
            )
        except TimeoutError as error:
            return Verification(status="timed_out", detail=str(error)), {}
        return completion(request=Completion(result=result, marker=marker))

    async def cleanup(self) -> None:
        if not self.environments:
            return
        task = asyncio.create_task(
            provider(agent=self.agent).sample_cleanup(
                "genius-verification", None, self.environments, interrupted=self.interrupted
            )
        )
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            await task
            raise

    async def execute(self) -> tuple[Verification, dict[str, JsonValue]]:
        match await self.candidate_files():
            case Verification() as invalid:
                return invalid, {}
            case dict() as inputs:
                self.environments.update(
                    await provider(agent=self.agent).sample_init("genius-verification", None, {})
                )
                return await self.run_verifier(inputs=inputs)
            case _ as unreachable:
                assert_never(unreachable)

    async def verify(self) -> tuple[Verification, dict[str, JsonValue]]:
        try:
            return await self.execute()
        except asyncio.CancelledError:
            self.interrupted = True
            raise
        except Exception as error:
            return Verification(status="harness_error", detail=str(error)), {}
        finally:
            await self.cleanup()
