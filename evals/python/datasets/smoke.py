"""Load the default smoke dataset from smoke.toml."""

from pathlib import Path

from evals.python import Declaration
from evals.python.integrations.smoke import load_cases

info = None


def cases() -> tuple[Declaration, ...]:
    return load_cases(Path(__file__).with_suffix(".toml"))
