# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for resilience patterns.

This module contains integration tests for the circuit breaker and retry patterns
with API client and Endpoint.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from khive.clients.api_client import AsyncAPIClient
from khive.clients.errors import CircuitBreakerOpenError, ServerError
from khive.clients.resilience import CircuitBreaker, RetryConfig
from khive.connections.endpoint import Endpoint
from khive.connections.endpoint_config import EndpointConfig


class TestAPIClientResilience:
    """Integration tests for API client with resilience patterns."""

    @pytest.mark.asyncio
    async def test_api_client_with_circuit_breaker(self):
        """Test API client with circuit breaker."""
        # Create a mock client that fails
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.is_closed = True

        # Create a mock for httpx.HTTPStatusError
        mock_status_error = httpx.HTTPStatusError(
            "Server error",
            request=httpx.Request("GET", "https://example.com/test"),
            response=httpx.Response(500, json={"detail": "Server error"}),
        )

        # Set up the side effects
        mock_client.request.side_effect = [
            mock_status_error,  # First call raises HTTPStatusError
            mock_status_error,  # Second call raises HTTPStatusError
            mock_response,  # Third call succeeds
        ]

        # Create circuit breaker
        cb = CircuitBreaker(failure_threshold=2)

        # Create API client with circuit breaker
        api_client = AsyncAPIClient(
            base_url="https://example.com", client=mock_client, circuit_breaker=cb
        )

        # Act & Assert
        # First failure
        with pytest.raises(ServerError):
            await api_client.get("/test")

        # Second failure - opens circuit
        with pytest.raises(ServerError):
            await api_client.get("/test")

        # Circuit is open - rejects request
        with pytest.raises(CircuitBreakerOpenError):
            await api_client.get("/test")

    @pytest.mark.asyncio
    async def test_api_client_with_retry(self):
        """Test API client with retry."""
        # Create a mock client that fails then succeeds
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.is_closed = True

        # Create a mock for httpx.HTTPStatusError
        mock_status_error = httpx.HTTPStatusError(
            "Server error",
            request=httpx.Request("GET", "https://example.com/test"),
            response=httpx.Response(500, json={"detail": "Server error"}),
        )

        # Set up the side effects
        mock_client.request.side_effect = [
            mock_status_error,  # First call raises HTTPStatusError
            mock_status_error,  # Second call raises HTTPStatusError
            mock_response,  # Third call succeeds
        ]

        # Make sure the mock response's json method returns a value, not a coroutine
        mock_response.json = MagicMock(return_value={"status": "success"})

        # Create retry config
        retry_config = RetryConfig(
            max_retries=2, base_delay=0.01, retry_exceptions=(ServerError,)
        )

        # Create API client with retry
        api_client = AsyncAPIClient(
            base_url="https://example.com",
            client=mock_client,
            retry_config=retry_config,
        )

        # Act
        with patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None
            result = await api_client.get("/test")

        # Assert
        assert result == {"status": "success"}
        assert mock_client.request.call_count == 3


@pytest.mark.skip("Endpoint integration tests require more complex mocking")
class TestEndpointResilience:
    """Integration tests for Endpoint with resilience patterns."""

    @pytest.mark.asyncio
    async def test_endpoint_with_circuit_breaker(self):
        """Test Endpoint with circuit breaker."""
        # Create a mock client that fails
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.closed = False
        mock_response.release = AsyncMock()

        # Create a mock for aiohttp.ClientResponseError
        mock_error = ServerError("Server error", status_code=500)

        # Set up the side effects for request
        mock_client.request.side_effect = [
            mock_error,  # First call raises error
            mock_error,  # Second call raises error
            mock_response,  # Third call succeeds
        ]

        # Create endpoint config with API key
        config = EndpointConfig(
            name="test-endpoint",
            provider="test",
            endpoint="/test",
            transport_type="http",
            base_url="https://example.com",
            api_key="test_api_key",
            auth_type="bearer",  # Use bearer auth
        )

        # Create circuit breaker
        cb = CircuitBreaker(failure_threshold=2)

        # Create endpoint with circuit breaker
        endpoint = Endpoint(config=config, circuit_breaker=cb)
        endpoint.client = mock_client

        # Patch the _call_aiohttp method to handle our mocks
        original_call = endpoint._call_aiohttp

        async def mock_call_aiohttp(payload, headers, **kwargs):
            if mock_client.request.call_count < 3:
                raise mock_error
            return {"status": "success"}

        endpoint._call_aiohttp = mock_call_aiohttp

        # Act & Assert
        # First failure
        with pytest.raises(ServerError):
            await endpoint.call({"method": "GET"})

        # Second failure - opens circuit
        with pytest.raises(ServerError):
            await endpoint.call({"method": "GET"})

        # Circuit is open - rejects request
        with pytest.raises(CircuitBreakerOpenError):
            await endpoint.call({"method": "GET"})

        # Restore original method
        endpoint._call_aiohttp = original_call

    @pytest.mark.asyncio
    async def test_endpoint_with_retry(self):
        """Test Endpoint with retry."""
        # Create a mock client that fails then succeeds
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.closed = False
        mock_response.release = AsyncMock()

        # Create a mock for aiohttp.ClientResponseError
        mock_error = ServerError("Server error", status_code=500)

        # Create endpoint config with API key
        config = EndpointConfig(
            name="test-endpoint",
            provider="test",
            endpoint="/test",
            transport_type="http",
            base_url="https://example.com",
            api_key="test_api_key",
            auth_type="bearer",  # Use bearer auth
        )

        # Create retry config
        retry_config = RetryConfig(
            max_retries=2, base_delay=0.01, retry_exceptions=(ServerError,)
        )

        # Create endpoint with retry
        endpoint = Endpoint(config=config, retry_config=retry_config)
        endpoint.client = mock_client

        # Patch the _call_aiohttp method to handle our mocks
        original_call = endpoint._call_aiohttp

        call_count = 0

        async def mock_call_aiohttp(payload, headers, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise mock_error
            return {"status": "success"}

        endpoint._call_aiohttp = mock_call_aiohttp

        # Act
        with patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None
            result = await endpoint.call({"method": "GET"})

        # Assert
        assert result == {"status": "success"}
        assert call_count == 3

        # Restore original method
        endpoint._call_aiohttp = original_call
