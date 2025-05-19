# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any

from pydantic import BaseModel

from khive.clients.executor import AsyncExecutor
from khive.connections.match_endpoint import match_endpoint
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
        self._executor = AsyncExecutor(max_concurrency=10)

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
        """
        Perform a search using the Perplexity API.

        Args:
            params: The parameters for the Perplexity search.

        Returns:
            InfoResponse: The response from the search.
        """
        # Lazy initialization of the Perplexity endpoint
        if self._perplexity is None:
            self._perplexity = match_endpoint("perplexity", "chat")

        if self._perplexity is None:
            return InfoResponse(
                success=False,
                error="Perplexity search error: Endpoint not initialized",
                action_performed=InfoAction.SEARCH,
            )

        try:
            # Import here to avoid circular imports
            from khive.connections.providers.perplexity_ import PerplexityChatRequest

            # Always create a new PerplexityChatRequest from the params
            if hasattr(params, "get") and callable(params.get):
                # Dict-like object
                model = params.get("model", "sonar")
                query = params.get("query", "")

                request_params = {
                    "model": model,
                    "messages": [{"role": "user", "content": query}],
                }
                perplexity_params = PerplexityChatRequest(**request_params)
            else:
                # Assume it's already a valid request object
                perplexity_params = params

            response = await self._perplexity.call(perplexity_params)
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
        """
        Perform a search using the Exa API.

        Args:
            params: The parameters for the Exa search.

        Returns:
            InfoResponse: The response from the search.
        """
        # Lazy initialization of the Exa endpoint
        if self._exa is None:
            self._exa = match_endpoint("exa", "search")

        if self._exa is None:
            return InfoResponse(
                success=False,
                error="Exa search error: Endpoint not initialized",
                action_performed=InfoAction.SEARCH,
            )

        try:
            # Import here to avoid circular imports
            from khive.connections.providers.exa_ import ExaSearchRequest

            # Always create a new ExaSearchRequest from the params
            if hasattr(params, "get") and callable(params.get):
                # Dict-like object
                query = params.get("query", "")
                num_results = params.get("numResults", 10)
                use_autoprompt = params.get("useAutoprompt", False)

                request_params = {
                    "query": query,
                    "numResults": num_results,
                    "useAutoprompt": use_autoprompt,
                }
                exa_params = ExaSearchRequest(**request_params)
            else:
                # Assume it's already a valid request object
                exa_params = params

            response = await self._exa.call(exa_params)
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

    async def _make_model_call(self, payload: dict[str, Any]) -> Any:
        """
        Make a call to a model using the OpenRouter endpoint.

        Args:
            payload: The payload to send to the model, which includes the model identifier.

        Returns:
            The response from the model, or an error dict if the call fails.
        """
        if self._openrouter is None:
            return {"error": "OpenRouter endpoint not initialized"}

        try:
            response = await self._openrouter.call(payload)
            return (
                response.model_dump() if isinstance(response, BaseModel) else response
            )
        except Exception as e:
            return {"error": str(e)}

    async def _consult(self, params: InfoConsultParams) -> InfoResponse:
        """
        Consult multiple models using the OpenRouter API.

        Args:
            params: The parameters for the consultation.

        Returns:
            InfoResponse: The response from the consultation.
        """
        # Lazy initialization of the OpenRouter endpoint
        if self._openrouter is None:
            self._openrouter = match_endpoint("openrouter", "chat")

        if self._openrouter is None:
            return InfoResponse(
                success=False,
                error="Consult error: Endpoint not initialized",
                action_performed=InfoAction.CONSULT,
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

            # Use our executor to make concurrent calls with controlled concurrency
            async def process_model_call(item):
                model, payload = item
                result = await self._make_model_call(payload)
                return model, result

            # Execute all model calls with controlled concurrency
            results = await self._executor.map(process_model_call, payloads)

            # Convert results to the expected format
            res = dict(results)

            return InfoResponse(
                success=True, action_performed=InfoAction.CONSULT, content=res
            )
        except Exception as e:
            return InfoResponse(
                success=False,
                error=f"Consult error: {e!s}",
                action_performed=InfoAction.CONSULT,
            )

    async def close(self) -> None:
        """
        Close the service and release resources.

        This method ensures proper cleanup of all resources.
        """
        # Shutdown the executor
        if hasattr(self, "_executor") and self._executor is not None:
            await self._executor.shutdown()

        # Close any initialized endpoints
        for endpoint_attr in ("_perplexity", "_exa", "_openrouter"):
            endpoint = getattr(self, endpoint_attr, None)
            if endpoint is not None and hasattr(endpoint, "aclose"):
                await endpoint.aclose()
