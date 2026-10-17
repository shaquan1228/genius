"""Download pinned HumanEval+ records and map them to canonical case declarations."""

import gzip
import hashlib
import os
import urllib.request
from collections.abc import Iterable
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import BaseModel, ConfigDict, Field

from evals.python.integrations.evalplus import checks
from evals.python.schema import DatasetInfo
from kernel import Completion, File, Fixture, Instruction, Reference, Task

info = DatasetInfo(
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
    return Task.create(
        id="humaneval-" + problem.task_id.split("/")[1],
        fixture=Fixture.create(files=[File.create(path="solution.py", contents=problem.prompt)]),
        instruction=Instruction.create(
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
            edits=Fixture.create(
                files=[
                    File.create(
                        path="solution.py", contents=problem.prompt + problem.canonical_solution
                    )
                ]
            ),
            completion=Completion.Plain(text=""),
        ),
    )


def _cache_path(sha256: str) -> Path:
    root = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    return root / "genius-evals" / f"{sha256}.jsonl"


def _download(*, source: str, sha256: str, destination: Path) -> bytes:
    if destination.exists():
        data = destination.read_bytes()
    else:
        with urllib.request.urlopen(source, timeout=60) as response:
            data = gzip.decompress(response.read())
    if hashlib.sha256(data).hexdigest() != sha256:
        raise ValueError("Dataset checksum mismatch")
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
            temporary = Path(stream.name)
            try:
                stream.write(data)
                stream.close()
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)
    return data


def cases() -> tuple[Task, ...]:
    data = _download(source=info.source, sha256=info.sha256, destination=_cache_path(info.sha256))
    return declarations(data.decode().splitlines())
