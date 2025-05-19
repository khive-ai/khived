# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import logging

import aiohttp
import backoff
from aiocache import cached
from pydantic import BaseModel

from khive.clients.resilience import CircuitBreaker, RetryConfig, retry_with_backoff
from khive.config import settings
from khive.utils import is_package_installed

from .endpoint_config import EndpointConfig
from .header_factory import HeaderFactory

logger = logging.getLogger(__name__)

_HAS_OPENAI = is_package_installed("openai")


class Endpoint:
    def __init__(
        self,
        config: dict | EndpointConfig,
        circuit_breaker: CircuitBreaker | None = None,
        retry_config: RetryConfig | None = None,
        **kwargs,
    ):
        """
        Initialize the endpoint.

        Args:
            config: The endpoint configuration.
            circuit_breaker: Optional circuit breaker for resilience.
            retry_config: Optional retry configuration for resilience.
            **kwargs: Additional keyword arguments to update the configuration.
        """
        _config = {}
        if isinstance(config, dict):
            _config = EndpointConfig(**config, **kwargs)
        if isinstance(config, EndpointConfig):
            _config = config.model_copy()
            _config.update(**kwargs)
        self.config = _config
        self.client = None
        self.circuit_breaker = circuit_breaker
        self.retry_config = retry_config

        logger.debug(
            f"Initialized Endpoint with provider={self.config.provider}, "
            f"endpoint={self.config.endpoint}, circuit_breaker={circuit_breaker is not None}, "
            f"retry_config={retry_config is not None}"
        )

    def _create_client(self):
        if self.config.transport_type == "sdk" and self.config.openai_compatible:
            if not _HAS_OPENAI:
                raise ModuleNotFoundError(
                    "The OpenAI SDK is not installed. Please install it with `pip install openai`."
                )
            from openai import AsyncOpenAI  # type: ignore[import]

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
        """
        Enter the async context manager and initialize the client.

        Returns:
            The Endpoint instance with an initialized client.
        """
        self.client = self._create_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Close the client when exiting the context manager.

        This method ensures proper resource cleanup for both HTTP and SDK clients.
        It handles exceptions gracefully to ensure resources are always released.

        Args:
            exc_type: The exception type, if an exception was raised.
            exc_val: The exception value, if an exception was raised.
            exc_tb: The exception traceback, if an exception was raised.
        """
        await self._close_client()

    async def aclose(self):
        """
        Gracefully close the client session.

        This method can be called explicitly to close the client without using
        the context manager. It ensures proper resource cleanup for both HTTP
        and SDK clients.
        """
        await self._close_client()

    async def _close_client(self):
        """
        Internal method to close the client and release resources.

        This method handles different client types and ensures proper cleanup
        in all cases, including error scenarios.
        """
        if self.client is None:
            return

        try:
            if self.config.transport_type == "http":
                await self.client.close()
            elif self.config.transport_type == "sdk" and hasattr(self.client, "close"):
                # Some SDK clients might have a close method
                if asyncio.iscoroutinefunction(self.client.close):
                    await self.client.close()
                else:
                    self.client.close()
        except Exception as e:
            # Log the error but don't re-raise to ensure cleanup continues
            logger.warning(
                "Error closing client",
                extra={
                    "error": str(e),
                    "client_type": self.config.transport_type,
                    "endpoint": self.config.endpoint,
                    "provider": self.config.provider,
                },
            )
        finally:
            # Always clear the client reference
            self.client = None

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

        # First update params with the request data
        params.update(request)

        # Then handle any additional kwargs
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

        # Apply request_options validation if configured
        if self.request_options is not None:
            params = self.request_options.model_validate(params).model_dump(
                exclude_none=True
            )

        return (params, headers)

    async def call(
        self, request: dict | BaseModel, cache_control: bool = False, **kwargs
    ):
        """
        Make a call to the endpoint.

        Args:
            request: The request parameters or model.
            cache_control: Whether to use cache control.
            **kwargs: Additional keyword arguments for the request.

        Returns:
            The response from the endpoint.
        """
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

        # Apply resilience patterns if configured
        call_func = _call

        # Apply retry if configured
        if self.retry_config:

            async def call_func(p, h, **kw):
                return await retry_with_backoff(
                    _call, p, h, **kw, **self.retry_config.as_kwargs()
                )

        # Apply circuit breaker if configured
        if self.circuit_breaker:
            if self.retry_config:
                # If both are configured, apply circuit breaker to the retry-wrapped function
                if not cache_control:
                    return await self.circuit_breaker.execute(
                        call_func, payload, headers, **kwargs
                    )
            else:
                # If only circuit breaker is configured, apply it directly
                if not cache_control:
                    return await self.circuit_breaker.execute(
                        _call, payload, headers, **kwargs
                    )

        # Handle caching if requested
        if cache_control:

            @cached(**settings.aiocache_config.as_kwargs())
            async def _cached_call(payload: dict, headers: dict, **kwargs):
                # Apply resilience patterns to cached call if configured
                if self.circuit_breaker and self.retry_config:
                    return await self.circuit_breaker.execute(
                        call_func, payload, headers, **kwargs
                    )
                if self.circuit_breaker:
                    return await self.circuit_breaker.execute(
                        _call, payload, headers, **kwargs
                    )
                if self.retry_config:
                    return await call_func(payload, headers, **kwargs)

                return await _call(payload, headers, **kwargs)

            return await _cached_call(payload, headers, **kwargs)

        # No caching, apply resilience patterns directly
        if self.retry_config:
            return await call_func(payload, headers, **kwargs)

        return await _call(payload, headers, **kwargs)

    async def _call_aiohttp(self, payload: dict, headers: dict, **kwargs):
        """
        Make a call using aiohttp.

        Args:
            payload: The request payload.
            headers: The request headers.
            **kwargs: Additional keyword arguments for the request.

        Returns:
            The response from the endpoint.
        """

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

                # Extract and return the JSON response
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
        """
        Make a call using the OpenAI SDK.

        Args:
            payload: The request payload.
            headers: The request headers.
            **kwargs: Additional keyword arguments for the request.

        Returns:
            The response from the endpoint.
        """
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
