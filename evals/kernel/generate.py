"""Generate Python typing declarations from the kernel's OCaml type subset."""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

HEADER = "# Generated from ocaml/ast.ml and public .mli files; do not edit.\n"
PREAMBLE = "from collections.abc import Sequence\n\n"
PRIMITIVES = {"string": "str", "bool": "bool", "int": "int", "float": "float", "unit": "None"}


def clean(source: str) -> str:
    return re.sub(r"\(\*.*?\*\)", "", source, flags=re.S).strip()


def split(source: str, *, delimiter: str) -> list[str]:
    parts = []
    depth = 0
    start = 0
    for index, character in enumerate(source):
        depth += (character == "(") - (character == ")")
        if depth == 0 and source.startswith(delimiter, index):
            parts.append(source[start:index].strip())
            start = index + len(delimiter)
    parts.append(source[start:].strip())
    return parts


def type_name(source: str, *, qualify: bool = False) -> str:
    source = source.strip()
    if source.endswith(" list"):
        return f"Sequence[{type_name(source[:-5], qualify=qualify)}]"
    if source.endswith(" option"):
        return f"{type_name(source[:-7], qualify=qualify)} | None"
    if source.startswith("(") and source.endswith(")"):
        return type_name(source[1:-1], qualify=qualify)
    parts = split(source, delimiter="*")
    if len(parts) > 1:
        return "tuple[" + ", ".join(type_name(item, qualify=qualify) for item in parts) + "]"
    if source in PRIMITIVES:
        return PRIMITIVES[source]
    if not re.fullmatch(r"(?:Ast\.)?[a-z_]+", source):
        raise ValueError(f"Unsupported OCaml type: {source}")
    name = source.removeprefix("Ast.")
    return "Ast." + name if qualify else name


def record(name: str, *, body: str) -> str:
    fields = []
    for item in body.strip("{} \n").split(";"):
        if item.strip():
            field, annotation = item.strip().split(":", 1)
            fields.append((field.strip(), type_name(annotation)))
    constructor = ", ".join(f"{field}: {annotation}" for field, annotation in fields)
    result = f"class {name}:\n    def __init__(self, *, {constructor}) -> None: ...\n"
    for field, annotation in fields:
        result += f"    @property\n    def {field}(self) -> {annotation}: ...\n"
    return result


def ast_bindings(source: str) -> tuple[str, list[str]]:
    result = HEADER + PREAMBLE
    constructors = ["fixture"]
    declarations = re.split(r"\btype\s+([a-z_]+)\s*=", clean(source))
    if declarations[0].strip():
        raise ValueError("AST contains declarations other than types")
    for name, raw_body in zip(declarations[1::2], declarations[2::2], strict=True):
        body = raw_body.strip().lstrip("| \n")
        if name == "fixture":
            result += "class fixture: ...\n\n"
        elif body.startswith("{"):
            result += record(name, body=body) + "\n"
            constructors.append(name)
        elif re.match(r"[A-Z]", body):
            variants = []
            for item in body.split("|"):
                variant, *payload = item.strip().split(" of ", 1)
                variants.append(variant)
                constructors.append(variant)
                result += f"class {variant}:\n"
                if payload:
                    annotation = type_name(payload[0])
                    result += f"    def __init__(self, value: {annotation}, /) -> None: ...\n"
                    result += f"    def __getitem__(self, index: int, /) -> {annotation}: ...\n"
                else:
                    result += "    def __init__(self) -> None: ...\n"
            result += f"type {name} = {' | '.join(variants)}\n\n"
        else:
            result += f"type {name} = {type_name(body)}\n\n"
    return result, constructors


def signatures(source: str, *, method: bool = False) -> str:
    result = ""
    for match in re.finditer(r"\bval\s+(\w+)\s*:\s*(.*?)(?=\bval\s|\Z)", clean(source), re.S):
        name, annotation = match.groups()
        arguments = split(annotation, delimiter="->")
        if len(arguments) == 1:
            result += f"{name}: {type_name(annotation, qualify=True)}\n"
            continue
        positional = ["self"] if method else []
        keywords = []
        for argument in arguments[:-1]:
            if argument == "unit":
                continue
            label = re.fullmatch(r"(\??)(\w+)\s*:(.+)", argument, re.S)
            if label:
                optional, field, field_type = label.groups()
                keywords.append(
                    f"{field}: {type_name(field_type, qualify=True)}"
                    + (" = ..." if optional else "")
                )
            else:
                positional.append(f"value: {type_name(argument, qualify=True)}")
        if positional:
            positional.append("/")
        parameters = positional + (["*", *keywords] if keywords else [])
        result_type = type_name(arguments[-1], qualify=True)
        result += f"def {name}({', '.join(parameters)}) -> {result_type}: ...\n"
    return result


def generate(source: Path) -> dict[str, str]:
    ast, constructors = ast_bindings((source / "ast.ml").read_text())
    outputs = {"Ast.pyi": ast}
    namespace = HEADER + PREAMBLE + "from . import Ast\n\n"
    exports = ["Ast"]
    for path in sorted(source.glob("*.mli")):
        name = path.stem.capitalize()
        exports.append(name)
        options = ""
        for match in re.finditer(
            r"\bval\s+(\w+)\s*:\s*(.*?)(?=\bval\s|\Z)", clean(path.read_text()), re.S
        ):
            function, annotation = match.groups()
            arguments = split(annotation, delimiter="->")[:-1]
            if not any(argument.startswith("?") for argument in arguments):
                continue
            options += f"class {function.capitalize()}Args(TypedDict, total=False):\n"
            for argument in arguments:
                if argument == "unit":
                    continue
                label = re.fullmatch(r"(\??)(\w+)\s*:(.+)", argument, re.S)
                if label is None:
                    raise ValueError("Optional operation arguments must be labeled")
                optional, field, field_type = label.groups()
                annotation = type_name(field_type, qualify=True)
                if not optional:
                    annotation = f"Required[{annotation}]"
                options += f"    {field}: {annotation}\n"
            options += "\n"
        outputs[name + ".pyi"] = (
            HEADER
            + PREAMBLE
            + "from typing import Required, TypedDict\nfrom . import Ast\n\n"
            + options
            + signatures(path.read_text())
        )
        namespace += (
            f"class {name}Module:\n"
            + "\n".join(
                "    " + line for line in signatures(path.read_text(), method=True).splitlines()
            )
            + "\n\n"
        )
    namespace += "class Namespace:\n"
    namespace += "".join(f"    {name}: type[Ast.{name}]\n" for name in constructors)
    namespace += "".join(f"    {name}: {name}Module\n" for name in exports[1:])
    outputs["_types.pyi"] = namespace
    outputs["__init__.pyi"] = (
        HEADER
        + "\n"
        + "\n".join(f"from . import {name} as {name}" for name in exports)
        + "\nfrom ._types import Namespace as Namespace\n\n"
        + "class InvalidArgument(Exception): ...\n\n"
        + "def load(modules: tuple[tuple[str, str], ...]) -> Namespace: ...\n"
    )
    return outputs


def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    with TemporaryDirectory(prefix="genius-kernel-types-") as temporary:
        destination = Path(temporary)
        for filename, contents in generate(root.parent / "ocaml").items():
            (destination / filename).write_text(contents)
        subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--select", "I", "--fix", str(destination)],
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
                str(destination),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        for source in destination.glob("*.pyi"):
            target = root / source.name
            content = source.read_text()
            if options.check:
                if not target.exists() or target.read_text() != content:
                    raise SystemExit("Kernel types changed; run python kernel/generate.py")
            else:
                target.write_text(content)


if __name__ == "__main__":
    main()
