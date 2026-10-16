"""Enforce the kernel/transport/integration dependency seams."""

import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest

from evals.python.transport import DATASET_INTERFACE, EXPORTER, LIBRARY, OCAML_ROOT, SUITE

PYTHON_ROOT = Path(__file__).resolve().parents[1]


def nodes[T: ast.AST](path: Path, *, kind: type[T]) -> list[T]:
    return [node for node in ast.walk(ast.parse(path.read_text())) if isinstance(node, kind)]


def imported(path: Path) -> set[str]:
    plain = {alias.name for node in nodes(path, kind=ast.Import) for alias in node.names}
    named = {
        f"{node.module}.{alias.name}"
        for node in nodes(path, kind=ast.ImportFrom)
        for alias in node.names
    }
    return plain | named


def runtime_files() -> tuple[Path, ...]:
    return tuple(path for path in PYTHON_ROOT.rglob("*.py") if "tests" not in path.parts)


def test_only_transport_and_standalone_drivers_use_subprocess() -> None:
    callers = {
        str(path.relative_to(PYTHON_ROOT))
        for path in runtime_files()
        if "subprocess" in imported(path)
    }
    assert callers == {
        "transport.py",
        "integrations/evalplus/evalplus_verifier.py",
        "integrations/smoke/verifier.py",
    }


def test_core_cannot_import_integrations_or_sdks() -> None:
    dependencies = {
        name for file in ("_kernel.py", "transport.py") for name in imported(PYTHON_ROOT / file)
    }
    assert not any(
        name.startswith(("evals.python.integrations", "inspect_ai", "huggingface_hub"))
        for name in dependencies
    )


def test_transport_has_no_dataset_or_provider_dispatch() -> None:
    assert not re.search(r"humaneval|evalplus|hugging|inspect_ai", EXPORTER.read_text(), re.I)
    assert not re.search(
        r"humaneval|evalplus|hugging|inspect_ai", (PYTHON_ROOT / "transport.py").read_text(), re.I
    )


def test_inspect_integration_does_not_select_hugging_face() -> None:
    imports = {
        name
        for path in (PYTHON_ROOT / "integrations/inspect").glob("*.py")
        for name in imported(path)
    }
    assert not any(name.startswith("evals.python.integrations.hugging_face") for name in imports)


def test_transport_internals_stay_private() -> None:
    names = {name for path in runtime_files() for name in imported(path)}
    assert not any(name.startswith("evals.python.transport._") for name in names)
    assert not any(name.startswith("evals.python.tests") for name in names)


def test_domain_modules_are_codec_free() -> None:
    assert sorted(OCAML_ROOT.glob("*.ml*")) == sorted(
        (*LIBRARY, SUITE, DATASET_INTERFACE, EXPORTER)
    )
    boundary = {"codec.ml", "declaration.ml", "declaration.mli"}
    domain = (path for path in (*LIBRARY, SUITE) if path.name not in boundary)
    assert not any(re.search(r"Jsonm|Codec|print_", path.read_text()) for path in domain)


def test_only_codec_uses_json_library() -> None:
    users = {path.name for path in LIBRARY if re.search(r"\bJsonm\b", path.read_text())}
    assert users == {"codec.ml"}


def test_integration_entry_points_use_explicit_catalog_selection() -> None:
    expected = {"case": (1, 1), "reference": (1, 1), "verifier": (1, 1), "grade": (0, 5)}
    signatures = {
        node.name: (len(node.args.args), len(node.args.kwonlyargs))
        for node in nodes(PYTHON_ROOT / "catalog.py", kind=ast.FunctionDef)
        if node.name in expected
    }
    assert signatures == expected


def test_shared_domain_types_live_in_ast() -> None:
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


def test_public_interfaces_only_declare_operations() -> None:
    interfaces = [path.read_text() for path in OCAML_ROOT.glob("*.mli")]
    assert not any(re.search(r"^type ", body, re.M) for body in interfaces)


def test_integrations_do_not_import_sibling_implementations() -> None:
    for path in runtime_files():
        if "integrations" not in path.parts:
            continue
        owner = path.relative_to(PYTHON_ROOT / "integrations").parts[0]
        prefix = f"evals.python.integrations.{owner}"
        assert all(
            not name.startswith("evals.python.integrations.") or name.startswith(prefix + ".")
            for name in imported(path)
        ), str(path)


def test_hugging_face_owns_only_its_sdk() -> None:
    dependencies = {
        name
        for path in (PYTHON_ROOT / "integrations/hugging_face").glob("*.py")
        for name in imported(path)
    }
    assert not any(
        name.startswith(("inspect_ai", "inspect_swe", "evals.python.contracts"))
        for name in dependencies
    )


@pytest.mark.parametrize(
    ("owner", "filename"), [("evalplus", "evalplus_verifier.py"), ("smoke", "verifier.py")]
)
def test_framework_driver_is_standalone(owner: str, *, filename: str) -> None:
    path = PYTHON_ROOT / "integrations" / owner / filename
    assert {name.split(".")[0] for name in imported(path)} <= sys.stdlib_module_names


def test_integrations_use_typed_public_operations_without_legacy_facades() -> None:
    obsolete = (
        "command.py",
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
        name for path in (PYTHON_ROOT / "integrations").rglob("*.py") for name in imported(path)
    }
    assert not any(name.startswith("evals.python.verification") for name in imports)


def test_integrations_cannot_bypass_the_public_operation_contract() -> None:
    private = (
        "evals.python._kernel",
        "evals.python.catalog",
        "evals.python.transport",
        "evals.python.verification",
    )
    imports = {
        name for path in (PYTHON_ROOT / "integrations").rglob("*.py") for name in imported(path)
    }
    assert not any(name.startswith(private) for name in imports)


def test_public_commands_and_verification_have_no_sdk_imports() -> None:
    imports = {
        name
        for file in ("commands.py", "query.py", "verification.py")
        for name in imported(PYTHON_ROOT / file)
    }
    assert not any(
        name.startswith(("inspect_ai", "inspect_swe", "huggingface_hub")) for name in imports
    )


@pytest.mark.parametrize("path", sorted((PYTHON_ROOT / "integrations").rglob("*.py")))
def test_integrations_import_public_namespaces_or_single_values(path: Path) -> None:
    imports = [
        node
        for node in nodes(path, kind=ast.ImportFrom)
        if str(node.module).startswith("evals.python")
    ]
    assert all(
        len(node.names) == 1
        or (
            node.module == "evals.python"
            and {name.name for name in node.names} <= {"commands", "query"}
        )
        for node in imports
    )


def test_case_query_does_not_load_runner_sdks() -> None:
    script = """from evals.python import query
from evals.python import commands
import sys
assert query.Cases()
assert not {'inspect_ai', 'inspect_swe', 'huggingface_hub'}.intersection(sys.modules)
print('kernel-only')
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PYTHON_ROOT.parent.parent,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert result.stdout.strip() == "kernel-only"
