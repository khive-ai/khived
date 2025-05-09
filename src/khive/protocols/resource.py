import json
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from .identifiable import Identifiable


class ResourceType(str, Enum):
    """Resource types for tracking action execution progress."""

    DOCUMENT = "document"
    PROMPT = "prompt"
    MEMORY = "memory"


class ResourceMeta(BaseModel):
    title: str | None = None
    version: str = Field(default="0.1.0", frozen=True)
    description: str | None = None


class Resource(Identifiable):
    """Resource protocol, contains embedding and metadata."""

    type: str
    content: str
    embedding: list[float] = Field(default_factory=list)
    metadata: ResourceMeta = Field(default_factory=ResourceMeta)

    @property
    def n_dim(self) -> int:
        """Get the number of dimensions of the embedding."""
        return len(self.embedding)

    @field_validator("embedding", mode="before")
    def _parse_embedding(cls, value: list[float] | str | None) -> list[float] | None:
        if value is None:
            return None
        if isinstance(value, str):
            try:
                loaded = json.loads(value)
                return [float(x) for x in loaded]
            except Exception as e:
                raise ValueError("Invalid embedding string.") from e
        if isinstance(value, list):
            try:
                return [float(x) for x in value]
            except Exception as e:
                raise ValueError("Invalid embedding list.") from e
        raise ValueError("Invalid embedding type; must be list or JSON-encoded string.")


class Document(Resource):
    """Document resource protocol."""

    type: ResourceType = Field(default=ResourceType.DOCUMENT, frozen=True)


class Prompt(Resource):
    """Prompt resource protocol."""

    type: ResourceType = Field(default=ResourceType.PROMPT, frozen=True)


class Memory(Resource):
    """Memory resource protocol."""

    type: ResourceType = Field(default=ResourceType.MEMORY, frozen=True)
