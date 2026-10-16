"""Pinned HumanEval+ records mapped to canonical case declarations."""

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from evals.python import queries
from evals.python.integrations.datasets.download import Download, cache_path, download
from evals.python.integrations.evalplus import checks
from kernel import Instruction, Plain, Reference, Task
from kernel._operations import fixture as fixture_ops

info = queries.DatasetInfo(
    source="https://github.com/evalplus/humanevalplus_release/releases/download/v0.1.10/HumanEvalPlus.jsonl.gz",
    revision="v0.1.10",
    sha256="42526ec0e7d5f3ee0b06d6ced98f8c8bae3d76519151bfb3d36f79010645bd7f",
    count=164,
    attributes={
        "evaluator_commit": "6eb1e199c2e370518e7bf3e8eee6322c2b23c89c",
        "numpy_version": "2.5.4",
        "psutil_version": "7.2.2",
    },
)


class Problem(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore", frozen=True)
    task_id: str = Field(pattern=r"\AHumanEval/(0|[1-9][0-9]*)\z")
    prompt: str
    entry_point: str = Field(min_length=1)
    canonical_solution: str


def declarations(records: Iterable[str]) -> tuple[Task, ...]:
    return tuple(declaration(raw) for raw in records)


def declaration(raw: str) -> Task:
    problem = Problem.model_validate_json(raw)
    return Task(
        id="humaneval-" + problem.task_id.split("/")[1],
        fixture=fixture_ops.of_files([("solution.py", problem.prompt)]),
        instruction=Instruction(
            skill="reasoning",
            prompt=(
                "Implement the specified function in solution.py. Preserve its signature and edit "
                "only solution.py."
            ),
        ),
        criterion=checks(
            record=raw, manifest={**info.model_dump(exclude={"attributes"}), **info.attributes}
        ),
        allowed_files=("solution.py",),
        reference=Reference(
            edits=fixture_ops.of_files(
                [("solution.py", problem.prompt + problem.canonical_solution)]
            ),
            completion=Plain(""),
        ),
    )


def cases() -> tuple[Task, ...]:
    data = download(
        request=Download(
            source=info.source, sha256=info.sha256, destination=cache_path(info.sha256)
        )
    )
    return declarations(data.decode().splitlines())
