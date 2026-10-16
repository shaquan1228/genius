"""Build content-addressed plugins from the existing OCaml types and signatures."""

import hashlib
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

MODULES = (
    "ast",
    "experiment",
    "response",
    "fixture",
    "verifier",
    "criterion",
    "case",
    "reference",
    "grader",
    "projection",
)
ROOT = Path(__file__).resolve().parent.parent / "ocaml"
LIBRARY = tuple(
    ROOT / f"{name}.{extension}"
    for name in MODULES
    for extension in ("mli", "ml")
    if (ROOT / f"{name}.{extension}").exists()
)


def sources() -> tuple[tuple[str, str], ...]:
    return tuple((path.name, path.read_text()) for path in LIBRARY)


def _interface(modules: dict[str, str]) -> str:
    ast = modules["ast.ml"]
    fixture_type = "type fixture = string Map.Make(String).t"
    if ast.count(fixture_type) != 1:
        raise ValueError("Update the bridge's opaque fixture export for the current AST")
    interface = ast.replace(fixture_type, "type fixture")
    return (
        interface
        + "\n"
        + "\n".join(
            f"module {name.capitalize()} : sig\n"
            + modules[f"{name}.mli"].replace("Ast.", "")
            + "\nend"
            for name in MODULES[1:]
        )
    )


def _compile(modules: tuple[tuple[str, str], ...], *, destination: Path, name: str) -> None:
    packed = f"Kernel_{name}"
    exported = f"Kernel_api_{name}"
    for filename, contents in modules:
        (destination / filename).write_text(contents)
    body = f"include {packed}.Ast\n" + "\n".join(
        f"module {part.capitalize()} = {packed}.{part.capitalize()}" for part in MODULES[1:]
    )
    (destination / f"{exported.lower()}.ml").write_text(
        f"include (struct\n{body}\nend : sig\n{_interface(dict(modules))}\nend)\n"
    )
    commands = (
        ["-for-pack", packed, "-c", *(filename for filename, _ in modules)],
        ["-pack", "-o", f"{packed.lower()}.cmx", *(f"{part}.cmx" for part in MODULES)],
        ["-c", f"{exported.lower()}.ml"],
        ["-shared", "-o", "kernel.cmxs", f"{packed.lower()}.cmx", f"{exported.lower()}.cmx"],
    )
    for arguments in commands:
        subprocess.run(["ocamlopt", *arguments], cwd=destination, check=True)


def build(modules: tuple[tuple[str, str], ...]) -> tuple[Path, str]:
    # The generator participates in the key so changing exports cannot reuse stale code.
    material = repr(modules) + Path(__file__).read_text()
    name = hashlib.sha256(material.encode()).hexdigest()[:24]
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "genius-evals/kernel"
    destination = cache / name
    if not (destination / "kernel.cmxs").is_file():
        cache.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=cache) as temporary:
            stage = Path(temporary) / "plugin"
            stage.mkdir()
            _compile(modules, destination=stage, name=name)
            try:
                stage.rename(destination)
            except OSError:
                # Another process may have published the same immutable build first.
                if not (destination / "kernel.cmxs").is_file():
                    raise
    return destination, f"Kernel_api_{name}"
