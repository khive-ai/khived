# Copyright (c) 2023 - 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from .endpoint import Endpoint


def match_endpoint(
    provider: str,
    endpoint: str,
) -> Endpoint:

    if provider == "openai":
        if "chat" in endpoint:
            from ..providers.oai_ import OpenaiChatEndpoint

            return OpenaiChatEndpoint()
        if "response" in endpoint:
            from ..providers.oai_ import OpenaiResponseEndpoint

            return OpenaiResponseEndpoint()
    if provider == "openrouter":
        if "chat" in endpoint:
            from ..providers.oai_ import OpenrouterChatEndpoint

            return OpenrouterChatEndpoint()
    if provider == "ollama":
        if "chat" in endpoint:
            from ..providers.oai_ import OllamaChatEndpoint

            return OllamaChatEndpoint()
    if provider == "exa":
        if "search" in endpoint:
            from ..providers.exa_ import ExaSearchEndpoint

            return ExaSearchEndpoint()
    if provider == "anthropic":
        if "messages" in endpoint:
            from ..providers.anthropic_ import AnthropicMessagesEndpoint

            return AnthropicMessagesEndpoint()
    if provider == "groq":
        if "chat" in endpoint:
            from ..providers.oai_ import GroqChatEndpoint

            return GroqChatEndpoint()
    if provider == "perplexity":
        if "chat" in endpoint:
            from ..providers.perplexity_ import PerplexityChatEndpoint

            return PerplexityChatEndpoint()

    return None
