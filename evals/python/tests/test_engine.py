"""Check Inspect scoring, repeated runs, and saved logs."""

from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from inspect_ai.log import read_eval_log
from inspect_ai.scorer import CORRECT, INCORRECT

from evals.python.contracts import Verification
from evals.python.integrations.datasets.catalog import grade
from evals.python.integrations.inspect.agents import AGENT_REGISTRY
from evals.python.integrations.inspect.tasks import baseline, genius
from evals.python.tests.scenarios import Mode, crashing
from evals.python.tests.support import crash_evidence, offline_run, results


def test_complete_suite_repeats_and_saves_logs(tmp_path: Path) -> None:
    with patch("evals.python.integrations.inspect.scoring.grade", wraps=grade) as grading:
        logs = offline_run([baseline(), genius()], mode="pass", directory=tmp_path, epochs=2)
    assert grading.call_count == 16
    expected = [
        (case, CORRECT, CORRECT)
        for case in ["clear-task", "known-preflight", "small-decision", "decision-review"]
    ] * 2
    assert [(log.status, sorted(results(log))) for log in logs] == [
        ("success", sorted(expected))
    ] * 2


def test_logs_reopen_with_scores_and_model_calls(tmp_path: Path) -> None:
    log = offline_run([baseline()], mode="pass", directory=tmp_path)[0]
    saved = read_eval_log(str(log.location))
    assert saved.results is not None
    assert {score.name for score in saved.results.scores} == {"correctness", "scope"}
    assert (saved.status, len(saved.samples or []), set(saved.stats.model_usage)) == (
        "success",
        4,
        {"mockllm/model"},
    )


@pytest.mark.parametrize("mode", ["extra", "committed-extra", "instructions", "tampered-checks"])
def test_scope_rejects_extra_committed_and_instruction_edits(*, mode: Mode, tmp_path: Path) -> None:
    logs = offline_run([baseline(), genius()], mode=mode, directory=tmp_path)
    assert [[scope for _, _, scope in results(log)] for log in logs] == [[INCORRECT] * 4] * 2


def test_untouched_seeded_bugs_fail(tmp_path: Path) -> None:
    log = offline_run([baseline()], mode="untouched", directory=tmp_path)[0]
    assert results(log) == sorted(
        [
            ("clear-task", INCORRECT, CORRECT),
            ("known-preflight", INCORRECT, CORRECT),
            ("small-decision", CORRECT, CORRECT),
            ("decision-review", CORRECT, CORRECT),
        ]
    )


def test_invalid_answers_fail(tmp_path: Path) -> None:
    log = offline_run([baseline()], mode="bad-answer", directory=tmp_path)[0]
    assert {case: correct for case, correct, _ in results(log)} == {
        "clear-task": CORRECT,
        "known-preflight": CORRECT,
        "small-decision": INCORRECT,
        "decision-review": INCORRECT,
    }


def test_tampered_visible_checks_cannot_pass_seeded_bugs(tmp_path: Path) -> None:
    log = offline_run([baseline()], mode="tampered-checks", directory=tmp_path)[0]
    coding = {case: correct for case, correct, _ in results(log)}
    assert coding["clear-task"] == INCORRECT
    assert coding["known-preflight"] == INCORRECT


def test_early_exit_cannot_skip_heldout_assertions(tmp_path: Path) -> None:
    log = offline_run([baseline()], mode="early-exit", directory=tmp_path)[0]
    scores = {case: (correct, scope) for case, correct, scope in results(log)}
    assert scores["clear-task"] == (INCORRECT, CORRECT)
    assert scores["known-preflight"] == (INCORRECT, CORRECT)


def test_crashed_agent_is_scored_on_its_workspace(
    *, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    message = "Error executing codex cli agent 1: tool 'apply_patch' was not in request.tools"
    factory = Mock(return_value=crashing(message=message))
    monkeypatch.setitem(
        AGENT_REGISTRY, "codex", replace(AGENT_REGISTRY["codex"], factory=lambda: factory)
    )
    log = offline_run([baseline(agent="codex")], mode=None, directory=tmp_path)[0]
    assert (log.status, results(log)) == (
        "success",
        sorted(
            (case, INCORRECT, CORRECT)
            for case in ["clear-task", "known-preflight", "small-decision", "decision-review"]
        ),
    )
    crash = f"Agent process crashed: {message}"
    assert {str(sample.id): crash_evidence(sample) for sample in log.samples or []} == {
        "clear-task": (crash, message, "failed"),
        "known-preflight": (crash, message, "failed"),
        "small-decision": (crash, message, "unchecked"),
        "decision-review": (crash, message, "unchecked"),
    }


def test_verifier_infrastructure_failure_is_sample_error(tmp_path: Path) -> None:
    with patch(
        "evals.python.integrations.inspect.scoring.Verifier.verify",
        return_value=(Verification(status="harness_error", detail="grader failed to import"), {}),
    ):
        log = offline_run([baseline()], mode="pass", directory=tmp_path)[0]
    assert log.status == "error"
    assert log.error is not None
    assert "grader failed to import" in log.error.message
