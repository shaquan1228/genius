"""Helpers for checks over a repo fixture, prepended to each check program.

``repo_checks`` in this package fills ``ORIGINAL`` with the fixture text of every input,
so a check can compare the candidate's file against the repo it started from.
"""

import difflib
from pathlib import Path

ORIGINAL: dict[str, str] = {}


def text(path: str) -> str:
    return Path(path).read_text()


def delta(path: str) -> tuple[list[str], list[str]]:
    """Lines added and removed relative to the fixture, in order."""
    before, after = ORIGINAL[path].splitlines(), text(path).splitlines()
    added: list[str] = []
    removed: list[str] = []
    matcher = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            removed += before[i1:i2]
            added += after[j1:j2]
    return added, removed


def section(path: str, *, heading: str) -> list[str]:
    """The lines under ``heading``, up to the next Markdown heading."""
    lines = text(path).splitlines()
    start = lines.index(heading) + 1
    stop = next((i for i in range(start, len(lines)) if lines[i].startswith("#")), len(lines))
    return lines[start:stop]
