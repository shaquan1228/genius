"""OCaml-backed modules; public bindings are derived from the kernel interfaces."""

import os
import sys
from functools import cache
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import cast

_environment = {name: os.environ.get(name) for name in ("PATH", "PYTHONHOME", "PYTHONPATH")}
os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + (_environment["PATH"] or "")
try:
    _ocaml = import_module("ocaml")
finally:
    # PyML mutates libc's environment without updating Python's os.environ mapping.
    for _name, _value in _environment.items():
        if _value is None:
            os.unsetenv(_name)
            os.environ.pop(_name, None)
        else:
            os.environ[_name] = _value


try:
    _ocaml.require("genius_evals_kernel")
except ImportError as error:
    raise ImportError("OCaml kernel is not installed; run make -C evals setup-kernel") from error

Ast = cast(ModuleType, _ocaml.Genius_evals_kernel)


@cache
def sources() -> tuple[tuple[str, str], ...]:
    """The exact trusted sources embedded in the installed native library."""
    return tuple((str(name), str(contents)) for name, contents in Ast.sources)


Case = Ast.Case
Criterion = Ast.Criterion
Experiment = Ast.Experiment
Fixture = Ast.Fixture
Grader = Ast.Grader
Projection = Ast.Projection
Reference = Ast.Reference
Response = Ast.Response
Verifier = Ast.Verifier
InvalidArgument = _ocaml.Invalid_argument

__all__ = [
    "Ast",
    "Case",
    "Criterion",
    "Experiment",
    "Fixture",
    "Grader",
    "InvalidArgument",
    "Projection",
    "Reference",
    "Response",
    "Verifier",
    "sources",
]
