"""Check setup failures are surfaced to Inspect."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from inspect_ai.util import ExecResult

from evals.workspace import execute


@pytest.mark.parametrize("error", ["stderr", "stdout"])
def test_failed_setup_commands_raise(error: str) -> None:
    result = ExecResult(
        success=False, returncode=1, stdout="stdout", stderr="stderr" if error == "stderr" else ""
    )
    with patch("evals.workspace.sandbox") as environment:
        environment.return_value.exec = AsyncMock(return_value=result)
        with pytest.raises(RuntimeError, match=error):
            asyncio.run(execute(["git", "init"]))


def test_command_timeouts_propagate() -> None:
    with patch("evals.workspace.sandbox") as environment:
        environment.return_value.exec = AsyncMock(side_effect=TimeoutError("Timed out"))
        with pytest.raises(TimeoutError):
            asyncio.run(execute(["git", "init"]))
