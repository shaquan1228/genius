from pathlib import Path

from kernel import Criterion, Instruction, Reference, Rubric, Task, TextRule

from evals.python import Declaration
from evals.python.integrations.smoke import repo_cases

info = None


def answer(*, id: str, prompt: str, expected: dict[str, str | bool], reason: str) -> Task:
    return Task(
        id=id,
        fixture=[],
        instruction=Instruction(prompt=prompt),
        criterion=Criterion.Answer(
            rubric=Rubric(
                expected=list(expected.items()),
                text_rule=TextRule(field="reason", min_words=1, max_words=40),
            )
        ),
        allowed_files=(),
        reference=Reference(
            edits=[],
            completion={**expected, "reason": reason},
        ),
    )


def cases() -> tuple[Declaration, ...]:
    decisions = (
        answer(
            id="small-decision",
            prompt=(
                "Choose a service for a one-month trial. A costs $10 total; B costs $8 total. "
                "Features, reliability, cancellation terms, and all other costs are identical. "
                "Reply with JSON containing choice (A or B) and reason (one sentence). "
                "Do not change files."
            ),
            expected={"choice": "B"},
            reason="B costs less for identical service.",
        ),
        answer(
            id="decision-review",
            prompt=(
                "I took a one-time $1 bet with a known 80% chance of winning $1 profit "
                "and 20% chance of losing $1. I could comfortably afford the loss. I lost. "
                "No new information about the odds appeared. Was the original decision "
                "supported, and should this loss alone "
                "change the rule? Reply with JSON containing decision_was_supported (boolean), "
                "change_rule (boolean), and reason (one sentence). Do not change files."
            ),
            expected={"decision_was_supported": True, "change_rule": False},
            reason="One loss did not change the known odds.",
        ),
    )
    return (
        *repo_cases(Path(__file__).with_suffix(".toml")),
        *(Declaration(skill="bayesian", task=task) for task in decisions),
    )
