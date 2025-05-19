# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the enhanced rate limiting functionality in RateLimitedExecutor.
"""

from unittest.mock import AsyncMock, patch

import pytest
from khive.clients.executor import RateLimitedExecutor
from khive.clients.rate_limiter import (
    AdaptiveRateLimiter,
    EndpointRateLimiter,
    TokenBucketRateLimiter,
)


@pytest.mark.asyncio
async def test_rate_limited_executor_init_default():
    """Test that RateLimitedExecutor initializes correctly with default parameters."""
    # Arrange & Act
    executor = RateLimitedExecutor(rate=10, period=1.0, max_concurrency=5)

    # Assert
    assert isinstance(executor.limiter, TokenBucketRateLimiter)
    assert executor.limiter.rate == 10
    assert executor.limiter.period == 1.0
    assert executor.executor.semaphore._value == 5
    assert executor.endpoint_rate_limiting is False
    assert executor.adaptive_rate_limiting is False


@pytest.mark.asyncio
async def test_rate_limited_executor_init_endpoint_rate_limiting():
    """Test that RateLimitedExecutor initializes correctly with endpoint rate limiting."""
    # Arrange & Act
    executor = RateLimitedExecutor(
        endpoint_rate_limiting=True, default_rate=10.0, period=1.0, max_concurrency=5
    )

    # Assert
    assert isinstance(executor.limiter, EndpointRateLimiter)
    assert executor.limiter.default_rate == 10.0
    assert executor.limiter.default_period == 1.0
    assert executor.executor.semaphore._value == 5
    assert executor.endpoint_rate_limiting is True
    assert executor.adaptive_rate_limiting is False


@pytest.mark.asyncio
async def test_rate_limited_executor_init_adaptive_rate_limiting():
    """Test that RateLimitedExecutor initializes correctly with adaptive rate limiting."""
    # Arrange & Act
    executor = RateLimitedExecutor(
        rate=10.0,
        period=1.0,
        max_concurrency=5,
        adaptive_rate_limiting=True,
        min_rate=2.0,
        safety_factor=0.8,
    )

    # Assert
    assert isinstance(executor.limiter, AdaptiveRateLimiter)
    assert executor.limiter.rate == 10.0
    assert executor.limiter.period == 1.0
    assert executor.limiter.min_rate == 2.0
    assert executor.limiter.safety_factor == 0.8
    assert executor.executor.semaphore._value == 5
    assert executor.endpoint_rate_limiting is False
    assert executor.adaptive_rate_limiting is True


@pytest.mark.asyncio
async def test_rate_limited_executor_execute_default():
    """Test that execute applies both rate limiting and concurrency control."""
    # Arrange
    executor = RateLimitedExecutor(rate=10, period=1.0, max_concurrency=5)
    mock_func = AsyncMock(return_value="result")

    # Mock the limiter's execute method to verify it's called
    executor.limiter.execute = AsyncMock(return_value="result")

    # Act
    result = await executor.execute(mock_func, "arg1", kwarg1="value1")

    # Assert
    assert result == "result"
    executor.limiter.execute.assert_called_once_with(
        executor.executor.execute, mock_func, "arg1", kwarg1="value1"
    )


@pytest.mark.asyncio
async def test_rate_limited_executor_execute_endpoint_rate_limiting():
    """Test that execute uses endpoint-specific rate limiting."""
    # Arrange
    executor = RateLimitedExecutor(
        endpoint_rate_limiting=True, default_rate=10.0, max_concurrency=5
    )
    mock_func = AsyncMock(return_value="result")
    endpoint = "api/v1/users"

    # Mock the limiter's execute method to verify it's called
    executor.limiter.execute = AsyncMock(return_value="result")

    # Act
    result = await executor.execute(
        mock_func, "arg1", kwarg1="value1", endpoint=endpoint
    )

    # Assert
    assert result == "result"
    executor.limiter.execute.assert_called_once_with(
        endpoint, executor.executor.execute, mock_func, "arg1", kwarg1="value1"
    )


@pytest.mark.asyncio
async def test_rate_limited_executor_execute_adaptive_rate_limiting():
    """Test that execute updates rate limits based on response headers."""
    # Arrange
    executor = RateLimitedExecutor(rate=10.0, adaptive_rate_limiting=True, min_rate=2.0)
    mock_func = AsyncMock(return_value="result")

    # Mock response headers
    response_headers = {
        "X-RateLimit-Limit": "100",
        "X-RateLimit-Remaining": "80",
        "X-RateLimit-Reset": "30",
    }

    # Mock the update_from_headers method to verify it's called
    with patch.object(executor.limiter, "update_from_headers") as mock_update:
        # Act
        result = await executor.execute(
            mock_func, "arg1", kwarg1="value1", response_headers=response_headers
        )

        # Assert
        mock_update.assert_called_once_with(response_headers)


@pytest.mark.asyncio
async def test_rate_limited_executor_update_rate_limit():
    """Test that update_rate_limit updates endpoint-specific rate limits."""
    # Arrange
    executor = RateLimitedExecutor(endpoint_rate_limiting=True, default_rate=10.0)
    endpoint = "api/v1/users"

    # Mock the limiter's update_rate_limit method to verify it's called
    with patch.object(executor.limiter, "update_rate_limit") as mock_update:
        # Act
        await executor.update_rate_limit(
            endpoint=endpoint, rate=5.0, period=2.0, max_tokens=15.0, reset_tokens=True
        )

        # Assert
        mock_update.assert_called_once_with(
            endpoint=endpoint, rate=5.0, period=2.0, max_tokens=15.0, reset_tokens=True
        )


@pytest.mark.asyncio
async def test_rate_limited_executor_update_rate_limit_error():
    """Test that update_rate_limit raises an error when endpoint rate limiting is not enabled."""
    # Arrange
    executor = RateLimitedExecutor(rate=10.0)  # No endpoint rate limiting
    endpoint = "api/v1/users"

    # Act & Assert
    with pytest.raises(TypeError, match="Endpoint rate limiting is not enabled"):
        await executor.update_rate_limit(endpoint=endpoint, rate=5.0)


@pytest.mark.asyncio
async def test_rate_limited_executor_with_custom_tokens():
    """Test that execute respects custom token cost."""
    # Arrange
    executor = RateLimitedExecutor(rate=10.0, period=1.0)
    mock_func = AsyncMock(return_value="result")

    # Mock the limiter's execute method to verify it's called with the right token count
    executor.limiter.execute = AsyncMock(return_value="result")

    # Act
    result = await executor.execute(mock_func, "arg1", tokens=2.5)

    # Assert
    assert result == "result"
    # Verify that tokens parameter was passed to the limiter's execute method
    executor.limiter.execute.assert_called_once()
    call_args = executor.limiter.execute.call_args
    assert "tokens" in call_args[1]
    assert call_args[1]["tokens"] == 2.5
