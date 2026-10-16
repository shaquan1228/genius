"""Check setup failures are surfaced to Inspect."""

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from inspect_ai.model import ModelName
from inspect_ai.solver import TaskState
from inspect_ai.util import ExecResult

from evals.python.integrations.inspect.workspace import changed_files, execute, prepare_sample


@pytest.mark.parametrize("error", ["stderr", "stdout"])
def test_failed_setup_commands_raise(error: str) -> None:
    result = ExecResult(
        success=False, returncode=1, stdout="stdout", stderr="stderr" if error == "stderr" else ""
    )
    with patch("evals.python.integrations.inspect.workspace.sandbox") as environment:
        environment.return_value.exec = AsyncMock(return_value=result)
        with pytest.raises(RuntimeError, match=error):
            asyncio.run(execute(["git", "init"]))


def test_command_timeouts_propagate() -> None:
    with patch("evals.python.integrations.inspect.workspace.sandbox") as environment:
        environment.return_value.exec = AsyncMock(side_effect=TimeoutError("Timed out"))
        with pytest.raises(TimeoutError):
            asyncio.run(execute(["git", "init"]))


def write_files(root: Path, *, files: dict[str, str | None]) -> None:
    for name, contents in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if contents is None:
            path.unlink()
        else:
            path.write_text(contents)


@pytest.mark.parametrize(
    ("edits", "expected"),
    [
        ({}, set()),
        ({"workspace/extra.py": "extra"}, {"workspace/extra.py"}),
        ({"workspace/__pycache__-notes.py": "extra"}, {"workspace/__pycache__-notes.py"}),
        (
            {"workspace/.pytest_cache-notes/extra.py": "extra"},
            {"workspace/.pytest_cache-notes/extra.py"},
        ),
        (
            {
                "workspace/tracked.pyc": "changed",
                "workspace/__pycache__/tracked.pyc": None,
                "workspace/.pytest_cache/tracked": "changed",
            },
            {
                "workspace/tracked.pyc",
                "workspace/__pycache__/tracked.pyc",
                "workspace/.pytest_cache/tracked",
            },
        ),
        (
            {"workspace/.gitignore": "extra.py", "workspace/extra.py": "extra"},
            {"workspace/.gitignore", "workspace/extra.py"},
        ),
    ],
)
def test_git_scope_preserves_tracked_changes(
    *, tmp_path: Path, edits: dict[str, str | None], expected: set[str]
) -> None:
    write_files(
        tmp_path,
        files=dict.fromkeys(
            [
                "workspace/solution.py",
                "workspace/tracked.pyc",
                "workspace/__pycache__/tracked.pyc",
                "workspace/.pytest_cache/tracked",
            ],
            "initial",
        ),
    )
    state = TaskState(
        model=ModelName("mockllm/model"), sample_id="case", epoch=1, input="task", messages=[]
    )

    async def run_git(command: list[str]) -> str:
        return subprocess.run(
            command, cwd=tmp_path, text=True, capture_output=True, check=True
        ).stdout

    with patch("evals.python.integrations.inspect.workspace.execute", side_effect=run_git):
        asyncio.run(prepare_sample(state, Mock()))
        write_files(
            tmp_path,
            files={
                "workspace/solution.py": "changed",
                "workspace/__pycache__/solution.cpython-312.pyc": "cache",
                "workspace/nested/__pycache__/solution.pyc": "cache",
                "workspace/.pytest_cache/v/cache/nodeids": "cache",
                "workspace/stray.pyc": "cache",
                **edits,
            },
        )
        assert asyncio.run(changed_files(state)) == {"workspace/solution.py", *expected}
