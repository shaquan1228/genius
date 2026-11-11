"""Touchup cases: one small edit that must land in the right file of a confusing repo.

Each fixture holds decoys a careless edit would touch: a pointer file, a generated twin, a
deprecated twin, vendored and archived copies, history, and a list scoped to one part of
the repo. ``allowed_files`` scores the file choice. The private checks score the edit
itself against the original text: what changed, and that nothing else did.

Fixture paths are flat because the pinned kernel accepts only single-segment paths, so
layout is carried by file names, headers, and section scope rather than directories.
"""

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


def files(layout: dict[str, str]) -> list[SourceFile]:
    return [SourceFile(path=path, contents=contents) for path, contents in layout.items()]


def program(layout: dict[str, str], *, inputs: tuple[str, ...], body: str) -> str:
    return PRELUDE.format(original={path: layout[path] for path in inputs}) + body


def touch(  # noqa: PLR0913 - Each field is a distinct part of one declaration.
    *,
    id: str,
    layout: dict[str, str],
    prompt: str,
    edits: dict[str, str],
    body: str,
    completion: str,
) -> Task:
    inputs = tuple(edits)
    return Task(
        id=id,
        fixture=files(layout),
        instruction=Instruction(prompt=prompt + FINISH),
        criterion=checks(inputs=inputs, program=program(layout, inputs=inputs, body=body)),
        allowed_files=inputs,
        reference=Reference(edits=files(edits), completion=completion),
    )


def skill(name: str, *, hint: bool = True, header: str = "") -> str:
    argument = 'argument-hint: "[task]"\n' if hint else ""
    return (
        f"---\nname: {name}\ndescription: Run the {name} workflow.\n{argument}---\n\n"
        f"{header}## Task\n\nApply {name} to the supplied task.\n"
    )


def scaffold() -> Task:
    """A scaffold deviates from its template, contributor guide, and sibling majority."""
    target = "skill-gamma.md"
    layout = {
        "CONTRIBUTING.md": "# Contributing\n\n## Skills\n\n"
        "Each skill is a `skill-<name>.md` file. Start from `skill-template.md`.\n"
        "Frontmatter declares `name`, `description`, and `argument-hint`.\n\n"
        "`upstream-*.md` files mirror another repository. Do not edit them.\n"
        "`*.archived.md` files are retired. Do not edit them.\n",
        "skill-template.md": skill("<name>"),
        "skill-alpha.md": skill("alpha"),
        "skill-beta.md": skill("beta"),
        target: skill("gamma", hint=False),
        "upstream-skill-delta.md": skill(
            "delta", hint=False, header="<!-- Vendored from upstream. Do not edit. -->\n\n"
        ),
        "skill-omega.archived.md": skill("omega", hint=False),
    }
    return touch(
        id="scaffold-drift",
        layout=layout,
        prompt="One skill in this repo has drifted from the scaffold the repo prescribes. "
        "Touch it up so it conforms.",
        edits={target: skill("gamma")},
        body=f"""path = {target!r}
added, removed = delta(path)
assert removed == [], removed
assert len(added) == 1, added
assert added[0].startswith("argument-hint:") and added[0].split(":", 1)[1].strip(), added
front = text(path).split("---")[1].splitlines()
assert added[0] in front, "argument-hint must be in the frontmatter"
""",
        completion="Added argument-hint to skill-gamma.md, matching CONTRIBUTING.md.",
    )


def retry(*, comment: str, errors: str, header: str = "") -> str:
    return (
        f'{header}"""Retry helpers for the netkit client."""\n\nimport time\n\n\n'
        "def call_with_retry(operation, attempts=3, delay=0.1):\n"
        '    """Call operation again when calls do not recieve a reply."""\n'
        "    for attempt in range(attempts):\n"
        f"        # {comment}\n"
        "        try:\n"
        "            return operation()\n"
        f"        except {errors}:\n"
        "            if attempt == attempts - 1:\n"
        "                raise\n"
        "            time.sleep(delay)\n"
    )


def widen() -> Task:
    """A narrow comment must be widened in the live copy, not its legacy or built twins."""
    target = "retry.py"
    live = "(TimeoutError, ConnectionError)"
    layout = {
        "pyproject.toml": '[project]\nname = "netkit"\n\n'
        '[tool.setuptools]\npy-modules = ["retry"]\n',
        target: retry(comment="Retry on timeouts.", errors=live),
        "retry_legacy.py": retry(
            comment="Retry on timeouts.",
            errors="TimeoutError",
            header="# Deprecated: kept for the 1.x API. Not imported by netkit.\n",
        ),
        "retry_build.py": retry(
            comment="Retry on timeouts.",
            errors=live,
            header="# Generated by setup.py build. Do not edit.\n",
        ),
    }
    return touch(
        id="widen-note",
        layout=layout,
        prompt="The retry comment in netkit is narrower than the behavior it describes. Widen it.",
        edits={target: retry(comment="Retry on timeouts and dropped connections.", errors=live)},
        body=f"""path = {target!r}
assert ast.dump(ast.parse(text(path))) == ast.dump(ast.parse(ORIGINAL[path])), "code changed"
added, removed = delta(path)
assert removed == ["        # Retry on timeouts."], removed
assert len(added) == 1 and added[0].lstrip().startswith("#"), added
assert "connection" in added[0].lower(), added
""",
        completion="Widened the comment in retry.py to cover dropped connections.",
    )


def agents(*, repo: tuple[str, ...] = (), web: tuple[str, ...] = ()) -> str:
    """The canonical doc: repo-wide conventions first, then the web client's own section."""

    def bullets(lines: tuple[str, ...]) -> str:
        return "".join(f"- {line}\n" for line in lines)

    return (
        "# Agents\n\n## Conventions\n\nThese apply to every part of the repo.\n\n"
        "- Keep functions small and name them for what they return.\n"
        f"- Put tests next to the module they cover.\n{bullets(repo)}\n"
        "## Web client\n\nThese apply only to `web_*.py` modules.\n\n"
        f"- Components subclass `web_base.Component`.\n{bullets(web)}"
    )


def monorepo(root: str) -> dict[str, str]:
    """A pointer file, the canonical doc it names, a contributor guide, and two services."""
    return {
        "CLAUDE.md": "See AGENTS.md for repository conventions.\n",
        "AGENTS.md": root,
        "CONTRIBUTING.md": "# Contributing\n\nOpen a pull request against `main`. "
        "Agent conventions live in AGENTS.md.\n",
        "Makefile": "test-api:\n\tpython3 -I -B -m unittest api_test\n\n"
        "test-web:\n\tpython3 -I -B -m unittest web_test\n\n"
        "test-tools:\n\tpython3 -I -B -m unittest tools_test\n",
        "api_routes.py": 'ROUTES = {"/health": "ok"}\n',
        "web_base.py": "class Component:\n    display_name = None\n",
        "web_button.py": "from web_base import Component\n\n\n"
        'class Button(Component):\n    display_name = "Button"\n',
        "web_card.py": "from web_base import Component\n\n\n"
        'class Card(Component):\n    display_name = "Card"\n',
    }


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
        layout=monorepo(agents()),
        prompt="Every test target in this repo now runs Python with -I -B, and that is the "
        "convention from now on. Codify it where agents will read it.",
        edits={"AGENTS.md": agents(repo=("Run tests with `python3 -I -B`.",))},
        body=added_bullet(heading="## Conventions", terms=("-I", "-B")),
        completion="Added the -I -B test rule to AGENTS.md Conventions; CLAUDE.md points there.",
    )


def package_rule() -> Task:
    """A pattern seen only in the web client belongs in that client's scoped list."""
    return touch(
        id="codify-package-pattern",
        layout=monorepo(agents()),
        prompt="Every web component now sets display_name. Write that convention down where "
        "agents will read it.",
        edits={"AGENTS.md": agents(web=("Every component sets `display_name`.",))},
        body=added_bullet(heading="## Web client", terms=("display_name",)),
        completion="Added the display_name rule to the Web client section of AGENTS.md.",
    )


def dedupe() -> Task:
    """The requested rule already exists in other words; a second copy is a failure."""
    root = agents(repo=("Never commit build output from `dist/` or `build/`.",))
    return touch(
        id="dedupe-rule",
        layout=monorepo(root),
        prompt="Add a rule so agents stop committing generated files in dist/.",
        edits={"AGENTS.md": root},
        body="""path = "AGENTS.md"
assert sum("dist/" in line for line in text(path).splitlines()) == 1, "rule duplicated"
added, removed = delta(path)
assert all("dist/" in line for line in added + removed), (added, removed)
""",
        completion="AGENTS.md already forbids committing dist/ output; no change was needed.",
    )


def readme(*, deploy: bool) -> str:
    line = "- `deploy.sh`: upload the wheel to the package index.\n" if deploy else ""
    return (
        "# Tool\n\n## Scripts\n\n- `build.sh`: build the wheel.\n"
        f"{line}\n## Usage\n\nRun `tool --help` to recieve the full option list.\n"
    )


def release(*, deploy: bool) -> str:
    line = "For hotfixes, run `deploy.sh` locally.\n" if deploy else ""
    return f"# Releasing\n\nReleases publish from CI when a tag is pushed.\n{line}"


def delete() -> Task:
    """Stale references leave current docs; the changelog keeps its history."""
    layout = {
        "build.sh": "#!/bin/sh\npython3 -m build\n",
        "README.md": readme(deploy=True),
        "RELEASING.md": release(deploy=True),
        "CHANGELOG.md": "# Changelog\n\n## 2.0.0\n\n"
        "- Removed `deploy.sh`. Releases publish from CI.\n\n"
        "## 1.4.0\n\n- Added `deploy.sh`.\n",
    }
    return touch(
        id="delete-stale",
        layout=layout,
        prompt="deploy.sh was removed and releases now publish from CI. Clean up the "
        "docs that still point to it.",
        edits={"README.md": readme(deploy=False), "RELEASING.md": release(deploy=False)},
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
