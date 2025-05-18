# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the AsyncAPIClient class.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from khive.clients.api_client import AsyncAPIClient
from khive.clients.errors import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
    ResourceNotFoundError,
    ServerError,
)


@pytest.mark.asyncio
async def test_async_api_client_init():
    """Test that AsyncAPIClient initializes correctly."""
    # Arrange
    base_url = "https://api.example.com"
    timeout = 10.0
    headers = {"User-Agent": "Test"}

    # Act
    client = AsyncAPIClient(base_url=base_url, timeout=timeout, headers=headers)

    # Assert
    assert client.base_url == base_url
    assert client.timeout == timeout
    assert client.headers == headers
    assert client._client is None
    assert client._closed is False


@pytest.mark.asyncio
async def test_async_api_client_context_manager():
    """Test that AsyncAPIClient context manager works correctly."""
    # Arrange
    base_url = "https://api.example.com"
    mock_session = AsyncMock(spec=httpx.AsyncClient)

    # Act & Assert
    with patch("httpx.AsyncClient", return_value=mock_session):
        async with AsyncAPIClient(base_url=base_url) as client:
            # Assert client was initialized correctly
            assert client.base_url == base_url
            assert client._client is not None

        # Assert session was closed
        mock_session.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_async_api_client_get():
    """Test that get method works correctly."""
    # Arrange
    base_url = "https://api.example.com"
    mock_session = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": "test"}
    mock_session.request.return_value = mock_response

    # Act
    with patch("httpx.AsyncClient", return_value=mock_session):
        async with AsyncAPIClient(base_url=base_url) as client:
            result = await client.get("/test", params={"key": "value"})

    # Assert
    mock_session.request.assert_called_once_with(
        "GET", "/test", params={"key": "value"}
    )
    assert result == {"data": "test"}


@pytest.mark.asyncio
async def test_async_api_client_post():
    """Test that post method works correctly."""
    # Arrange
    base_url = "https://api.example.com"
    mock_session = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": "test"}
    mock_session.request.return_value = mock_response

    # Act
    with patch("httpx.AsyncClient", return_value=mock_session):
        async with AsyncAPIClient(base_url=base_url) as client:
            result = await client.post("/test", json={"key": "value"})

    # Assert
    mock_session.request.assert_called_once_with(
        "POST", "/test", json={"key": "value"}, data=None
    )
    assert result == {"data": "test"}


@pytest.mark.asyncio
async def test_async_api_client_connection_error():
    """Test that connection errors are handled correctly."""
    # Arrange
    base_url = "https://api.example.com"
    mock_session = AsyncMock(spec=httpx.AsyncClient)
    mock_session.request.side_effect = httpx.ConnectError("Connection failed")

    # Act & Assert
    with patch("httpx.AsyncClient", return_value=mock_session):
        async with AsyncAPIClient(base_url=base_url) as client:
            with pytest.raises(APIConnectionError) as excinfo:
                await client.get("/test")

    # Assert
    assert "Connection error: Connection failed" in str(excinfo.value)


@pytest.mark.asyncio
async def test_async_api_client_timeout_error():
    """Test that timeout errors are handled correctly."""
    # Arrange
    base_url = "https://api.example.com"
    mock_session = AsyncMock(spec=httpx.AsyncClient)
    mock_session.request.side_effect = httpx.TimeoutException("Request timed out")

    # Act & Assert
    with patch("httpx.AsyncClient", return_value=mock_session):
        async with AsyncAPIClient(base_url=base_url) as client:
            with pytest.raises(APITimeoutError) as excinfo:
                await client.get("/test")

    # Assert
    assert "Request timed out" in str(excinfo.value)


@pytest.mark.asyncio
async def test_async_api_client_rate_limit_error():
    """Test that rate limit errors are handled correctly."""
    # Arrange
    base_url = "https://api.example.com"
    mock_session = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.json.return_value = {"detail": "Rate limit exceeded"}
    mock_response.headers = {"Retry-After": "60"}
    mock_response.text = "Rate limit exceeded"

    mock_request_info = MagicMock()
    mock_request_info.url = httpx.URL(base_url + "/test")
    mock_request_info.method = "GET"

    mock_error = httpx.HTTPStatusError(
        "429 Too Many Requests", request=mock_request_info, response=mock_response
    )
    mock_session.request.side_effect = mock_error

    # Act & Assert
    with patch("httpx.AsyncClient", return_value=mock_session):
        async with AsyncAPIClient(base_url=base_url) as client:
            with pytest.raises(RateLimitError) as excinfo:
                await client.get("/test")

    # Assert
    assert "Rate limit exceeded" in str(excinfo.value)
    assert excinfo.value.status_code == 429
    assert excinfo.value.retry_after == 60.0


@pytest.mark.asyncio
async def test_async_api_client_authentication_error():
    """Test that authentication errors are handled correctly."""
    # Arrange
    base_url = "https://api.example.com"
    mock_session = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {"detail": "Invalid credentials"}
    mock_response.text = "Invalid credentials"

    mock_request_info = MagicMock()
    mock_request_info.url = httpx.URL(base_url + "/test")
    mock_request_info.method = "GET"

    mock_error = httpx.HTTPStatusError(
        "401 Unauthorized", request=mock_request_info, response=mock_response
    )
    mock_session.request.side_effect = mock_error

    # Act & Assert
    with patch("httpx.AsyncClient", return_value=mock_session):
        async with AsyncAPIClient(base_url=base_url) as client:
            with pytest.raises(AuthenticationError) as excinfo:
                await client.get("/test")

    # Assert
    assert "Invalid credentials" in str(excinfo.value)
    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_async_api_client_resource_not_found_error():
    """Test that resource not found errors are handled correctly."""
    # Arrange
    base_url = "https://api.example.com"
    mock_session = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {"detail": "Resource not found"}
    mock_response.text = "Resource not found"

    mock_request_info = MagicMock()
    mock_request_info.url = httpx.URL(base_url + "/test")
    mock_request_info.method = "GET"

    mock_error = httpx.HTTPStatusError(
        "404 Not Found", request=mock_request_info, response=mock_response
    )
    mock_session.request.side_effect = mock_error

    # Act & Assert
    with patch("httpx.AsyncClient", return_value=mock_session):
        async with AsyncAPIClient(base_url=base_url) as client:
            with pytest.raises(ResourceNotFoundError) as excinfo:
                await client.get("/test")

    # Assert
    assert "Resource not found" in str(excinfo.value)
    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_async_api_client_server_error():
    """Test that server errors are handled correctly."""
    # Arrange
    base_url = "https://api.example.com"
    mock_session = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.json.return_value = {"detail": "Internal server error"}
    mock_response.text = "Internal server error"

    mock_request_info = MagicMock()
    mock_request_info.url = httpx.URL(base_url + "/test")
    mock_request_info.method = "GET"

    mock_error = httpx.HTTPStatusError(
        "500 Internal Server Error", request=mock_request_info, response=mock_response
    )
    mock_session.request.side_effect = mock_error

    # Act & Assert
    with patch("httpx.AsyncClient", return_value=mock_session):
        async with AsyncAPIClient(base_url=base_url) as client:
            with pytest.raises(ServerError) as excinfo:
                await client.get("/test")

    # Assert
    assert "Internal server error" in str(excinfo.value)
    assert excinfo.value.status_code == 500


@pytest.mark.asyncio
async def test_async_api_client_call_method():
    """Test that call method works correctly."""
    # Arrange
    base_url = "https://api.example.com"
    mock_session = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": "test"}
    mock_session.request.return_value = mock_response

    # Act
    with patch("httpx.AsyncClient", return_value=mock_session):
        async with AsyncAPIClient(base_url=base_url) as client:
            result = await client.call({
                "method": "POST",
                "url": "/test",
                "json": {"key": "value"},
                "headers": {"X-Test": "test"},
            })

    # Assert
    # The order of kwargs doesn't matter for the assertion, just check that it was called with the right parameters
    mock_session.request.assert_called_once()
    call_args = mock_session.request.call_args
    assert call_args[0] == ("POST", "/test")
    assert call_args[1]["json"] == {"key": "value"}
    assert call_args[1]["headers"] == {"X-Test": "test"}
    assert result == {"data": "test"}


@pytest.mark.asyncio
async def test_async_api_client_resource_cleanup_on_exception():
    """Test that resources are properly cleaned up when exceptions occur."""
    # Arrange
    base_url = "https://api.example.com"
    mock_session = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.is_closed = False
    mock_response.close = MagicMock()
    mock_session.request.side_effect = Exception("Test exception")

    # Act & Assert
    with patch("httpx.AsyncClient", return_value=mock_session):
        async with AsyncAPIClient(base_url=base_url) as client:
            # Patch the _get_client method to return the mock response
            with patch.object(client, "_get_client", return_value=mock_session):
                with patch.object(
                    client, "request", side_effect=ValueError("Test exception")
                ):
                    with pytest.raises(ValueError):
                        await client.get("/test")

    # Assert
    mock_session.aclose.assert_called_once()
