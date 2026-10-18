"""Immutable datasets composed from native tasks, resources, and public cases."""

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cached_property
from types import MappingProxyType
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, PlainSerializer

from evals.python import FROZEN
from evals.python.provenance import fingerprint, value_fingerprint
from kernel import Case, Kernel, ResourceBinding, Task

Attributes = Annotated[Mapping[str, str], AfterValidator(MappingProxyType), PlainSerializer(dict)]


class DatasetInfo(BaseModel):
    model_config = FROZEN
    source: str
    revision: str
    sha256: str
    count: int = Field(ge=0)
    attributes: Attributes


@dataclass(frozen=True, kw_only=True)
class Dataset:
    records: Mapping[str, Task]
    resources: tuple[ResourceBinding, ...] = ()
    info: DatasetInfo | None = None

    def __post_init__(self) -> None:
        if self.info is not None and len(self.records) != self.info.count:
            raise ValueError("Dataset count mismatch")
        resources = tuple(self.resources)
        records = _resolve(self.records, resources=resources)
        object.__setattr__(self, "resources", resources)
        object.__setattr__(self, "records", MappingProxyType(records))

    @cached_property
    def cases(self) -> Mapping[str, Case]:
        return MappingProxyType(
            {name: Case.create(task=record) for name, record in self.records.items()}
        )

    @cached_property
    def source_hash(self) -> str:
        resources = tuple((resource.key, resource.contents) for resource in self.resources)
        return fingerprint(Kernel.current.sources, resources=resources)

    @cached_property
    def cases_hash(self) -> str:
        resources = tuple((resource.key, resource.contents) for resource in self.resources)
        records = tuple((name, value_fingerprint(task)) for name, task in self.records.items())
        metadata = self.info.model_dump_json() if self.info else "null"
        return fingerprint(
            Kernel.current.sources,
            resources=(*resources, *records, ("dataset-info", metadata)),
        )


def _resolve(
    records: Mapping[str, Task], *, resources: tuple[ResourceBinding, ...]
) -> dict[str, Task]:
    result = {}
    for name, record in records.items():
        if name != record.id:
            raise ValueError(f"Dataset record ID differs from its key: {name}")
        result[name] = Task.resolve_resources(task=record, resources=resources)
    return result
