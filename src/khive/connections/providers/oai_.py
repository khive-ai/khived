# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from khive.config import settings
from khive.connections.endpoint import Endpoint, EndpointConfig

__all__ = (
    "OpenaiChatEndpoint",
    "OpenaiResponseEndpoint",
    "OpenrouterChatEndpoint",
)


OPENAI_CHAT_ENDPOINT_CONFIG = EndpointConfig(
    name="openai_chat",
    provider="openai",
    base_url=None,
    endpoint="chat/completions",
    kwargs={"model": "gpt-4o"},
    openai_compatible=True,
    api_key=settings.OPENAI_API_KEY,
    auth_type="bearer",
    content_type="application/json",
    transport_type="sdk",
)

OPENAI_RESPONSE_ENDPOINT_CONFIG = EndpointConfig(
    name="openai_response",
    provider="openai",
    base_url=None,
    endpoint="response",
    kwargs={"model": "gpt-4o"},
    openai_compatible=True,
    api_key=settings.OPENAI_API_KEY,
    auth_type="bearer",
    content_type="application/json",
    transport_type="sdk",
)

OPENROUTER_CHAT_ENDPOINT_CONFIG = EndpointConfig(
    name="openrouter_chat",
    provider="openrouter",
    base_url="https://openrouter.ai/api/v1",
    endpoint="chat/completions",
    kwargs={"model": "gpt-4o"},
    openai_compatible=True,
    api_key=settings.OPENROUTER_API_KEY,
    auth_type="bearer",
    content_type="application/json",
    transport_type="sdk",
)

OPENAI_EMBEDDING_ENDPOINT_CONFIG = EndpointConfig(
    name="openai_embed",
    provider="openai",
    base_url=None,
    endpoint="embeddings",
    kwargs={"model": "text-embedding-3-small"},
    openai_compatible=True,
    api_key=settings.OPENAI_API_KEY,
    auth_type="bearer",
    content_type="application/json",
    transport_type="sdk",
)

GROQ_CHAT_ENDPOINT_CONFIG = EndpointConfig(
    name="groq_chat",
    provider="groq",
    base_url="https://api.groq.com/v1",
    endpoint="chat/completions",
    openai_compatible=True,
    api_key=settings.GROQ_API_KEY,
    auth_type="bearer",
    content_type="application/json",
    transport_type="sdk",
)


class OpenaiChatEndpoint(Endpoint):
    def __init__(self, config=OPENAI_CHAT_ENDPOINT_CONFIG, **kwargs):
        super().__init__(config, **kwargs)


class OpenaiResponseEndpoint(Endpoint):
    def __init__(self, config=OPENAI_RESPONSE_ENDPOINT_CONFIG, **kwargs):
        super().__init__(config, **kwargs)


class OpenrouterChatEndpoint(Endpoint):
    def __init__(self, config=OPENROUTER_CHAT_ENDPOINT_CONFIG, **kwargs):
        super().__init__(config, **kwargs)


class GroqChatEndpoint(Endpoint):
    def __init__(self, config=GROQ_CHAT_ENDPOINT_CONFIG, **kwargs):
        super().__init__(config, **kwargs)


class OpenaiEmbedEndpoint(Endpoint):
    def __init__(self, config=OPENAI_EMBEDDING_ENDPOINT_CONFIG, **kwargs):
        super().__init__(config, **kwargs)
