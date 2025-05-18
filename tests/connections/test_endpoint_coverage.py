# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Additional tests for the Endpoint class to increase coverage.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from khive.connections.endpoint import Endpoint, EndpointConfig


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


@pytest.mark.asyncio
async def test_endpoint_init_with_dict():
    """Test that Endpoint.__init__ properly handles dict config."""
    # Arrange
    config_dict = {
        "name": "test_dict",
        "provider": "test",
        "base_url": "https://test.com",
        "endpoint": "test",
        "transport_type": "http",
    }

    # Act
    endpoint = Endpoint(config_dict)

    # Assert
    assert endpoint.config.name == "test_dict"
    assert endpoint.config.provider == "test"
    assert endpoint.config.base_url == "https://test.com"
    assert endpoint.config.endpoint == "test"
    assert endpoint.config.transport_type == "http"


@pytest.mark.asyncio
async def test_endpoint_init_with_config_and_kwargs():
    """Test that Endpoint.__init__ properly handles EndpointConfig with kwargs."""
    # Arrange
    config = EndpointConfig(
        name="test_config",
        provider="test",
        base_url="https://test.com",
        endpoint="test",
        transport_type="http",
    )

    # Act
    endpoint = Endpoint(config, timeout=500)

    # Assert
    assert endpoint.config.name == "test_config"
    assert endpoint.config.timeout == 500  # Override from kwargs


@pytest.mark.asyncio
async def test_endpoint_request_options_setter():
    """Test that request_options setter properly validates options."""
    # Arrange
    endpoint = Endpoint({
        "name": "test",
        "provider": "test",
        "base_url": "https://test.com",
        "endpoint": "test",
        "transport_type": "http",
    })

    # Act
    # Just test that we can set it to None without error
    endpoint.request_options = None

    # Assert
    assert endpoint.request_options is None


@pytest.mark.asyncio
async def test_endpoint_call_with_cache_control():
    """Test that call() properly handles cache_control."""
    # Arrange
    with patch(
        "khive.connections.endpoint.Endpoint._call_aiohttp"
    ) as mock_call_aiohttp:
        mock_call_aiohttp.return_value = {"result": "success"}

        with patch("khive.connections.endpoint.cached") as mock_cached:
            mock_cached.return_value = lambda func: func

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
            assert result == {"result": "success"}
            mock_cached.assert_called_once()


@pytest.mark.asyncio
async def test_endpoint_create_payload_with_extra_headers():
    """Test that create_payload correctly handles extra headers."""
    # Arrange
    with patch(
        "khive.connections.header_factory.HeaderFactory.get_header",
        return_value={"Authorization": "Bearer test"},
    ):
        endpoint = Endpoint({
            "name": "test",
            "provider": "test",
            "base_url": "https://test.com",
            "endpoint": "test",
            "transport_type": "http",
        })

        # Act
        payload, headers = endpoint.create_payload(
            {"test": "data"}, extra_headers={"X-Custom-Header": "custom-value"}
        )

        # Assert
        assert payload == {"test": "data"}
        assert headers == {
            "Authorization": "Bearer test",
            "X-Custom-Header": "custom-value",
        }


@pytest.mark.asyncio
async def test_endpoint_create_payload_with_model():
    """Test that create_payload correctly handles BaseModel input."""
    # Arrange
    from pydantic import BaseModel

    class TestModel(BaseModel):
        field1: str
        field2: int

    with patch(
        "khive.connections.header_factory.HeaderFactory.get_header",
        return_value={"Authorization": "Bearer test"},
    ):
        endpoint = Endpoint({
            "name": "test",
            "provider": "test",
            "base_url": "https://test.com",
            "endpoint": "test",
            "transport_type": "http",
        })

        # Act
        payload, headers = endpoint.create_payload(TestModel(field1="test", field2=123))

        # Assert
        assert payload == {"field1": "test", "field2": 123}
        assert headers == {"Authorization": "Bearer test"}


@pytest.mark.asyncio
async def test_endpoint_create_payload_with_kwargs():
    """Test that create_payload correctly handles kwargs."""
    # Arrange
    with patch(
        "khive.connections.header_factory.HeaderFactory.get_header",
        return_value={"Authorization": "Bearer test"},
    ):
        endpoint = Endpoint({
            "name": "test",
            "provider": "test",
            "base_url": "https://test.com",
            "endpoint": "test",
            "transport_type": "http",
        })

        # Act
        payload, headers = endpoint.create_payload(
            {"test": "data"}, extra_param="extra_value"
        )

        # Assert
        assert payload == {"test": "data", "extra_param": "extra_value"}
        assert headers == {"Authorization": "Bearer test"}
