"""Pure Python declarations for the default four-case smoke dataset."""

from kernel import Criterion, Instruction, Reference, Rubric, SourceFile, Task, TextRule

from evals.python.dataset import Declaration
from evals.python.integrations.smoke import checks

info = None


def receipt(*, term: str = "price") -> Task:
    return Task(
        id="clear-task",
        fixture=[
            SourceFile(
                path="receipt.py",
                contents="def total(items):\n"
                f"    return sum({term} for price, quantity in items)\n",
            ),
            SourceFile(
                path="test_receipt.py",
                contents="""import runpy

total = runpy.run_path("receipt.py")["total"]
assert total([]) == 0
assert total([(3.0, 1), (4.0, 1)]) == 7.0
""",
            ),
        ],
        instruction=Instruction(
            prompt=(
                "Fix total in receipt.py so each item's quantity contributes to the total. "
                "Change only receipt.py. Verify with python3 -I -B test_receipt.py. "
                "Complete the change and summarize it."
            ),
        ),
        criterion=checks(
            inputs=("receipt.py",),
            program="""import runpy

total = runpy.run_path("receipt.py")["total"]
assert total([]) == 0
assert total([(3.0, 4)]) == 12.0
assert total([(3.0, 0)]) == 0.0
assert total([(2.0, 3), (4.0, 2)]) == 14.0
assert total([(1.5, 2)]) == 3.0
""",
        ),
        allowed_files=("receipt.py",),
        reference=Reference(
            edits=[
                SourceFile(
                    path="receipt.py",
                    contents="def total(items):\n"
                    "    return sum(price * quantity for price, quantity in items)\n",
                )
            ],
            completion="Each quantity now contributes to the total.",
        ),
    )


def client(timeout: int) -> str:
    return f"""fallback_timeout = {timeout}


def timeout(value=None):
    if value is None:
        return fallback_timeout
    if value <= 0:
        raise ValueError("timeout must be positive")
    return value
"""


def timeout(*, initial: int = 15, requested: int = 30) -> Task:
    if initial <= 0 or requested <= 0 or initial == requested:
        raise ValueError("Timeout changes need distinct positive initial and requested values")
    return Task(
        id="known-preflight",
        fixture=[
            SourceFile(path="config.py", contents=f"timeout_seconds = {initial}\n"),
            SourceFile(path="client.py", contents=client(initial)),
            SourceFile(
                path="test_client.py",
                contents="""import runpy

config = runpy.run_path("config.py")
client = runpy.run_path("client.py")
assert client["timeout"]() == config["timeout_seconds"]
assert client["timeout"](5) == 5
try:
    client["timeout"](0)
except ValueError:
    pass
else:
    raise AssertionError("nonpositive timeout accepted")
""",
            ),
        ],
        instruction=Instruction(
            prompt=(
                f"On branch eval, change the default timeout from {initial} to {requested} seconds "
                "in config.py and client.py. Only those two files are in scope. "
                "Keep tests and other behavior unchanged. Deliver the diff and a brief summary. "
                "Verify with python3 -I -B test_client.py. Complete the change."
            ),
        ),
        criterion=checks(
            inputs=("config.py", "client.py"),
            program=f"""import runpy

config = runpy.run_path("config.py")
client = runpy.run_path("client.py")
assert config["timeout_seconds"] == {requested}
assert client["fallback_timeout"] == {requested}
assert client["timeout"]() == {requested}
assert client["timeout"](5) == 5
assert client["timeout"](1) == 1
for value in (0, -1):
    try:
        client["timeout"](value)
    except ValueError:
        pass
    else:
        raise AssertionError("nonpositive timeout accepted")
""",
        ),
        allowed_files=("config.py", "client.py"),
        reference=Reference(
            edits=[
                SourceFile(path="config.py", contents=f"timeout_seconds = {requested}\n"),
                SourceFile(path="client.py", contents=client(requested)),
            ],
            completion="Updated both defaults and preserved overrides.",
        ),
    )


def answer(*, id: str, prompt: str, expected: dict[str, str | bool], reason: str) -> Task:
    return Task(
        id=id,
        fixture=[],
        instruction=Instruction(prompt=prompt),
        criterion=Criterion.answer(
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
        Declaration(skill="reasoning", task=receipt()),
        Declaration(skill="preflight", task=timeout()),
        *(Declaration(skill="bayesian", task=task) for task in decisions),
    )
