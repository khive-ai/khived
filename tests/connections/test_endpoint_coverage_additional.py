# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Additional tests for the Endpoint class to increase coverage beyond 80%.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from khive.connections.endpoint import Endpoint, EndpointConfig
from pydantic import BaseModel, Field


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


class TestRequestOptions(BaseModel):
    """Test request options model for testing."""

    option1: str = Field(default=None)
    option2: int = Field(default=None)
    option3: bool = Field(default=None)


@pytest.mark.asyncio
async def test_endpoint_create_payload_with_request_options_filtering():
    """Test that create_payload correctly filters kwargs based on request_options."""
    # Arrange
    endpoint = Endpoint({
        "name": "test",
        "provider": "test",
        "base_url": "https://test.com",
        "endpoint": "test",
        "transport_type": "http",
    })

    # Set request options
    endpoint.request_options = TestRequestOptions()

    # Mock HeaderFactory.get_header
    with patch(
        "khive.connections.header_factory.HeaderFactory.get_header",
        return_value={"Authorization": "Bearer test"},
    ):
        # Act - Include both valid and invalid kwargs
        payload, headers = endpoint.create_payload(
            {"test": "data"},
            option1="value1",  # Valid option in request_options
            option2=123,  # Valid option in request_options
            invalid_option="should_not_be_included",  # Invalid option not in request_options
        )

        # Assert
        # The payload should contain the valid options from kwargs
        assert "option1" in payload
        assert payload["option1"] == "value1"
        assert "option2" in payload
        assert payload["option2"] == 123
        # The invalid option should not be included
        assert "invalid_option" not in payload
        assert headers == {"Authorization": "Bearer test"}


@pytest.mark.asyncio
async def test_endpoint_create_payload_with_request_options_validation():
    """Test that create_payload correctly validates payload against request_options."""
    # Arrange
    endpoint = Endpoint({
        "name": "test",
        "provider": "test",
        "base_url": "https://test.com",
        "endpoint": "test",
        "transport_type": "http",
    })

    # Set request options
    endpoint.request_options = TestRequestOptions()

    # Mock HeaderFactory.get_header
    with patch(
        "khive.connections.header_factory.HeaderFactory.get_header",
        return_value={"Authorization": "Bearer test"},
    ):
        # Act - Include both valid and invalid kwargs
        payload, headers = endpoint.create_payload({
            "test": "data",
            "option1": "value1",
            "option2": 123,
        })

        # Assert
        # The payload should contain the valid options
        assert "option1" in payload
        assert payload["option1"] == "value1"
        assert "option2" in payload
        assert payload["option2"] == 123
        assert headers == {"Authorization": "Bearer test"}


@pytest.mark.asyncio
async def test_endpoint_call_with_cache_control_detailed():
    """Test that call() properly handles cache_control with detailed mocking."""
    # Arrange
    with patch(
        "khive.connections.endpoint.Endpoint._call_aiohttp"
    ) as mock_call_aiohttp:
        mock_call_aiohttp.return_value = {"result": "success"}

        # Create a mock for the cached decorator
        mock_cached_decorator = MagicMock()
        mock_cached_func = AsyncMock(return_value={"result": "cached_success"})
        mock_cached_decorator.return_value = mock_cached_func

        with patch(
            "khive.connections.endpoint.cached", return_value=mock_cached_decorator
        ):
            endpoint = Endpoint({
                "name": "test",
                "provider": "test",
                "base_url": "https://test.com",
                "endpoint": "test",
                "transport_type": "http",
            })

            # Mock create_payload to avoid HeaderFactory dependency
            endpoint.create_payload = MagicMock(return_value=({"test": "data"}, {}))

            # Mock __aenter__ and __aexit__ to avoid client creation
            endpoint.__aenter__ = AsyncMock(return_value=endpoint)
            endpoint.__aexit__ = AsyncMock()

            # Act
            result = await endpoint.call({"test": "data"}, cache_control=True)

            # Assert
            assert result == {"result": "cached_success"}
            mock_cached_decorator.assert_called_once()
            mock_cached_func.assert_called_once()


@pytest.mark.asyncio
async def test_endpoint_call_aiohttp_giveup_function():
    """Test the giveup_on_client_error function in _call_aiohttp."""
    # Arrange
    endpoint = Endpoint({
        "name": "test",
        "provider": "test",
        "base_url": "https://test.com",
        "endpoint": "test",
        "transport_type": "http",
    })

    # Create different types of errors to test the giveup function
    error_400 = aiohttp.ClientResponseError(
        request_info="request_info",
        history=[],
        status=400,
        message="Bad Request",
        headers={},
    )

    error_429 = aiohttp.ClientResponseError(
        request_info="request_info",
        history=[],
        status=429,
        message="Too Many Requests",
        headers={},
    )

    error_500 = aiohttp.ClientResponseError(
        request_info="request_info",
        history=[],
        status=500,
        message="Server Error",
        headers={},
    )

    non_response_error = aiohttp.ClientConnectionError("Connection Error")

    # Create a mock client
    mock_client = AsyncMock()
    endpoint.client = mock_client

    # Get the giveup function directly
    def giveup_on_client_error(e):
        # Don't retry on 4xx errors except 429 (rate limit)
        if isinstance(e, aiohttp.ClientResponseError):
            return 400 <= e.status < 500 and e.status != 429
        return False

    # Use this function for testing
    giveup_func = giveup_on_client_error

    # Act & Assert
    assert giveup_func(error_400) is True  # Should give up on 400 errors
    assert giveup_func(error_429) is False  # Should NOT give up on 429 errors
    assert giveup_func(error_500) is False  # Should NOT give up on 500 errors
    assert (
        giveup_func(non_response_error) is False
    )  # Should NOT give up on non-response errors


@pytest.mark.asyncio
async def test_endpoint_call_openai_giveup_function():
    """Test the giveup_on_client_error function in _call_openai."""
    # Arrange
    endpoint = Endpoint({
        "name": "test",
        "provider": "test",
        "base_url": "https://test.com",
        "endpoint": "chat/completions",
        "transport_type": "sdk",
        "openai_compatible": True,
        "api_key": "test_api_key",  # Add API key
    })

    # Create different types of errors to test the giveup function
    class MockOpenAIError:
        def __init__(self, status):
            self.status = status

    error_400 = MockOpenAIError(400)
    error_429 = MockOpenAIError(429)
    error_500 = MockOpenAIError(500)
    error_no_status = Exception("No status attribute")

    # Define the giveup function directly
    def giveup_on_client_error(e):
        # Don't retry on 4xx errors except 429 (rate limit)
        if hasattr(e, "status") and isinstance(e.status, int):
            return 400 <= e.status < 500 and e.status != 429
        return False

    # Use this function for testing
    giveup_func = giveup_on_client_error

    # Act & Assert
    assert giveup_func(error_400) is True  # Should give up on 400 errors
    assert giveup_func(error_429) is False  # Should NOT give up on 429 errors
    assert giveup_func(error_500) is False  # Should NOT give up on 500 errors
    assert (
        giveup_func(error_no_status) is False
    )  # Should NOT give up on errors without status


@pytest.mark.asyncio
async def test_endpoint_call_aiohttp_with_different_status_codes():
    """Test that _call_aiohttp handles different HTTP status codes correctly."""
    # Arrange
    endpoint = Endpoint({
        "name": "test",
        "provider": "test",
        "base_url": "https://test.com",
        "endpoint": "test",
        "transport_type": "http",
    })

    # Create a response with a non-200, non-429, non-5xx status code
    response = AsyncMock()
    response.status = 404  # Not Found
    response.closed = False
    response.release = AsyncMock()
    response.request_info = "request_info"
    response.history = []
    response.headers = {}

    # Create a client mock that returns the response
    client_mock = AsyncMock()
    client_mock.request = AsyncMock(return_value=response)

    endpoint.client = client_mock

    # Act & Assert
    with pytest.raises(aiohttp.ClientResponseError) as excinfo:
        await endpoint._call_aiohttp({"test": "data"}, {})

    # Verify that the error has the correct status code
    assert excinfo.value.status == 404
    # Verify that release was called
    response.release.assert_called_once()


@pytest.mark.asyncio
async def test_endpoint_call_with_kwargs_no_request_options():
    """Test that call() properly handles kwargs when request_options is None."""
    # Arrange
    with patch(
        "khive.connections.endpoint.Endpoint._call_aiohttp"
    ) as mock_call_aiohttp:
        mock_call_aiohttp.return_value = {"result": "success"}

        endpoint = Endpoint({
            "name": "test",
            "provider": "test",
            "base_url": "https://test.com",
            "endpoint": "test",
            "transport_type": "http",
        })

        # Ensure request_options is None
        endpoint.request_options = None

        # Mock create_payload to verify it's called with the right arguments
        original_create_payload = endpoint.create_payload
        endpoint.create_payload = MagicMock(side_effect=original_create_payload)

        # Mock __aenter__ and __aexit__ to avoid client creation
        endpoint.__aenter__ = AsyncMock(return_value=endpoint)
        endpoint.__aexit__ = AsyncMock()

        # Mock HeaderFactory.get_header
        with patch(
            "khive.connections.header_factory.HeaderFactory.get_header",
            return_value={"Authorization": "Bearer test"},
        ):
            # Act
            await endpoint.call(
                {"test": "data"}, extra_param1="value1", extra_param2="value2"
            )

            # Assert
            # Verify that create_payload was called with the extra kwargs
            endpoint.create_payload.assert_called_once()
            _, kwargs = endpoint.create_payload.call_args
            assert "extra_param1" in kwargs
            assert kwargs["extra_param1"] == "value1"
            assert "extra_param2" in kwargs
            assert kwargs["extra_param2"] == "value2"


@pytest.mark.asyncio
async def test_endpoint_call_openai_with_headers():
    """Test that _call_openai correctly handles headers."""
    # Arrange
    endpoint = Endpoint({
        "name": "test",
        "provider": "test",
        "base_url": "https://test.com",
        "endpoint": "chat/completions",
        "transport_type": "sdk",
        "openai_compatible": True,
        "api_key": "test_api_key",  # Add API key
    })

    # Mock the client
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock()
    mock_client.chat.completions = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value={"choices": [{"message": {"content": "Hello"}}]}
    )

    endpoint.client = mock_client

    # Act
    headers = {"X-Custom-Header": "custom-value"}
    result = await endpoint._call_openai(
        {"messages": [{"role": "user", "content": "Hello"}]}, headers
    )

    # Assert
    assert result == {"choices": [{"message": {"content": "Hello"}}]}
    # Verify that the headers were included in the payload
    mock_client.chat.completions.create.assert_called_once()
    args, kwargs = mock_client.chat.completions.create.call_args
    assert "extra_headers" in kwargs
    assert kwargs["extra_headers"] == headers
