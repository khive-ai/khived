# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel

from khive.config import settings
from khive.connections.endpoint import Endpoint, EndpointConfig

ANTHROPIC_MESSAGES_ENDPOINT_CONFIG = EndpointConfig(
    provider="anthropic",
    base_url="https://api.anthropic.com/v1",
    endpoint="messages",
    method="POST",
    openai_compatible=False,
    auth_type="x-api-key",
    default_headers={"api_version": "2023-06-01"},
    transport_type="http",
    api_key=settings.ANTHROPIC_API_KEY,
)


class AnthropicMessagesEndpoint(Endpoint):
    def __init__(
        self, config: EndpointConfig = ANTHROPIC_MESSAGES_ENDPOINT_CONFIG, **kwargs
    ):
        super().__init__(config, **kwargs)

    def create_payload(
        self,
        request: dict | BaseModel,
        extra_headers: dict | None = None,
        **kwargs,
    ):
        payload, headers = super().create_payload(
            request, extra_headers=extra_headers, **kwargs
        )

        if "cache_control" in payload:
            cache_control = payload.pop("cache_control")
            if cache_control:
                cache_control = {"type": "ephemeral"}
                last_message = payload["messages"][-1]["content"]
                if isinstance(last_message, str):
                    last_message = {
                        "type": "text",
                        "text": last_message,
                        "cache_control": cache_control,
                    }
                elif isinstance(last_message, list) and isinstance(
                    last_message[-1], dict
                ):
                    last_message[-1]["cache_control"] = cache_control
                payload["messages"][-1]["content"] = (
                    [last_message]
                    if not isinstance(last_message, list)
                    else last_message
                )

        first_message = payload["messages"][0]
        system = None
        if first_message.get("role") == "system":
            system = first_message["content"]
            system = [{"type": "text", "text": system}]
            payload["messages"] = payload["messages"][1:]
            payload["system"] = system

        return (payload, headers)
