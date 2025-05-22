# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for async resource cleanup in the executor classes.

This module tests the proper implementation of async context manager
protocol and resource cleanup in the AsyncExecutor and RateLimitedExecutor classes.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from khive.clients.errors import TestError
from khive.clients.executor import AsyncExecutor, RateLimitedExecutor


@pytest.fixture
def mock_async_executor():
    """Create a mock AsyncExecutor for testing."""
    executor = AsyncExecutor(max_concurrency=5)
    executor.shutdown = AsyncMock()
    return executor


@pytest.fixture
def mock_rate_limiter():
    """Create a mock TokenBucketRateLimiter for testing."""
    rate_limiter = AsyncMock()
    rate_limiter.execute = AsyncMock()
    return rate_limiter


@pytest.mark.asyncio
async def test_async_executor_aenter():
    """Test that AsyncExecutor.__aenter__ returns self."""
    # Arrange
    executor = AsyncExecutor(max_concurrency=5)

    # Act
    result = await executor.__aenter__()

    # Assert
    assert result is executor


@pytest.mark.asyncio
async def test_async_executor_aexit(mock_async_executor):
    """Test that AsyncExecutor.__aexit__ calls shutdown."""
    # Arrange
    executor = mock_async_executor

    # Act
    await executor.__aexit__(None, None, None)

    # Assert
    executor.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_async_executor_aexit_with_exception(mock_async_executor):
    """Test that AsyncExecutor.__aexit__ calls shutdown even when an exception occurs."""
    # Arrange
    executor = mock_async_executor

    # Act
    await executor.__aexit__(Exception, Exception("Test exception"), None)

    # Assert
    executor.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_async_executor_as_context_manager():
    """Test that AsyncExecutor can be used as an async context manager."""
    # Arrange
    executor = AsyncExecutor(max_concurrency=5)
    executor.shutdown = AsyncMock()

    # Act
    async with executor:
        # Simulate some work
        await asyncio.sleep(0.01)

    # Assert
    executor.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_async_executor_as_context_manager_with_exception():
    """Test that AsyncExecutor properly cleans up resources when an exception occurs."""
    # Arrange
    executor = AsyncExecutor(max_concurrency=5)
    executor.shutdown = AsyncMock()

    # Act & Assert
    with pytest.raises(TestError, match="Test exception"):
        async with executor:
            # Simulate an exception
            raise TestError("Test exception")

    # Assert
    executor.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_rate_limited_executor_aenter():
    """Test that RateLimitedExecutor.__aenter__ returns self."""
    # Arrange
    with patch("khive.clients.executor.TokenBucketRateLimiter"):
        with patch("khive.clients.executor.AsyncExecutor"):
            executor = RateLimitedExecutor(rate=10, period=1.0, max_concurrency=5)

            # Act
            result = await executor.__aenter__()

            # Assert
            assert result is executor


@pytest.mark.asyncio
async def test_rate_limited_executor_aexit():
    """Test that RateLimitedExecutor.__aexit__ calls shutdown on the underlying executor."""
    # Arrange
    with patch("khive.clients.executor.TokenBucketRateLimiter"):
        executor = RateLimitedExecutor(rate=10, period=1.0, max_concurrency=5)
        executor.executor.shutdown = AsyncMock()

        # Act
        await executor.__aexit__(None, None, None)

        # Assert
        executor.executor.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_rate_limited_executor_aexit_with_exception():
    """Test that RateLimitedExecutor.__aexit__ calls shutdown even when an exception occurs."""
    # Arrange
    with patch("khive.clients.executor.TokenBucketRateLimiter"):
        executor = RateLimitedExecutor(rate=10, period=1.0, max_concurrency=5)
        executor.executor.shutdown = AsyncMock()

        # Act
        await executor.__aexit__(Exception, Exception("Test exception"), None)

        # Assert
        executor.executor.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_rate_limited_executor_as_context_manager():
    """Test that RateLimitedExecutor can be used as an async context manager."""
    # Arrange
    with patch("khive.clients.executor.TokenBucketRateLimiter"):
        executor = RateLimitedExecutor(rate=10, period=1.0, max_concurrency=5)
        executor.executor.shutdown = AsyncMock()

        # Act
        async with executor:
            # Simulate some work
            await asyncio.sleep(0.01)

        # Assert
        executor.executor.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_rate_limited_executor_as_context_manager_with_exception():
    """Test that RateLimitedExecutor properly cleans up resources when an exception occurs."""
    # Arrange
    with patch("khive.clients.executor.TokenBucketRateLimiter"):
        executor = RateLimitedExecutor(rate=10, period=1.0, max_concurrency=5)
        executor.executor.shutdown = AsyncMock()

        # Act & Assert
        with pytest.raises(TestError, match="Test exception"):
            async with executor:
                # Simulate an exception
                raise TestError("Test exception")

        # Assert
        executor.executor.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_nested_resource_cleanup():
    """Test that nested resource managers clean up properly."""
    # Arrange
    with patch("khive.clients.executor.TokenBucketRateLimiter"):
        executor = RateLimitedExecutor(rate=10, period=1.0, max_concurrency=5)
        executor.executor.shutdown = AsyncMock()

        mock_http_client = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_http_client):
            from khive.connections.endpoint import Endpoint

            endpoint_config = {
                "name": "test",
                "provider": "test",
                "base_url": "https://test.com",
                "endpoint": "test",
                "transport_type": "http",
            }

            # Act
            async with executor:
                async with Endpoint(endpoint_config) as endpoint:
                    # Simulate some work
                    await asyncio.sleep(0.01)

            # Assert
            mock_http_client.close.assert_called_once()
            executor.executor.shutdown.assert_called_once()
