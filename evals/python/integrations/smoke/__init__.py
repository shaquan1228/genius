"""Load smoke cases from TOML: repo edits with private checks, or graded answers."""

import tomllib
from pathlib import Path

from kernel import Criterion, Instruction, Reference, Rubric, SourceFile, Task, TextRule, Verifier
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


class AnswerCase(BaseModel):
    model_config = DATA
    id: str
    skill: str
    prompt: str
    expected: dict[str, str | bool]
    reason: str


class Cases(BaseModel):
    model_config = DATA
    case: tuple[RepoCase | AnswerCase, ...]


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


def answer_task(case: AnswerCase) -> Task:
    return Task(
        id=case.id,
        fixture=[],
        instruction=Instruction(prompt=case.prompt),
        criterion=Criterion.Answer(
            rubric=Rubric(
                expected=list(case.expected.items()),
                text_rule=TextRule(field="reason", min_words=1, max_words=40),
            )
        ),
        allowed_files=(),
        reference=Reference(edits=[], completion={**case.expected, "reason": case.reason}),
    )


def task(case: RepoCase | AnswerCase) -> Task:
    return repo_task(case) if isinstance(case, RepoCase) else answer_task(case)


def load_cases(path: Path) -> tuple[Declaration, ...]:
    cases = Cases.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
    return tuple(Declaration(skill=case.skill, task=task(case)) for case in cases.case)
