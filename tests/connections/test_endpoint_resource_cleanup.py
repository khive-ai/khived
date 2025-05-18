# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for async resource cleanup in the Endpoint class.

This module tests the proper implementation of async context manager
protocol and resource cleanup in the Endpoint class.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from khive.connections.endpoint import Endpoint, EndpointConfig
from khive.utils import is_package_installed


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


@pytest.fixture
def mock_sdk_client():
    """Create a mock SDK client for testing."""
    client = AsyncMock()
    client.chat = AsyncMock()
    client.chat.completions = AsyncMock()
    client.chat.completions.create = AsyncMock(
        return_value={"choices": [{"message": {"content": "Hello"}}]}
    )
    client.close = AsyncMock()
    return client


@pytest.fixture
def http_endpoint_config():
    """Create an HTTP endpoint config for testing."""
    return EndpointConfig(
        name="test_http",
        provider="test",
        base_url="https://test.com",
        endpoint="test",
        transport_type="http",
    )


@pytest.fixture
def sdk_endpoint_config():
    """Create an SDK endpoint config for testing."""
    return EndpointConfig(
        name="test_sdk",
        provider="test",
        base_url="https://test.com",
        endpoint="chat/completions",
        transport_type="sdk",
        openai_compatible=True,
        api_key="test",
    )


@pytest.mark.asyncio
async def test_endpoint_aenter_http_client(monkeypatch, mock_http_client, http_endpoint_config):
    """Test that __aenter__ properly initializes the HTTP client."""
    # Arrange
    monkeypatch.setattr("aiohttp.ClientSession", lambda **kwargs: mock_http_client)
    endpoint = Endpoint(http_endpoint_config)
    
    # Act
    result = await endpoint.__aenter__()
    
    # Assert
    assert result is endpoint
    assert endpoint.client is mock_http_client


@pytest.mark.asyncio
async def test_endpoint_aexit_http_client(monkeypatch, mock_http_client, http_endpoint_config):
    """Test that __aexit__ properly closes the HTTP client."""
    # Arrange
    monkeypatch.setattr("aiohttp.ClientSession", lambda **kwargs: mock_http_client)
    endpoint = Endpoint(http_endpoint_config)
    await endpoint.__aenter__()
    
    # Act
    await endpoint.__aexit__(None, None, None)
    
    # Assert
    mock_http_client.close.assert_called_once()
    assert endpoint.client is None


@pytest.mark.asyncio
@pytest.mark.skipif(not is_package_installed("openai"), reason="OpenAI SDK not installed")
async def test_endpoint_aexit_sdk_client(monkeypatch, mock_sdk_client, sdk_endpoint_config):
    """Test that __aexit__ properly closes the SDK client if it has a close method."""
    # Arrange
    monkeypatch.setattr("khive.connections.endpoint._HAS_OPENAI", True)
    monkeypatch.setattr("openai.AsyncOpenAI", lambda **kwargs: mock_sdk_client)
    endpoint = Endpoint(sdk_endpoint_config)
    await endpoint.__aenter__()
    
    # Act
    await endpoint.__aexit__(None, None, None)
    
    # Assert
    mock_sdk_client.close.assert_called_once()
    assert endpoint.client is None


@pytest.mark.asyncio
async def test_endpoint_aexit_with_exception(monkeypatch, mock_http_client, http_endpoint_config):
    """Test that __aexit__ properly closes the client even if an exception occurs."""
    # Arrange
    monkeypatch.setattr("aiohttp.ClientSession", lambda **kwargs: mock_http_client)
    endpoint = Endpoint(http_endpoint_config)
    await endpoint.__aenter__()
    
    # Act
    await endpoint.__aexit__(Exception, Exception("Test exception"), None)
    
    # Assert
    mock_http_client.close.assert_called_once()
    assert endpoint.client is None


@pytest.mark.asyncio
async def test_endpoint_aclose(monkeypatch, mock_http_client, http_endpoint_config):
    """Test that aclose() properly closes the client."""
    # Arrange
    monkeypatch.setattr("aiohttp.ClientSession", lambda **kwargs: mock_http_client)
    endpoint = Endpoint(http_endpoint_config)
    await endpoint.__aenter__()
    
    # Act
    await endpoint.aclose()
    
    # Assert
    mock_http_client.close.assert_called_once()
    assert endpoint.client is None


@pytest.mark.asyncio
@pytest.mark.skipif(not is_package_installed("openai"), reason="OpenAI SDK not installed")
async def test_endpoint_aclose_sdk_client(monkeypatch, mock_sdk_client, sdk_endpoint_config):
    """Test that aclose() properly closes the SDK client if it has a close method."""
    # Arrange
    monkeypatch.setattr("khive.connections.endpoint._HAS_OPENAI", True)
    monkeypatch.setattr("openai.AsyncOpenAI", lambda **kwargs: mock_sdk_client)
    endpoint = Endpoint(sdk_endpoint_config)
    await endpoint.__aenter__()
    
    # Act
    await endpoint.aclose()
    
    # Assert
    mock_sdk_client.close.assert_called_once()
    assert endpoint.client is None


@pytest.mark.asyncio
async def test_endpoint_aclose_no_client(http_endpoint_config):
    """Test that aclose() handles the case where client is None."""
    # Arrange
    endpoint = Endpoint(http_endpoint_config)
    assert endpoint.client is None
    
    # Act & Assert - should not raise an exception
    await endpoint.aclose()
    assert endpoint.client is None


@pytest.mark.asyncio
async def test_endpoint_close_client_error(monkeypatch, mock_http_client, http_endpoint_config):
    """Test that _close_client handles errors during client close."""
    # Arrange
    monkeypatch.setattr("aiohttp.ClientSession", lambda **kwargs: mock_http_client)
    mock_http_client.close.side_effect = Exception("Close error")
    endpoint = Endpoint(http_endpoint_config)
    await endpoint.__aenter__()
    
    # Act - should not raise an exception
    await endpoint.aclose()
    
    # Assert
    mock_http_client.close.assert_called_once()
    assert endpoint.client is None


@pytest.mark.asyncio
async def test_endpoint_as_context_manager(monkeypatch, mock_http_client, http_endpoint_config):
    """Test that Endpoint can be used as an async context manager."""
    # Arrange
    monkeypatch.setattr("aiohttp.ClientSession", lambda **kwargs: mock_http_client)
    # Mock the HeaderFactory.get_header to avoid API key requirement
    monkeypatch.setattr(
        "khive.connections.header_factory.HeaderFactory.get_header",
        lambda **kwargs: {"Authorization": "Bearer test", "Content-Type": "application/json"}
    )
    
    # Act
    async with Endpoint(http_endpoint_config) as endpoint:
        # Simulate some work
        await endpoint.call({"test": "data"})
    
    # Assert
    mock_http_client.close.assert_called_once()
    assert endpoint.client is None


@pytest.mark.asyncio
async def test_endpoint_as_context_manager_with_exception(
    monkeypatch, mock_http_client, http_endpoint_config
):
    """Test that Endpoint properly cleans up resources when an exception occurs."""
    # Arrange
    monkeypatch.setattr("aiohttp.ClientSession", lambda **kwargs: mock_http_client)
    
    # Act & Assert
    with pytest.raises(Exception, match="Test exception"):
        async with Endpoint(http_endpoint_config) as endpoint:
            # Simulate an exception
            raise Exception("Test exception")
    
    # Assert
    mock_http_client.close.assert_called_once()
    assert endpoint.client is None


@pytest.mark.asyncio
@pytest.mark.skipif(not is_package_installed("openai"), reason="OpenAI SDK not installed")
async def test_endpoint_sdk_client_with_sync_close(monkeypatch, sdk_endpoint_config):
    """Test that _close_client handles SDK clients with synchronous close methods."""
    # Arrange
    mock_sdk_client = MagicMock()
    mock_sdk_client.close = MagicMock()  # Synchronous close method
    
    monkeypatch.setattr("khive.connections.endpoint._HAS_OPENAI", True)
    monkeypatch.setattr("openai.AsyncOpenAI", lambda **kwargs: mock_sdk_client)
    
    endpoint = Endpoint(sdk_endpoint_config)
    await endpoint.__aenter__()
    
    # Act
    await endpoint.aclose()
    
    # Assert
    mock_sdk_client.close.assert_called_once()
    assert endpoint.client is None