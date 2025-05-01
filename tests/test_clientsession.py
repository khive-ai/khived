from unittest.mock import MagicMock, patch

import aiohttp
import pytest

from khive.services.endpoint import Endpoint, EndpointConfig
from khive.services.providers.oai_compatible import OpenaiChatEndpoint


@pytest.mark.asyncio
@pytest.mark.integration  # Mark as integration test since it tests actual client behavior
async def test_aiohttp_session_reuse():
    """Test that the aiohttp ClientSession is reused across multiple calls."""
    # Create a simple endpoint config
    config = EndpointConfig(
        name="test",
        provider="test",
        base_url="http://example.com",
        endpoint="test",
        request_options=None,
        api_key="test-key",
    )

    # Create endpoint
    endpoint = Endpoint(config)

    # Initialize client
    await endpoint.__aenter__()

    # Create a proper mock for aiohttp response
    mock_response = MagicMock()
    mock_response.__aenter__ = MagicMock(return_value=mock_response)
    mock_response.__aexit__ = MagicMock(return_value=None)
    mock_response.status = 200
    mock_response.json = MagicMock(return_value={"result": "success"})
    mock_response.closed = False
    mock_response.release = MagicMock(return_value=None)

    # Save original request method
    original_request = endpoint.client.request

    # Replace with our mock
    endpoint.client.request = MagicMock(return_value=mock_response)

    # Make multiple calls
    for _ in range(3):
        result = await endpoint._call_aiohttp({}, {})
        assert result == {"result": "success"}

    # Check that request was called multiple times
    assert endpoint.client.request.call_count == 3

    # Check that client is still not closed
    assert not endpoint.client.closed

    # Restore original request method
    endpoint.client.request = original_request

    # Close client
    await endpoint.aclose()

    # Check that client is closed
    assert endpoint.client.closed


@pytest.mark.asyncio
@pytest.mark.integration  # Mark as integration test since it depends on openai package
async def test_openai_client_lifecycle():
    """Test that the OpenAI client is properly initialized and doesn't need explicit closing."""
    # Skip if openai package is not installed
    pytest.importorskip("openai")

    # Create a mock AsyncOpenAI client
    mock_client = MagicMock()

    # Patch the AsyncOpenAI constructor
    with patch("openai.AsyncOpenAI", return_value=mock_client):
        # Create an OpenAI endpoint
        endpoint = OpenaiChatEndpoint(api_key="test-key")

        # Initialize client
        await endpoint.__aenter__()

        # Check that AsyncOpenAI was called with the right arguments
        from openai import AsyncOpenAI

        AsyncOpenAI.assert_called_once()

        # Exit context
        await endpoint.__aexit__(None, None, None)

        # No close method should be called on the OpenAI client
        assert not hasattr(mock_client, "close") or not mock_client.close.called


@pytest.mark.asyncio
@pytest.mark.integration  # Mark as integration test since it tests actual client behavior
async def test_aclose_method():
    """Test that the aclose method properly closes the client."""
    # Create a simple endpoint config
    config = EndpointConfig(
        name="test",
        provider="test",
        base_url="http://example.com",
        endpoint="test",
        request_options=None,
        api_key="test-key",
    )

    # Create endpoint
    endpoint = Endpoint(config)

    # Initialize client
    await endpoint.__aenter__()

    # Check that client is initialized
    assert endpoint.client is not None

    # Check that client is not closed
    assert not endpoint.client.closed

    # Call aclose
    await endpoint.aclose()

    # Check that client is closed
    assert endpoint.client.closed

    # Call aclose again (should not raise an error)
    await endpoint.aclose()
