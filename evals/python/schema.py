"""Python-owned dataset metadata and public API validation configuration."""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, PlainSerializer

FROZEN = ConfigDict(strict=True, extra="forbid", frozen=True, arbitrary_types_allowed=True)
FileName = Annotated[str, Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_.-]*$")]
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
