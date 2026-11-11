"""Declare executable checks for private Python assertions."""

import tomllib
from pathlib import Path

from kernel import Criterion, Instruction, Reference, SourceFile, Task, Verifier
from pydantic import BaseModel, ConfigDict

from evals.python import Declaration

REPOS = Path(__file__).with_name("repos")
DATA = ConfigDict(extra="forbid", frozen=True)


def checks(*, inputs: tuple[str, ...], program: str) -> Criterion:
    return Criterion.Code(
        verifier=Verifier(
            inputs=inputs,
            files=[
                SourceFile(
                    path="verifier.py", contents=Path(__file__).with_name("verifier.py").read_text()
                )
            ],
            tools=[],
            command=("python3", "-I", "verifier.py", *inputs),
            stdin=program,
            timeout_seconds=30,
        )
    )


def repo(name: str) -> dict[str, str]:
    return {
        path.name: path.read_text(encoding="utf-8") for path in sorted((REPOS / name).iterdir())
    }


def repo_checks(*, original: dict[str, str], program: str) -> Criterion:
    support = Path(__file__).with_name("repo_support.py").read_text()
    return checks(
        inputs=tuple(original),
        program=f"{support}\nORIGINAL.update({original!r})\n\n{program}",
    )


class Edit(BaseModel):
    model_config = DATA
    path: str
    old: str
    new: str


class RepoCase(BaseModel):
    model_config = DATA
    id: str
    skill: str
    fixture: str
    scope: tuple[str, ...]
    prompt: str
    edits: tuple[Edit, ...] = ()
    completion: str
    check: str


class RepoCases(BaseModel):
    model_config = DATA
    case: tuple[RepoCase, ...]


def apply(files: dict[str, str], *, edits: tuple[Edit, ...]) -> dict[str, str]:
    result = dict(files)
    for edit in edits:
        if result[edit.path].count(edit.old) != 1:
            raise ValueError(f"Edit target must occur once in {edit.path}: {edit.old!r}")
        result[edit.path] = result[edit.path].replace(edit.old, edit.new)
    return result


def _sources(files: dict[str, str]) -> list[SourceFile]:
    return [SourceFile(path=path, contents=contents) for path, contents in files.items()]


def repo_task(case: RepoCase) -> Task:
    if not {edit.path for edit in case.edits} <= set(case.scope):
        raise ValueError(f"Reference edits must stay inside scope: {case.id}")
    fixture = repo(case.fixture)
    reference = apply(fixture, edits=case.edits)
    return Task(
        id=case.id,
        fixture=_sources(fixture),
        instruction=Instruction(prompt=case.prompt),
        criterion=repo_checks(
            original={path: fixture[path] for path in case.scope}, program=case.check
        ),
        allowed_files=case.scope,
        reference=Reference(
            edits=_sources({path: reference[path] for path in case.scope}),
            completion=case.completion,
        ),
    )


def repo_cases(path: Path) -> tuple[Declaration, ...]:
    cases = RepoCases.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
    return tuple(Declaration(skill=case.skill, task=repo_task(case)) for case in cases.case)
