"""Check Inspect scoring, repeated runs, and saved logs."""

import asyncio
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from inspect_ai.log import read_eval_log
from inspect_ai.model import ModelName, ModelOutput
from inspect_ai.scorer import CORRECT, INCORRECT, Target
from inspect_ai.solver import TaskState

from evals.python import assessment as assessment_api
from evals.python.assessment import Assessment
from evals.python.integrations.inspect import environments, scoring, workspace
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
from evals.python.tests.verification import _agent_port, _grader_port, _runtime_port
from evals.python.verification import VerificationResult
from kernel import Task, Verification


def complete_suite_repeats_and_saves_logs(tmp_path: Path) -> None:
    with patch("kernel.Task.grade", wraps=Task.grade) as grading:
        logs = _offline_run([baseline(), genius()], mode="pass", directory=tmp_path, epochs=2)
    assert grading.call_count == 16
    expected = [
        (case, CORRECT, CORRECT)
        for case in ["clear-task", "known-preflight", "small-decision", "decision-review"]
    ] * 2
    assert [(log.status, sorted(_results(log))) for log in logs] == [
        ("success", sorted(expected))
    ] * 2


def logs_reopen_with_scores_and_model_calls(tmp_path: Path) -> None:
    log = _offline_run([baseline()], mode="pass", directory=tmp_path)[0]
    saved = read_eval_log(str(log.location))
    assert saved.results is not None
    assert {score.name for score in saved.results.scores} == {"correctness", "scope"}
    assert (saved.status, len(saved.samples or []), set(saved.stats.model_usage)) == (
        "success",
        4,
        {"mockllm/model"},
    )


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


def scorer_maps_sdk_observation_to_public_assessment() -> None:

    state = TaskState(
        model=ModelName("mockllm/model"),
        sample_id="sdk-id",
        epoch=1,
        input="task",
        messages=[],
        metadata={"case_id": "clear-task", "dataset": "smoke"},
    )
    state.output = ModelOutput.from_content("mockllm/model", "observed answer")
    agent, runtime = _agent_port(), _runtime_port(_grader_port())
    assessment = Assessment(
        evidence=VerificationResult(
            verification=Verification.Passed(),
            detail="canonical evidence",
            metadata={"nested": {"items": (True, None, 4.2)}},
        ),
        scores={"correctness": True, "scope": False},
    )
    with (
        patch.object(workspace, "changed_files", return_value={"b.ml", "a.ml"}),
        patch.object(scoring, "sandbox"),
        patch.object(environments, "environment", return_value=agent),
        patch.object(environments, "runtime", return_value=runtime),
        patch.object(assessment_api, "assess", return_value=assessment) as execute,
    ):
        score = asyncio.run(scoring.score_sample(state, Target([""])))
    assert score.metadata is not None
    assert (
        execute.call_args.kwargs,
        score.value,
        score.explanation,
        score.metadata["verifier_metadata"],
        assessment.evidence.metadata,
    ) == (
        {
            "case_id": "clear-task",
            "response": "observed answer",
            "changed_files": ("a.ml", "b.ml"),
            "selection": "smoke",
            "agent": agent,
            "runtime": runtime,
        },
        {"correctness": CORRECT, "scope": INCORRECT},
        "canonical evidence",
        {"nested": {"items": [True, None, 4.2]}},
        {"nested": {"items": (True, None, 4.2)}},
    )


def extended_native_contract_drives_fresh_inspect_registration() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
from unittest.mock import patch
from kernel import Task
with patch.object(Task, "required_scores", ["correctness", "scope", "extension"]):
    from evals.python import grading
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
    pairs = [("correctness", True), ("scope", False), ("extension", True)]
    with patch.object(Task, "grade", return_value=pairs):
        scores = grading.score_case(case_id="small-decision", response="{}", changed_files=())
    assert scoring.score_values(scores) == encoded
""",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=Path(__file__).resolve().parents[3],
    )
    assert result.returncode == 0, result.stdout + result.stderr
