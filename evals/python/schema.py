"""Python-owned dataset metadata and public API validation configuration."""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, PlainSerializer

from kernel import File

FROZEN = ConfigDict(strict=True, extra="forbid", frozen=True, arbitrary_types_allowed=True)


def _file_name(value: str) -> str:
    if not File.valid_path(path=value):
        raise ValueError("Invalid file name")
    return value


FileName = Annotated[str, AfterValidator(_file_name)]
Files = Annotated[Mapping[FileName, str], AfterValidator(MappingProxyType), PlainSerializer(dict)]
Attributes = Annotated[Mapping[str, str], AfterValidator(MappingProxyType), PlainSerializer(dict)]


class DatasetInfo(BaseModel):
    model_config = FROZEN
    source: str
    revision: str
    sha256: str
    count: int = Field(ge=0)
    attributes: Attributes

    def __hash__(self) -> int:
        return hash(
            (
                self.source,
                self.revision,
                self.sha256,
                self.count,
                tuple(sorted(self.attributes.items())),
            )
        )
