"""Build identical fixtures; add instructions only to the Genius profile."""

import base64
import hashlib
import json
from collections.abc import Mapping
from itertools import chain
from pathlib import Path, PurePosixPath
from types import MappingProxyType

from inspect_ai.dataset import Sample

from evals.python import REPO_ROOT
from evals.python.evaluation import InstructionDelivery
from kernel import Case, Experiment, Profile

REASONING_DOCUMENTS = (
    "skills/reasoning/SKILL.md",
    "docs/identity.md",
    "skills/reasoning/references/trigger-map.md",
    "skills/reasoning/references/worked-example.md",
)


def load_documents(spec: Experiment, *, source_dir: str | None = None) -> Mapping[str, bytes]:
    root = Path(source_dir).resolve() if source_dir is not None else REPO_ROOT
    return MappingProxyType(
        {
            f"instructions/{path.relative_to(root).as_posix()}": path.read_bytes()
            for folder in sorted(set(chain.from_iterable(p.instructions for p in spec.profiles)))
            for path in instruction_files(root, folder=folder)
        }
    )


def instruction_files(root: Path, *, folder: str) -> list[Path]:
    selected = root / folder
    safe_instruction(selected, root=root)
    paths = [selected] if selected.is_file() else sorted(selected.rglob("*"))
    for path in paths:
        safe_instruction(path, root=root)
    return [path for path in paths if path.is_file()]


def safe_instruction(path: Path, *, root: Path) -> None:
    if not path.exists():
        raise ValueError(f"Missing instruction source: {path.name}")
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise ValueError("Instruction sources must not contain links or escape their root")


def document_envelope(
    *,
    delivery: InstructionDelivery,
    root: str,
    documents: Mapping[str, bytes],
) -> str:
    paths = [str(PurePosixPath(root) / name) for name in REASONING_DOCUMENTS]
    if delivery == "manifest":
        return (
            "Instruction paths (resolve relative references from their containing file):\n"
            + "\n".join(paths)
            + "\n\n"
        )
    return (
        "Apply the reasoning skill below. These are the complete, unchanged required documents; "
        "they are already loaded. Resolve other references from their containing file.\n\n"
        + "\n\n".join(
            f"<document path={json.dumps(path)}>\n"
            f"{documents[f'instructions/{name}'].decode()}</document>"
            for name, path in zip(REASONING_DOCUMENTS, paths, strict=True)
        )
        + "\n\n"
    )


def inline_file(contents: bytes) -> str:
    return "data:text/plain;base64," + base64.b64encode(contents).decode()


def content_hash(files: Mapping[str, bytes]) -> str:
    contents = {
        name: hashlib.sha256(contents).hexdigest() for name, contents in sorted(files.items())
    }
    return hashlib.sha256(json.dumps(contents, sort_keys=True).encode()).hexdigest()


def document_files(profile: Profile, *, documents: Mapping[str, bytes]) -> dict[str, bytes]:
    selected = tuple(f"instructions/{folder}" for folder in profile.instructions)
    prefixes = tuple(f"{name}/" for name in selected)
    return {
        name: contents
        for name, contents in documents.items()
        if document_selected(name, selected=selected, prefixes=prefixes)
    }


def document_selected(name: str, *, selected: tuple[str, ...], prefixes: tuple[str, ...]) -> bool:
    return name in selected or name.startswith(prefixes)


def prompt(
    profile: Profile,
    *,
    case: Case,
    documents: Mapping[str, bytes],
    delivery: InstructionDelivery = "files",
    instruction_root: str = "../instructions",
) -> str:
    preamble = profile.preamble.format(skill=case.skill)
    if not profile.instructions or delivery == "files":
        return preamble + case.prompt
    if case.skill != "reasoning":
        raise ValueError("Instruction delivery diagnostics currently support reasoning only")
    envelope = document_envelope(delivery=delivery, root=instruction_root, documents=documents)
    return (preamble + envelope if delivery == "manifest" else envelope) + case.prompt


def workspace_files(case: Case) -> dict[str, str]:
    workspace = {"workspace/.gitkeep": inline_file(contents=b"")}
    for artifact in case.files:
        workspace[f"workspace/{artifact.path}"] = inline_file(contents=artifact.contents.encode())
    return workspace


def samples(  # noqa: PLR0913 - explicit sample inputs and native delivery options
    profile: Profile,
    *,
    cases: tuple[Case, ...],
    documents: Mapping[str, bytes],
    dataset: str = "smoke",
    delivery: InstructionDelivery = "files",
    instruction_root: str = "../instructions",
    sandbox_image: str | None = None,
) -> list[Sample]:
    instructions = {
        name: inline_file(contents=contents)
        for name, contents in document_files(profile, documents=documents).items()
    }
    return [
        Sample(
            id=case.case_id,
            input=prompt(
                profile,
                case=case,
                documents=documents,
                delivery=delivery,
                instruction_root=instruction_root,
            ),
            files={**workspace_files(case), **instructions},
            metadata={
                "case_id": case.case_id,
                "profile": profile.name,
                "dataset": dataset,
                **({"sandbox_image": sandbox_image} if sandbox_image is not None else {}),
            },
        )
        for case in cases
    ]


def load_profile(name: str, *, spec: Experiment) -> Profile:
    return {value.name: value for value in spec.profiles}[name]
