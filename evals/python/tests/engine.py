"""Check Inspect scoring, repeated runs, and saved logs."""

import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from inspect_ai.log import EvalLog, EvalSample, read_eval_log
from inspect_ai.scorer import CORRECT, INCORRECT

from evals.python.integrations.inspect.agents import AGENT_REGISTRY
from evals.python.integrations.inspect.tasks import baseline, genius
from evals.python.tests.scenarios import Mode
from evals.python.tests.scenarios import crashing as _crashing
from evals.python.tests.support import (
    crash_evidence as _crash_evidence,
)
from evals.python.tests.support import (
    offline_run as _offline_run,
)
from evals.python.tests.support import (
    results as _results,
)
from evals.python.verification import VerificationResult
from kernel import Verification


def complete_suite_repeats_and_saves_logs(tmp_path: Path) -> None:
    logs = _offline_run([baseline(), genius()], mode="pass", directory=tmp_path, epochs=2)
    expected = [
        (case, CORRECT, CORRECT)
        for case in ["clear-task", "known-preflight", "small-decision", "decision-review"]
    ] * 2
    assert [(log.status, sorted(_results(log))) for log in logs] == [
        ("success", sorted(expected))
    ] * 2
    _assert_saved_log(read_eval_log(str(logs[0].location)), count=len(expected))


def _assert_saved_log(saved: EvalLog, *, count: int) -> None:
    assert saved.results is not None
    assert saved.samples is not None
    assert (
        {score.name for score in saved.results.scores},
        saved.status,
        len(saved.samples),
        set(saved.stats.model_usage),
    ) == (
        {"correctness", "scope"},
        "success",
        count,
        {"mockllm/model"},
    )
    _assert_answer_judgments(
        next(filter(lambda sample: sample.id == "small-decision", saved.samples))
    )


def _assert_answer_judgments(sample: EvalSample) -> None:
    assert sample.scores is not None
    metadata = sample.scores["evaluation"].metadata
    assert metadata is not None
    assert metadata["assessment"]["checks"]["correctness"]["checks"]["fields"]["checks"][
        "choice"
    ] == {
        "passed": True,
        "predicate": {"kind": "equals", "path": ["response", "choice"], "expected": "B"},
        "observed": "B",
    }
    assert metadata["assessment"]["checks"]["correctness"]["checks"]["text"]["passed"] is True


@pytest.mark.parametrize("mode", ["extra", "committed-extra", "instructions", "tampered-checks"])
def scope_rejects_extra_committed_and_instruction_edits(*, mode: Mode, tmp_path: Path) -> None:
    logs = _offline_run([baseline(), genius()], mode=mode, directory=tmp_path)
    assert [[scope for _, _, scope in _results(log)] for log in logs] == [[INCORRECT] * 4] * 2


def untouched_seeded_bugs_fail(tmp_path: Path) -> None:
    log = _offline_run([baseline()], mode="untouched", directory=tmp_path)[0]
    assert _results(log) == sorted(
        [
            ("clear-task", INCORRECT, CORRECT),
            ("known-preflight", INCORRECT, CORRECT),
            ("small-decision", CORRECT, CORRECT),
            ("decision-review", CORRECT, CORRECT),
        ]
    )


def invalid_answers_fail(tmp_path: Path) -> None:
    log = _offline_run([baseline()], mode="bad-answer", directory=tmp_path)[0]
    assert {case: correct for case, correct, _ in _results(log)} == {
        "clear-task": CORRECT,
        "known-preflight": CORRECT,
        "small-decision": INCORRECT,
        "decision-review": INCORRECT,
    }


def tampered_visible_checks_cannot_pass_seeded_bugs(tmp_path: Path) -> None:
    log = _offline_run([baseline()], mode="tampered-checks", directory=tmp_path)[0]
    coding = {case: correct for case, correct, _ in _results(log)}
    assert coding["clear-task"] == INCORRECT
    assert coding["known-preflight"] == INCORRECT


def early_exit_cannot_skip_heldout_assertions(tmp_path: Path) -> None:
    log = _offline_run([baseline()], mode="early-exit", directory=tmp_path)[0]
    scores = {case: (correct, scope) for case, correct, scope in _results(log)}
    assert scores["clear-task"] == (INCORRECT, CORRECT)
    assert scores["known-preflight"] == (INCORRECT, CORRECT)


def crashed_agent_is_scored_on_its_workspace(
    *, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    message = "Error executing codex cli agent 1: tool 'apply_patch' was not in request.tools"
    factory = Mock(return_value=_crashing(message=message))
    monkeypatch.setitem(
        AGENT_REGISTRY, "codex", replace(AGENT_REGISTRY["codex"], factory=lambda: factory)
    )
    log = _offline_run([baseline(agent="codex")], mode=None, directory=tmp_path)[0]
    assert (log.status, _results(log)) == (
        "success",
        sorted(
            (case, INCORRECT, CORRECT)
            for case in ["clear-task", "known-preflight", "small-decision", "decision-review"]
        ),
    )
    crash = f"Agent process crashed: {message}"
    assert {str(sample.id): _crash_evidence(sample) for sample in log.samples or []} == {
        "clear-task": (crash, message, "failed"),
        "known-preflight": (crash, message, "failed"),
        "small-decision": (crash, message, "unchecked"),
        "decision-review": (crash, message, "unchecked"),
    }


def verifier_infrastructure_failure_is_sample_error(tmp_path: Path) -> None:
    with patch(
        "evals.python.verification.verify",
        return_value=VerificationResult(
            verification=Verification.HarnessError(detail="grader failed to import")
        ),
    ):
        log = _offline_run([baseline()], mode="pass", directory=tmp_path)[0]
    assert log.status == "error"
    assert log.error is not None
    assert "grader failed to import" in log.error.message


def extended_native_contract_drives_fresh_inspect_registration() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
from unittest.mock import patch
from kernel import Assessment, Predicate, Task, Value
with patch.object(Task, "required_scores", ["correctness", "scope", "extension"]):
    from evals.python.integrations.inspect import completeness, scoring
    from inspect_ai.scorer._scorer import scorer_metrics
    from inspect_ai.scorer import CORRECT, INCORRECT
    metrics = scorer_metrics(scoring.evaluation())
    assert isinstance(metrics, dict)
    assert tuple(metrics) == tuple(Task.required_scores)
    assert all(len(items) == 2 for items in metrics.values())
    assert not completeness.complete_value({"correctness": CORRECT, "scope": INCORRECT})
    encoded = {"correctness": CORRECT, "scope": INCORRECT, "extension": CORRECT}
    assert completeness.complete_value(encoded)
    yes = Predicate.all(checks=[])
    no = Predicate.present(path=["absent"])
    predicate = Predicate.all(checks=[("correctness", yes), ("scope", no), ("extension", yes)])
    assessment = Assessment.create(predicate=predicate, observation=Value.Null())
    scores = Assessment.scores(assessment=assessment)
    assert scoring.score_values(scores) == encoded
""",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=Path(__file__).resolve().parents[3],
    )
    assert result.returncode == 0, result.stdout + result.stderr
