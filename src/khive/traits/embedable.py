# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

import orjson as json
from pydantic import BaseModel, Field, field_validator

from .types import Embedding


class Embedable(BaseModel):
    """Embedable trait, contains embedding and content"""

    content: str
    embedding: Embedding = Field(default_factory=list)

    @property
    def n_dim(self) -> int:
        """Get the number of dimensions of the embedding."""
        return len(self.embedding)

    @field_validator("embedding", mode="before")
    def _parse_embedding(cls, value: list[float] | str | None) -> Embedding | None:
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
