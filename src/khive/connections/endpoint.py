import asyncio

import aiohttp
import backoff
from aiocache import cached
from pydantic import BaseModel

from khive.config import settings

from .endpoint_config import EndpointConfig
from .header_factory import HeaderFactory


class Endpoint:
    def __init__(self, config: dict | EndpointConfig, **kwargs):
        if isinstance(config, dict):
            config = EndpointConfig(**config)
        if not isinstance(config, EndpointConfig):
            raise TypeError(f"Expected EndpointConfig, got {type(config)}")
        self.config = config
        self.config.update(**kwargs)
        self.client = None

    def _create_client(self):
        if self.config.transport_type == "sdk" and self.config.openai_compatible:
            from openai import AsyncOpenAI

            return AsyncOpenAI(
                api_key=self.config._api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
                default_headers=self.config.default_headers,
                **self.config.client_kwargs,
            )
        if self.config.transport_type == "http":
            return aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(self.config.timeout),
                **self.config.client_kwargs,
            )

        raise ValueError(f"Unsupported transport type: {self.config.transport_type}")

    async def __aenter__(self):
        self.client = self._create_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close the client when exiting the context manager."""
        if self.client and self.config.transport_type == "http":
            await self.client.close()

    async def aclose(self):
        """Gracefully close the client session."""
        if self.client and self.config.transport_type == "http":
            await self.client.close()

    @property
    def request_options(self):
        return self.config.request_options

    @request_options.setter
    def request_options(self, value):
        self.config.request_options = EndpointConfig._validate_request_options(value)

    def create_payload(
        self,
        request: dict | BaseModel,
        extra_headers: dict | None = None,
        **kwargs,
    ):
        headers = HeaderFactory.get_header(
            auth_type=self.config.auth_type,
            content_type=self.config.content_type,
            api_key=self.config._api_key,
            default_headers=self.config.default_headers,
        )
        if extra_headers:
            headers.update(extra_headers)

        request = (
            request
            if isinstance(request, dict)
            else request.model_dump(exclude_none=True)
        )
        params = self.config.kwargs.copy()

        if kwargs:
            if self.request_options is not None:
                update_config = {
                    k: v
                    for k, v in kwargs.items()
                    if k
                    in list(
                        self.request_options.model_json_schema()["properties"].keys()
                    )
                }
                params.update(update_config)
            else:
                params.update(kwargs)

        params.update(request)

        if self.request_options is not None:
            params = self.request_options.model_validate(params).model_dump(
                exclude_none=True
            )

        return (params, headers)

    async def call(
        self, request: dict | BaseModel, cache_control: bool = False, **kwargs
    ):
        payload, headers = self.create_payload(request, **kwargs)

        async def _call(payload: dict, headers: dict, **kwargs):
            async with self:  # Use the context manager to handle client lifecycle
                if self.config.openai_compatible:
                    return await self._call_openai(
                        payload=payload, headers=headers, **kwargs
                    )
                return await self._call_aiohttp(
                    payload=payload, headers=headers, **kwargs
                )

        if not cache_control:
            return await _call(payload, headers, **kwargs)

        @cached(**settings.aiocache_config.as_kwargs())
        async def _cached_call(payload: dict, headers: dict, **kwargs):
            return await _call(payload=payload, headers=headers, **kwargs)

        return await _cached_call(payload, headers, **kwargs)

    async def _call_aiohttp(self, payload: dict, headers: dict, **kwargs):
        async def _make_request_with_backoff():
            response = None
            try:
                # Don't use context manager to have more control over response lifecycle
                response = await self.client.request(
                    method=self.config.method,
                    url=self.config.full_url,
                    headers=headers,
                    json=payload,
                    **kwargs,
                )

                # Check for rate limit or server errors that should be retried
                if response.status == 429 or response.status >= 500:
                    response.raise_for_status()  # This will be caught by backoff
                elif response.status != 200:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"Request failed with status {response.status}",
                        headers=response.headers,
                    )

                return await response.json()
            finally:
                # Ensure response is properly released if coroutine is cancelled between retries
                if response is not None and not response.closed:
                    await response.release()

        # Define a giveup function for backoff
        def giveup_on_client_error(e):
            # Don't retry on 4xx errors except 429 (rate limit)
            if isinstance(e, aiohttp.ClientResponseError):
                return 400 <= e.status < 500 and e.status != 429
            return False

        # Use backoff for retries with exponential backoff and jitter
        # Moved inside the method to reference runtime config
        backoff_handler = backoff.on_exception(
            backoff.expo,
            (aiohttp.ClientError, asyncio.TimeoutError),
            max_tries=self.config.max_retries,
            giveup=giveup_on_client_error,
            jitter=backoff.full_jitter,
        )

        # Apply the decorator at runtime
        return await backoff_handler(_make_request_with_backoff)()

    async def _call_openai(self, payload: dict, headers: dict, **kwargs):
        payload = {**payload, **self.config.kwargs, **kwargs}

        if headers:
            payload["extra_headers"] = headers

        async def _make_request_with_backoff():
            if "chat" in self.config.endpoint:
                if "response_format" in payload:
                    return await self.client.beta.chat.completions.parse(**payload)
                payload.pop("response_format", None)
                return await self.client.chat.completions.create(**payload)

            if "responses" in self.config.endpoint:
                if "response_format" in payload:
                    return await self.client.responses.parse(**payload)
                payload.pop("response_format", None)
                return await self.client.responses.create(**payload)

            if "embed" in self.config.endpoint:
                return await self.client.embeddings.create(**payload)

            raise ValueError(f"Invalid endpoint: {self.config.endpoint}")

        # Define a giveup function for backoff
        def giveup_on_client_error(e):
            # Don't retry on 4xx errors except 429 (rate limit)
            if hasattr(e, "status") and isinstance(e.status, int):
                return 400 <= e.status < 500 and e.status != 429
            return False

        # Use backoff for retries with exponential backoff and jitter
        backoff_handler = backoff.on_exception(
            backoff.expo,
            Exception,  # OpenAI client can raise various exceptions
            max_tries=self.config.max_retries,
            giveup=giveup_on_client_error,
            jitter=backoff.full_jitter,
        )

        # Apply the decorator at runtime
        return await backoff_handler(_make_request_with_backoff)()
