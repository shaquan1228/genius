import asyncio
from pathlib import Path

import pytest
from inspect_ai.scorer import CORRECT, INCORRECT
from inspect_ai.util._sandbox.docker.docker import DockerSandboxEnvironment

from evals.python.execution import Execution
from evals.python.integrations.inspect import environments, tasks
from evals.python.tests import support
from evals.python.tests.scenarios import Mode

CONFIG = str(Path(__file__).resolve().parents[1] / "docker" / "compose.yaml")


@pytest.mark.parametrize("mode", ["pass", "untouched", "tampered-checks"])
def container_evaluations(mode: Mode, *, tmp_path: Path) -> None:
    log = support.offline_run(
        [tasks.baseline()], mode=mode, directory=tmp_path, sandbox=("docker", CONFIG)
    )[0]
    assert log.status == "success"
    observed = {case: correct for case, correct, _ in support.results(log)}
    expected = CORRECT if mode == "pass" else INCORRECT
    assert observed == {
        "clear-task": expected,
        "known-preflight": expected,
        "small-decision": CORRECT,
        "decision-review": CORRECT,
    }


def candidate_and_grader_are_restricted(*, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    secret = tmp_path / "host-secret"
    secret.write_text("host-only")
    monkeypatch.setenv("GENIUS_HOST_SECRET", "host-only")

    async def check() -> None:
        provider = DockerSandboxEnvironment
        await provider.task_init("isolation", CONFIG)
        sandboxes = await provider.sample_init("isolation", CONFIG, {})
        candidate = sandboxes["default"]
        ports = environments.runtime(candidate)
        try:
            await candidate.write_file("candidate-only", "private workspace")
            grader = await ports.create()
            try:
                for target in (environments.environment(candidate), grader):
                    result = await target.execute(
                        Execution(
                            command=(
                                "python",
                                "-c",
                                f"""import os, pathlib, socket
assert os.getuid() == 10001
assert not pathlib.Path({str(secret)!r}).exists()
assert 'GENIUS_HOST_SECRET' not in os.environ
assert not pathlib.Path('/var/run/docker.sock').exists()
status = pathlib.Path('/proc/self/status').read_text()
assert int(status.split('CapEff:')[1].split()[0], 16) == 0
assert 'NoNewPrivs:\t1' in status
assert socket.socket().connect_ex(('1.1.1.1', 443)) != 0
assert os.statvfs('/').f_flag & os.ST_RDONLY
limits = pathlib.Path('/sys/fs/cgroup')
assert (limits / 'memory.max').read_text().strip() == '1073741824'
assert (limits / 'pids.max').read_text().strip() == '128'
quota, period = (limits / 'cpu.max').read_text().split()
assert int(quota) == int(period)
""",
                            )
                        )
                    )
                    assert result.returncode == 0, result.stderr
                result = await grader.execute(
                    Execution(command=("test", "!", "-e", "candidate-only"))
                )
                assert result.returncode == 0
                await grader.write_bytes("grader-only", b"private verifier")
                candidate_result = await candidate.exec(["test", "!", "-e", "grader-only"])
                assert candidate_result.success
            finally:
                await ports.cleanup(grader, interrupted=False)
        finally:
            await provider.sample_cleanup("isolation", CONFIG, sandboxes, interrupted=False)
            await provider.task_cleanup("isolation", CONFIG, cleanup=True)

    asyncio.run(check())
