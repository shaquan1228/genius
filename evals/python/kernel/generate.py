"""Render named Python APIs from the compiler-owned public interface."""

import argparse
import json
import keyword
from pathlib import Path
from textwrap import indent
from typing import Any

HEADER = "# Generated from compiled OCaml interfaces; do not edit.\n"
PREAMBLE = (
    "from collections.abc import Mapping, Sequence\n"
    "from typing import ClassVar, Never, Required, TypedDict, overload\n"
    "import {package} as _types\n\n"
    "# Any JSON-shaped input is accepted where the kernel expects a value.\n"
    "type Json = None | bool | int | float | str | Sequence[Json] | Mapping[str, Json]\n\n"
)
RESERVED = {
    "_bind",
    "_named",
    "_native",
    "_types",
    "__all__",
    "Json",
    "Mapping",
    "Sequence",
    "ClassVar",
    "Never",
    "Required",
    "TypedDict",
    "overload",
}
PRIMITIVES = {"string": "str", "bool": "bool", "int": "int", "float": "float", "unit": "None"}
type Node = dict[str, Any]


def identifier(value: object) -> str:
    name = str(value)
    if not name.isidentifier() or keyword.iskeyword(name):
        raise ValueError(f"Unsupported Python identifier: {name}")
    return name


def public_name(value: object) -> str:
    return identifier("".join(part[:1].upper() + part[1:] for part in identifier(value).split("_")))


def type_name(
    value: Node,
    *,
    qualify: bool = False,
    variants: frozenset[str] = frozenset(),
    loose: bool = False,
) -> str:
    """Render a type; a loose rendering also accepts JSON where a value is expected."""
    if value["kind"] == "tuple":
        return (
            "tuple["
            + ", ".join(
                type_name(item, qualify=qualify, variants=variants, loose=loose)
                for item in value["items"]
            )
            + "]"
        )
    if value["kind"] != "name":
        raise ValueError(f"Unsupported type node: {value['kind']}")
    name, arguments = str(value["name"]), value["args"]
    if name in ("list", "option") and len(arguments) == 1:
        item = type_name(arguments[0], qualify=qualify, variants=variants, loose=loose)
        if name == "option":
            return f"{item} | None"
        return f"Sequence[{item}]" + (
            f" | Mapping[{item[6:-1]}]" if loose and named_pairs(arguments[0]) else ""
        )
    if loose and name == "value":
        return ("_types." if qualify else "") + "Value.Value | Json"
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


def named_pairs(node: Node) -> bool:
    """A list of (string, _) pairs also accepts a mapping at the bridge."""
    return (
        node["kind"] == "tuple"
        and len(node["items"]) == 2
        and node["items"][0] == {"kind": "name", "name": "string", "args": []}
    )


def result_payload(value: Node) -> tuple[Node, Node] | None:
    if value["kind"] != "name" or value["name"] not in ("result", "Stdlib.result"):
        return None
    success, failure = value["args"]
    if failure["kind"] != "name" or failure["args"]:
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
            f"{type_name(arg['argument'], qualify=True, variants=variants, loose=True)})"
            f" -> {returned}: ...\n"
            for arg in arguments
        )
    parameters = [
        f"{arg['label']}: "
        f"{type_name(arg['argument'], qualify=True, variants=variants, loose=True)}"
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
        annotation = type_name(arg["argument"], qualify=True, variants=variants, loose=True)
        result += (
            f"    {arg['label']}: {annotation if arg['optional'] else f'Required[{annotation}]'}\n"
        )
    return result + "\n"


def fields_body(fields: list[Node], *, variants: frozenset[str], private: bool = False) -> str:
    parameters = [
        f"{identifier(field['name'])}: {type_name(field['type'], variants=variants, loose=True)}"
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


def domain_bindings(items: list[Node], *, package: str) -> str:
    variants = frozenset(
        str(item["name"]) for item in items if item["kind"] in ("variant", "namespace_alias")
    )
    result = HEADER + PREAMBLE.format(package=package)
    for value in items:
        name, kind = public_name(value["name"]), value["kind"]
        if kind == "value":
            result += operation(value, variants=variants) + "\n"
        elif kind in ("namespace", "namespace_alias"):
            result += f"class {name}:\n"
            if kind == "namespace_alias":
                result += f"    type Value = {type_name(value['type'], variants=variants)}\n"
            result += owner_bindings(value, variants=variants) or "    ...\n"
            result += "\n"
        elif kind == "variant":
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


def type_exports(items: list[Node], *, exceptions: tuple[str, ...] = ()) -> list[tuple[str, str]]:
    exports = [
        (
            identifier(item["name"]) if item["kind"] == "value" else public_name(item["name"]),
            str(item.get("native", item["name"])),
        )
        for item in items
    ]
    names = [*exceptions, *(name for name, _ in exports)]
    if len(set(names)) != len(names) or RESERVED.intersection(names):
        raise ValueError("Public Python type and constructor names collide")
    if len({native for _, native in exports}) != len(exports):
        raise ValueError("Native names collide in the bridge namespace")
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


def holds_value(node: Node) -> bool:
    if node["kind"] == "tuple":
        return any(holds_value(item) for item in node["items"])
    return node["name"] == "value" or any(holds_value(item) for item in node["args"])


def coercions(typed: list[tuple[str, Node]]) -> str:
    """Render the value-bearing inputs the bridge converts from plain Python."""
    specs = {name: node for name, node in typed if holds_value(node)}
    return f", coerce={specs!r}" if specs else ""


def runtime_member(owner: str, *, value: Node, method: bool = False) -> str:
    native = "_native." + ".".join(filter(None, (owner, value["name"])))
    if value["type"]["kind"] != "arrow":
        return native
    arguments, returned = named_arguments(value)
    parameters = {arg["label"]: arg["optional"] for arg in arguments}
    payload = result_payload(returned)
    failure = None if payload is None else payload[1]["name"]
    typed = [(str(arg["label"]), arg["argument"]) for arg in arguments]
    bound = (
        f"_bind(operation={native}, arguments={parameters!r}, failure={failure!r}"
        + coercions(typed)
        + ")"
    )
    return f"staticmethod({bound})" if method else bound


def record_member(native: str, *, fields: list[Node]) -> str:
    typed = [(str(field["name"]), field["type"]) for field in fields]
    return f"_named(constructor={native}{coercions(typed)})"


def runtime_types(items: list[Node], *, exceptions: tuple[str, ...] = ()) -> str:
    exports = type_exports(items, exceptions=exceptions)
    result = (
        HEADER
        + exception_imports(exceptions)
        + "from ._bridge import native as _native, named as _named, bind as _bind\n\n"
    )
    records = {
        str(item.get("native", item["name"])): item["fields"]
        for item in items
        if item["kind"] == "record"
    }
    by_name = {str(item.get("native", item["name"])): item for item in items}
    for name, original in exports:
        item = by_name[original]
        if item["kind"] == "value":
            result += f"{name} = {runtime_member(item['owner'], value=item)}\n"
            continue
        if item["kind"] in ("namespace", "namespace_alias"):
            result += f"class {name}:\n    pass\n"
            if item["kind"] == "namespace_alias":
                result += f"{name}.Value = _native.{original}\n"
            continue
        native = f"_native.{original}"
        result += (
            f"{name} = "
            + (record_member(native, fields=records[original]) if original in records else native)
            + "\n"
        )
    for item in items:
        if item["kind"] == "variant":
            owner = public_name(item["name"])
            result += f"{owner}.Value = {owner}\n"
        for owner, name, original in variant_exports([item]):
            prefix = str(item["owner"]) + "." if "owner" in item else ""
            fields = next(c["fields"] for c in item["constructors"] if c["name"] == original)
            result += (
                f"{owner}.{name} = {record_member(f'_native.{prefix}{original}', fields=fields)}\n"
            )
            if item.get("private"):
                result += f"{owner}.{name}._default_type = ()\n"
        for method in item.get("methods", []):
            result += (
                f"{public_name(item['name'])}.{method['name']} = "
                + runtime_member(item["owner"], value=method, method=True)
                + "\n"
            )
    return (
        result + "\n__all__ = " + repr(sorted([*exceptions, *(name for name, _ in exports)])) + "\n"
    )


def declarations(modules: list[Node]) -> list[Node]:
    symbols: dict[tuple[str, ...], str] = {}
    scopes: list[tuple[tuple[str, ...], str, list[Node]]] = []

    def collect(items: list[Node], *, path: tuple[str, ...], root: str) -> None:
        scopes.append((path, root, items))
        for item in items:
            name = str(item["name"])
            if item["kind"] == "module":
                collect(item["items"], path=(*path, name), root=root)
            elif item["kind"] != "value":
                symbols[(root, *path, name)] = (
                    "_".join(path).lower() if name == "t" and path else name
                )

    for module in modules:
        collect(module["items"], path=(), root=str(module["module"]))

    def resolve(value: Any, *, path: tuple[str, ...], root: str) -> Any:
        if isinstance(value, list):
            return [resolve(item, path=path, root=root) for item in value]
        if not isinstance(value, dict):
            return value
        result = {key: resolve(item, path=path, root=root) for key, item in value.items()}
        if result.get("kind") == "name":
            name = str(result["name"])
            parts = tuple(name.split("."))
            # A module's own name still refers to its outer namesake inside its body.
            candidates = [
                (root, *path[:length], *parts)
                for length in range(len(path), -1, -1)
                if length == len(path) or parts[0] != path[length]
            ]
            candidates.append(parts)
            resolved = next((symbols[key] for key in candidates if key in symbols), None)
            if resolved is not None:
                result["name"] = resolved
            elif name not in {*PRIMITIVES, "list", "option", "result", "Stdlib.result"}:
                raise ValueError(f"Unresolved type reference: {name}")
        return result

    values: list[Node] = []
    for path, root, items in scopes:
        operations = [
            resolve(item, path=path, root=root) for item in items if item["kind"] == "value"
        ]
        primary = next(
            (item for item in items if item.get("name") == "t" and item["kind"] != "value"), None
        )
        native_path = (root, *path) if len(modules) > 1 else path
        owner = ".".join(native_path)
        if not path:
            values.extend(
                dict(item, owner=owner, native=".".join((*native_path, item["name"])))
                for item in operations
            )
        elif primary is None and operations:
            values.append(
                {
                    "kind": "namespace",
                    "name": "_".join(path).lower(),
                    "native": owner,
                    "owner": owner,
                    "methods": operations,
                }
            )
        for original in items:
            if original["kind"] in ("value", "module"):
                continue
            item = resolve(original, path=path, root=root)
            item.update(
                name=symbols[(root, *path, original["name"])],
                owner=owner,
                native=".".join((*native_path, original["name"])),
            )
            if path and original["name"] == "t":
                item["methods"] = operations
                if item["kind"] == "alias" and operations:
                    item["kind"] = "namespace_alias"
            values.append(item)
    return values


def exception_imports(exceptions: tuple[str, ...]) -> str:
    return "".join(
        f"from ._bridge import {identifier(name)} as {identifier(name)}\n" for name in exceptions
    )


def render(
    modules: list[Node], *, package: str, exceptions: tuple[str, ...] = ()
) -> dict[str, str]:
    values = declarations(modules)
    return {
        "__init__.py": runtime_types(values, exceptions=exceptions),
        "__init__.pyi": domain_bindings(values, package=package) + exception_imports(exceptions),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schema", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--package", required=True, type=identifier)
    parser.add_argument("--exception", action="append", default=[], type=identifier)
    args = parser.parse_args()
    for name, content in render(
        json.loads(args.schema.read_text()), package=args.package, exceptions=tuple(args.exception)
    ).items():
        (args.destination / name).write_text(content)


if __name__ == "__main__":
    main()
