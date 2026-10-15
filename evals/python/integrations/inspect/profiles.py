"""Build identical fixtures; add instructions only to the Genius profile."""

import base64
import hashlib
import json
from pathlib import Path

from inspect_ai.dataset import Sample

from evals.python.contracts import Case, Experiment, ProfileSpec
from evals.python.integrations.datasets.catalog import experiment, load_cases
from evals.python.paths import REPO_ROOT


def inline_file(contents: str) -> str:
    return "data:text/plain;base64," + base64.b64encode(contents.encode()).decode()


def content_hash(files: dict[str, str]) -> str:
    contents = {
        name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
        for name, path in sorted(files.items())
    }
    return hashlib.sha256(json.dumps(contents, sort_keys=True).encode()).hexdigest()


class Profile(ProfileSpec):
    """What a profile adds to every case: a prompt preamble and instruction folders."""

    def instruction_files(self) -> dict[str, str]:
        return {
            f"instructions/{folder}/{path.relative_to(REPO_ROOT / folder).as_posix()}": str(path)
            for folder in self.instructions
            for path in sorted((REPO_ROOT / folder).rglob("*"))
            if path.is_file()
        }

    def prompt(self, case: Case) -> str:
        return self.preamble.format(skill=case.skill) + case.prompt

    def files(self, case: Case) -> dict[str, str]:
        workspace = {
            f"workspace/{name}": inline_file(contents=text) for name, text in case.files.items()
        }
        return {
            "workspace/.gitkeep": inline_file(contents=""),
            **workspace,
            **self.instruction_files(),
        }

    def samples(self, *, dataset: str = "smoke") -> list[Sample]:
        return [
            Sample(
                id=case.id,
                input=self.prompt(case),
                files=self.files(case),
                metadata={"case_id": case.id, "profile": self.name, "dataset": dataset},
            )
            for case in load_cases(selection=dataset)
        ]


def load_profile(name: str, *, spec: Experiment | None = None) -> Profile:
    profile = {value.name: value for value in (spec or experiment()).profiles}[name]
    return Profile.model_validate(profile.model_dump())
