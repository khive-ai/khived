# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Callable
from typing import ClassVar

import orjson as json
from pydantic import BaseModel, Field, field_validator
from typing_extensions import Self

from khive.config import settings
from khive.connections.api.endpoint import Endpoint

from .types import Embedding


class Embedable(BaseModel):
    """Embedable trait, contains embedding and content"""

    content: str
    embedding: Embedding = Field(default_factory=list)
    embed_endpoint: ClassVar[Endpoint] = None

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

    async def generate_embedding(self) -> Self:
        if self.__class__.embed_endpoint is None:
            endpoint, parse_func = get_default_embed_endpoint()

        response = await endpoint.call({"input": self.content})
        self.embedding = parse_func(response)
        return self


def get_default_embed_endpoint() -> tuple[Endpoint, Callable[..., list[float]]]:
    from khive.providers.oai_ import OpenaiEmbedEndpoint

    endpoint = None
    parse_func = None
    if settings.DEFAULT_EMBEDDING_PROVIDER == "openai":
        endpoint = OpenaiEmbedEndpoint(model=settings.DEFAULT_EMBEDDING_MODEL)

        def _parse(x):
            return x.data[0].embedding

        parse_func = _parse

    return endpoint, parse_func
