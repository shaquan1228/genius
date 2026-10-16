"""Render Python stubs from compiler-parsed, compiled OCaml interfaces."""

import argparse
import json
import keyword
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

HEADER = "# Generated from compiled OCaml interfaces; do not edit.\n"
PREAMBLE = "from collections.abc import Sequence\n\n"
ROOT = Path(__file__).resolve().parent.parent
PRIMITIVES = {"string": "str", "bool": "bool", "int": "int", "float": "float", "unit": "None"}
type Node = dict[str, Any]


def identifier(value: object) -> str:
    name = str(value)
    if not name.isidentifier() or keyword.iskeyword(name):
        raise ValueError(f"Unsupported Python identifier: {name}")
    return name


def schema(paths: tuple[Path, ...], *, reader: Path) -> list[Node]:
    result = subprocess.run(
        [str(reader), *(str(path) for path in paths)], check=True, capture_output=True, text=True
    )
    return json.loads(result.stdout)  # type: ignore[no-any-return]


def type_name(value: Node, *, qualify: bool = False) -> str:
    match value["kind"]:
        case "tuple":
            return (
                "tuple["
                + ", ".join(type_name(item, qualify=qualify) for item in value["items"])
                + "]"
            )
        case "name":
            name, arguments = str(value["name"]), value["args"]
            if name in ("list", "option") and len(arguments) == 1:
                item = type_name(arguments[0], qualify=qualify)
                return f"Sequence[{item}]" if name == "list" else f"{item} | None"
            if arguments:
                raise ValueError(f"Unsupported type application: {name}")
            if name in PRIMITIVES:
                return PRIMITIVES[name]
            parts = name.split(".")
            if len(parts) == 1:
                return ("Ast." if qualify else "") + identifier(name)
            if parts[-2] == "Ast":
                return ("Ast." if qualify else "") + identifier(parts[-1])
            raise ValueError(f"Unsupported type reference: {name}")
        case _:
            raise ValueError(f"Unsupported type node: {value['kind']}")


def record(value: Node) -> str:
    fields = [(identifier(field["name"]), type_name(field["type"])) for field in value["fields"]]
    parameters = ", ".join(f"{name}: {annotation}" for name, annotation in fields)
    name = identifier(value["name"])
    result = f"class {name}:\n    def __init__(self, *, {parameters}) -> None: ...\n"
    for name, annotation in fields:
        result += f"    @property\n    def {name}(self) -> {annotation}: ...\n"
    return result


def ast_bindings(items: list[Node]) -> str:
    result = HEADER + PREAMBLE
    for value in items:
        name, kind = identifier(value["name"]), value["kind"]
        if kind == "abstract":
            result += f"class {name}: ...\n\n"
        elif kind == "record":
            result += record(value) + "\n"
        elif kind == "variant":
            variants = []
            for constructor in value["constructors"]:
                variant, arguments = identifier(constructor["name"]), constructor["arguments"]
                variants.append(variant)
                result += f"class {variant}:\n"
                if arguments:
                    payload = (
                        arguments[0]
                        if len(arguments) == 1
                        else {"kind": "tuple", "items": arguments}
                    )
                    annotation = type_name(payload)
                    result += f"    def __init__(self, value: {annotation}, /) -> None: ...\n"
                    result += f"    def __getitem__(self, index: int, /) -> {annotation}: ...\n"
                else:
                    result += "    def __init__(self) -> None: ...\n"
            result += f"type {name} = {' | '.join(variants)}\n\n"
        elif kind == "alias":
            result += f"type {name} = {type_name(value['type'])}\n\n"
        else:
            raise ValueError(f"Unsupported AST declaration: {kind}")
    return result


def arrows(value: Node) -> tuple[list[Node], Node]:
    arguments = []
    while value["kind"] == "arrow":
        arguments.append(value)
        value = value["result"]
    return arguments, value


def operation(value: Node) -> str:
    name = identifier(value["name"])
    arguments, result = arrows(value["type"])
    if not arguments:
        return f"{name}: {type_name(result, qualify=True)}\n"
    positional, keywords = [], []
    for index, argument in enumerate(arguments):
        annotation = type_name(argument["argument"], qualify=True)
        if argument["label"]:
            keywords.append(
                f"{identifier(argument['label'])}: {annotation}"
                + (" = ..." if argument["optional"] else "")
            )
        elif annotation != "None":
            positional.append(f"value{index or ''}: {annotation}")
    parameters = positional + (["/"] if positional else []) + (["*", *keywords] if keywords else [])
    return f"def {name}({', '.join(parameters)}) -> {type_name(result, qualify=True)}: ...\n"


def options(value: Node) -> str:
    arguments, _ = arrows(value["type"])
    if not any(argument["optional"] for argument in arguments):
        return ""
    result = f"class {identifier(value['name']).capitalize()}Args(TypedDict, total=False):\n"
    for argument in arguments:
        annotation = type_name(argument["argument"], qualify=True)
        if annotation == "None" and not argument["label"]:
            continue
        if not argument["label"]:
            raise ValueError("Optional operation arguments must be labeled")
        if not argument["optional"]:
            annotation = f"Required[{annotation}]"
        result += f"    {identifier(argument['label'])}: {annotation}\n"
    return result + "\n"


def render(modules: list[Node]) -> dict[str, str]:
    if len(modules) != 1:
        raise ValueError("Expected one compiled public kernel interface")
    items = modules[0]["items"]
    ast = [item for item in items if item["kind"] not in ("module", "value")]
    outputs = {"Ast.pyi": ast_bindings(ast)}
    exports = []
    for module in items:
        if module["kind"] != "module":
            continue
        name, declarations = identifier(module["name"]), module["items"]
        if any(item["kind"] != "value" for item in declarations):
            raise ValueError(f"Operation module {name} contains non-value declarations")
        exports.append(name)
        outputs[name + ".pyi"] = (
            HEADER
            + PREAMBLE
            + "from typing import Required, TypedDict\nfrom . import Ast\n\n"
            + "".join(options(item) for item in declarations)
            + "".join(operation(item) for item in declarations)
        )
    if any(item["kind"] == "value" and item["name"] != "sources" for item in items):
        raise ValueError("Unexpected public root value")
    outputs["__init__.pyi"] = (
        HEADER
        + "\n"
        + "\n".join(f"from . import {name} as {name}" for name in ("Ast", *exports))
        + "\n\nclass InvalidArgument(Exception): ...\n"
        + "\ndef sources() -> tuple[tuple[str, str], ...]: ...\n"
    )
    return outputs


def generate(*, compiled: Path, reader: Path) -> dict[str, str]:
    return render(schema((compiled / "genius_evals_kernel.cmi",), reader=reader))


def write(outputs: dict[str, str], *, destination: Path, check: bool) -> None:
    with TemporaryDirectory(prefix="genius-kernel-types-") as temporary:
        staging = Path(temporary)
        for name, content in outputs.items():
            (staging / name).write_text(content)
        subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--select", "I", "--fix", str(staging)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--target-version",
                "py312",
                "--line-length",
                "100",
                str(staging),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        expected = set(outputs)
        for path in destination.glob("*.pyi"):
            if path.name not in expected:
                if check:
                    raise SystemExit("Kernel types changed; rerun make setup-kernel")
                path.unlink()
        for path in staging.glob("*.pyi"):
            target = destination / path.name
            content = path.read_text()
            if check:
                if not target.exists() or target.read_text() != content:
                    raise SystemExit("Kernel types changed; rerun make setup-kernel")
            else:
                target.write_text(content)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--compiled",
        type=Path,
        default=ROOT / "_build/default/ocaml/.genius_evals_kernel.objs/byte",
    )
    parser.add_argument("--reader", type=Path, default=ROOT / "_build/default/tools/bindings.exe")
    options_ = parser.parse_args()
    write(
        generate(compiled=options_.compiled, reader=options_.reader),
        destination=ROOT / "kernel",
        check=options_.check,
    )


if __name__ == "__main__":
    main()
