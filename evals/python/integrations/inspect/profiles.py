"""Build identical fixtures; add instructions only to the Genius profile."""

import base64
import hashlib
import json
from collections.abc import Mapping
from itertools import chain
from pathlib import PurePosixPath
from types import MappingProxyType

from inspect_ai.dataset import Sample

from evals.python import evaluation_settings
from evals.python.paths import REPO_ROOT
from kernel import Case, Content, Experiment, Profile

# A diagnostic treatment of reasoning's four required reads, without rewriting them.
REASONING_DOCUMENTS = (
    "skills/reasoning/SKILL.md",
    "docs/identity.md",
    "skills/reasoning/references/trigger-map.md",
    "skills/reasoning/references/worked-example.md",
)


def load_instructions(spec: Experiment) -> Mapping[str, bytes]:
    return MappingProxyType(
        {
            f"instructions/{path.relative_to(REPO_ROOT).as_posix()}": path.read_bytes()
            for folder in sorted(set(chain.from_iterable(p.instructions for p in spec.profiles)))
            for path in sorted((REPO_ROOT / folder).rglob("*"))
            if path.is_file()
        }
    )


def instruction_envelope(
    *,
    delivery: evaluation_settings.InstructionDelivery,
    root: str,
    instructions: Mapping[str, bytes],
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
            f"{instructions[f'instructions/{name}'].decode()}</document>"
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


def instruction_files(profile: Profile, *, instructions: Mapping[str, bytes]) -> dict[str, bytes]:
    prefixes = tuple(f"instructions/{folder}/" for folder in profile.instructions)
    return {name: contents for name, contents in instructions.items() if name.startswith(prefixes)}


def prompt(
    profile: Profile,
    *,
    case: Case,
    instructions: Mapping[str, bytes],
    delivery: evaluation_settings.InstructionDelivery = "files",
    instruction_root: str = "../instructions",
) -> str:
    preamble = profile.preamble.format(skill=case.skill)
    if not profile.instructions or delivery == "files":
        return preamble + case.prompt
    if case.skill != "reasoning":
        raise ValueError("Instruction delivery diagnostics currently support reasoning only")
    envelope = instruction_envelope(
        delivery=delivery, root=instruction_root, instructions=instructions
    )
    return (preamble + envelope if delivery == "manifest" else envelope) + case.prompt


def files(
    profile: Profile,
    *,
    case: Case,
    instructions: Mapping[str, bytes],
) -> dict[str, str]:
    workspace = {}
    for name, content in case.files:
        if not isinstance(content, Content.Inline):
            raise ValueError(f"Unresolved resource in public case {case.id}: {name}")
        workspace[f"workspace/{name}"] = inline_file(contents=content[0].encode())
    return {
        "workspace/.gitkeep": inline_file(contents=b""),
        **workspace,
        **{
            name: inline_file(contents=contents)
            for name, contents in instruction_files(profile, instructions=instructions).items()
        },
    }


def samples(  # noqa: PLR0913 - explicit sample inputs and native delivery options
    profile: Profile,
    *,
    cases: tuple[Case, ...],
    instructions: Mapping[str, bytes],
    dataset: str = "smoke",
    delivery: evaluation_settings.InstructionDelivery = "files",
    instruction_root: str = "../instructions",
) -> list[Sample]:
    return [
        Sample(
            id=case.id,
            input=prompt(
                profile,
                case=case,
                instructions=instructions,
                delivery=delivery,
                instruction_root=instruction_root,
            ),
            files=files(profile, case=case, instructions=instructions),
            metadata={"case_id": case.id, "profile": profile.name, "dataset": dataset},
        )
        for case in cases
    ]


def load_profile(name: str, *, spec: Experiment) -> Profile:
    return {value.name: value for value in spec.profiles}[name]
