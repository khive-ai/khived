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
            from .providers.oai_ import OpenaiChatEndpoint

            return OpenaiChatEndpoint()
        if "response" in endpoint:
            from .providers.oai_ import OpenaiResponseEndpoint

            return OpenaiResponseEndpoint()
    if provider == "openrouter" and "chat" in endpoint:
        from .providers.oai_ import OpenrouterChatEndpoint

        return OpenrouterChatEndpoint()
    if provider == "ollama" and "chat" in endpoint:
        from .providers.ollama_ import OllamaChatEndpoint

        return OllamaChatEndpoint()
    if provider == "exa" and "search" in endpoint:
        from .providers.exa_ import ExaSearchEndpoint

        return ExaSearchEndpoint()
    if provider == "anthropic" and ("messages" in endpoint or "chat" in endpoint):
        from .providers.anthropic_ import AnthropicMessagesEndpoint

        return AnthropicMessagesEndpoint()
    if provider == "groq" and "chat" in endpoint:
        from .providers.oai_ import GroqChatEndpoint

        return GroqChatEndpoint()
    if provider == "perplexity" and "chat" in endpoint:
        from .providers.perplexity_ import PerplexityChatEndpoint

        return PerplexityChatEndpoint()

    return None
