"""Temporary compatibility entry point; public commands own verification policy."""

from collections.abc import Mapping
from dataclasses import dataclass

from inspect_ai.util import SandboxEnvironment
from pydantic import JsonValue

from evals.python.contracts import ExecutableChecks, Verification
from evals.python.integrations.inspect.environments import environment, runtime
from evals.python.verification import Diagnostic, verify


def _json(value: Diagnostic) -> JsonValue:
    if isinstance(value, Mapping):
        return {key: _json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json(item) for item in value]
    return value


@dataclass(frozen=True, kw_only=True)
class Verifier:
    checks: ExecutableChecks
    agent: SandboxEnvironment

    async def verify(self) -> tuple[Verification, dict[str, JsonValue]]:
        result = await verify(
            self.checks, agent=environment(self.agent), runtime=runtime(self.agent)
        )
        return result.verification, {key: _json(value) for key, value in result.metadata.items()}
