# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from khive.connections.imodel import iModel
from khive.services.info.parts import (
    InfoAction,
    InfoConsultParams,
    InfoRequest,
    InfoResponse,
    SearchProvider,
)
from khive.types import Service


class InfoServiceGroup(Service):
    def __init__(self):
        """
        Initialize the InfoService with lazy-loaded endpoints.

        Endpoints will be initialized only when they are first used.
        """
        self._perplexity = None
        self._exa = None
        self._openrouter = None

    async def handle_request(self, request: InfoRequest) -> InfoResponse:
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

    async def _perplexity_search(self, params) -> InfoResponse:
        from khive.connections.providers.perplexity_ import PerplexityChatRequest

        params: PerplexityChatRequest

        if self._perplexity is None:
            self._perplexity = iModel(
                provider="perplexity",
                endpoint="chat",
                queue_capacity=20,
                interval=60,
                limit_requests=10,
            )
        try:
            api_call = self._perplexity.create_api_calling(
                request=params,
                cache_control=True,
            )
            response = await self._perplexity.invoke(api_call)
            response = response[0].execution.response
            return InfoResponse(
                success=True,
                action_performed=InfoAction.SEARCH,
                content=response,
            )
        except Exception as e:
            return InfoResponse(
                success=False,
                error=f"Perplexity search error: {e!s}",
                action_performed=InfoAction.SEARCH,
            )

    async def _exa_search(self, params) -> InfoResponse:
        from khive.connections.providers.exa_ import ExaSearchRequest

        params: ExaSearchRequest

        if self._exa is None:
            self._exa = iModel(
                provider="exa",
                endpoint="search",
                queue_capacity=5,
                interval=1,
                concurrency_limit=5,
                limit_requests=5,
            )

        try:
            api_call = self._exa.create_api_calling(
                request=params,
                cache_control=True,
            )
            response = await self._exa.invoke(api_call)
            response = response[0].execution.response
            return InfoResponse(
                success=True,
                action_performed=InfoAction.SEARCH,
                content=response,
            )
        except Exception as e:
            return InfoResponse(
                success=False,
                error=f"Exa search error: {e!s}",
                action_performed=InfoAction.SEARCH,
            )

    async def _consult(self, params: InfoConsultParams) -> InfoResponse:
        if self._openrouter is None:
            self._openrouter = iModel(
                provider="openrouter",
                endpoint="chat",
                queue_capacity=20,
                interval=60,
                limit_requests=10,
                concurrency_limit=10,
            )

        try:
            models = params.models
            system_prompt = (
                params.system_prompt
                or "You are a diligent technical expert who is good at critical thinking and problem solving."
            )

            # Prepare payloads for each model
            payloads = []
            for model in models:
                payload = {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": params.question},
                    ],
                    "temperature": 0.7,
                    "model": model,
                }
                payloads.append((model, payload))

            api_calls = [
                self._openrouter.create_api_calling(
                    request=payload,
                    cache_control=True,
                )
                for _, payload in payloads
            ]
            responses = await self._openrouter.invoke(api_calls)
            responses = {
                model: response.execution.response
                for (model, _), response in zip(payloads, responses, strict=False)
            }
            return InfoResponse(
                success=True, action_performed=InfoAction.CONSULT, content=responses
            )
        except Exception as e:
            return InfoResponse(
                success=False,
                error=f"Consult error: {e!s}",
                action_performed=InfoAction.CONSULT,
            )
