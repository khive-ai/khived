from khive.connections.endpoint import Endpoint, EndpointConfig
from khive.third_party.pplx_models import PerplexityChatRequest

__all__ = ("PerplexityChatEndpoint",)


ENDPOINT_CONFIG = EndpointConfig(
    name="perplexity_chat",
    provider="perplexity",
    base_url="https://api.perplexity.ai",
    endpoint="chat/completions",
    method="POST",
    kwargs={"model": "sonar"},
    api_key="PERPLEXITY_API_KEY",
    auth_type="bearer",
    content_type="application/json",
    request_options=PerplexityChatRequest,
    transport_type="http",
)


class PerplexityChatEndpoint(Endpoint):
    def __init__(self, config=ENDPOINT_CONFIG, **kwargs):
        super().__init__(config, **kwargs)
