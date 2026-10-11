"""Exercise the real Inspect engine offline, including repeats and failure logs."""

import asyncio
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from inspect_ai import Task, eval
from inspect_ai.log import EvalLog, EvalSample, read_eval_log
from inspect_ai.model import get_model
from inspect_ai.scorer import CORRECT, INCORRECT
from inspect_ai.util import ExecResult
from inspect_swe import claude_code, codex_cli

from genius_evals.agents import AgentKind, coding_agent
from genius_evals.cases import EVALS_ROOT
from genius_evals.tasks import baseline, build_task, genius
from genius_evals.workspace import execute
from tests.scenarios import Mode, echo_model, scripted


def offline_run(tasks: list[Task], mode: Mode, directory: Path, epochs: int = 1) -> list[EvalLog]:
    model = get_model("mockllm/model", custom_outputs=echo_model)
    logs = eval(
        tasks,
        model=model,
        solver=scripted(mode),
        sandbox="local",
        epochs=epochs,
        max_samples=1,
        log_dir=str(directory),
        display="none",
        log_format="json",
        ctl_server=False,
    )
    archive = EVALS_ROOT / "results/offline"
    archive.mkdir(parents=True, exist_ok=True)
    for log in logs:
        shutil.copy2(str(log.location), archive)
    return logs


def sample_result(sample: EvalSample) -> tuple[str, object, object]:
    assert sample.scores is not None
    return (str(sample.id), sample.scores["correctness"].value, sample.scores["scope"].value)


def results(log: EvalLog) -> list[tuple[str, object, object]]:
    return sorted(sample_result(sample) for sample in log.samples or [])


def test_complete_suite_repeats_and_saves_logs(tmp_path: Path) -> None:
    logs = offline_run([baseline(), genius()], "pass", tmp_path, epochs=2)
    expected = [
        (case, CORRECT, CORRECT)
        for case in ["clear-task", "known-preflight", "small-decision", "decision-review"]
    ] * 2
    assert [(log.status, sorted(results(log))) for log in logs] == [
        ("success", sorted(expected))
    ] * 2


def test_logs_reopen_with_scores_and_model_calls(tmp_path: Path) -> None:
    log = offline_run([baseline()], "pass", tmp_path)[0]
    saved = read_eval_log(str(log.location))
    assert (saved.status, len(saved.samples or []), set(saved.stats.model_usage)) == (
        "success",
        4,
        {"mockllm/model"},
    )


@pytest.mark.parametrize("mode", ["extra", "committed-extra", "instructions"])
def test_scope_rejects_extra_committed_and_instruction_edits(mode: Mode, tmp_path: Path) -> None:
    logs = offline_run([baseline(), genius()], mode, tmp_path)
    assert [[scope for _, _, scope in results(log)] for log in logs] == [[INCORRECT] * 4] * 2


def test_untouched_seeded_bugs_fail(tmp_path: Path) -> None:
    log = offline_run([baseline()], "untouched", tmp_path)[0]
    assert results(log) == sorted(
        [
            ("clear-task", INCORRECT, CORRECT),
            ("known-preflight", INCORRECT, CORRECT),
            ("small-decision", CORRECT, CORRECT),
            ("decision-review", CORRECT, CORRECT),
        ]
    )


def test_invalid_answers_fail(tmp_path: Path) -> None:
    log = offline_run([baseline()], "bad-answer", tmp_path)[0]
    assert {case: correct for case, correct, _ in results(log)} == {
        "clear-task": CORRECT,
        "known-preflight": CORRECT,
        "small-decision": INCORRECT,
        "decision-review": INCORRECT,
    }


@pytest.mark.parametrize("kind", ["claude", "codex"])
def test_real_swe_bindings_accept_our_options(kind: AgentKind) -> None:
    assert callable(coding_agent(kind, "sandbox"))


def test_claude_options_are_fixed() -> None:
    with patch("genius_evals.agents.claude_code", wraps=claude_code) as factory:
        coding_agent("claude", "2.1.278")
    assert factory.call_args.kwargs == {
        "cwd": "workspace",
        "version": "2.1.278",
        "attempts": 1,
        "effort": "medium",
        "disallowed_tools": ["WebSearch", "WebFetch"],
        "retry_refusals": 0,
        "retry_uncaught_errors": 0,
    }


def test_codex_options_disable_network() -> None:
    with patch("genius_evals.agents.codex_cli", wraps=codex_cli) as factory:
        coding_agent("codex", "0.137.0")
    assert factory.call_args.kwargs == {
        "cwd": "workspace",
        "version": "0.137.0",
        "attempts": 1,
        "web_search": "disabled",
        "network_access": False,
        "retry_refusals": 0,
        "config_overrides": {"model_reasoning_effort": '"medium"'},
    }


def test_explicit_agent_version_is_logged() -> None:
    task = build_task("genius", "codex", "0.137.0")
    metadata = task.metadata
    assert metadata is not None
    assert (metadata["agent"], metadata["agent_version"]) == ("codex", "0.137.0")


@pytest.mark.parametrize("error", ["stderr", "stdout"])
def test_failed_setup_commands_raise(error: str) -> None:
    result = ExecResult(
        success=False, returncode=1, stdout="stdout", stderr="stderr" if error == "stderr" else ""
    )
    with patch("genius_evals.workspace.sandbox") as environment:
        environment.return_value.exec = AsyncMock(return_value=result)
        with pytest.raises(RuntimeError, match=error):
            asyncio.run(execute(["git", "init"]))


def test_command_timeouts_propagate() -> None:
    with patch("genius_evals.workspace.sandbox") as environment:
        environment.return_value.exec = AsyncMock(side_effect=TimeoutError("Timed out"))
        with pytest.raises(TimeoutError):
            asyncio.run(execute(["git", "init"]))
