"""Enforce the kernel/transport/integration dependency seams."""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import kernel as native
from evals.python import commands, queries
from kernel import Ast, sources

PYTHON_ROOT = Path(__file__).resolve().parents[1]
OCAML_ROOT = PYTHON_ROOT.parent / "ocaml"
LIBRARY = tuple(OCAML_ROOT / name for name, _ in sources() if name.endswith((".ml", ".mli")))


def _nodes[T: ast.AST](path: Path, *, kind: type[T]) -> list[T]:
    return [node for node in ast.walk(ast.parse(path.read_text())) if isinstance(node, kind)]


def _imported(path: Path) -> set[str]:
    plain = {alias.name for node in _nodes(path, kind=ast.Import) for alias in node.names}
    named = {
        f"{node.module}.{alias.name}"
        for node in _nodes(path, kind=ast.ImportFrom)
        for alias in node.names
    }
    return plain | named


def _runtime_files() -> tuple[Path, ...]:
    return tuple(path for path in PYTHON_ROOT.rglob("*.py") if "tests" not in path.parts)


def only_standalone_drivers_use_subprocess() -> None:
    callers = {
        str(path.relative_to(PYTHON_ROOT))
        for path in _runtime_files()
        if "subprocess" in _imported(path)
    }
    assert callers == {
        "integrations/evalplus/evalplus_verifier.py",
        "integrations/smoke/verifier.py",
    }


def core_cannot_import_integrations_or_sdks() -> None:
    dependencies = {
        name
        for file in ("schema.py", "datasets/__init__.py")
        for name in _imported(PYTHON_ROOT / file)
    }
    assert not any(
        name.startswith(("evals.python.integrations", "inspect_ai", "huggingface_hub"))
        for name in dependencies
    )


def dataset_loader_has_no_provider_dispatch() -> None:
    assert not re.search(
        r"humaneval|evalplus|hugging|inspect_ai",
        (PYTHON_ROOT / "datasets/__init__.py").read_text(),
        re.I,
    )


def dataset_ingestion_has_no_ocaml_adapters_or_global_drivers() -> None:
    assert not (OCAML_ROOT / "datasets").exists()
    assert not (OCAML_ROOT / "dataset.mli").exists()
    assert not any("Dataset." in path.read_text() for path in LIBRARY)
    assert not re.search(
        r"humaneval|evalplus|DRIVERS", (PYTHON_ROOT / "datasets/__init__.py").read_text()
    )


def inspect_integration_does_not_select_hugging_face() -> None:
    imports = {
        name
        for path in (PYTHON_ROOT / "integrations/inspect").glob("*.py")
        for name in _imported(path)
    }
    assert not any(name.startswith("evals.python.integrations.hugging_face") for name in imports)


def dataset_internals_stay_private() -> None:
    names = {name for path in _runtime_files() for name in _imported(path)}
    assert not any(name.startswith("evals.python.datasets._") for name in names)
    assert not any(name.startswith("evals.python.tests") for name in names)


def domain_modules_are_codec_free() -> None:
    assert sorted(OCAML_ROOT.glob("*.ml*")) == sorted(LIBRARY)
    assert not any(re.search(r"Jsonm|Codec|print_", path.read_text()) for path in LIBRARY)


def public_operations_use_native_calls_without_a_transport_layer() -> None:
    assert "subprocess" not in _imported(PYTHON_ROOT / "queries.py")
    assert "subprocess" not in _imported(PYTHON_ROOT / "commands.py")
    assert not (PYTHON_ROOT.parent / "kernel/build.py").exists()
    assert "subprocess" not in _imported(PYTHON_ROOT.parent / "kernel/__init__.py")


def public_operations_carry_dataset_selection() -> None:
    names = {"list_cases", "score_case", "verify", "assess", "validate_reference"}
    operations = [
        node
        for file in ("queries.py", "commands.py")
        for node in _nodes(PYTHON_ROOT / file, kind=ast.FunctionDef)
        if node.name in names
    ]
    assert all("selection" in {arg.arg for arg in node.args.kwonlyargs} for node in operations)


def shared_domain_types_live_in_ast() -> None:
    operations = (
        "fixture",
        "response",
        "verifier",
        "criterion",
        "case",
        "reference",
        "grader",
        "experiment",
        "projection",
    )
    bodies = [(OCAML_ROOT / f"{name}.ml").read_text() for name in operations]
    assert not any(re.search(r"^type ", body, re.M) for body in bodies)
    assert not re.search(r"^let |^module ", (OCAML_ROOT / "ast.ml").read_text(), re.M)


def public_interfaces_only_declare_operations() -> None:
    assert not any(
        re.search(r"^type ", path.read_text(), re.M)
        for path in OCAML_ROOT.glob("*.mli")
        if path.name != "fixture_store.mli"
    )


def integrations_do_not_import_sibling_implementations() -> None:
    for path in _runtime_files():
        if "integrations" not in path.parts:
            continue
        owner = path.relative_to(PYTHON_ROOT / "integrations").parts[0]
        prefix = f"evals.python.integrations.{owner}"
        assert all(
            not name.startswith("evals.python.integrations.") or name.startswith(prefix + ".")
            for name in _imported(path)
        ), str(path)


def hugging_face_owns_only_its_sdk() -> None:
    dependencies = {
        name
        for path in (PYTHON_ROOT / "integrations/hugging_face").glob("*.py")
        for name in _imported(path)
    }
    assert not any(
        name.startswith(("inspect_ai", "inspect_swe", "evals.python.contracts"))
        for name in dependencies
    )


@pytest.mark.parametrize(
    ("owner", "filename"), [("evalplus", "evalplus_verifier.py"), ("smoke", "verifier.py")]
)
def framework_driver_is_standalone(owner: str, *, filename: str) -> None:
    path = PYTHON_ROOT / "integrations" / owner / filename
    assert {name.split(".")[0] for name in _imported(path)} <= sys.stdlib_module_names


def integrations_use_typed_public_operations_without_legacy_facades() -> None:
    obsolete = (
        "command.py",
        "catalog.py",
        "transport.py",
        "_kernel.py",
        "contracts.py",
        "integrations/datasets/catalog.py",
        "integrations/datasets/commands.py",
        "integrations/inspect/commands.py",
        "integrations/inspect/datasets.py",
        "integrations/inspect/verification.py",
        "integrations/inspect/benchmarks.py",
    )
    assert not [name for name in obsolete if (PYTHON_ROOT / name).exists()]
    imports = {
        name for path in (PYTHON_ROOT / "integrations").rglob("*.py") for name in _imported(path)
    }
    assert not any(name.startswith("evals.python.verification") for name in imports)


def integrations_cannot_bypass_the_public_operation_contract() -> None:
    private = (
        "evals.python.schema",
        "evals.python.datasets",
        "evals.python.verification",
    )
    imports = {
        name for path in (PYTHON_ROOT / "integrations").rglob("*.py") for name in _imported(path)
    }
    assert not any(name.startswith(private) for name in imports)


def public_commands_and_verification_have_no_sdk_imports() -> None:
    imports = {
        name
        for file in ("commands.py", "queries.py", "verification.py")
        for name in _imported(PYTHON_ROOT / file)
    }
    assert not any(
        name.startswith(("inspect_ai", "inspect_swe", "huggingface_hub")) for name in imports
    )


@pytest.mark.parametrize("path", sorted((PYTHON_ROOT / "integrations").rglob("*.py")))
def integrations_import_public_namespaces_or_single_values(path: Path) -> None:
    imports = [
        node
        for node in _nodes(path, kind=ast.ImportFrom)
        if str(node.module).startswith("evals.python")
    ]
    assert all(
        len(node.names) == 1
        or (
            node.module == "evals.python"
            and {name.name for name in node.names} <= {"commands", "queries"}
        )
        for node in imports
    )


def case_query_does_not_load_runner_sdks() -> None:
    script = """from evals.python import queries
from evals.python import commands
import sys
assert queries.list_cases()
assert not {'inspect_ai', 'inspect_swe', 'huggingface_hub'}.intersection(sys.modules)
print('kernel-only')
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PYTHON_ROOT.parent.parent,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "kernel-only"


def native_import_preserves_child_environment_and_working_directory(tmp_path: Path) -> None:
    script = """import ctypes
import pathlib
import subprocess
import sys
libc = ctypes.CDLL(None)
libc.getenv.restype = ctypes.c_char_p
names = (b"PATH", b"PYTHONHOME", b"PYTHONPATH")
before = tuple(libc.getenv(name) for name in names)
from kernel import Experiment
assert Experiment.resolve(epochs=1).epochs == 1
assert tuple(libc.getenv(name) for name in names) == before
assert list(pathlib.Path.cwd().iterdir()) == []
subprocess.run([sys.executable, "-c", "import re, pathlib"], check=True)
"""
    subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(PYTHON_ROOT.parent.parent)},
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )


def public_domain_values_are_native_types() -> None:
    assert not (PYTHON_ROOT / "_kernel.py").exists()
    assert isinstance(queries.list_cases()[0], Ast.case)
    assert isinstance(queries.resolve_settings(), Ast.experiment)


def public_operations_do_not_reexport_kernel_namespaces() -> None:
    assert set(vars(native)["__all__"]).isdisjoint(commands.__all__ + queries.__all__)
