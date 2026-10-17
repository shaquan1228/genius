"""Render named Python APIs from the compiler-owned public interface."""

import argparse
import json
import keyword
from pathlib import Path
from textwrap import indent
from typing import Any

HEADER = "# Generated from compiled OCaml interfaces; do not edit.\n"
PREAMBLE = (
    "from collections.abc import Sequence\n"
    "from typing import ClassVar, Never, Required, TypedDict, overload\n"
    "import kernel as _types\n\n"
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
    if len(parts) > 1:
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
    if value.get("exclusive"):
        raw, _ = arrows(value["type"])
        if (
            len(arguments) < 2
            or len(raw) != len(arguments) + 1
            or raw[-1]["label"]
            or raw[-1]["argument"] != {"kind": "name", "name": "unit", "args": []}
            or any(not arg["optional"] for arg in arguments)
        ):
            raise ValueError(
                "Exclusive factories require optional named alternatives and final unit"
            )
        payload = result_payload(result)
        returned = type_name(
            result if payload is None else payload[0], qualify=True, variants=variants
        )
        return "".join(
            f"@overload\ndef {identifier(value['name'])}(*, {arg['label']}: "
            f"{type_name(arg['argument'], qualify=True, variants=variants)}) -> {returned}: ...\n"
            for arg in arguments
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
    result += owner_bindings(value, variants=variants)
    for ctor in value["constructors"]:
        result += f"    class {public_name(ctor['name'])}(_types.{name}):\n"
        result += "".join(
            "    " + line + "\n"
            for line in fields_body(
                ctor["fields"], variants=variants, private=value.get("private", False)
            ).splitlines()
        )
    alternatives = " | ".join(public_name(ctor["name"]) for ctor in value["constructors"])
    return result + f"    type Value = {alternatives}\n\n"


def domain_bindings(items: list[Node]) -> str:
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
            result += owner_bindings(value, variants=variants)
            result += "\n"
        else:
            raise ValueError(f"Unsupported domain declaration: {kind}")
    return result


def type_exports(items: list[Node]) -> list[tuple[str, str]]:
    exports = [(public_name(item["name"]), str(item.get("native", item["name"]))) for item in items]
    if len({"ValidationError", "GradingError", *(name for name, _ in exports)}) != len(exports) + 2:
        raise ValueError("Public Python type and constructor names collide")
    return sorted(exports)


def owner_bindings(value: Node, *, variants: frozenset[str]) -> str:
    result = ""
    for method in value.get("methods", []):
        if method["type"]["kind"] == "arrow":
            if not method.get("exclusive"):
                result += options(method, variants=variants)
            result += operation(method, variants=variants).replace(
                f"def {method['name']}(", f"@staticmethod\ndef {method['name']}("
            )
        else:
            result += (
                f"{identifier(method['name'])}: ClassVar["
                + type_name(method["type"], qualify=True, variants=variants)
                + "]\n"
            )
    return indent(result, "    ")


def runtime_member(owner: str, *, value: Node) -> str:
    native = f"_native.{owner}.{value['name']}"
    if value["type"]["kind"] != "arrow":
        return native
    arguments, returned = named_arguments(value)
    parameters = {arg["label"]: arg["optional"] for arg in arguments}
    payload = result_payload(returned)
    failure = None if payload is None else payload[1]["name"]
    return f"staticmethod(_bind(operation={native}, arguments={parameters!r}, failure={failure!r}))"


def runtime_types(items: list[Node]) -> str:
    exports = type_exports(items)
    result = (
        HEADER
        + "from ._bridge import GradingError as GradingError, ValidationError as ValidationError\n"
        + "from ._bridge import native as _native, named as _named, bind as _bind\n\n"
    )
    records = {str(item.get("native", item["name"])) for item in items if item["kind"] == "record"}
    for name, original in exports:
        native = f"_native.{original}"
        result += (
            f"{name} = "
            + (f"_named(constructor={native})" if original in records else native)
            + "\n"
        )
    for item in items:
        if item["kind"] == "variant":
            owner = public_name(item["name"])
            result += f"{owner}.Value = {owner}\n"
        for owner, name, original in variant_exports([item]):
            prefix = str(item["owner"]) + "." if "owner" in item else ""
            result += f"{owner}.{name} = _named(constructor=_native.{prefix}{original})\n"
            if item.get("private"):
                result += f"{owner}.{name}._default_type = ()\n"
        for method in item.get("methods", []):
            result += (
                f"{public_name(item['name'])}.{method['name']} = "
                + runtime_member(item["owner"], value=method)
                + "\n"
            )
    return (
        result
        + "\n__all__ = "
        + repr(sorted(["ValidationError", "GradingError", *(name for name, _ in exports)]))
        + "\n"
    )


def normalize(value: object, *, local: dict[str, str]) -> Any:
    if isinstance(value, list):
        return [normalize(item, local=local) for item in value]
    if not isinstance(value, dict):
        return value
    result = {name: normalize(item, local=local) for name, item in value.items()}
    if result.get("kind") == "name":
        name = str(result["name"])
        parts = name.split(".")
        if name in local:
            result["name"] = local[name]
        elif len(parts) > 1 and parts[-1] == "t":
            result["name"] = parts[-2].lower()
    return result


def owner_declarations(items: list[Node]) -> tuple[list[Node], list[Node]]:
    values, owners = [], []
    for module in items:
        if module["kind"] != "module":
            raise ValueError("Public kernel exports must be owner types")
        name = identifier(module["name"])
        declarations = module["items"]
        local = {
            str(item["name"]): name.lower() if item["name"] == "t" else str(item["name"])
            for item in declarations
            if item["kind"] != "value"
        }
        normalized = normalize(declarations, local=local)
        operations = [item for item in normalized if item["kind"] == "value"]
        owners.append({"name": name, "items": operations})
        if operations and "t" not in local:
            raise ValueError("Public owner operations require a native type t")
        factory = next((item for item in operations if item["name"] == "create"), None)
        if factory is not None and "t" in local:
            _, returned = named_arguments(factory)
            payload = result_payload(returned)
            returned = returned if payload is None else payload[0]
            if returned["kind"] != "name" or returned["name"] != local["t"]:
                raise ValueError("Factory must return its owner type")
        for original, item in zip(declarations, normalized, strict=True):
            if item["kind"] == "value":
                continue
            item.update(
                name=local[str(original["name"])], owner=name, native=f"{name}.{original['name']}"
            )
            if original["name"] == "t":
                if item["kind"] == "alias" and operations:
                    raise ValueError("Native aliases cannot own public operations")
                item["methods"] = operations
            values.append(item)
    return values, owners


def render(modules: list[Node]) -> dict[str, str]:
    if len(modules) != 1:
        raise ValueError("Expected one compiled public kernel interface")
    values, _ = owner_declarations(modules[0]["items"])
    return {
        "__init__.py": runtime_types(values),
        "__init__.pyi": domain_bindings(values)
        + "from ._bridge import ValidationError as ValidationError, GradingError as GradingError\n",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schema", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    for name, content in render(json.loads(args.schema.read_text())).items():
        (args.destination / name).write_text(content)


if __name__ == "__main__":
    main()
