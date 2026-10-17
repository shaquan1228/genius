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
READER = EVALS / "_build/default/tools/bindings.exe"


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
          type token = A | B of string
          type item = { flag : bool; values : (string * int option) list }
        end
        val choose : ?fallback:string option -> expected:token -> unit -> token
        """,
    )
    (tmp_path / "sample.mli").unlink()
    items = _schema((path,))[0]["items"]
    stub = generate.ast_bindings(items[:-1])
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
    source = workspace / "ocaml/ast.ml"
    source.write_text(source.read_text() + "\ntype dune_probe = { payload : int }\n")
    return _build_bindings(workspace, check=False)


def _promote_bindings(workspace: Path) -> None:
    subprocess.run(["dune", "promote"], cwd=workspace, check=True, capture_output=True)
    _build_bindings(workspace)


@pytest.fixture
def binding_workspace(tmp_path: Path) -> Path:
    for name in ("ocaml", "tools", "kernel"):
        shutil.copytree(
            EVALS / name,
            tmp_path / name,
            ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyi"),
        )
    for name in ("dune-project", "pyproject.toml"):
        shutil.copyfile(EVALS / name, tmp_path / name)
    _build_bindings(tmp_path)
    return tmp_path


def dune_binding_builds_are_incremental(binding_workspace: Path) -> None:
    generated = binding_workspace / "_build/default/kernel/generated/__init__.pyi"
    before = generated.stat().st_mtime_ns
    _build_bindings(binding_workspace)
    assert generated.stat().st_mtime_ns == before


def dune_requires_promotion_for_changed_runtime_exports(binding_workspace: Path) -> None:
    stale = _add_probe(binding_workspace)
    assert stale.returncode != 0
    assert "DuneProbe" in stale.stdout + stale.stderr
    _promote_bindings(binding_workspace)
    assert "def payload(self) -> int:" in (binding_workspace / "kernel/__init__.pyi").read_text()
    assert (
        "DuneProbe = _native.dune_probe" in (binding_workspace / "kernel/__init__.py").read_text()
    )


def dune_rebuilds_stubs_after_compiled_types_change(binding_workspace: Path) -> None:
    _add_probe(binding_workspace)
    _promote_bindings(binding_workspace)
    source = binding_workspace / "ocaml/ast.ml"
    source.write_text(source.read_text().replace("payload : int", "payload : string"))
    _build_bindings(binding_workspace)
    assert "def payload(self) -> str:" in (binding_workspace / "kernel/__init__.pyi").read_text()


def dune_clean_removes_stubs_and_preserves_runtime_sources(binding_workspace: Path) -> None:
    subprocess.run(["dune", "clean"], cwd=binding_workspace, check=True, capture_output=True)
    assert not (binding_workspace / "kernel/__init__.pyi").exists()
    assert (binding_workspace / "kernel/__init__.py").exists()


def installed_kernel_keeps_policy_and_provenance_together(tmp_path: Path) -> None:
    for name in ("ocaml", "tools"):
        shutil.copytree(EVALS / name, tmp_path / name, ignore=shutil.ignore_patterns("tests"))
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
    from kernel._operations import experiment as experiment_ops, fixture as fixture_ops, sources
    spec = experiment_ops.resolve()
    assert isinstance(fixture_ops.empty, Fixture)
    assert not hasattr(fixture_ops.empty, 'add')
    assert dict(sources())['experiment.ml'].find('epochs = 7') >= 0
    assert dict(sources())['experiment.ml'].find('epochs = 9') == -1
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
        runpy.run_path(str(EVALS / "kernel/_bridge.py"))


def incompatible_python_identifiers_fail_loudly(tmp_path: Path) -> None:
    path = _compile(tmp_path / "keywords", text="type state = None | Value")
    with pytest.raises(ValueError, match="Unsupported Python identifier: None"):
        generate.ast_bindings(_schema((path,))[0]["items"])


@pytest.mark.parametrize(
    "text", ["type foo_bar = string\ntype fooBar = bool", "type invalid_argument = { code : int }"]
)
def capitalized_binding_names_cannot_silently_collide(tmp_path: Path, *, text: str) -> None:
    path = _compile(tmp_path / "collision", text=text)
    items = _schema((path,))[0]["items"]
    with pytest.raises(ValueError, match="names collide"):
        generate.runtime_types(items)


def constructor_names_can_match_their_owner(tmp_path: Path) -> None:
    path = _compile(tmp_path / "owned", text="type entry = Entry")
    items = _schema((path,))[0]["items"]
    assert "Entry.Entry = _native.Entry" in generate.runtime_types(items)
    assert "class Entry(_types.Entry):" in generate.ast_bindings(items)


@pytest.mark.parametrize("text", ["type state = Value", "type state = Foo_bar | FooBar"])
def alternative_names_cannot_silently_collide(tmp_path: Path, *, text: str) -> None:
    path = _compile(tmp_path / "collision", text=text)
    items = _schema((path,))[0]["items"]
    with pytest.raises(ValueError, match="alternative names collide"):
        generate.runtime_types(items)
