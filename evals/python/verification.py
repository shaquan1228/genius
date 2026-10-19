"""Runner-independent verification policy over immutable execution capabilities."""

from secrets import token_hex

from pydantic import InstanceOf, validate_call

from evals.python import FROZEN, execution
from evals.python.evidence import Diagnostic, VerificationResult, completion
from evals.python.execution import Environment, Execution, Runtime
from kernel import Content, Fixture, Task, Verification, Verifier

__all__ = ["Diagnostic", "VerificationResult", "validate_reference", "verify"]


async def _inputs(checks: Verifier, *, agent: Environment) -> dict[str, bytes]:
    result = {}
    for name in checks.inputs:
        path = f"workspace/{name}"
        inspection = await agent.execute(Execution(command=("test", "-f", path)))
        if inspection.returncode == 1:
            raise FileNotFoundError(name)
        if inspection.returncode != 0:
            raise RuntimeError(f"Could not inspect candidate input: {inspection.stderr}")
        result[name] = await agent.read_bytes(path)
    return result


def _contents(value: Content.Value) -> str:
    if not isinstance(value, Content.Inline):
        raise ValueError("Verifier resources must be resolved before execution")
    return value.text


async def _execute(
    checks: Verifier, *, grader: Environment, inputs: dict[str, bytes]
) -> VerificationResult:
    setup = await grader.execute(Execution(command=("mkdir", "-p", "workspace")))
    if setup.returncode != 0:
        raise RuntimeError(f"Could not create verifier workspace: {setup.stderr}")
    artifacts = {
        **inputs,
        **{
            artifact.path: _contents(artifact.content).encode()
            for artifact in (*checks.tools, *checks.files)
        },
    }
    for name, contents in artifacts.items():
        await grader.write_bytes(f"workspace/{name}", contents)
    marker = token_hex(32)
    try:
        result = await grader.execute(
            Execution(
                command=tuple(checks.command),
                input=checks.stdin,
                cwd="workspace",
                env={"GENIUS_VERIFIER_MARKER": marker},
                timeout=checks.timeout_seconds,
            )
        )
    except TimeoutError as error:
        return VerificationResult(verification=Verification.TimedOut(), detail=str(error))
    return completion(result, marker=marker)


@validate_call(config=FROZEN)
async def verify(
    checks: InstanceOf[Verifier] | None,
    *,
    agent: InstanceOf[Environment],
    runtime: InstanceOf[Runtime],
) -> VerificationResult:
    if checks is None:
        return VerificationResult(verification=Verification.Unchecked())
    try:
        try:
            inputs = await _inputs(checks, agent=agent)
        except FileNotFoundError as error:
            return VerificationResult(
                verification=Verification.InvalidSubmission(),
                detail=f"Missing required input: {error}",
            )
        async with execution.allocated(runtime, candidate=agent) as grader:
            return await _execute(checks, grader=grader, inputs=inputs)
    except Exception as error:
        return VerificationResult(verification=Verification.HarnessError(detail=str(error)))


async def stage_reference(fixture: Fixture, *, agent: Environment) -> None:
    result = await agent.execute(Execution(command=("mkdir", "-p", "workspace")))
    if result.returncode != 0:
        raise RuntimeError(f"Could not create reference workspace: {result.stderr}")
    for file in Fixture.files(fixture=fixture):
        await agent.write_bytes(f"workspace/{file.path}", file.contents.encode())


@validate_call(config=FROZEN)
async def validate_reference(
    task: InstanceOf[Task],
    *,
    runtime: InstanceOf[Runtime] | None = None,
) -> VerificationResult:
    checks = Task.verifier(task=task)
    if checks is None:
        return VerificationResult(verification=Verification.Unchecked())
    runtime = runtime or execution.create_runtime()
    try:
        async with execution.allocated(runtime) as agent:
            await stage_reference(task.reference.edits, agent=agent)
            return await verify(checks, agent=agent, runtime=runtime)
    except Exception as error:
        return VerificationResult(verification=Verification.HarnessError(detail=str(error)))
