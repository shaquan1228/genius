"""Repository locations shared by the Python harness."""

from pathlib import Path
from typing import Final

EVALS_ROOT: Final = Path(__file__).resolve().parents[1]
REPO_ROOT: Final = EVALS_ROOT.parent
