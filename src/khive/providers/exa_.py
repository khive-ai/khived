# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from khive.config import settings
from khive.connections.endpoint import Endpoint, EndpointConfig
from khive.third_party.exa_models import ExaSearchRequest

__all__ = ("ExaSearchEndpoint",)


ENDPOINT_CONFIG = EndpointConfig(
    name="exa_search",
    provider="exa",
    base_url="https://api.exa.ai",
    endpoint="search",
    method="POST",
    request_options=ExaSearchRequest,
    api_key=settings.EXA_API_KEY,
    timeout=120,
    max_retries=3,
    auth_type="x-api-key",
    transport_type="http",
    content_type="application/json",
)


class ExaSearchEndpoint(Endpoint):
    def __init__(self, config=ENDPOINT_CONFIG, **kwargs):
        super().__init__(config=config, **kwargs)
