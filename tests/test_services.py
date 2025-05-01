from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from khive.config import settings
from khive.services.endpoint import Endpoint, EndpointConfig
from khive.services.providers.oai_compatible import (
    DUMMY_OLLAMA_API_KEY,
    OllamaChatEndpoint,
    OpenaiChatEndpoint,
)


@pytest.mark.asyncio
async def test_openai_header():
    """Test that OpenAI header is properly formatted with API key."""
    from khive.services.providers.oai_compatible import OpenaiChatEndpoint

    # Create endpoint with a test API key
    ep = OpenaiChatEndpoint(api_key=SecretStr("test-key"))

    # Generate payload and headers
    payload, headers = ep.create_payload({"model": "gpt-4o", "messages": []})

    # Check that Authorization header is properly formatted
    assert headers["Authorization"] == "Bearer test-key"
    assert "None" not in headers["Authorization"]


@pytest.mark.asyncio
@pytest.mark.integration  # Mark as integration test since it depends on ollama package
async def test_ollama_dummy_key():
    """Test that Ollama uses the dummy key."""
    # Skip if ollama package is not installed
    pytest.importorskip("ollama")

    # Create Ollama endpoint with mocked _list and _pull methods
    with (
        patch("khive.services.providers.oai_compatible.ollama.list") as mock_list,
        patch("khive.services.providers.oai_compatible.ollama.pull") as mock_pull,
    ):

        # Mock the _list_local_models method to return a set with the test model
        mock_list.return_value = MagicMock(models=[MagicMock(model="test-model")])

        # Create endpoint
        ep = OllamaChatEndpoint(kwargs={"model": "test-model"})

        # Check that the API key is the dummy key
        assert ep.config._api_key == DUMMY_OLLAMA_API_KEY


@pytest.mark.asyncio
@pytest.mark.integration  # Mark as integration test since it tests actual client behavior
async def test_clientsession_lifecycle():
    """Test that ClientSession is not closed after one call."""
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

    # Close client
    await endpoint.aclose()

    # Check that client is closed
    assert endpoint.client.closed


@pytest.mark.asyncio
@pytest.mark.unit  # Explicitly mark as unit test
async def test_api_key_validation():
    """Test that API key validation fails fast on missing key."""
    # Create config with no API key
    with pytest.raises(
        ValueError, match="API key is required but not set for this endpoint"
    ):
        EndpointConfig(
            name="test",
            provider="test",
            base_url="http://example.com",
            endpoint="test",
            request_options=None,
            api_key=None,
        )


@pytest.mark.asyncio
@pytest.mark.unit  # Explicitly mark as unit test
async def test_cache_config():
    """Test that CacheConfig.as_kwargs() returns the expected dict."""
    from khive.config import CacheConfig

    # Create a cache config
    config = CacheConfig(ttl=600, namespace="test")

    # Get kwargs
    kwargs = config.as_kwargs()

    # Check that kwargs contains the expected values
    assert kwargs["ttl"] == 600
    assert kwargs["namespace"] == "test"

    # Check that None values are excluded
    assert "key" not in kwargs
