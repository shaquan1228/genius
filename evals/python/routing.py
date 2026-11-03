"""Routing: the choices an agent makes before the work, read back from its tool calls.

Each route kind names one choice point. It observes the agent's choice from the
recorded trace and takes the accepted choices from the case declaration, so existing
cases grade routing without a separate dataset. `None` means the agent chose nothing.
"""

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from itertools import chain

from pydantic import JsonValue

from evals.python import Declaration

__all__ = ["KINDS", "Call", "Choice", "Route", "RouteKind", "assess"]

type Call = Mapping[str, JsonValue]
type Choice = str | None

SKILL_FILE = re.compile(r"(?:^|[/\s'\"])skills/([a-z][a-z0-9-]*)/SKILL\.md\b")
SKILL_TOOLS = frozenset({"Skill", "skill"})


@dataclass(frozen=True, kw_only=True)
class RouteKind:
    """One choice point: how to observe the agent's choice and which choices are accepted."""

    name: str
    observe: Callable[[Sequence[Call]], Choice]
    expect: Callable[[Declaration], tuple[Choice, ...]]


@dataclass(frozen=True, kw_only=True)
class Route:
    """One graded choice: what the agent chose and what the case accepts."""

    kind: str
    observed: Choice
    accepted: tuple[Choice, ...]

    @property
    def passed(self) -> bool:
        return self.observed in self.accepted

    def details(self) -> dict[str, JsonValue]:
        return {"observed": self.observed, "accepted": list(self.accepted), "passed": self.passed}


def strings(value: JsonValue) -> tuple[str, ...]:
    """Every string inside a tool argument value, depth first."""
    if isinstance(value, str):
        return (value,)
    items = value.values() if isinstance(value, dict) else value if isinstance(value, list) else ()
    return tuple(chain.from_iterable(map(strings, items)))


def invoked_skill(call: Call) -> Choice:
    """The skill a call loads: a skill tool's argument, or a SKILL.md path it reads."""
    arguments = call.get("arguments")
    if call.get("name") in SKILL_TOOLS and isinstance(arguments, dict):
        named = arguments.get("skill", arguments.get("name"))
        if isinstance(named, str):
            return named.rpartition(":")[2]
    match = next(filter(None, map(SKILL_FILE.search, strings(arguments))), None)
    return match.group(1) if match else None


def first_skill(trace: Sequence[Call]) -> Choice:
    """The first skill the agent loaded, or None when it loaded none."""
    return next(filter(None, map(invoked_skill, trace)), None)


def accepted_skills(declaration: Declaration) -> tuple[Choice, ...]:
    """The skills a case accepts: its declared override, else the skill it exercises."""
    return declaration.routes.get("skill", (declaration.skill,))


SKILL = RouteKind(name="skill", observe=first_skill, expect=accepted_skills)
KINDS: tuple[RouteKind, ...] = (SKILL,)


def assess(trace: Sequence[Call], *, declaration: Declaration) -> tuple[Route, ...]:
    """Grade every registered route kind against one recorded trace."""
    return tuple(
        Route(kind=kind.name, observed=kind.observe(trace), accepted=kind.expect(declaration))
        for kind in KINDS
    )
