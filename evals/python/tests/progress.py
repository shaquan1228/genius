"""Exercise observable lifecycle through Inspect's real concurrent engine."""

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from inspect_ai import Task, eval_async
from inspect_ai.dataset import Sample
from inspect_ai.scorer import Score, Scorer, Target, scorer
from inspect_ai.solver import Generate, Solver, TaskState, solver

from evals.python import commands, evaluation_settings
from evals.python.integrations.hugging_face.job import configuration
from evals.python.integrations.inspect import completeness, evaluation, progress


@scorer(metrics=[])
def _complete_score() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:  # noqa: PLR0917
        return Score(value={"correctness": 1, "scope": 1})

    return score


@pytest.mark.parametrize("value", ["0", "-1", "17", "invalid"])
def invalid_concurrency(value: str) -> None:
    with pytest.raises(ValueError, match=r"validation error|invalid literal"):
        configuration({"EVAL_MODEL": "mockllm/model", "EVAL_MAX_SAMPLES": value})


def concurrency_configuration() -> None:
    assert configuration({"EVAL_MODEL": "mockllm/model"}).max_samples == 1
    assert configuration({"EVAL_MODEL": "mockllm/model", "EVAL_MAX_SAMPLES": "2"}).max_samples == 2


def native_parallel_events(*, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    async def run() -> None:
        active = 0
        peak = 0
        both = asyncio.Event()

        @solver
        def blocked() -> Solver:
            async def solve(state: TaskState, generate: Generate) -> TaskState:  # noqa: PLR0917
                nonlocal active, peak
                active += 1
                peak = max(peak, active)
                if active == 2:
                    both.set()
                await asyncio.wait_for(both.wait(), timeout=10)
                await asyncio.sleep(0.01)
                active -= 1
                state.output.completion = "yes"
                return state

            return solve

        task = Task(
            name="parallel",
            dataset=[Sample(id=n, input="question", target="yes") for n in (1, 2)],
            solver=blocked(),
            scorer=_complete_score(),
        )
        state = progress.Progress()
        token = progress.current.set(state)
        heartbeat = asyncio.create_task(state.heartbeat(interval=0.001))
        try:
            logs = await eval_async(
                task,
                model="mockllm/model",
                epochs=2,
                max_samples=2,
                max_tasks=1,
                log_dir=str(tmp_path),
                ctl_server=False,
            )
        finally:
            heartbeat.cancel()
            with pytest.raises(asyncio.CancelledError):
                await heartbeat
            state.finish()
            progress.current.reset(token)
        assert peak == 2
        assert state.completed == 4
        expected = {(task.name, str(case), epoch) for case in (1, 2) for epoch in (1, 2)}
        summary = completeness.report(logs, expected=expected)
        assert not completeness.failed(summary)

    asyncio.run(run())
    _assert_lifecycle(capsys.readouterr().out)
    assert progress.current.get() is None


def _assert_lifecycle(output: str) -> None:
    events = _events(output)
    assert _active_heartbeat(events)
    ended = [event for event in events if event["event"] == "sample_end"]
    assert {(event["case"], event["epoch"]) for event in ended} == {(1, 1), (1, 2), (2, 1), (2, 2)}


@pytest.mark.parametrize("outcome", ["error", "cancel"])
def evaluation_stops_heartbeat(outcome: str, *, capsys: pytest.CaptureFixture[str]) -> None:
    async def fail(*args: object, **kwargs: object) -> list[object]:
        state = progress.current.get()
        assert state is not None
        state.active["execution"] = {"task": "baseline", "case": "public", "epoch": 1}
        await asyncio.sleep(0)
        if outcome == "error":
            raise RuntimeError("engine failed")
        raise asyncio.CancelledError

    async def run() -> None:
        with (
            patch.object(evaluation, "eval_async", side_effect=fail),
            pytest.raises(RuntimeError if outcome == "error" else asyncio.CancelledError),
        ):
            await evaluation.evaluate_async(
                evaluation_settings.EvaluationSettings(
                    model="mockllm/model",
                    model_cost=evaluation_settings.ModelPricing(
                        input=0.0, output=0.0, input_cache_write=0.0, input_cache_read=0.0
                    ),
                )
            )
        assert progress.current.get() is None
        assert len(asyncio.all_tasks()) == 1

    asyncio.run(run())
    output = capsys.readouterr().out
    assert '"outcome": "aborted"' in output
    assert '"event": "run_end"' in output


def native_evaluation_success(*, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from inspect_ai.solver import generate  # noqa: PLC0415

    task = Task(
        name="profile",
        dataset=[Sample(id="case", input="question", target="yes")],
        solver=generate(),
        scorer=_complete_score(),
    )
    with patch.object(evaluation, "evaluation_tasks", return_value=[task]):
        result = asyncio.run(
            evaluation.evaluate_async(
                evaluation_settings.EvaluationSettings(
                    model="mockllm/model",
                    model_cost=evaluation_settings.ModelPricing(
                        input=0.0, output=0.0, input_cache_write=0.0, input_cache_read=0.0
                    ),
                    epochs=1,
                    max_samples=2,
                    log_dir=str(tmp_path),
                )
            )
        )
    assert result == 0
    assert '"lifecycle_missing": 0' in capsys.readouterr().out


def telemetry_write_error_is_recorded() -> None:
    state = progress.Progress()
    with (
        patch("sys.stdout.write", side_effect=OSError("closed stream")),
        pytest.raises(OSError, match="closed stream"),
    ):
        state.emit("heartbeat")
    assert state.telemetry_errors == 1


def inactive_hooks_are_noops() -> None:
    from typing import cast  # noqa: PLC0415

    from inspect_ai.hooks import SampleEnd, SampleInit, SampleStart, TaskStart  # noqa: PLC0415

    async def run() -> None:
        hooks = progress.ProgressHooks()
        await hooks.on_task_start(cast(TaskStart, None))
        await hooks.on_sample_init(cast(SampleInit, None))
        await hooks.on_sample_start(cast(SampleStart, None))
        await hooks.on_sample_end(cast(SampleEnd, None))

    asyncio.run(run())


def incomplete_native_records_fail() -> None:
    from types import SimpleNamespace  # noqa: PLC0415
    from typing import cast  # noqa: PLC0415

    from inspect_ai.log import EvalLog  # noqa: PLC0415
    from inspect_ai.scorer import Score  # noqa: PLC0415

    sample = SimpleNamespace(
        id="case",
        epoch=1,
        scores={
            "score": Score(
                value={"correctness": 0, "scope": 0}, metadata={"agent_failure": "crash"}
            )
        },
        error="infrastructure failure",
        limit="token",
    )
    log = cast(
        EvalLog,
        SimpleNamespace(
            eval=SimpleNamespace(task="profile"),
            samples=[sample, sample],
            status="error",
        ),
    )
    expected = {("profile", "case", 1), ("profile", "missing", 1)}
    summary = completeness.report([log], expected=expected)
    assert completeness.failed(summary)
    assert summary == {
        "expected": 2,
        "scored": 1,
        "missing": [("profile", "missing", 1)],
        "unexpected": [],
        "duplicates": [("profile", "case", 1)],
        "failed_tasks": 1,
        "errors": 2,
        "crashes": 2,
        "cutoffs": 2,
    }
    assert completeness.report([log], expected=set())["unexpected"] == [("profile", "case", 1)]


def public_concurrency_override() -> None:
    with patch.object(evaluation, "evaluate_async", return_value=0) as execute:
        assert asyncio.run(commands.evaluate(model="mockllm/model", max_samples=3)) == 0
    assert execute.call_args.args[0].max_samples == 3


def _events(output: str) -> list[dict[str, object]]:
    return [json.loads(line) for line in output.splitlines() if line.startswith("{")]


def _active_heartbeat(events: list[dict[str, object]]) -> bool:
    return any(event["event"] == "heartbeat" and bool(event["active"]) for event in events)


@pytest.mark.parametrize("source", ["parent", "vm"])
def telemetry_writes_one_complete_line(source: str) -> None:
    from evals.python.integrations.hugging_face import sandbox  # noqa: PLC0415

    with patch("sys.stdout") as stream:
        if source == "parent":
            progress.Progress(run="run").emit("sample_start", case="public-case")
        else:
            sandbox.event("vm_ready", handle="sandbox-id")
    stream.write.assert_called_once()
    stream.flush.assert_called_once_with()
    line = stream.write.call_args.args[0]
    assert line.endswith("\n")
    assert len(line.splitlines()) == 1
    assert json.loads(line)["event"] == ("sample_start" if source == "parent" else "vm_ready")
