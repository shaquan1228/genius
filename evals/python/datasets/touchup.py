"""Touchup cases: one small edit that must land in the right file of a confusing repo.

Each fixture holds decoys a careless edit would touch: a pointer file, a generated twin, a
deprecated twin, vendored and archived copies, history, and a list scoped to one part of
the repo. ``allowed_files`` scores the file choice. The private checks score the edit
itself against the original text: what changed, and that nothing else did.

Each scenario's repo lives as plain files under ``fixtures/touchup/<repo>/``. A case names
its repo, the files in scope, and the reference as text replacements on those files.

Fixture paths are flat because the pinned kernel accepts only single-segment paths, so
layout is carried by file names, headers, and section scope rather than directories.
"""

from pathlib import Path
from typing import NamedTuple

from kernel import Instruction, Reference, SourceFile, Task

from evals.python import Declaration
from evals.python.integrations.smoke import checks

info = None

FINISH = " Make the change and summarize it."

PRELUDE = '''import ast
import difflib
import pathlib

ORIGINAL = {original!r}


def text(path):
    return pathlib.Path(path).read_text()


def delta(path):
    """Lines added and removed relative to the fixture, in order."""
    before, after = ORIGINAL[path].splitlines(), text(path).splitlines()
    added, removed = [], []
    matcher = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            removed += before[i1:i2]
            added += after[j1:j2]
    return added, removed


def section(path, heading):
    lines = text(path).splitlines()
    start = lines.index(heading) + 1
    stop = next((i for i in range(start, len(lines)) if lines[i].startswith("#")), len(lines))
    return lines[start:stop]

'''


FIXTURES = Path(__file__).with_name("fixtures") / "touchup"


class Edit(NamedTuple):
    """Replace ``old`` with ``new`` once in ``path``. An empty ``new`` deletes ``old``."""

    path: str
    old: str
    new: str


def repo(name: str) -> dict[str, str]:
    """Every file of one fixture repo, keyed by its path in the candidate workspace."""
    return {
        path.name: path.read_text(encoding="utf-8") for path in sorted((FIXTURES / name).iterdir())
    }


def apply(layout: dict[str, str], *, edits: tuple[Edit, ...]) -> dict[str, str]:
    result = dict(layout)
    for edit in edits:
        if result[edit.path].count(edit.old) != 1:
            raise ValueError(f"Edit target must occur once in {edit.path}: {edit.old!r}")
        result[edit.path] = result[edit.path].replace(edit.old, edit.new)
    return result


def files(layout: dict[str, str]) -> list[SourceFile]:
    return [SourceFile(path=path, contents=contents) for path, contents in layout.items()]


def program(layout: dict[str, str], *, inputs: tuple[str, ...], body: str) -> str:
    return PRELUDE.format(original={path: layout[path] for path in inputs}) + body


def touch(  # noqa: PLR0913 - Each field is a distinct part of one declaration.
    *,
    id: str,
    fixture: str,
    scope: tuple[str, ...],
    prompt: str,
    edits: tuple[Edit, ...],
    body: str,
    completion: str,
) -> Task:
    """Build a case: the agent may change only ``scope``; ``edits`` produce the reference."""
    if not {edit.path for edit in edits} <= set(scope):
        raise ValueError("Reference edits must stay inside scope")
    layout = repo(fixture)
    reference = apply(layout, edits=edits)
    return Task(
        id=id,
        fixture=files(layout),
        instruction=Instruction(prompt=prompt + FINISH),
        criterion=checks(inputs=scope, program=program(layout, inputs=scope, body=body)),
        allowed_files=scope,
        reference=Reference(
            edits=files({path: reference[path] for path in scope}), completion=completion
        ),
    )


def scaffold() -> Task:
    """A scaffold deviates from its template, contributor guide, and sibling majority."""
    return touch(
        id="scaffold-drift",
        fixture="skills",
        scope=("skill-gamma.md",),
        prompt="One skill in this repo has drifted from the scaffold the repo prescribes. "
        "Touch it up so it conforms.",
        edits=(
            Edit("skill-gamma.md", "workflow.\n---", 'workflow.\nargument-hint: "[task]"\n---'),
        ),
        body="""path = "skill-gamma.md"
added, removed = delta(path)
assert removed == [], removed
assert len(added) == 1, added
assert added[0].startswith("argument-hint:") and added[0].split(":", 1)[1].strip(), added
front = text(path).split("---")[1].splitlines()
assert added[0] in front, "argument-hint must be in the frontmatter"
""",
        completion="Added argument-hint to skill-gamma.md, matching CONTRIBUTING.md.",
    )


def widen() -> Task:
    """A narrow comment must be widened in the live copy, not its legacy or built twins."""
    return touch(
        id="widen-note",
        fixture="netkit",
        scope=("retry.py",),
        prompt="The retry comment in netkit is narrower than the behavior it describes. Widen it.",
        edits=(Edit("retry.py", "on timeouts.", "on timeouts and dropped connections."),),
        body="""path = "retry.py"
assert ast.dump(ast.parse(text(path))) == ast.dump(ast.parse(ORIGINAL[path])), "code changed"
added, removed = delta(path)
assert removed == ["        # Retry on timeouts."], removed
assert len(added) == 1 and added[0].lstrip().startswith("#"), added
assert "connection" in added[0].lower(), added
""",
        completion="Widened the comment in retry.py to cover dropped connections.",
    )


def added_bullet(*, heading: str, terms: tuple[str, ...]) -> str:
    return f"""path = "AGENTS.md"
added, removed = delta(path)
assert removed == [], removed
assert len(added) == 1 and added[0].startswith("- "), added
assert added[0] in section(path, {heading!r}), "rule must join the list for its scope"
assert all(term in added[0] for term in {terms!r}), added
"""


def repo_rule() -> Task:
    """A repo-wide pattern belongs in the repo-wide list of the doc a pointer names."""
    return touch(
        id="codify-repo-pattern",
        fixture="monorepo",
        scope=("AGENTS.md",),
        prompt="Every test target in this repo now runs Python with -I -B, and that is the "
        "convention from now on. Codify it where agents will read it.",
        edits=(Edit("AGENTS.md", "`build/`.\n", "`build/`.\n- Run tests with `python3 -I -B`.\n"),),
        body=added_bullet(heading="## Conventions", terms=("-I", "-B")),
        completion="Added the -I -B test rule to AGENTS.md Conventions; CLAUDE.md points there.",
    )


def package_rule() -> Task:
    """A pattern seen only in the web client belongs in that client's scoped list."""
    return touch(
        id="codify-package-pattern",
        fixture="monorepo",
        scope=("AGENTS.md",),
        prompt="Every web component now sets display_name. Write that convention down where "
        "agents will read it.",
        edits=(
            Edit(
                "AGENTS.md",
                "`web_base.Component`.\n",
                "`web_base.Component`.\n- Every component sets `display_name`.\n",
            ),
        ),
        body=added_bullet(heading="## Web client", terms=("display_name",)),
        completion="Added the display_name rule to the Web client section of AGENTS.md.",
    )


def dedupe() -> Task:
    """The requested rule already exists in other words; a second copy is a failure."""
    return touch(
        id="dedupe-rule",
        fixture="monorepo",
        scope=("AGENTS.md",),
        prompt="Add a rule so agents stop committing generated files in dist/.",
        edits=(),
        body="""path = "AGENTS.md"
assert sum("dist/" in line for line in text(path).splitlines()) == 1, "rule duplicated"
added, removed = delta(path)
assert all("dist/" in line for line in added + removed), (added, removed)
""",
        completion="AGENTS.md already forbids committing dist/ output; no change was needed.",
    )


def delete() -> Task:
    """Stale references leave current docs; the changelog keeps its history."""
    return touch(
        id="delete-stale",
        fixture="release",
        scope=("README.md", "RELEASING.md"),
        prompt="deploy.sh was removed and releases now publish from CI. Clean up the "
        "docs that still point to it.",
        edits=(
            Edit("README.md", "- `deploy.sh`: upload the wheel to the package index.\n", ""),
            Edit("RELEASING.md", "For hotfixes, run `deploy.sh` locally.\n", ""),
        ),
        body="""for path in ("README.md", "RELEASING.md"):
    added, removed = delta(path)
    assert "deploy.sh" not in text(path), path
    assert removed and all("deploy.sh" in line for line in removed), (path, removed)
    assert added == [], (path, added)
assert "recieve" in text("README.md"), "unrelated typo was edited"
""",
        completion="Removed deploy.sh from README.md and RELEASING.md; the changelog is history.",
    )


def cases() -> tuple[Declaration, ...]:
    tasks = (scaffold(), widen(), repo_rule(), package_rule(), dedupe(), delete())
    return tuple(Declaration(skill="touchup", task=task) for task in tasks)
