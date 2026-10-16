"""Build identical fixtures; add instructions only to the Genius profile."""

import base64
import hashlib
import json
from pathlib import Path, PurePosixPath

from inspect_ai.dataset import Sample

from evals.python import commands
from evals.python.paths import REPO_ROOT

# A diagnostic treatment of reasoning's four required reads, without rewriting them.
REASONING_DOCUMENTS = (
    "skills/reasoning/SKILL.md",
    "docs/identity.md",
    "skills/reasoning/references/trigger-map.md",
    "skills/reasoning/references/worked-example.md",
)


def instruction_envelope(*, delivery: commands.InstructionDelivery, root: str) -> str:
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
            f"<document path={json.dumps(path)}>\n{(REPO_ROOT / name).read_text()}</document>"
            for name, path in zip(REASONING_DOCUMENTS, paths, strict=True)
        )
        + "\n\n"
    )


def inline_file(contents: str) -> str:
    return "data:text/plain;base64," + base64.b64encode(contents.encode()).decode()


def content_hash(files: dict[str, str]) -> str:
    contents = {
        name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
        for name, path in sorted(files.items())
    }
    return hashlib.sha256(json.dumps(contents, sort_keys=True).encode()).hexdigest()


def instruction_files(profile: commands.ProfileSpec) -> dict[str, str]:
    return {
        f"instructions/{folder}/{path.relative_to(REPO_ROOT / folder).as_posix()}": str(path)
        for folder in profile.instructions
        for path in sorted((REPO_ROOT / folder).rglob("*"))
        if path.is_file()
    }


def prompt(
    profile: commands.ProfileSpec,
    *,
    case: commands.Case,
    delivery: commands.InstructionDelivery = "files",
    instruction_root: str = "../instructions",
) -> str:
    preamble = profile.preamble.format(skill=case.skill)
    if not profile.instructions or delivery == "files":
        return preamble + case.prompt
    if case.skill != "reasoning":
        raise ValueError("Instruction delivery diagnostics currently support reasoning only")
    envelope = instruction_envelope(delivery=delivery, root=instruction_root)
    return (preamble + envelope if delivery == "manifest" else envelope) + case.prompt


def files(profile: commands.ProfileSpec, *, case: commands.Case) -> dict[str, str]:
    workspace = {
        f"workspace/{name}": inline_file(contents=text) for name, text in case.files.items()
    }
    return {
        "workspace/.gitkeep": inline_file(contents=""),
        **workspace,
        **instruction_files(profile),
    }


def samples(
    profile: commands.ProfileSpec,
    *,
    cases: tuple[commands.Case, ...],
    dataset: str = "smoke",
    delivery: commands.InstructionDelivery = "files",
    instruction_root: str = "../instructions",
) -> list[Sample]:
    return [
        Sample(
            id=case.id,
            input=prompt(profile, case=case, delivery=delivery, instruction_root=instruction_root),
            files=files(profile, case=case),
            metadata={"case_id": case.id, "profile": profile.name, "dataset": dataset},
        )
        for case in cases
    ]


def load_profile(name: str, *, spec: commands.Experiment | None = None) -> commands.ProfileSpec:
    return {
        value.name: value
        for value in (spec or commands.query(commands.ExperimentSettings())).profiles
    }[name]
