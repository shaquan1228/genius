"""Per-evaluation public lifecycle events; prompts and answers never enter telemetry."""

import asyncio
import json
import sys
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import monotonic
from typing import override
from uuid import uuid4

from inspect_ai.hooks import Hooks, SampleEnd, SampleInit, SampleStart, TaskStart, hooks


@dataclass
class Progress:
    run: str = field(default_factory=lambda: uuid4().hex)
    started: float = field(default_factory=monotonic)
    tasks: dict[str, str] = field(default_factory=dict)
    active: dict[str, dict[str, object]] = field(default_factory=dict)
    completed: int = 0
    telemetry_errors: int = 0

    def emit(self, event: str, **fields: object) -> None:
        try:
            sys.stdout.write(
                json.dumps(
                    {
                        "event": event,
                        "run": self.run,
                        "elapsed": round(monotonic() - self.started, 3),
                        "timestamp": datetime.now(UTC).isoformat(),
                        **fields,
                    }
                )
                + "\n"
            )
            sys.stdout.flush()
        except Exception:
            self.telemetry_errors += 1
            raise

    def sample(self, data: SampleInit | SampleStart, *, event: str) -> None:
        identity: dict[str, object] = {
            "task": self.tasks[data.eval_id],
            "case": data.summary.id,
            "epoch": data.summary.epoch,
            "sample": data.sample_id,
        }
        self.active[data.sample_id] = identity
        self.emit(event, **identity)

    async def heartbeat(self, *, interval: float = 30) -> None:
        while True:
            await asyncio.sleep(interval)
            self.emit(
                "heartbeat",
                completed=self.completed,
                active=list(self.active.values()),
                elapsed=round(monotonic() - self.started, 1),
            )

    def finish(self) -> None:
        for identity in self.active.values():
            self.emit("sample_end", **identity, outcome="aborted")
        self.active.clear()
        self.emit("run_end", completed=self.completed)


current: ContextVar[Progress | None] = ContextVar("evaluation_progress", default=None)


@hooks(name="genius-progress", description="Public evaluation lifecycle")
class ProgressHooks(Hooks):
    @override
    async def on_task_start(self, data: TaskStart) -> None:
        if state := current.get():
            state.tasks[data.eval_id] = data.spec.task

    @override
    async def on_sample_init(self, data: SampleInit) -> None:
        if state := current.get():
            state.sample(data, event="sample_init")

    @override
    async def on_sample_start(self, data: SampleStart) -> None:
        if state := current.get():
            state.sample(data, event="sample_start")

    @override
    async def on_sample_end(self, data: SampleEnd) -> None:
        if state := current.get():
            identity = state.active.pop(data.sample_id)
            state.completed += 1
            state.emit(
                "sample_end", **identity, outcome="error" if data.sample.error else "complete"
            )
