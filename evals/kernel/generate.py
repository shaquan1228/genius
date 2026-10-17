"""Render the Python API from a compiler-derived interface schema supplied by Dune."""

import argparse
import json
import keyword
from pathlib import Path
from typing import Any

HEADER = "# Generated from compiled OCaml interfaces; do not edit.\n"
PREAMBLE = "from collections.abc import Sequence\n\n"
PRIMITIVES = {"string": "str", "bool": "bool", "int": "int", "float": "float", "unit": "None"}
TYPE_NAMES = {"answer": "Rubric"}
type Node = dict[str, Any]


def identifier(value: object) -> str:
    name = str(value)
    if not name.isidentifier() or keyword.iskeyword(name):
        raise ValueError(f"Unsupported Python identifier: {name}")
    return name


def public_name(value: object) -> str:
    name = identifier(value)
    return identifier(
        TYPE_NAMES.get(name, "".join(part[:1].upper() + part[1:] for part in name.split("_")))
    )


def type_name(value: Node, *, qualify: bool = False, variants: frozenset[str] = frozenset()) -> str:
    match value["kind"]:
        case "tuple":
            return (
                "tuple["
                + ", ".join(
                    type_name(item, qualify=qualify, variants=variants) for item in value["items"]
                )
                + "]"
            )
        case "name":
            name, arguments = str(value["name"]), value["args"]
            if name in ("list", "option") and len(arguments) == 1:
                item = type_name(arguments[0], qualify=qualify, variants=variants)
                return f"Sequence[{item}]" if name == "list" else f"{item} | None"
            if arguments:
                raise ValueError(f"Unsupported type application: {name}")
            if name in PRIMITIVES:
                return PRIMITIVES[name]
            parts = name.split(".")
            if len(parts) == 1:
                return (
                    ("_types." if qualify else "")
                    + public_name(name)
                    + (".Value" if name in variants else "")
                )
            if parts[-2] == "Ast":
                return (
                    ("_types." if qualify else "")
                    + public_name(parts[-1])
                    + (".Value" if parts[-1] in variants else "")
                )
            raise ValueError(f"Unsupported type reference: {name}")
        case _:
            raise ValueError(f"Unsupported type node: {value['kind']}")


def record(value: Node, *, variants: frozenset[str]) -> str:
    fields = [
        (identifier(field["name"]), type_name(field["type"], variants=variants))
        for field in value["fields"]
    ]
    parameters = ", ".join(f"{name}: {annotation}" for name, annotation in fields)
    name = public_name(value["name"])
    result = f"class {name}:\n    def __init__(self, *, {parameters}) -> None: ...\n"
    for name, annotation in fields:
        result += f"    @property\n    def {name}(self) -> {annotation}: ...\n"
    return result


def variant_exports(items: list[Node]) -> list[tuple[str, str, str]]:
    exports: list[tuple[str, str, str]] = []
    for item in items:
        if item["kind"] != "variant":
            continue
        names = [public_name(constructor["name"]) for constructor in item["constructors"]]
        if len({"Value", *names}) != len(names) + 1:
            raise ValueError("Owned alternative names collide with each other or Value")
        exports.extend(
            (public_name(item["name"]), name, str(constructor["name"]))
            for name, constructor in zip(names, item["constructors"], strict=True)
        )
    return exports


def variant_bindings(value: Node, *, variants: frozenset[str]) -> str:
    variant_exports([value])
    name = public_name(value["name"])
    result = f"class {name}:\n"
    alternatives = []
    for constructor in value["constructors"]:
        variant, arguments = public_name(constructor["name"]), constructor["arguments"]
        alternatives.append(variant)
        result += f"    class {variant}(_types.{name}):\n"
        if arguments:
            payload = arguments[0] if len(arguments) == 1 else {"kind": "tuple", "items": arguments}
            annotation = type_name(payload, variants=variants)
            result += f"        def __init__(self, value: {annotation}, /) -> None: ...\n"
            result += f"        def __getitem__(self, index: int, /) -> {annotation}: ...\n"
        else:
            result += "        def __init__(self) -> None: ...\n"
    return result + f"    type Value = {' | '.join(alternatives)}\n\n"


def ast_bindings(items: list[Node]) -> str:
    variants = frozenset(str(item["name"]) for item in items if item["kind"] == "variant")
    result = HEADER + PREAMBLE + "import kernel as _types\n\n"
    for value in items:
        name, kind = public_name(value["name"]), value["kind"]
        if kind == "abstract":
            result += f"class {name}: ...\n\n"
        elif kind == "record":
            result += record(value, variants=variants) + "\n"
        elif kind == "variant":
            result += variant_bindings(value, variants=variants)
        elif kind == "alias":
            result += f"type {name} = {type_name(value['type'], variants=variants)}\n\n"
        else:
            raise ValueError(f"Unsupported AST declaration: {kind}")
    return result


def type_exports(items: list[Node]) -> list[tuple[str, str]]:
    names = [str(item["name"]) for item in items]
    exports = [(public_name(name), name) for name in names]
    if len({"InvalidArgument", *(name for name, _ in exports)}) != len(exports) + 1:
        raise ValueError("Public Python type and constructor names collide")
    return sorted(exports)


def runtime_types(items: list[Node]) -> str:
    exports = type_exports(items)
    names = ["InvalidArgument", *(name for name, _ in exports)]
    alternatives = []
    for item in items:
        if item["kind"] != "variant":
            continue
        owner = public_name(item["name"])
        alternatives.append(f"{owner}.Value = {owner}")
    alternatives.extend(
        f"{owner}.{name} = _native.{original}" for owner, name, original in variant_exports(items)
    )
    return (
        HEADER
        + '"""Native domain types, with alternatives attached to their owners."""\n\n'
        + "from ._bridge import InvalidArgument as InvalidArgument\n"
        + "from ._bridge import native as _native\n\n"
        + "\n".join(f"{name} = _native.{original}" for name, original in exports)
        + "\n\n"
        + "\n".join(alternatives)
        + "\n\n__all__ = "
        + repr(sorted(names))
        + "\n"
    )


def runtime_operations(modules: list[str]) -> str:
    return (
        HEADER
        + '"""Private native operations used by the Python implementation."""\n\n'
        + "from functools import cache\n\nfrom ._bridge import native as _native\n\n"
        + "\n".join(f"{name.lower()} = _native.{name}" for name in modules)
        + "\n\n@cache\ndef sources() -> tuple[tuple[str, str], ...]:\n"
        + "    return tuple((str(name), str(contents)) for name, contents in _native.sources)\n"
        + "\n__all__ = "
        + repr(sorted([*(name.lower() for name in modules), "sources"]))
        + "\n"
    )


def arrows(value: Node) -> tuple[list[Node], Node]:
    arguments = []
    while value["kind"] == "arrow":
        arguments.append(value)
        value = value["result"]
    return arguments, value


def operation(value: Node, *, variants: frozenset[str] = frozenset()) -> str:
    name = identifier(value["name"])
    arguments, result = arrows(value["type"])
    if not arguments:
        return f"{name}: {type_name(result, qualify=True, variants=variants)}\n"
    positional, keywords = [], []
    for index, argument in enumerate(arguments):
        annotation = type_name(argument["argument"], qualify=True, variants=variants)
        if argument["label"]:
            keywords.append(
                f"{identifier(argument['label'])}: {annotation}"
                + (" = ..." if argument["optional"] else "")
            )
        elif annotation != "None":
            positional.append(f"value{index or ''}: {annotation}")
    parameters = positional + (["/"] if positional else []) + (["*", *keywords] if keywords else [])
    result_type = type_name(result, qualify=True, variants=variants)
    return f"def {name}({', '.join(parameters)}) -> {result_type}: ...\n"


def options(value: Node, *, variants: frozenset[str] = frozenset()) -> str:
    arguments, _ = arrows(value["type"])
    if not any(argument["optional"] for argument in arguments):
        return ""
    result = f"class {identifier(value['name']).capitalize()}Args(TypedDict, total=False):\n"
    for argument in arguments:
        annotation = type_name(argument["argument"], qualify=True, variants=variants)
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
    outputs = {
        "__init__.py": runtime_types(ast),
        "__init__.pyi": ast_bindings(ast) + "class InvalidArgument(Exception): ...\n",
    }
    variants = frozenset(str(item["name"]) for item in ast if item["kind"] == "variant")
    exports = []
    for module in items:
        if module["kind"] != "module":
            continue
        name, declarations = identifier(module["name"]), module["items"]
        if any(item["kind"] != "value" for item in declarations):
            raise ValueError(f"Operation module {name} contains non-value declarations")
        exports.append(name)
        outputs["_" + name.lower() + ".pyi"] = (
            HEADER
            + PREAMBLE
            + "from typing import Required, TypedDict\nimport kernel as _types\n\n"
            + "".join(options(item, variants=variants) for item in declarations)
            + "".join(operation(item, variants=variants) for item in declarations)
        )
    if any(item["kind"] == "value" and item["name"] != "sources" for item in items):
        raise ValueError("Unexpected public root value")
    outputs["_operations.py"] = runtime_operations(exports)
    outputs["_operations.pyi"] = (
        HEADER
        + "\n"
        + "\n".join(f"from . import _{name.lower()} as {name.lower()}" for name in exports)
        + "\ndef sources() -> tuple[tuple[str, str], ...]: ...\n"
        + "\n__all__ = "
        + repr(sorted([*(name.lower() for name in exports), "sources"]))
        + "\n"
    )
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schema", type=Path)
    parser.add_argument("destination", type=Path)
    arguments = parser.parse_args()
    for name, content in render(json.loads(arguments.schema.read_text())).items():
        (arguments.destination / name).write_text(content)


if __name__ == "__main__":
    main()
