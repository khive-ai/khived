#!/usr/bin/env python3
"""
Unified async search wrapper around LionAGI's iModel for Exa & Perplexity.

Usage example
-------------
from khive.search_service import SearchService
exa_resp  = await SearchService().exa_search(ExaSearchRequest(query="…"))
pplx_resp = await SearchService().perplexity_search(PerplexityChatCompletionRequest(
                    messages=[{"role":"user", "content":"…"}]))
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Final, Literal, TypedDict

from dotenv import load_dotenv
from lionagi import iModel
from lionagi.service.endpoints.base import APICalling
from lionagi.service.providers.exa_.models import ExaSearchRequest
from lionagi.service.providers.perplexity_.models import PerplexityChatCompletionRequest

# --------------------------------------------------------------------------- #
# Configuration & Logging                                                     #
# --------------------------------------------------------------------------- #

ENV_FILE = Path(__file__).with_suffix(".env")  # optional local secrets
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)  # .env next to this file
else:
    load_dotenv()  # fall back to repo root .env

logger = logging.getLogger("khive.search")
logger.setLevel(logging.INFO)

# --------------------------------------------------------------------------- #
# Result type - helps static analysis                                         #
# --------------------------------------------------------------------------- #


class SearchResult(TypedDict, total=False):
    id: str
    created_at: str
    status: str
    duration: float | None
    response: dict | str | None
    error: str | None


# --------------------------------------------------------------------------- #
# Service Singleton                                                           #
# --------------------------------------------------------------------------- #


class SearchService:
    """
    Lazy-initialised singletons around iModel pools so that:

    * The first call to exa/perplexity creates a worker pool
    * Subsequent calls reuse it (lower latency, shared rate-limits)
    """

    _exa_model: iModel | None = None
    _pplx_model: iModel | None = None
    _lock: asyncio.Lock = asyncio.Lock()  # protects lazy init

    # ---------- Public API -------------------------------------------------- #

    async def exa_search(
        self, request: ExaSearchRequest, *, cached: bool = True
    ) -> SearchResult:
        model = await self._get_exa_model()
        return await self._invoke(model, request.model_dump(exclude_none=True), cached)

    async def perplexity_search(
        self, request: PerplexityChatCompletionRequest, *, cached: bool = True
    ) -> SearchResult:
        model = await self._get_pplx_model()
        return await self._invoke(model, request.model_dump(exclude_none=True), cached)

    # ---------- Internals --------------------------------------------------- #

    async def _get_exa_model(self) -> iModel:
        async with self._lock:
            if self._exa_model is None:
                api_key = os.getenv("EXA_API_KEY") or ""
                if not api_key:
                    raise RuntimeError("EXA_API_KEY not set in environment")
                self._exa_model = iModel(
                    provider="exa",
                    endpoint="search",
                    interval=1,  # one request / second
                    limit_requests=5,  # burst cap (client-side)
                    queue_capacity=5,
                    api_key=api_key,
                )
        return self._exa_model

    async def _get_pplx_model(self) -> iModel:
        async with self._lock:
            if self._pplx_model is None:
                api_key = os.getenv("PERPLEXITY_API_KEY") or ""
                if not api_key:
                    raise RuntimeError("PERPLEXITY_API_KEY not set in environment")
                self._pplx_model = iModel(
                    provider="perplexity",
                    endpoint="chat",
                    interval=60,  # safest: 1 call / minute
                    limit_requests=10,
                    limit_tokens=20_000,
                    api_key=api_key,
                )
        return self._pplx_model

    @staticmethod
    async def _invoke(model: iModel, payload: dict, cached: bool) -> SearchResult:
        result: APICalling = await model.invoke(**payload, is_cached=cached)
        exec_ = result.execution
        return SearchResult(
            id=str(result.id),
            created_at=result.created_datetime.isoformat(),
            status=exec_.status.value,
            duration=exec_.duration,
            response=exec_.response,
            error=exec_.error,
        )


# --------------------------------------------------------------------------- #
# Convenience module-level singleton so agents can simply:
#   from khive.search_service import search_service
#   await search_service.exa_search(…)
# --------------------------------------------------------------------------- #

search_service: Final[SearchService] = SearchService()
