# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

import json
from typing import Literal

from lionfuncs.async_utils import alcall
from lionfuncs.file_system import save_to_file
from lionfuncs.network import (
    Endpoint,
    EndpointConfig,
    Executor,
    NetworkRequestEvent,
    RequestStatus,
    iModel,
)
from pydapter.protocols.event import as_event

from khive.config import settings
from khive.services.info.parts import (
    InfoAction,
    InfoConsultParams,
    InfoRequest,
    InfoResponse,
    SearchProvider,
)
from khive.services.info.providers.exa_models import ExaSearchRequest
from khive.services.info.providers.pplx_models import PerplexityChatRequest
from khive.types import Service

event_type = "info_search"

USE_EMBEDDING = False
ADAPT_TO_QDRANT = False
ADAPTER = None
ADAPTER_KWARGS = {}
EMBED_IMODEL = None
EMBED_FUNCTION = None


if settings.KHIVE_AUTO_EMBED_LOG and settings.OPENAI_API_KEY is not None:
    USE_EMBEDDING = True
    EMBED_IMODEL = iModel(
        executor=Executor(),
        endpoint=Endpoint(
            config=EndpointConfig(
                name="openai_embed",
                provider="openai",
                transport_type="sdk",
                api_key=settings.OPENAI_API_KEY.get_secret_value(),
                oai_compatible=True,
            ),
        ),
    )

    async def _embed_with_oai(content: str) -> list[float]:
        async with EMBED_IMODEL as imodel:
            response = await imodel.invoke(
                request_payload={
                    "model": "text-embedding-3-small",
                    "input": content,
                    "encoding_format": "float",
                },
                sdk_method_name="embeddings.create",
            )
            await save_to_file(
                directory="./data/logs/embedding",
                filename=f"embedding_{response.request_id}.json",
                text=response.model_dump_json(),
            )
            if response.status is not RequestStatus.COMPLETED:
                raise ValueError(f"Embedding error: {response.error_message}")
            return response.response_body.data[0].embedding

    EMBED_FUNCTION = _embed_with_oai
    ADAPTER_KWARGS = {
        "collection": event_type,
        "url": settings.KHIVE_QDRANT_URL,
    }

if settings.KHIVE_AUTO_STORE_EVENT and settings.KHIVE_QDRANT_URL is not None:
    from pydapter.extras.async_qdrant_ import AsyncQdrantAdapter

    qdrant_url = settings.KHIVE_QDRANT_URL
    ADAPT_TO_QDRANT = True
    ADAPTER = AsyncQdrantAdapter


def get_exa_search():
    return EndpointConfig(
        name="exa_search",
        provider="exa",
        base_url="https://api.exa.ai",
        endpoint="search",
        method="POST",
        api_key=settings.EXA_API_KEY.get_secret_value(),
        timeout=120,
        max_retries=3,
        auth_type="x-api-key",
        transport_type="http",
        content_type="application/json",
    )


def get_pplx_search():
    return EndpointConfig(
        name="perplexity_search",
        provider="perplexity",
        transport_type="http",
        base_url="https://api.perplexity.ai",
        endpoint="chat/completions",
        api_key=settings.PERPLEXITY_API_KEY.get_secret_value(),
    )


def openrouter_chat():
    return EndpointConfig(
        name="openrouter_chat",
        provider="openrouter",
        transport_type="sdk",
        base_url="https://openrouter.ai/api/v1",
        endpoint="chat/completions",
        kwargs={"model": "anthropic/claude-sonnet-4"},
        default_headers={"HTTP-Referer": "https://khive.ai", "X-Title": "khive ai"},
    )


class InfoServiceGroup(Service):
    def __init__(self):
        """
        Initialize the InfoService with lazy-loaded endpoints.

        Endpoints will be initialized only when they are first used.
        """
        self._perplexity: iModel = None
        self._exa: iModel = None
        self._openrouter: iModel = None
        self._executor = Executor()

    async def handle_request(self, request: InfoRequest) -> InfoResponse:
        event = await self._handle_request(request)
        return event.response_obj

    @as_event(
        embed_content=USE_EMBEDDING,
        embed_function=EMBED_FUNCTION,
        adapt=ADAPT_TO_QDRANT,
        adapter=ADAPTER,
        event_type=event_type,
        content_function=lambda x: x.response_obj.content,
        **ADAPTER_KWARGS,
    )
    async def _handle_request(self, request: InfoRequest) -> InfoResponse:
        """Handle an info request."""
        if isinstance(request, str):
            request = InfoRequest.model_validate_json(request)
        if isinstance(request, dict):
            request = InfoRequest.model_validate(request)

        if request.action == InfoAction.SEARCH:
            if request.params.provider == SearchProvider.PERPLEXITY:
                return await self._perplexity_search(request.params.provider_params)
            if request.params.provider == SearchProvider.EXA:
                return await self._exa_search(request.params.provider_params)

        if request.action == InfoAction.CONSULT:
            return await self._consult(request.params)

        return InfoResponse(
            success=False,
            error="Invalid action or parameters.",
        )

    def get_imodel(self, provider: Literal["perplexity", "exa"]) -> iModel:
        config = None
        if provider == "perplexity":
            config = get_pplx_search()
        if provider == "exa":
            config = get_exa_search()
        return iModel(
            endpoint=Endpoint(config),
            executor=self._executor,
        )

    async def _perplexity_search(self, params: PerplexityChatRequest) -> InfoResponse:
        """
        Perform a search using the Perplexity API.

        Args:
            params: The parameters for the Perplexity search.

        Returns:
            InfoResponse: The response from the search.
        """
        if self._perplexity is None:
            self._perplexity = self.get_imodel("perplexity")

        async with self._perplexity as imodel:
            response = await imodel.invoke(params)

        if response.status is not RequestStatus.COMPLETED:
            return InfoResponse(
                success=False,
                action_performed=InfoAction.SEARCH,
                error=response.error_message,
                content=response.response_body,
            )

        content = (
            response.response_body.get("choices", [{}])[0]
            .get("message", {})
            .get("content")
        )

        if not content:
            return InfoResponse(
                success=False,
                action_performed=InfoAction.SEARCH,
                error="Perplexity search returned no valid content.",
                content=response.response_body,
            )

        return InfoResponse(
            success=True,
            action_performed=InfoAction.SEARCH,
            content={
                "request_id": response.request_id,
                "query": params.messages[0]["content"],
                "response": content,
                "metadata": {
                    "citations": response.response_body["citations"],
                    "model": response.response_body["model"],
                },
            },
        )

    async def _exa_search(self, params: ExaSearchRequest) -> InfoResponse:
        """
        Perform a search using the Exa API.

        Args:
            params: The parameters for the Exa search.

        Returns:
            InfoResponse: The response from the search.
        """
        if self._exa is None:
            self._exa = self.get_imodel("exa")

        async with self._exa as imodel:
            response = await imodel.invoke(params)

        content = response.response_body.get("results")

        if not content:
            return InfoResponse(
                success=False,
                action_performed=InfoAction.SEARCH,
                error="Exa search returned no valid content.",
                content=response.response_body,
            )

        return InfoResponse(
            success=True,
            action_performed=InfoAction.SEARCH,
            content={
                "request_id": response.request_id,
                "query": params.query,
                "response": content,
                "metadata": {
                    "num_results": params.numResults,
                    "category": params.category,
                },
            },
        )

    async def _consult(self, params: InfoConsultParams):
        if self._openrouter is None:
            self._openrouter = iModel(
                endpoint=Endpoint(openrouter_chat()),
                executor=self._executor,
            )
        async with self._openrouter as imodel:
            requests = []
            for i in params.models:
                messages = (
                    [{"role": "system", "content": params.system_prompt}]
                    if params.system_prompt
                    else []
                )
                messages.append({"role": "user", "content": params.question})
                request = {"model": i, "messages": messages}
                requests.append(request)
            responses: list[NetworkRequestEvent] = await alcall(imodel.invoke, requests)

        try:
            contents = {}
            for idx, i in enumerate(responses):
                if i.status is not RequestStatus.COMPLETED:
                    contents[params.models[idx]] = i.error_message
                else:
                    contents[params.models[idx]] = i.response_body.choices[
                        0
                    ].message.content

            return InfoResponse(
                success=True,
                action_performed=InfoAction.CONSULT,
                content=json.dumps(contents),
            )
        except Exception as e:
            return InfoResponse(
                success=False,
                action_performed=InfoAction.CONSULT,
                error=f"Error processing responses: {e!s}",
            )
