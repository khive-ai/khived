from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import ClassVar, Final

from khive.connections.endpoint import APICalling, iModel
from khive.connections.providers.exa_search import ExaSearchEndpoint, ExaSearchRequest
from khive.connections.providers.perplexity_chat import (
    PerplexityChatEndpoint,
    PerplexityChatRequest,
)
from khive.protocols.element import Log

logger = logging.getLogger("khive.search")
logger.setLevel(logging.INFO)


class SearchAction(str, Enum):
    """
    Enum for search actions.
    """

    EXA_SEARCH = "exa_search"
    PERPLEXITY_CHAT = "perplexity_chat"


class SearchService:
    """
    Lazy-initialised singletons around iModel pools so that:

    * The first call to exa/perplexity creates a worker pool
    * Subsequent calls reuse it (lower latency, shared rate-limits)
    """

    _exa_model: iModel | None = None
    _pplx_model: iModel | None = None
    _lock: asyncio.Lock = asyncio.Lock()  # protects lazy init

    SERVICES: ClassVar[list[str]] = [
        "exa_search",
        "perplexity_chat",
    ]

    # ---------- Public API -------------------------------------------------- #

    async def exa_search(
        self, request: ExaSearchRequest, *, cache_control: bool = True
    ) -> dict:
        model = await self._get_exa_model()
        return await self._invoke(
            model, request.model_dump(exclude_none=True), cache_control
        )

    async def perplexity_chat(
        self, request: PerplexityChatRequest, *, cache_control: bool = True
    ) -> dict:
        model = await self._get_pplx_model()
        return await self._invoke(
            model, request.model_dump(exclude_none=True), cache_control
        )

    # ---------- Internals --------------------------------------------------- #

    async def _get_exa_model(self) -> iModel:
        async with self._lock:
            if self._exa_model is None:
                endpoint = ExaSearchEndpoint()
                self._exa_model = iModel(
                    endpoint=endpoint,
                    request_limit=20,
                    concurrency_limit=5,
                    limit_interval=60,
                )
        return self._exa_model

    async def _get_pplx_model(self) -> iModel:
        async with self._lock:
            if self._pplx_model is None:
                endpoint = PerplexityChatEndpoint()
                self._pplx_model = iModel(
                    endpoint=endpoint,
                    request_limit=120,
                    concurrency_limit=10,
                    limit_interval=60,
                )
        return self._pplx_model

    @staticmethod
    async def _invoke(model: iModel, payload: dict, cache_control: bool) -> dict:
        result: APICalling = await model.invoke(**payload, cache_control=cache_control)
        return Log.create(result).to_dict()


search_service: Final[SearchService] = SearchService()
