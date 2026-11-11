"""Load the touchup cases declared in ``touchup.toml``.

Each case starts the agent in a repo fixture full of decoys a careless edit would touch:
a pointer file, generated and deprecated twins, vendored and archived copies, history,
and a list scoped to one part of the repo. ``scope`` scores the file choice. The case's
check scores the edit itself against the fixture: what changed, and that nothing else did.

Fixture paths are flat because the pinned kernel accepts only single-segment paths, so
layout is carried by file names, headers, and section scope rather than directories.
"""

import tomllib
from pathlib import Path

from kernel import Instruction, Reference, SourceFile, Task
from pydantic import BaseModel, ConfigDict

from evals.python import Declaration
from evals.python.integrations.smoke import repo, repo_checks

info = None

SPEC = Path(__file__).with_suffix(".toml")
DATA = ConfigDict(extra="forbid", frozen=True)


class Edit(BaseModel):
    """Replace ``old`` with ``new`` once in ``path``. An empty ``new`` deletes ``old``."""

    model_config = DATA
    path: str
    old: str
    new: str


class Spec(BaseModel):
    model_config = DATA
    id: str
    fixture: str
    scope: tuple[str, ...]
    prompt: str
    edits: tuple[Edit, ...] = ()
    completion: str
    check: str


class Suite(BaseModel):
    model_config = DATA
    skill: str
    finish: str
    case: tuple[Spec, ...]


def apply(files: dict[str, str], *, edits: tuple[Edit, ...]) -> dict[str, str]:
    result = dict(files)
    for edit in edits:
        if result[edit.path].count(edit.old) != 1:
            raise ValueError(f"Edit target must occur once in {edit.path}: {edit.old!r}")
        result[edit.path] = result[edit.path].replace(edit.old, edit.new)
    return result


def sources(files: dict[str, str]) -> list[SourceFile]:
    return [SourceFile(path=path, contents=contents) for path, contents in files.items()]


def task(spec: Spec, *, finish: str) -> Task:
    if not {edit.path for edit in spec.edits} <= set(spec.scope):
        raise ValueError(f"Reference edits must stay inside scope: {spec.id}")
    fixture = repo(spec.fixture)
    reference = apply(fixture, edits=spec.edits)
    return Task(
        id=spec.id,
        fixture=sources(fixture),
        instruction=Instruction(prompt=spec.prompt + finish),
        criterion=repo_checks(
            original={path: fixture[path] for path in spec.scope}, program=spec.check
        ),
        allowed_files=spec.scope,
        reference=Reference(
            edits=sources({path: reference[path] for path in spec.scope}),
            completion=spec.completion,
        ),
    )


def load(path: Path = SPEC) -> Suite:
    return Suite.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))


def cases() -> tuple[Declaration, ...]:
    suite = load()
    return tuple(
        Declaration(skill=suite.skill, task=task(spec, finish=suite.finish)) for spec in suite.case
    )
