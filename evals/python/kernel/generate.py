"""Render named Python APIs from the compiler-owned public interface."""

import argparse
import json
import keyword
from pathlib import Path
from typing import Any

HEADER = "# Generated from compiled OCaml interfaces; do not edit.\n"
PREAMBLE = (
    "from collections.abc import Sequence\nfrom typing import Never\nimport kernel as _types\n\n"
)
PRIMITIVES = {"string": "str", "bool": "bool", "int": "int", "float": "float", "unit": "None"}
ERRORS = {"validation_failure", "grading_failure"}
type Node = dict[str, Any]


def identifier(value: object) -> str:
    name = str(value)
    if not name.isidentifier() or keyword.iskeyword(name):
        raise ValueError(f"Unsupported Python identifier: {name}")
    return name


def public_name(value: object) -> str:
    return identifier("".join(part[:1].upper() + part[1:] for part in identifier(value).split("_")))


def type_name(value: Node, *, qualify: bool = False, variants: frozenset[str] = frozenset()) -> str:
    if value["kind"] == "tuple":
        return (
            "tuple["
            + ", ".join(
                type_name(item, qualify=qualify, variants=variants) for item in value["items"]
            )
            + "]"
        )
    if value["kind"] != "name":
        raise ValueError(f"Unsupported type node: {value['kind']}")
    name, arguments = str(value["name"]), value["args"]
    if name in ("list", "option") and len(arguments) == 1:
        item = type_name(arguments[0], qualify=qualify, variants=variants)
        return f"Sequence[{item}]" if name == "list" else f"{item} | None"
    if arguments:
        raise ValueError(f"Unsupported type application: {name}")
    if name in PRIMITIVES:
        return PRIMITIVES[name]
    parts = name.split(".")
    if len(parts) > 1 and parts[-2] != "Ast":
        raise ValueError(f"Unsupported type reference: {name}")
    return (
        ("_types." if qualify else "")
        + public_name(parts[-1])
        + (".Value" if parts[-1] in variants else "")
    )


def result_payload(value: Node) -> tuple[Node, Node] | None:
    if value["kind"] != "name" or value["name"] not in ("result", "Stdlib.result"):
        return None
    success, failure = value["args"]
    if failure["kind"] != "name" or failure["name"] not in ERRORS:
        raise ValueError("Unsupported native result failure")
    return success, failure


def arrows(value: Node) -> tuple[list[Node], Node]:
    arguments = []
    while value["kind"] == "arrow":
        arguments.append(value)
        value = value["result"]
    return arguments, value


def named_arguments(value: Node) -> tuple[list[Node], Node]:
    arguments, result = arrows(value["type"])
    named = []
    for argument in arguments:
        if not argument["label"]:
            if argument["argument"] == {"kind": "name", "name": "unit", "args": []}:
                continue
            raise ValueError(f"Operation {value['name']} arguments must be named")
        identifier(argument["label"])
        named.append(argument)
    return named, result


def operation(value: Node, *, variants: frozenset[str] = frozenset()) -> str:
    arguments, result = named_arguments(value)
    if value["type"]["kind"] != "arrow":
        return (
            f"{identifier(value['name'])}: {type_name(result, qualify=True, variants=variants)}\n"
        )
    parameters = [
        f"{arg['label']}: {type_name(arg['argument'], qualify=True, variants=variants)}"
        + (" = ..." if arg["optional"] else "")
        for arg in arguments
    ]
    payload = result_payload(result)
    returned = type_name(result if payload is None else payload[0], qualify=True, variants=variants)
    arguments_text = ", ".join(["*", *parameters]) if parameters else ""
    return f"def {identifier(value['name'])}({arguments_text}) -> {returned}: ...\n"


def options(value: Node, *, variants: frozenset[str] = frozenset()) -> str:
    arguments, _ = named_arguments(value)
    if not any(arg["optional"] for arg in arguments):
        return ""
    result = f"class {identifier(value['name']).capitalize()}Args(TypedDict, total=False):\n"
    for arg in arguments:
        annotation = type_name(arg["argument"], qualify=True, variants=variants)
        result += (
            f"    {arg['label']}: {annotation if arg['optional'] else f'Required[{annotation}]'}\n"
        )
    return result + "\n"


def fields_body(fields: list[Node], *, variants: frozenset[str], private: bool = False) -> str:
    parameters = [
        f"{identifier(field['name'])}: {type_name(field['type'], variants=variants)}"
        for field in fields
    ]
    parameters = ["_token: Never"] if private else parameters
    arguments_text = ", *, " + ", ".join(parameters) if parameters else ""
    result = f"    def __init__(self{arguments_text}) -> None: ...\n"
    return result + "".join(
        f"    @property\n    def {identifier(field['name'])}(self) -> "
        f"{type_name(field['type'], variants=variants)}: ...\n"
        for field in fields
    )


def variant_exports(items: list[Node]) -> list[tuple[str, str, str]]:
    exports: list[tuple[str, str, str]] = []
    for item in items:
        if item["kind"] != "variant":
            continue
        names = [public_name(ctor["name"]) for ctor in item["constructors"]]
        if len({"Value", *names}) != len(names) + 1:
            raise ValueError("Owned alternative names collide with each other or Value")
        exports.extend(
            (public_name(item["name"]), name, str(ctor["name"]))
            for name, ctor in zip(names, item["constructors"], strict=True)
        )
    return exports


def variant_bindings(value: Node, *, variants: frozenset[str]) -> str:
    variant_exports([value])
    name = public_name(value["name"])
    result = f"class {name}:\n"
    for ctor in value["constructors"]:
        result += f"    class {public_name(ctor['name'])}(_types.{name}):\n"
        result += "".join(
            "    " + line + "\n"
            for line in fields_body(ctor["fields"], variants=variants).splitlines()
        )
    alternatives = " | ".join(public_name(ctor["name"]) for ctor in value["constructors"])
    return result + f"    type Value = {alternatives}\n\n"


def constructor_operations(items: list[Node]) -> dict[str, Node]:
    constructors: list[Node] = next(
        (
            item["items"]
            for item in items
            if item["kind"] == "module" and item["name"] == "Construct"
        ),
        [],
    )
    result = {}
    for value in constructors:
        _, returned = named_arguments(value)
        payload = result_payload(returned)
        returned = returned if payload is None else payload[0]
        if returned["kind"] != "name" or returned["name"] != value["name"]:
            raise ValueError(f"Constructor {value['name']} must return its namesake domain type")
        result[value["name"]] = value
    return result


def ast_bindings(items: list[Node], *, constructors: dict[str, Node] | None = None) -> str:
    variants = frozenset(str(item["name"]) for item in items if item["kind"] == "variant")
    result = HEADER + PREAMBLE
    for value in items:
        name, kind = public_name(value["name"]), value["kind"]
        if kind == "variant":
            result += variant_bindings(value, variants=variants)
        elif kind == "alias":
            result += f"type {name} = {type_name(value['type'], variants=variants)}\n\n"
        elif kind in ("abstract", "record"):
            result += f"class {name}:\n"
            result += fields_body(
                value.get("fields", []),
                variants=variants,
                private=value.get("private", False) or kind == "abstract",
            )
            if factory := (constructors or {}).get(value["name"]):
                result += "    @staticmethod\n    " + operation(
                    {**factory, "name": "create"}, variants=variants
                )
            result += "\n"
        else:
            raise ValueError(f"Unsupported AST declaration: {kind}")
    return result


def type_exports(items: list[Node]) -> list[tuple[str, str]]:
    exports = [(public_name(item["name"]), str(item["name"])) for item in items]
    if len({"ValidationError", "GradingError", *(name for name, _ in exports)}) != len(exports) + 2:
        raise ValueError("Public Python type and constructor names collide")
    return sorted(exports)


def runtime_types(items: list[Node], *, constructors: dict[str, Node]) -> str:
    result = (
        HEADER
        + "from ._bridge import GradingError as GradingError, ValidationError as ValidationError\n"
        "from ._bridge import native as _native, named as _named\n"
        "from ._operations import construct as _construct\n\n"
    )
    records = {str(item["name"]) for item in items if item["kind"] == "record"}
    for name, original in type_exports(items):
        value = f"_native.{original}"
        result += (
            f"{name} = " + (f"_named(constructor={value})" if original in records else value) + "\n"
        )
    result += (
        "\n"
        + "\n".join(
            f"{public_name(item['name'])}.Value = {public_name(item['name'])}"
            for item in items
            if item["kind"] == "variant"
        )
        + "\n"
    )
    result += (
        "\n".join(
            f"{owner}.{name} = _named(constructor=_native.{original})"
            for owner, name, original in variant_exports(items)
        )
        + "\n\n"
    )
    result += "\n".join(
        f"{public_name(name)}.create = staticmethod(_construct.{name})" for name in constructors
    )
    return (
        result
        + "\n\n__all__ = "
        + repr(
            sorted(["ValidationError", "GradingError", *(name for name, _ in type_exports(items))])
        )
        + "\n"
    )


def runtime_operations(modules: list[Node]) -> str:
    result = (
        HEADER + "from functools import cache\nfrom types import SimpleNamespace\n"
        "from ._bridge import native as _native, bind as _bind\n\n"
    )
    for module in modules:
        entries = []
        for value in module["items"]:
            arguments, returned = named_arguments(value)
            native = f"_native.{module['name']}.{value['name']}"
            if value["type"]["kind"] == "arrow":
                parameters = {arg["label"]: arg["optional"] for arg in arguments}
                payload = result_payload(returned)
                failure = None if payload is None else payload[1]["name"]
                native = f"_bind(operation={native}, arguments={parameters!r}, failure={failure!r})"
            entries.append(f"    {value['name']}={native},")
        result += f"{module['name'].lower()} = SimpleNamespace(\n" + "\n".join(entries) + "\n)\n\n"
    result += (
        "@cache\ndef sources() -> tuple[tuple[str, str], ...]:\n"
        "    return tuple((str(name), str(contents)) for name, contents in _native.sources)\n"
    )
    return (
        result
        + "\n__all__ = "
        + repr(sorted([*(m["name"].lower() for m in modules), "sources"]))
        + "\n"
    )


def render(modules: list[Node]) -> dict[str, str]:
    if len(modules) != 1:
        raise ValueError("Expected one compiled public kernel interface")
    items = modules[0]["items"]
    ast = [item for item in items if item["kind"] not in ("module", "value")]
    constructors = constructor_operations(items)
    variants = frozenset(str(item["name"]) for item in ast if item["kind"] == "variant")
    operations = [item for item in items if item["kind"] == "module"]
    outputs = {
        "__init__.py": runtime_types(ast, constructors=constructors),
        "__init__.pyi": ast_bindings(ast, constructors=constructors)
        + "from ._bridge import ValidationError as ValidationError, GradingError as GradingError\n",
    }
    for module in operations:
        if any(item["kind"] != "value" for item in module["items"]):
            raise ValueError(f"Operation module {module['name']} contains non-value declarations")
        outputs["_" + module["name"].lower() + ".pyi"] = (
            HEADER
            + PREAMBLE
            + "from typing import Required, TypedDict\n\n"
            + "".join(
                options(value, variants=variants) + operation(value, variants=variants)
                for value in module["items"]
            )
        )
    if any(item["kind"] == "value" and item["name"] != "sources" for item in items):
        raise ValueError("Unexpected public root value")
    outputs["_operations.py"] = runtime_operations(operations)
    names = sorted([*(module["name"].lower() for module in operations), "sources"])
    outputs["_operations.pyi"] = (
        HEADER
        + "\n"
        + "\n".join(
            f"from . import _{module['name'].lower()} as {module['name'].lower()}"
            for module in operations
        )
        + "\ndef sources() -> tuple[tuple[str, str], ...]: ...\n\n__all__ = "
        + repr(names)
        + "\n"
    )
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schema", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    for name, content in render(json.loads(args.schema.read_text())).items():
        (args.destination / name).write_text(content)


if __name__ == "__main__":
    main()
