# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

import asyncio

from pydantic import BaseModel

from khive.protocols.service import Service
from khive.services.info.parts import (
    InfoAction,
    InfoConsultParams,
    InfoRequest,
    InfoResponse,
    SearchProvider,
)


class InfoServiceGroup(Service):
    def __init__(self):
        from khive.connections.api.endpoint import Endpoint

        self._perplexity: Endpoint = None
        self._exa: Endpoint = None
        self._openrouter: Endpoint = None

    async def handle_request(self, request: InfoRequest) -> InfoResponse:
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

    async def _perplexity_search(self, params) -> InfoResponse:
        from khive.providers.perplexity_ import (
            PerplexityChatEndpoint,
            PerplexityChatRequest,
        )

        params: PerplexityChatRequest

        if self._perplexity is None:
            self._perplexity = PerplexityChatEndpoint()
        try:
            response = await self._perplexity.call(params, cache_control=True)
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
        from khive.providers.exa_ import ExaSearchEndpoint, ExaSearchRequest

        params: ExaSearchRequest

        if self._exa is None:
            self._exa = ExaSearchEndpoint()
        try:
            response = await self._exa.call(params, cache_control=True)
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
        from khive.providers.oai_ import OpenrouterChatEndpoint

        if self._openrouter is None:
            self._openrouter = OpenrouterChatEndpoint()
        try:
            models = params.models
            system_prompt = (
                params.system_prompt
                or "You are a diligent technical expert who is good at critical thinking and problem solving."
            )

            tasks = {}
            for m in models:
                payload = {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": params.question},
                    ],
                    "temperature": 0.7,
                    "model": m,
                }
                tasks[m] = asyncio.create_task(self._openrouter.call(payload))

            responses = await asyncio.gather(*list(tasks.values()))
            res = {}
            for i, m in enumerate(models):
                r = responses[i]
                r = r.model_dump() if isinstance(r, BaseModel) else r
                res[m] = r

            return InfoResponse(
                success=True, action_performed=InfoAction.CONSULT, content=res
            )
        except Exception as e:
            return InfoResponse(
                success=False,
                error=f"Consult error: {e!s}",
                action_performed=InfoAction.CONSULT,
            )
