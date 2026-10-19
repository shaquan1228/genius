"""Build-time bindings and installed policy follow compiled OCaml interfaces."""

import json
import os
import runpy
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from kernel import generate

EVALS = Path(__file__).resolve().parents[2]
READER = EVALS / "_build/default/ocaml/tools/bindings.exe"


def _schema(paths: tuple[Path, ...]) -> list[generate.Node]:
    result = subprocess.run(
        [str(READER), *(str(path) for path in paths)], check=True, capture_output=True, text=True
    )
    return json.loads(result.stdout)  # type: ignore[no-any-return]


def _compile(path: Path, *, text: str, extension: str = ".mli") -> Path:
    source = path.with_suffix(extension)
    source.write_text(text)
    subprocess.run(["ocamlc", "-c", str(source)], cwd=path.parent, check=True)
    return path.with_suffix(".cmi")


def compiled_includes_and_inference_drive_bindings(tmp_path: Path) -> None:
    path = _compile(
        tmp_path / "sample",
        text="""include sig
          type token = A | B of { value : string }
          type item = { flag : bool; values : (string * int option) list }
        end
        val choose : ?fallback:string option -> expected:token -> unit -> token
        """,
    )
    (tmp_path / "sample.mli").unlink()
    items = _schema((path,))[0]["items"]
    stub = generate.domain_bindings(items[:-1], package="kernel")
    assert (
        "class A(_types.Token):" in stub,
        "class B(_types.Token):" in stub,
        "Sequence[tuple[str, int | None]]" in stub,
        "@property\n    def flag(self) -> bool:" in stub,
    ) == (True, True, True, True)
    assert generate.operation(items[-1], variants=frozenset({"token"})) == (
        "def choose(*, fallback: str | None = ..., expected: _types.Token.Value)"
        " -> _types.Token.Value: ...\n"
    )
    assert "fallback: str | None" in generate.options(items[-1])
    assert "expected: Required[_types.Token.Value]" in generate.options(
        items[-1], variants=frozenset({"token"})
    )


def inferred_compiled_values_drive_bindings(tmp_path: Path) -> None:
    inferred = _compile(tmp_path / "inferred", text="let value = true", extension=".ml")
    assert generate.operation(_schema((inferred,))[0]["items"][0]) == ("value: bool\n")


@pytest.mark.parametrize(
    "text",
    [
        "val identity : 'a -> 'a",
        "type 'a box = Box of 'a",
        "type pair = Pair of string * int",
        "type scalar = Scalar of string",
        "type state = { mutable value : int }",
        "module Alias = String",
    ],
)
def unsupported_compiled_interfaces_fail_loudly(tmp_path: Path, *, text: str) -> None:
    path = _compile(tmp_path / "unsupported", text=text)
    with pytest.raises(subprocess.CalledProcessError) as error:
        _schema((path,))
    assert "Unsupported OCaml interface" in error.value.stderr


def _build_bindings(workspace: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["dune", "build", "--root", str(workspace), "@python-bindings"],
        check=check,
        capture_output=True,
        text=True,
    )


def _add_probe(workspace: Path) -> subprocess.CompletedProcess[str]:
    source = workspace / "ocaml/instruction.ml"
    source.write_text(source.read_text() + "\ntype dune_probe = { payload : int }\n")
    interface = workspace / "ocaml/instruction.mli"
    interface.write_text(interface.read_text() + "\ntype dune_probe = { payload : int }\n")
    return _build_bindings(workspace, check=False)


def _promote_bindings(workspace: Path) -> None:
    subprocess.run(["dune", "promote"], cwd=workspace, check=True, capture_output=True)
    _build_bindings(workspace)


@pytest.fixture
def binding_workspace(tmp_path: Path) -> Path:
    for name in ("ocaml", "python"):
        shutil.copytree(
            EVALS / name,
            tmp_path / name,
            ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyi"),
        )
    for name in ("dune-project", "pyproject.toml", "uv.lock", "__init__.py", "py.typed"):
        shutil.copyfile(EVALS / name, tmp_path / name)
    _build_bindings(tmp_path)
    return tmp_path


def base_dependencies_can_generate_bindings(binding_workspace: Path) -> None:
    subprocess.run(
        [
            "uv",
            "sync",
            "--project",
            str(binding_workspace),
            "--python",
            "3.12",
            "--locked",
            "--inexact",
        ],
        env=os.environ | {"UV_PROJECT_ENVIRONMENT": str(binding_workspace / ".venv")},
        check=True,
        capture_output=True,
        text=True,
    )
    dune = shutil.which("dune")
    assert dune is not None
    environment = os.environ | {
        "PATH": os.pathsep.join(
            (str(binding_workspace / ".venv/bin"), str(Path(dune).parent), os.defpath)
        )
    }
    result = subprocess.run(
        [
            dune,
            "build",
            "--root",
            str(binding_workspace),
            "--build-dir",
            "_build-base",
            "@python-bindings",
        ],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def dune_binding_builds_are_incremental(binding_workspace: Path) -> None:
    generated = binding_workspace / "_build/default/python/kernel/generated/__init__.pyi"
    before = generated.stat().st_mtime_ns
    _build_bindings(binding_workspace)
    assert generated.stat().st_mtime_ns == before


def dune_requires_promotion_for_changed_runtime_exports(binding_workspace: Path) -> None:
    stale = _add_probe(binding_workspace)
    assert stale.returncode != 0
    assert "DuneProbe" in stale.stdout + stale.stderr
    _promote_bindings(binding_workspace)
    assert (
        "def payload(self) -> int:"
        in (binding_workspace / "python/kernel/__init__.pyi").read_text()
    )
    assert (
        "DuneProbe = _named(constructor=_native.Instruction.dune_probe)"
        in (binding_workspace / "python/kernel/__init__.py").read_text()
    )


def dune_rebuilds_stubs_after_compiled_types_change(binding_workspace: Path) -> None:
    _add_probe(binding_workspace)
    _promote_bindings(binding_workspace)
    source = binding_workspace / "ocaml/instruction.ml"
    source.write_text(source.read_text().replace("payload : int", "payload : string"))
    interface = binding_workspace / "ocaml/instruction.mli"
    interface.write_text(interface.read_text().replace("payload : int", "payload : string"))
    _build_bindings(binding_workspace)
    assert (
        "def payload(self) -> str:"
        in (binding_workspace / "python/kernel/__init__.pyi").read_text()
    )


def dune_clean_removes_stubs_and_preserves_runtime_sources(binding_workspace: Path) -> None:
    subprocess.run(["dune", "clean"], cwd=binding_workspace, check=True, capture_output=True)
    assert not (binding_workspace / "python/kernel/__init__.pyi").exists()
    assert (binding_workspace / "python/kernel/__init__.py").exists()


def installed_kernel_keeps_policy_and_provenance_together(tmp_path: Path) -> None:
    shutil.copytree(EVALS / "ocaml", tmp_path / "ocaml", ignore=shutil.ignore_patterns("tests"))
    shutil.copyfile(EVALS / "dune-project", tmp_path / "dune-project")
    source = tmp_path / "ocaml/experiment.ml"
    source.write_text(source.read_text().replace("epochs = 5", "epochs = 7"))
    subprocess.run(["dune", "build", "--root", str(tmp_path), "@install"], check=True)
    prefix = tmp_path / "install"
    subprocess.run(
        ["dune", "install", "--root", str(tmp_path), "--prefix", str(prefix)], check=True
    )
    source.write_text(source.read_text().replace("epochs = 7", "epochs = 9"))
    script = """import json
from unittest.mock import patch
with patch('subprocess.run', side_effect=AssertionError('Import compiled the kernel')):
    from kernel import Fixture
    from kernel import Experiment, File, Kernel
    spec = Experiment.resolve()
    assert isinstance(Fixture.create(files=[]), Fixture)
    Fixture.add(fixture=Fixture.empty, file=File.create(path='probe.py', contents='text'))
    assert not Fixture.files(fixture=Fixture.empty)
    modules = {file.path: file.contents for file in Kernel.current.sources}
    assert modules['experiment.ml'].find('epochs = 7') >= 0
    assert modules['experiment.ml'].find('epochs = 9') == -1
    print(json.dumps({'epochs': spec.epochs}))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env={
            **os.environ,
            "OCAMLPATH": str(prefix / "lib"),
            "PYTHONPATH": str(EVALS.parent),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(result.stdout) == {"epochs": 7}


def missing_installed_package_reports_setup_command() -> None:
    with (
        patch("ocaml.require", side_effect=ImportError("No such package")),
        pytest.raises(ImportError, match="make -C evals setup-kernel"),
    ):
        runpy.run_path(str(EVALS / "python/kernel/_bridge.py"))


def incompatible_python_identifiers_fail_loudly(tmp_path: Path) -> None:
    path = _compile(tmp_path / "keywords", text="type state = None | Value")
    with pytest.raises(ValueError, match="Unsupported Python identifier: None"):
        generate.domain_bindings(_schema((path,))[0]["items"], package="kernel")


@pytest.mark.parametrize(
    "text", ["type foo_bar = string\ntype fooBar = bool", "type grading_error = { code : int }"]
)
def capitalized_binding_names_cannot_silently_collide(tmp_path: Path, *, text: str) -> None:
    path = _compile(tmp_path / "collision", text=text)
    items = _schema((path,))[0]["items"]
    with pytest.raises(ValueError, match="names collide"):
        generate.runtime_types(items, exceptions=("GradingError",))


def constructor_names_can_match_their_owner(tmp_path: Path) -> None:
    path = _compile(tmp_path / "owned", text="type entry = Entry")
    items = _schema((path,))[0]["items"]
    assert "Entry.Entry = _named(constructor=_native.Entry)" in generate.runtime_types(items)
    assert "class Entry(_types.Entry):" in generate.domain_bindings(items, package="kernel")


@pytest.mark.parametrize("text", ["type state = Value", "type state = Foo_bar | FooBar"])
def alternative_names_cannot_silently_collide(tmp_path: Path, *, text: str) -> None:
    path = _compile(tmp_path / "collision", text=text)
    items = _schema((path,))[0]["items"]
    with pytest.raises(ValueError, match="alternative names collide"):
        generate.runtime_types(items)


@pytest.mark.parametrize(
    "expression",
    [
        'let forge (task : Genius_evals_kernel.Task.t) = { task with id = "" }',
        "let forge (value : Genius_evals_kernel.Verifier.t) = { value with inputs = [] }",
        "let forge : Genius_evals_kernel.Response.t = { fields = [] }",
    ],
)
def ocaml_clients_cannot_construct_unvalidated_values(tmp_path: Path, *, expression: str) -> None:
    source = tmp_path / "forge.ml"
    source.write_text(expression)
    result = subprocess.run(
        ["ocamlfind", "ocamlc", "-package", "genius_evals_kernel", "-c", str(source)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "private type" in result.stderr


@pytest.mark.parametrize(
    "text", ["val create : string -> string", "val create : fields:string list -> string -> string"]
)
def unnamed_operation_inputs_fail_generation(tmp_path: Path, *, text: str) -> None:
    path = _compile(tmp_path / "unnamed", text=text)
    item = _schema((path,))[0]["items"][0]
    with pytest.raises(ValueError, match="arguments must be named"):
        generate.operation(item)


def factories_can_return_other_types(tmp_path: Path) -> None:
    path = _compile(
        tmp_path / "mismatch",
        text="module Response : sig type t = { fields : string list }\n"
        "val create : fields:string list -> string end",
    )
    assert "-> str" in generate.render(_schema((path,)), package="kernel")["__init__.pyi"]


@pytest.mark.parametrize(
    ("source", "accepted"),
    [
        ('Content.create(inline="")', True),
        ('Content.create(resource="checker")', True),
        ('Completion.create(plain="")', True),
        ("ResponseValue.create(bool=False)", True),
        ("Content.create()", False),
        ('Content.create(inline="x", resource="checker")', False),
        ("Completion.create()", False),
        ('Completion.create(plain="", structured=Response.create(fields=[]))', False),
        ('ResponseValue.create(string="x", bool=False)', False),
        ("Criterion.create()", False),
        ('Content.Inline("unchecked")', False),
        ('TextRule(field="x", min_words=1, max_words=2)', False),
    ],
)
def compiler_owned_factory_contracts_are_checked_statically(
    tmp_path: Path, *, source: str, accepted: bool
) -> None:
    path = tmp_path / "factory_contract.py"
    path.write_text(
        "from kernel import Content, Completion, Response, ResponseValue, Criterion, TextRule\n"
        + source
        + "\n"
    )
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "--config-file", str(EVALS / "pyproject.toml"), str(path)],
        cwd=EVALS,
        capture_output=True,
        text=True,
        check=False,
    )
    assert (result.returncode == 0) is accepted, result.stdout + result.stderr


@pytest.mark.parametrize(
    "signature",
    [
        "?a:string -> ?b:string -> int -> t",
        "?a:string -> ?b:string -> required:int -> unit -> t",
        "?a:string -> ?b:string -> t",
    ],
)
def exclusive_contracts_cannot_silently_lose_arguments(tmp_path: Path, *, signature: str) -> None:
    path = _compile(
        tmp_path / "exclusive",
        text=f"type t = Ready\nval create : {signature} [@@python.exclusive]",
    )
    value = _schema((path,))[0]["items"][-1]
    with pytest.raises(ValueError, match=r"Exclusive factories|arguments must be named"):
        generate.operation(value)


def compiled_private_nullary_constructors_retain_their_boundary(tmp_path: Path) -> None:
    path = _compile(
        tmp_path / "private_sum", text="type state = private Ready | Set of { value : string }"
    )
    stub = generate.domain_bindings(_schema((path,))[0]["items"], package="kernel")
    assert "class Ready(_types.State):\n        def __init__(self, *, _token: Never)" in stub
    assert "class Set(_types.State):\n        def __init__(self, *, _token: Never)" in stub


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("val root_function : unit -> bool", "def root_function() -> bool"),
        ("module Service : sig val run : unit -> int end", "class Service:"),
        (
            "module Values : sig type t = int list val create : values:int list -> t end",
            "type Value = Sequence[int]",
        ),
    ],
)
def modules_and_functions_do_not_require_nominal_owners(
    tmp_path: Path, *, text: str, expected: str
) -> None:
    path = _compile(tmp_path / "nonowner", text=text)
    assert expected in generate.render(_schema((path,)), package="kernel")["__init__.pyi"]


def multiple_compiled_interfaces_can_be_rendered(tmp_path: Path) -> None:
    first = _compile(tmp_path / "first", text="type first = { value : string }")
    second = _compile(tmp_path / "second", text="type second = { value : First.first }")
    rendered = generate.render(_schema((first, second)), package="kernel")
    stub = rendered["__init__.pyi"]
    assert "_native.First.first" in rendered["__init__.py"]
    assert "_native.Second.second" in rendered["__init__.py"]
    assert "class First:" in stub
    assert "def value(self) -> First:" in stub


def unresolved_module_paths_are_rejected(tmp_path: Path) -> None:
    path = _compile(tmp_path / "external", text="type value = String.t")
    with pytest.raises(ValueError, match="Unresolved type reference"):
        generate.render(_schema((path,)), package="kernel")


def a_new_public_module_needs_only_its_contract_and_export(binding_workspace: Path) -> None:
    root = binding_workspace / "ocaml"
    (root / "probe.ml").write_text("type t = { value : string }\n")
    (root / "probe.mli").write_text("type t = { value : string }\n")
    facade = root / "genius_evals_kernel.ml"
    facade.write_text(facade.read_text() + "module Probe = Probe\n")
    result = _build_bindings(binding_workspace, check=False)
    assert result.returncode != 0
    assert "Probe" in result.stdout + result.stderr
    _promote_bindings(binding_workspace)
    assert "class Probe:" in (binding_workspace / "python/kernel/__init__.pyi").read_text()


def compiled_library_identity_is_an_input(tmp_path: Path) -> None:
    path = _compile(tmp_path / "other__Item", text="type t = { value : string }")
    exported = subprocess.run(
        [str(READER), "--interface", "Other", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "module Item : sig" in exported.stdout
    wrong = subprocess.run(
        [str(READER), "--interface", "Unrelated", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert wrong.returncode != 0
    assert "interface outside library" in wrong.stderr


def result_failures_and_exception_exports_are_adapter_inputs(tmp_path: Path) -> None:
    path = _compile(
        tmp_path / "custom",
        text="type rejection = { detail : string }\nval run : unit -> (int, rejection) result",
    )
    rendered = generate.render(_schema((path,)), package="custom", exceptions=("Rejected",))
    assert (
        "import custom as _types" in rendered["__init__.pyi"],
        "def run() -> int" in rendered["__init__.pyi"],
        "failure='rejection'" in rendered["__init__.py"],
        "from ._bridge import Rejected as Rejected" in rendered["__init__.py"],
        "ValidationError" not in rendered["__init__.py"],
    ) == (True, True, True, True, True)


def kernel_public_contracts_follow_owner_conventions() -> None:
    schema = json.loads((EVALS / "_build/default/python/kernel/schema.json").read_text())
    assert all(module["kind"] == "module" for module in schema[0]["items"])
    assert all(
        item["kind"] not in {"value", "namespace", "namespace_alias"}
        for item in generate.declarations(schema)
    )


def _factory_returns_owner(factory: generate.Node, *, owner: str) -> bool:
    _, returned = generate.named_arguments(factory)
    payload = generate.result_payload(returned)
    return str((returned if payload is None else payload[0])["name"]) == owner


def kernel_factories_return_their_owner_type() -> None:
    schema = json.loads((EVALS / "_build/default/python/kernel/schema.json").read_text())
    for owner in generate.declarations(schema):
        for method in owner.get("methods", []):
            if method["name"] == "create":
                assert _factory_returns_owner(method, owner=owner["name"])


@pytest.mark.parametrize("name", ["_bind", "_named", "_native", "_types", "__all__", "overload"])
def generated_helpers_cannot_be_shadowed(tmp_path: Path, *, name: str) -> None:
    path = _compile(tmp_path / "helper", text=f"val {name} : int\nval run : unit -> int")
    with pytest.raises(ValueError, match="names collide"):
        generate.render(_schema((path,)), package="kernel")


def native_type_and_value_names_cannot_silently_collide(tmp_path: Path) -> None:
    path = _compile(tmp_path / "native_collision", text="type foo = { value : int }\nval foo : int")
    with pytest.raises(ValueError, match="Native names collide"):
        generate.render(_schema((path,)), package="kernel")


def nested_modules_keep_references_to_the_outer_namesake(tmp_path: Path) -> None:
    path = _compile(
        tmp_path / "shadowed",
        text="module Comparison : sig type t = { equal : bool } end\n"
        "module Task : sig module Comparison : sig\n"
        "type t = { id : Comparison.t }\n"
        "val create : id:Comparison.t -> t end\n"
        "val compare : before:string -> after:string -> Comparison.t end",
    )
    stub = generate.render(_schema((path,)), package="kernel")["__init__.pyi"]
    assert "def id(self) -> Comparison:" in stub
    assert "def create(*, id: _types.Comparison) -> _types.TaskComparison:" in stub
    assert "def compare(*, before: str, after: str) -> _types.TaskComparison:" in stub
