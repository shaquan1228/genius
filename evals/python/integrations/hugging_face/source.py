"""Export trusted execution code and untrusted instruction data separately."""

import io
import subprocess
import tarfile
from pathlib import Path

from evals.python.evaluation import VariantSettings


def git(*arguments: str, repository: Path) -> bytes:
    return subprocess.check_output(["git", "-C", str(repository), *arguments])


def resolve(ref: str | None, *, repository: Path) -> str:
    ref = ref or "HEAD"
    if ref.startswith("-"):
        raise ValueError("Invalid source reference")
    return git("rev-parse", "--verify", f"{ref}^{{commit}}", repository=repository).decode().strip()


def trusted_snapshot(destination: Path, *, repository: Path) -> str:
    revision = resolve("HEAD", repository=repository)
    archive = git(
        "archive", revision, "README.md", "docs", "skills", "evals", repository=repository
    )
    with tarfile.open(fileobj=io.BytesIO(archive)) as content:
        content.extractall(destination, filter="data")
    return revision


def instructions(
    variant: VariantSettings, *, destination: Path, repository: Path
) -> VariantSettings:
    if variant.source_dir is not None:
        raise ValueError("Hosted variants must use source_ref, never a local source_dir")
    revision = resolve(variant.source_ref, repository=repository)
    destination.mkdir(parents=True, exist_ok=True)
    for selected in variant.instructions:
        entries = git("ls-tree", "-r", "-z", revision, "--", selected, repository=repository)
        if not entries:
            raise ValueError(f"Instruction path not found: {selected}")
        for entry in entries.rstrip(b"\0").split(b"\0"):
            export_blob(entry, destination=destination, repository=repository)
    return variant.model_copy(update={"source_ref": revision})


def export_blob(entry: bytes, *, destination: Path, repository: Path) -> None:
    metadata, raw_name = entry.split(b"\t", 1)
    mode, kind, oid = metadata.decode().split()
    name = raw_name.decode()
    path = Path(name)
    if mode not in {"100644", "100755"} or kind != "blob":
        raise ValueError(f"Only regular instruction data is allowed: {name}")
    target = destination / path
    if not target.resolve().is_relative_to(destination.resolve()):
        raise ValueError("Instruction path escapes snapshot")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(git("cat-file", "blob", oid, repository=repository))
