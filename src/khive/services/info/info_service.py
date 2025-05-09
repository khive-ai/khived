import asyncio

from pydantic import BaseModel

from khive.providers.exa_ import ExaSearchEndpoint, ExaSearchRequest
from khive.providers.oai_ import OpenrouterChatEndpoint
from khive.providers.perplexity_ import PerplexityChatEndpoint, PerplexityChatRequest

from .parts import (
    InfoAction,
    InfoConsultParams,
    InfoRequest,
    InfoResponse,
    SearchProvider,
)


class InfoService:
    def __init__(self):
        self._perplexity: PerplexityChatEndpoint = None
        self._exa: ExaSearchEndpoint = None
        self._openrouter: OpenrouterChatEndpoint = None

    async def handle_request(self, request: InfoRequest) -> InfoResponse:
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

    async def _perplexity_search(self, params: PerplexityChatRequest) -> InfoResponse:
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

    async def _exa_search(self, params: ExaSearchRequest) -> InfoResponse:
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
        if self._openrouter is None:
            self._openrouter = OpenrouterChatEndpoint()
        try:
            models = params.models
            system_prompt = params.system_prompt or "You are a helpful assistant."

            tasks = {}
            for m in models:
                payload = {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": params.question},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 400,
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
