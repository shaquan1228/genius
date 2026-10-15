"""Keep every OCaml-Python translation inside the two transport modules."""

import ast
import re
from pathlib import Path

from evals.python.transport import EXPORTER, LIBRARY, OCAML_ROOT, SUITE

PYTHON_ROOT = Path(__file__).resolve().parents[1]
OCAML_REFERENCE = re.compile(r"\.(ml|mli|sh)$|^subprocess\b")


def nodes[T: ast.AST](path: Path, kind: type[T]) -> list[T]:
    return [node for node in ast.walk(ast.parse(path.read_text())) if isinstance(node, kind)]


def imported(path: Path) -> set[str]:
    plain = {alias.name for node in nodes(path, ast.Import) for alias in node.names}
    named = {
        f"{node.module}.{alias.name}"
        for node in nodes(path, ast.ImportFrom)
        for alias in node.names
    }
    return plain | named


def ocaml_references(path: Path) -> set[str]:
    """OCaml file names in string literals, plus any compiler-running import."""
    names = {str(node.value) for node in nodes(path, ast.Constant)} | imported(path)
    return {name for name in names if OCAML_REFERENCE.search(name)}


def test_only_python_transport_reads_ocaml_or_runs_compilers() -> None:
    harness = {path.name: path for path in PYTHON_ROOT.glob("*.py")}
    transport = harness.pop("transport.py")
    assert "scoring.py" in harness and ocaml_references(transport)
    references = {name: ocaml_references(path) for name, path in harness.items()}
    assert references == dict.fromkeys(harness, set())


def test_transport_internals_stay_private() -> None:
    names = {name for path in PYTHON_ROOT.rglob("*.py") for name in imported(path)}
    assert {name for name in names if name.startswith("evals.python.transport._")} == set()


def test_only_ocaml_transport_encodes_or_prints() -> None:
    assert sorted(OCAML_ROOT.glob("*.ml*")) == sorted((*LIBRARY, SUITE, EXPORTER))
    domain = {path.name: path.read_text() for path in (*LIBRARY, SUITE)}
    assert {name for name, text in domain.items() if re.search(r"Json|print_", text)} == set()
    assert "Json" in EXPORTER.read_text()
