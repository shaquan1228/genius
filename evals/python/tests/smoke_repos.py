import asyncio
from typing import NamedTuple

import pytest
from inspect_ai.util._sandbox.local import LocalSandboxEnvironment
from kernel import Outcome, Task, Verification

from evals.python import REPO_ROOT, datasets, verification
from evals.python.datasets import smoke
from evals.python.integrations.inspect.environments import environment, runtime

TASKS = {record.task.id: record.task for record in smoke.cases() if record.skill == "improve"}


def _fixture(task: Task) -> dict[str, str]:
    return {file.path: file.contents for file in task.fixture}


def _reference(task: Task) -> dict[str, str]:
    return {file.path: file.contents for file in task.reference.edits}


def _verify(files: dict[str, str], *, task: Task) -> Verification:
    async def execute() -> Verification:
        agent = LocalSandboxEnvironment()
        try:
            for name, contents in files.items():
                await agent.write_file(f"workspace/{name}", contents.encode())
            result = await verification.verify(
                task.checks(), agent=environment(agent), runtime=runtime(agent)
            )
            return result.verification
        finally:
            await LocalSandboxEnvironment.sample_cleanup(
                "test", None, {"default": agent}, interrupted=False
            )

    return asyncio.run(execute())


def _grade(case_id: str, *, rewrites: dict[str, str]) -> tuple[bool, bool]:
    task = TASKS[case_id]
    original = _fixture(task)
    files = original | rewrites
    changed = sorted(path for path, text in files.items() if original.get(path) != text)
    outcome = Outcome(
        changed_files=changed,
        verification=_verify(files, task=task),
        response=None,
        facts=[],
    )
    scores = dict(task.grade(outcome=outcome))
    return scores["correctness"], scores["scope"]


def smoke_holds_six_improve_cases_with_a_shipped_skill() -> None:
    assert len(TASKS) == 6
    assert set(TASKS) <= set(datasets.load_dataset().records)
    assert (REPO_ROOT / "skills" / "improve" / "SKILL.md").is_file()


def every_fixture_holds_a_decoy_outside_scope() -> None:
    for task in TASKS.values():
        assert set(_fixture(task)) - set(task.allowed_files), task.id


@pytest.mark.parametrize("case_id", sorted(TASKS))
def untouched_fixture_fails_and_reference_passes(case_id: str) -> None:
    task = TASKS[case_id]
    expected_untouched = (case_id == "dedupe-rule", True)
    assert _grade(case_id, rewrites={}) == expected_untouched
    assert _grade(case_id, rewrites=_reference(task)) == (True, True)
    assert all(dict(task.grade_reference(verification=Verification.Passed())).values())


HINT = 'argument-hint: "[task]"\n'
RULE = "- Run tests with `python3 -I -B`.\n"


class Control(NamedTuple):
    case_id: str
    name: str
    edits: tuple[tuple[str, str, str], ...]
    expected: tuple[bool, bool]
    on_reference: bool = False


CONTROLS = [
    Control(
        "scaffold-drift",
        "fix the deviant and the vendored copy",
        (("upstream-skill-delta.md", "---\n\n<!--", f"{HINT}---\n\n<!--"),),
        (True, False),
        on_reference=True,
    ),
    Control(
        "scaffold-drift",
        "fix only the vendored copy",
        (("upstream-skill-delta.md", "---\n\n<!--", f"{HINT}---\n\n<!--"),),
        (False, False),
    ),
    Control(
        "scaffold-drift",
        "field outside the frontmatter",
        (("skill-gamma.md", "## Task", f"{HINT}## Task"),),
        (False, True),
    ),
    Control(
        "widen-note",
        "widen and fix the docstring typo",
        (("retry.py", "recieve", "receive"),),
        (False, True),
        on_reference=True,
    ),
    Control(
        "widen-note",
        "widen the deprecated twin",
        (("retry_legacy.py", "on timeouts.", "on timeouts and dropped connections."),),
        (False, False),
    ),
    Control(
        "widen-note",
        "add a second comment",
        (("retry.py", "timeouts.\n", "timeouts.\n        # Also on dropped connections.\n"),),
        (False, True),
    ),
    Control(
        "codify-repo-pattern",
        "rule in the pointer file",
        (("CLAUDE.md", "conventions.\n", f"conventions.\n{RULE}"),),
        (False, False),
    ),
    Control(
        "codify-repo-pattern",
        "rule in the contributor guide",
        (("CONTRIBUTING.md", "AGENTS.md.\n", f"AGENTS.md.\n{RULE}"),),
        (False, False),
    ),
    Control(
        "codify-repo-pattern",
        "repo rule in the web-only list",
        (("AGENTS.md", "Component`.\n", f"Component`.\n{RULE}"),),
        (False, True),
    ),
    Control(
        "codify-package-pattern",
        "web rule in the repo-wide list",
        (("AGENTS.md", "cover.\n", "cover.\n- Every web component sets `display_name`.\n"),),
        (False, True),
    ),
    Control(
        "dedupe-rule",
        "restate the rule as a second bullet",
        (("AGENTS.md", "cover.\n", "cover.\n- Do not commit generated files in `dist/`.\n"),),
        (False, True),
    ),
    Control(
        "dedupe-rule",
        "reword the existing rule in place",
        (("AGENTS.md", "build output", "generated output"),),
        (True, True),
    ),
    Control(
        "delete-stale",
        "also rewrite the changelog",
        (("CHANGELOG.md", "- Added `deploy.sh`.\n", ""),),
        (True, False),
        on_reference=True,
    ),
    Control(
        "delete-stale",
        "replace the stale line with an invented one",
        (("RELEASING.md", "run `deploy.sh` locally.", "ask the release manager."),),
        (False, True),
    ),
    Control(
        "delete-stale",
        "fix the unrelated typo",
        (("README.md", "recieve", "receive"),),
        (False, True),
        on_reference=True,
    ),
]


def _rewrites(control: Control) -> dict[str, str]:
    task = TASKS[control.case_id]
    workspace = _fixture(task) | (_reference(task) if control.on_reference else {})
    rewrites = dict(workspace) if control.on_reference else {}
    for path, old, new in control.edits:
        current = rewrites.get(path, workspace[path])
        assert old in current, (path, old)
        rewrites[path] = current.replace(old, new, 1)
    return rewrites


@pytest.mark.parametrize("control", CONTROLS, ids=lambda control: control.name)
def careless_edits_lose_a_score(control: Control) -> None:
    assert _grade(control.case_id, rewrites=_rewrites(control)) == control.expected
