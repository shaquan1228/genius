"""Build identical fixtures; add instructions only to the Genius profile."""

import hashlib
import json
from pathlib import Path

from inspect_ai.dataset import Sample

from genius_evals.cases import EVALS_ROOT, REPO_ROOT, Case, Profile, load_cases


def directory_files(root: Path, destination: str) -> dict[str, str]:
    return {
        f"{destination}/{path.relative_to(root).as_posix()}": str(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def instruction_files() -> dict[str, str]:
    return {
        **directory_files(REPO_ROOT / "docs", "instructions/docs"),
        **directory_files(REPO_ROOT / "skills", "instructions/skills"),
    }


def files_for(case: Case, profile: Profile) -> dict[str, str]:
    files = directory_files(EVALS_ROOT / "fixtures" / case.fixture, "workspace")
    if profile == "genius":
        files.update(instruction_files())
    return files


def prompt_for(case: Case, profile: Profile) -> str:
    if profile == "baseline":
        return case.prompt
    return (
        f"Read ../instructions/skills/{case.skill}/SKILL.md and its referenced files. "
        f"Apply that skill to this task.\n\n{case.prompt}"
    )


def samples(profile: Profile) -> list[Sample]:
    return [
        Sample(
            id=case.id,
            input=prompt_for(case, profile),
            files=files_for(case, profile),
            metadata={"case": case.model_dump(), "profile": profile},
        )
        for case in load_cases()
    ]


def content_hash(files: dict[str, str]) -> str:
    contents = {
        name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
        for name, path in sorted(files.items())
    }
    return hashlib.sha256(json.dumps(contents, sort_keys=True).encode()).hexdigest()
