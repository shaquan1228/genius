"""Build identical fixtures; add instructions only to the Genius profile."""

import base64
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from inspect_ai.dataset import Sample

from evals.python.paths import REPO_ROOT
from evals.python.transport import Case, load_cases, workspace_files


@dataclass(frozen=True)
class Profile:
    """What a profile adds to every case: a prompt preamble and instruction folders."""

    name: str
    preamble: str = ""
    instructions: tuple[str, ...] = ()


BASELINE = Profile("baseline")
GENIUS = Profile(
    "genius",
    preamble=(
        "Read ../instructions/skills/{skill}/SKILL.md and its referenced files. "
        "Apply that skill to this task.\n\n"
    ),
    instructions=("docs", "skills"),
)


def directory_files(root: Path, destination: str) -> dict[str, str]:
    return {
        f"{destination}/{path.relative_to(root).as_posix()}": str(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def instruction_files(profile: Profile = GENIUS) -> dict[str, str]:
    return {
        name: path
        for folder in profile.instructions
        for name, path in directory_files(REPO_ROOT / folder, f"instructions/{folder}").items()
    }


def inline_file(contents: str) -> str:
    return "data:text/plain;base64," + base64.b64encode(contents.encode()).decode()


def files_for(case: Case, profile: Profile) -> dict[str, str]:
    workspace = {
        f"workspace/{name}": inline_file(text) for name, text in workspace_files(case).items()
    }
    return {"workspace/.gitkeep": inline_file(""), **workspace, **instruction_files(profile)}


def prompt_for(case: Case, profile: Profile) -> str:
    return profile.preamble.format(skill=case.skill) + case.prompt


def samples(profile: Profile) -> list[Sample]:
    return [
        Sample(
            id=case.id,
            input=prompt_for(case, profile),
            files=files_for(case, profile),
            metadata={"case_id": case.id, "profile": profile.name},
        )
        for case in load_cases()
    ]


def content_hash(files: dict[str, str]) -> str:
    contents = {
        name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
        for name, path in sorted(files.items())
    }
    return hashlib.sha256(json.dumps(contents, sort_keys=True).encode()).hexdigest()
