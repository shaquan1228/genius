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
    items = generate.schema((path,), reader=READER)[0]["items"]
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
    assert generate.operation(generate.schema((inferred,), reader=READER)[0]["items"][0]) == (
        "value: bool\n"
    )


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
        generate.schema((path,), reader=READER)
    assert "Unsupported OCaml interface" in error.value.stderr


def generated_stubs_detect_stale_compiled_signatures(tmp_path: Path) -> None:
    path = _compile(tmp_path / "sample", text="type state = { value : int }")
    original = generate.schema((path,), reader=READER)[0]["items"]
    outputs = {"__init__.pyi": generate.ast_bindings(original)}
    destination = tmp_path / "stubs"
    destination.mkdir()
    generate.write(outputs, destination=destination, check=False)
    before = (destination / "__init__.pyi").read_bytes()
    generate.write(outputs, destination=destination, check=True)
    assert (destination / "__init__.pyi").read_bytes() == before
    # Editing source cannot change a compiler-derived interface until it is compiled.
    path.with_suffix(".mli").write_text("type state = { value : string }")
    assert generate.schema((path,), reader=READER)[0]["items"] == original
    _compile(tmp_path / "sample", text="type state = { value : string }")
    updated = generate.schema((path,), reader=READER)[0]["items"]
    with pytest.raises(SystemExit, match="Kernel types changed"):
        generate.write(
            {"__init__.pyi": generate.ast_bindings(updated)}, destination=destination, check=True
        )
    generate.write(
        {"__init__.pyi": generate.ast_bindings(updated)}, destination=destination, check=False
    )
    assert "value: str" in (destination / "__init__.pyi").read_text()


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
        generate.ast_bindings(generate.schema((path,), reader=READER)[0]["items"])


@pytest.mark.parametrize(
    "text", ["type foo_bar = string\ntype fooBar = bool", "type invalid_argument = { code : int }"]
)
def capitalized_binding_names_cannot_silently_collide(tmp_path: Path, *, text: str) -> None:
    path = _compile(tmp_path / "collision", text=text)
    items = generate.schema((path,), reader=READER)[0]["items"]
    with pytest.raises(ValueError, match="names collide"):
        generate.runtime_types(items)


def constructor_names_can_match_their_owner(tmp_path: Path) -> None:
    path = _compile(tmp_path / "owned", text="type entry = Entry")
    items = generate.schema((path,), reader=READER)[0]["items"]
    assert "Entry.Entry = _native.Entry" in generate.runtime_types(items)
    assert "class Entry(_types.Entry):" in generate.ast_bindings(items)


@pytest.mark.parametrize("text", ["type state = Value", "type state = Foo_bar | FooBar"])
def alternative_names_cannot_silently_collide(tmp_path: Path, *, text: str) -> None:
    path = _compile(tmp_path / "collision", text=text)
    items = generate.schema((path,), reader=READER)[0]["items"]
    with pytest.raises(ValueError, match="alternative names collide"):
        generate.runtime_types(items)
