"""Enforce the concern and integration dependency seams."""

import ast
import inspect
import os
import re
import subprocess
import sys
from importlib import import_module
from pathlib import Path

import pytest

import kernel as native
from evals.python import datasets, evaluation
from kernel import Case, Experiment, Kernel

PYTHON_ROOT = Path(__file__).resolve().parents[1]
OCAML_ROOT = PYTHON_ROOT.parent / "ocaml"
LIBRARY = tuple(
    OCAML_ROOT / file.path for file in Kernel.current.sources if file.path.endswith((".ml", ".mli"))
)


PUBLIC_OPERATIONS = {
    "datasets": {
        "compile_dataset",
        "describe_dataset",
        "get_provenance",
        "get_reference",
        "list_cases",
        "load_dataset",
    },
    "grading": {"score_case"},
    "verification": {"verify_case", "validate_reference"},
    "assessment": {"assess"},
    "execution": {"create_runtime"},
    "evaluation": {"evaluate", "resolve_settings", "resolve_experiment"},
    "comparison": {
        "compare_observations",
        "compare_runs",
        "fingerprint",
        "prepare_run",
        "validate_run",
        "render_report",
    },
}
OWNER_TYPES = {
    "schema": {"DatasetInfo", "FileName", "Files", "Attributes"},
    "datasets": {"Dataset", "Selection", "DatasetProvenance"},
    "grading": {"Scores"},
    "verification": {"Diagnostic", "VerificationResult"},
    "assessment": {"Assessment"},
    "execution": {"Execution", "Completion", "Environment", "Runtime", "Cleanup"},
    "evaluation": {"EvaluationSettings", "ModelPricing", "InstructionDelivery", "VariantSettings"},
    "comparison": {
        "ComparisonRequest",
        "VariantRequest",
        "Measurement",
        "RunRecord",
        "Observation",
        "PreparedRun",
    },
}
PUBLIC_NAMES = {
    owner: names | PUBLIC_OPERATIONS.get(owner, set()) for owner, names in OWNER_TYPES.items()
}


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
        "integrations/evalplus/verifier.py",
        "integrations/smoke/verifier.py",
        "integrations/hugging_face/source.py",
    }


def core_cannot_import_integrations_or_sdks() -> None:
    dependencies = {
        name
        for file in (
            "schema.py",
            "datasets/__init__.py",
            "grading.py",
            "verification.py",
            "assessment.py",
        )
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


@pytest.mark.parametrize("prefix", ["evals.python.datasets._", "evals.python.tests", "kernel._"])
def runtime_consumers_use_public_namespaces(prefix: str) -> None:
    names = {name for path in _runtime_files() for name in _imported(path)}
    assert not any(name.startswith(prefix) for name in names)


def domain_modules_are_codec_free() -> None:
    assert sorted(OCAML_ROOT.glob("*.ml*")) == sorted(LIBRARY)
    assert not any(re.search(r"Jsonm|Codec|print_", path.read_text()) for path in LIBRARY)


@pytest.mark.parametrize("owner", PUBLIC_OPERATIONS)
def public_operations_use_native_calls_without_a_transport_layer(owner: str) -> None:
    path = PYTHON_ROOT / ("datasets/__init__.py" if owner == "datasets" else f"{owner}.py")
    assert "subprocess" not in _imported(path)
    assert not (PYTHON_ROOT / "kernel/build.py").exists()
    assert "subprocess" not in _imported(PYTHON_ROOT / "kernel/__init__.py")


@pytest.mark.parametrize(
    ("owner", "name"),
    [
        ("datasets", "list_cases"),
        ("grading", "score_case"),
        ("verification", "verify_case"),
        ("verification", "validate_reference"),
        ("assessment", "assess"),
    ],
)
def public_operations_carry_dataset_selection(owner: str, *, name: str) -> None:
    operation = getattr(import_module(f"evals.python.{owner}"), name)
    parameter = inspect.signature(operation).parameters["selection"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY


@pytest.mark.parametrize("path", sorted(OCAML_ROOT.glob("*.mli")))
def domain_types_live_with_owner_contracts(path: Path) -> None:
    if path.stem in ("validation", "text"):
        return
    assert re.search(r"^type t\b", path.read_text(), re.M)
    assert re.search(r"^type t\b", path.with_suffix(".ml").read_text(), re.M)


def kernel_facade_only_exports_owner_modules() -> None:
    assert not (OCAML_ROOT / "ast.ml").exists()
    assert not (OCAML_ROOT / "construct.ml").exists()
    assert not re.search(
        r"^type |^include ", (OCAML_ROOT / "genius_evals_kernel.ml").read_text(), re.M
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
    ("owner", "filename"), [("evalplus", "verifier.py"), ("smoke", "verifier.py")]
)
def framework_driver_is_standalone(owner: str, *, filename: str) -> None:
    path = PYTHON_ROOT / "integrations" / owner / filename
    assert {name.split(".")[0] for name in _imported(path)} <= sys.stdlib_module_names


def integrations_use_typed_public_operations_without_legacy_facades() -> None:
    obsolete = (
        "command.py",
        "commands.py",
        "queries.py",
        "evaluation_settings.py",
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


@pytest.mark.parametrize("path", sorted((PYTHON_ROOT / "integrations").rglob("*.py")))
@pytest.mark.parametrize("owner", PUBLIC_NAMES)
def integrations_import_only_public_operations_and_types(path: Path, *, owner: str) -> None:
    allowed = {f"evals.python.{owner}.{name}" for name in PUBLIC_NAMES[owner]}
    owned = {name for name in _imported(path) if name.startswith(f"evals.python.{owner}.")}
    assert owned <= allowed


@pytest.mark.parametrize("path", sorted((PYTHON_ROOT / "integrations").rglob("*.py")))
def integrations_use_supported_owner_import_style(path: Path) -> None:
    plain = {alias.name for node in _nodes(path, kind=ast.Import) for alias in node.names}
    assert plain.isdisjoint(f"evals.python.{owner}" for owner in PUBLIC_NAMES)


def _owner_aliases(path: Path) -> dict[str, str]:
    return {
        alias.asname or alias.name: alias.name
        for node in _nodes(path, kind=ast.ImportFrom)
        if node.module == "evals.python"
        for alias in node.names
    }


@pytest.mark.parametrize("path", sorted((PYTHON_ROOT / "integrations").rglob("*.py")))
def integrations_qualify_only_public_operations(path: Path) -> None:
    aliases = _owner_aliases(path)
    for node in _nodes(path, kind=ast.Attribute):
        if isinstance(node.value, ast.Name) and aliases.get(node.value.id) in PUBLIC_NAMES:
            assert node.attr in PUBLIC_OPERATIONS.get(aliases[node.value.id], set())


def _check_owner_access(path: Path) -> None:
    integrations_use_supported_owner_import_style(path)
    integrations_qualify_only_public_operations(path)


@pytest.mark.parametrize(
    ("source", "accepted"),
    [
        ("import evals.python.verification as v\nv.verify_case()", False),
        ("from evals.python import verification as v\nv.verify()", False),
        ("from evals.python import verification as v\nv.verify_case()", True),
        ("from evals.python import execution as e\ne.Runtime()", False),
        ("from evals.python.execution import Runtime", True),
        ("from evals.python import grading as g\ng.score()", False),
        ("from evals.python import grading as g\ng.score_case()", True),
        ("from evals.python import datasets as d\nd.record()", False),
    ],
)
def owner_import_rules_reject_bypasses_and_allow_public_operations(
    tmp_path: Path, *, source: str, accepted: bool
) -> None:
    path = tmp_path / "adapter.py"
    path.write_text(source)
    if accepted:
        _check_owner_access(path)
        return
    with pytest.raises(AssertionError):
        _check_owner_access(path)


@pytest.mark.parametrize("owner", PUBLIC_OPERATIONS)
def public_operations_are_defined_by_their_concern(owner: str) -> None:
    module = import_module(f"evals.python.{owner}")
    for name in PUBLIC_OPERATIONS[owner]:
        operation = getattr(module, name)
        assert operation.__module__ == module.__name__


@pytest.mark.parametrize("owner", PUBLIC_OPERATIONS)
def public_concerns_export_only_their_operations_and_types(owner: str) -> None:
    module = import_module(f"evals.python.{owner}")
    assert set(module.__all__) == PUBLIC_NAMES[owner]


@pytest.mark.parametrize("filename", ["schema.py", "datasets/__init__.py", "grading.py"])
def query_concerns_do_not_import_execution_workflows(filename: str) -> None:
    imports = _imported(PYTHON_ROOT / filename)
    assert not any(
        name.startswith(
            tuple(
                f"evals.python.{owner}"
                for owner in ("assessment", "execution", "evaluation", "verification")
            )
        )
        for name in imports
    )


def public_concerns_have_no_direct_sdk_imports() -> None:
    imports = {
        name
        for owner in PUBLIC_OPERATIONS
        for name in _imported(
            PYTHON_ROOT / ("datasets/__init__.py" if owner == "datasets" else f"{owner}.py")
        )
    }
    assert not any(
        name.startswith(("inspect_ai", "inspect_swe", "huggingface_hub")) for name in imports
    )


def query_concerns_do_not_compose_execution_adapters() -> None:
    assert not any(
        name.startswith("evals.python.integrations")
        for filename in ("datasets/__init__.py", "grading.py")
        for name in _imported(PYTHON_ROOT / filename)
    )


@pytest.mark.parametrize("path", sorted((PYTHON_ROOT / "integrations").rglob("*.py")))
def integrations_import_public_namespaces_or_owned_types(path: Path) -> None:
    imports = [
        node
        for node in _nodes(path, kind=ast.ImportFrom)
        if str(node.module).startswith("evals.python")
    ]
    allowed = {f"evals.python.{owner}": names for owner, names in OWNER_TYPES.items()}
    allowed["evals.python"] = set(PUBLIC_NAMES)
    assert all(
        len(node.names) == 1
        or {name.name for name in node.names} <= allowed.get(str(node.module), set())
        for node in imports
    )


def case_query_does_not_load_runner_sdks() -> None:
    script = """from evals.python import assessment, datasets, evaluation
from evals.python import execution, grading, verification
import sys
assert datasets.list_cases()
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
    assert isinstance(datasets.list_cases()[0], Case)
    assert isinstance(evaluation.resolve_settings(), Experiment)


@pytest.mark.parametrize("owner", PUBLIC_OPERATIONS)
def public_operations_do_not_reexport_native_types(owner: str) -> None:
    module = import_module(f"evals.python.{owner}")
    exported = set(vars(native)["__all__"]) & set(module.__all__)
    assert all(getattr(native, name) is not getattr(module, name) for name in exported)
