"""Immutable datasets composed from native tasks and their public cases."""

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cached_property
from types import MappingProxyType
from typing import Annotated

from kernel import SourceFile, Task, source_hash
from pydantic import AfterValidator, BaseModel, Field, PlainSerializer

from evals.python import FROZEN
from evals.python.provenance import fingerprint

Attributes = Annotated[Mapping[str, str], AfterValidator(MappingProxyType), PlainSerializer(dict)]


class DatasetInfo(BaseModel):
    model_config = FROZEN
    source: str
    revision: str
    sha256: str
    count: int = Field(ge=0)
    attributes: Attributes


@dataclass(frozen=True, kw_only=True)
class Case:
    case_id: str
    skill: str
    prompt: str
    files: tuple[SourceFile, ...]


class Declaration(BaseModel):
    model_config = FROZEN
    skill: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    task: Task

    def project(self) -> Case:
        case = self.task.project()
        return Case(case_id=case.case_id, skill=self.skill, prompt=case.prompt, files=case.files)


@dataclass(frozen=True, kw_only=True)
class Dataset:
    records: Mapping[str, Declaration]
    info: DatasetInfo | None = None

    def __post_init__(self) -> None:
        records = MappingProxyType(dict(self.records))
        if self.info is not None and len(records) != self.info.count:
            raise ValueError("Dataset count mismatch")
        for name, record in records.items():
            if name != record.task.id:
                raise ValueError(f"Dataset record ID differs from its key: {name}")
        object.__setattr__(self, "records", records)

    @cached_property
    def cases(self) -> Mapping[str, Case]:
        return MappingProxyType({name: record.project() for name, record in self.records.items()})

    @cached_property
    def cases_hash(self) -> str:
        metadata = self.info.model_dump_json() if self.info else None
        return fingerprint((source_hash(), tuple(self.records.items()), metadata))
