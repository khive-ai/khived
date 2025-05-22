# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for async resource cleanup across components.

This module tests the proper resource cleanup when multiple components
are used together in various scenarios.
"""

import asyncio
import gc
import weakref
from unittest.mock import AsyncMock

import pytest

from khive.clients.errors import TestError
from khive.clients.executor import AsyncExecutor, RateLimitedExecutor
from khive.connections.endpoint import Endpoint, EndpointConfig


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client for testing."""
    client = AsyncMock()
    client.close = AsyncMock()
    client.request = AsyncMock()
    client.request.return_value = AsyncMock()
    client.request.return_value.json = AsyncMock(return_value={"result": "success"})
    client.request.return_value.raise_for_status = AsyncMock()
    client.request.return_value.status = 200
    client.request.return_value.closed = False
    client.request.return_value.release = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_endpoint_with_executor_integration(monkeypatch, mock_http_client):
    """Test that Endpoint and Executor work together properly."""
    # Arrange
    monkeypatch.setattr("aiohttp.ClientSession", lambda **kwargs: mock_http_client)
    # Mock the HeaderFactory.get_header to avoid API key requirement
    monkeypatch.setattr(
        "khive.connections.header_factory.HeaderFactory.get_header",
        lambda **kwargs: {
            "Authorization": "Bearer test",
            "Content-Type": "application/json",
        },
    )

    executor = AsyncExecutor(max_concurrency=5)
    endpoint_config = EndpointConfig(
        name="test",
        provider="test",
        base_url="https://test.com",
        endpoint="test",
        transport_type="http",
        api_key="test_key",  # Add API key to config
    )

    # Act
    async with executor:
        async with Endpoint(endpoint_config) as endpoint:
            # Use the executor to call the endpoint
            await executor.execute(endpoint.call, {"test": "data"})

    # Assert
    mock_http_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_endpoint_with_rate_limited_executor_integration(
    monkeypatch, mock_http_client
):
    """Test that Endpoint and RateLimitedExecutor work together properly."""
    # Arrange
    monkeypatch.setattr("aiohttp.ClientSession", lambda **kwargs: mock_http_client)
    # Mock the HeaderFactory.get_header to avoid API key requirement
    monkeypatch.setattr(
        "khive.connections.header_factory.HeaderFactory.get_header",
        lambda **kwargs: {
            "Authorization": "Bearer test",
            "Content-Type": "application/json",
        },
    )

    executor = RateLimitedExecutor(rate=10, period=1.0, max_concurrency=5)
    endpoint_config = EndpointConfig(
        name="test",
        provider="test",
        base_url="https://test.com",
        endpoint="test",
        transport_type="http",
        api_key="test_key",  # Add API key to config
    )

    # Act
    async with executor:
        async with Endpoint(endpoint_config) as endpoint:
            # Use the rate-limited executor to call the endpoint
            await executor.execute(endpoint.call, {"test": "data"})

    # Assert
    mock_http_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_multiple_endpoints_with_executor(monkeypatch):
    """Test that multiple endpoints can be used with a single executor."""
    # Arrange
    # Create a list to track all created clients
    created_clients = []

    def get_mock_client(**kwargs):
        mock_client = AsyncMock()
        mock_client.close = AsyncMock()
        mock_client.request = AsyncMock()
        mock_client.request.return_value = AsyncMock()
        # Alternate between success1 and success2 for the response
        result = "success1" if len(created_clients) % 2 == 0 else "success2"
        mock_client.request.return_value.json = AsyncMock(
            return_value={"result": result}
        )
        mock_client.request.return_value.status = 200
        mock_client.request.return_value.closed = False
        mock_client.request.return_value.release = AsyncMock()
        created_clients.append(mock_client)
        return mock_client

    monkeypatch.setattr("aiohttp.ClientSession", get_mock_client)
    # Mock the HeaderFactory.get_header to avoid API key requirement
    monkeypatch.setattr(
        "khive.connections.header_factory.HeaderFactory.get_header",
        lambda **kwargs: {
            "Authorization": "Bearer test",
            "Content-Type": "application/json",
        },
    )

    executor = AsyncExecutor(max_concurrency=5)
    endpoint_config1 = EndpointConfig(
        name="test1",
        provider="test",
        base_url="https://test1.com",
        endpoint="test1",
        transport_type="http",
        api_key="test_key",  # Add API key to config
    )
    endpoint_config2 = EndpointConfig(
        name="test2",
        provider="test",
        base_url="https://test2.com",
        endpoint="test2",
        transport_type="http",
        api_key="test_key",  # Add API key to config
    )

    # Act
    async with executor:
        endpoint1 = Endpoint(endpoint_config1)
        endpoint2 = Endpoint(endpoint_config2)
        # Use the executor to call both endpoints
        results = await asyncio.gather(
            executor.execute(endpoint1.call, {"test": "data1"}),
            executor.execute(endpoint2.call, {"test": "data2"}),
        )

    # Assert
    # Verify that all clients were closed
    for client in created_clients:
        client.close.assert_called_once()

    # Verify the results
    assert results[0]["result"] in ["success1", "success2"]
    assert results[1]["result"] in ["success1", "success2"]


@pytest.mark.asyncio
async def test_resource_cleanup_with_exception(monkeypatch, mock_http_client):
    """Test that resources are properly cleaned up when an exception occurs."""
    # Arrange
    monkeypatch.setattr("aiohttp.ClientSession", lambda **kwargs: mock_http_client)

    executor = AsyncExecutor(max_concurrency=5)
    endpoint_config = EndpointConfig(
        name="test",
        provider="test",
        base_url="https://test.com",
        endpoint="test",
        transport_type="http",
    )

    # Act & Assert
    with pytest.raises(TestError, match="Test exception"):
        async with executor:
            async with Endpoint(endpoint_config) as endpoint:
                # Simulate an exception
                raise TestError("Test exception")

    # Assert
    mock_http_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_resource_cleanup_under_load(monkeypatch):
    """Test that resources are properly cleaned up under load."""
    # Arrange
    num_iterations = 10
    created_clients = []

    def get_mock_client(**kwargs):
        mock_client = AsyncMock()
        mock_client.close = AsyncMock()
        mock_client.request = AsyncMock()
        mock_client.request.return_value = AsyncMock()
        mock_client.request.return_value.json = AsyncMock(
            return_value={"result": "success"}
        )
        mock_client.request.return_value.status = 200
        mock_client.request.return_value.closed = False
        mock_client.request.return_value.release = AsyncMock()
        created_clients.append(mock_client)
        return mock_client

    monkeypatch.setattr("aiohttp.ClientSession", get_mock_client)
    # Mock the HeaderFactory.get_header to avoid API key requirement
    monkeypatch.setattr(
        "khive.connections.header_factory.HeaderFactory.get_header",
        lambda **kwargs: {
            "Authorization": "Bearer test",
            "Content-Type": "application/json",
        },
    )

    async def create_and_use_endpoint():
        endpoint_config = EndpointConfig(
            name="test",
            provider="test",
            base_url="https://test.com",
            endpoint="test",
            transport_type="http",
            api_key="test_key",  # Add API key to config
        )

        # Don't use context manager here, as call() creates its own client
        endpoint = Endpoint(endpoint_config)
        await endpoint.call({"test": "data"})

    # Act
    executor = AsyncExecutor(max_concurrency=5)
    async with executor:
        tasks = [
            executor.execute(create_and_use_endpoint) for _ in range(num_iterations)
        ]
        await asyncio.gather(*tasks)

    # Assert
    # Each call to endpoint.call() creates a new client
    assert len(created_clients) == num_iterations
    for client in created_clients:
        client.close.assert_called_once()


@pytest.mark.asyncio
async def test_no_resource_leaks(monkeypatch):
    """Test that no resources are leaked after cleanup."""
    # Arrange
    mock_client = AsyncMock()
    mock_client.close = AsyncMock()
    mock_client.request = AsyncMock()
    mock_client.request.return_value = AsyncMock()
    mock_client.request.return_value.json = AsyncMock(
        return_value={"result": "success"}
    )
    mock_client.request.return_value.status = 200
    mock_client.request.return_value.closed = False
    mock_client.request.return_value.release = AsyncMock()
    monkeypatch.setattr("aiohttp.ClientSession", lambda **kwargs: mock_client)
    # Mock the HeaderFactory.get_header to avoid API key requirement
    monkeypatch.setattr(
        "khive.connections.header_factory.HeaderFactory.get_header",
        lambda **kwargs: {
            "Authorization": "Bearer test",
            "Content-Type": "application/json",
        },
    )

    # Create a weak reference to track if the endpoint is garbage collected
    endpoint = None
    endpoint_ref = None

    # Act
    async def create_and_use_endpoint():
        nonlocal endpoint, endpoint_ref
        endpoint_config = EndpointConfig(
            name="test",
            provider="test",
            base_url="https://test.com",
            endpoint="test",
            transport_type="http",
            api_key="test_key",  # Add API key to config
        )

        endpoint = Endpoint(endpoint_config)
        endpoint_ref = weakref.ref(endpoint)

        async with endpoint:
            await endpoint.call({"test": "data"})

    await create_and_use_endpoint()

    # Remove the strong reference to the endpoint
    endpoint = None

    # Force garbage collection
    gc.collect()

    # Assert
    assert endpoint_ref() is None, "Endpoint was not garbage collected"
    mock_client.close.assert_called_once()
