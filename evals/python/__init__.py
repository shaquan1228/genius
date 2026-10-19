"""Python evaluation boundaries; domain values come from the native kernel."""

from pathlib import Path
from typing import Annotated

from pydantic import ConfigDict, Field

FROZEN = ConfigDict(strict=True, extra="forbid", frozen=True, arbitrary_types_allowed=True)
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")]

REPO_ROOT = Path(__file__).resolve().parents[2]
EVALS_ROOT = REPO_ROOT / "evals"
