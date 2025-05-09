from khive.connections.endpoint import Endpoint, EndpointConfig
from khive.third_party.openai_models import CreateChatCompletionRequest, CreateResponse

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
    api_key="OPENAI_API_KEY",
    auth_type="bearer",
    content_type="application/json",
    transport_type="sdk",
    request_options=CreateChatCompletionRequest,
)

OPENAI_RESPONSE_ENDPOINT_CONFIG = EndpointConfig(
    name="openai_response",
    provider="openai",
    base_url=None,
    endpoint="response",
    kwargs={"model": "gpt-4o"},
    openai_compatible=True,
    api_key="OPENAI_API_KEY",
    auth_type="bearer",
    content_type="application/json",
    transport_type="sdk",
    request_options=CreateResponse,
)

OPENROUTER_CHAT_ENDPOINT_CONFIG = EndpointConfig(
    name="openrouter_chat",
    provider="openrouter",
    base_url="https://openrouter.ai/api/v1",
    endpoint="chat/completions",
    kwargs={"model": "gpt-4o"},
    openai_compatible=True,
    api_key="OPENROUTER_API_KEY",
    auth_type="bearer",
    content_type="application/json",
    transport_type="sdk",
    request_options=CreateChatCompletionRequest,
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
