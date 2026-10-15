"""Build identical fixtures; add instructions only to the Genius profile."""

import base64
import hashlib
import json
from pathlib import Path

from inspect_ai.dataset import Sample

from evals.cases import EVALS_ROOT, REPO_ROOT, Case, Profile, load_cases


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


def inline_file(contents: str) -> str:
    return "data:text/plain;base64," + base64.b64encode(contents.encode()).decode()


def files_for(case: Case, profile: Profile) -> dict[str, str]:
    files = {"workspace/.gitkeep": inline_file("")}
    files.update({f"workspace/{name}": inline_file(text) for name, text in case.files.items()})
    if case.grading == "ocaml":
        files["workspace/check.sh"] = str(EVALS_ROOT / "check.sh")
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
            metadata={"case_id": case.id, "profile": profile},
        )
        for case in load_cases()
    ]


def content_hash(files: dict[str, str]) -> str:
    contents = {
        name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
        for name, path in sorted(files.items())
    }
    return hashlib.sha256(json.dumps(contents, sort_keys=True).encode()).hexdigest()
