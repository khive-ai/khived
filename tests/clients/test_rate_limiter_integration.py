# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for the rate limiter components with API client and executor.
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
async def test_token_bucket_with_api_client():
    """Test integration of TokenBucketRateLimiter with AsyncAPIClient."""
    # Arrange
    with patch("time.monotonic") as mock_time:
        # Set up mock time to advance by 0.1 seconds on each call
        # We need many more values because the event loop also calls time.monotonic()
        mock_time.side_effect = [i * 0.1 for i in range(100)]

        rate_limiter = TokenBucketRateLimiter(rate=5.0, period=1.0)

        # Mock API client to avoid actual HTTP requests
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value={"data": "response"})

        # Mock the acquire method to verify it's called correctly
        original_acquire = rate_limiter.acquire
        acquire_calls = []

        async def mock_acquire(tokens=1.0):
            acquire_calls.append(tokens)
            return await original_acquire(tokens)

        rate_limiter.acquire = mock_acquire

        # Act
        # Make 10 requests with rate limit of 5 per second
        results = []
        for i in range(10):
            result = await rate_limiter.execute(mock_client.get, f"/endpoint/{i}")
            results.append(result)

        # Assert
        assert len(results) == 10
        assert all(r == {"data": "response"} for r in results)

        # Verify the API client was called 10 times
        assert mock_client.get.call_count == 10

        # Verify acquire_tokens was called 10 times with the default token amount
        assert len(acquire_calls) == 10
        assert all(tokens == 1.0 for tokens in acquire_calls)


@pytest.mark.asyncio
async def test_endpoint_rate_limiter_with_api_client():
    """Test integration of EndpointRateLimiter with AsyncAPIClient."""
    # Arrange
    endpoint_limiter = EndpointRateLimiter(default_rate=10.0, default_period=1.0)

    # Update rate limits for specific endpoints
    endpoint_limiter.update_rate_limit("api/v1/users", rate=2.0)
    endpoint_limiter.update_rate_limit("api/v1/posts", rate=5.0)

    # Mock API client to avoid actual HTTP requests
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value={"data": "response"})

    # Get the endpoint-specific limiters
    users_limiter = endpoint_limiter.get_limiter("api/v1/users")
    posts_limiter = endpoint_limiter.get_limiter("api/v1/posts")

    # Mock the acquire methods to track calls
    users_acquire_calls = []
    posts_acquire_calls = []

    original_users_acquire = users_limiter.acquire
    original_posts_acquire = posts_limiter.acquire

    async def mock_users_acquire(tokens=1.0):
        users_acquire_calls.append(tokens)
        return await original_users_acquire(tokens)

    async def mock_posts_acquire(tokens=1.0):
        posts_acquire_calls.append(tokens)
        return await original_posts_acquire(tokens)

    users_limiter.acquire = mock_users_acquire
    posts_limiter.acquire = mock_posts_acquire

    # Act
    # Make 5 requests to the users endpoint (rate limit: 2 per second)
    users_results = []
    for i in range(5):
        result = await endpoint_limiter.execute(
            "api/v1/users", mock_client.get, f"/users/{i}"
        )
        users_results.append(result)

    # Make 5 requests to the posts endpoint (rate limit: 5 per second)
    posts_results = []
    for i in range(5):
        result = await endpoint_limiter.execute(
            "api/v1/posts", mock_client.get, f"/posts/{i}"
        )
        posts_results.append(result)

    # Assert
    assert len(users_results) == 5
    assert len(posts_results) == 5

    # Verify the API client was called 10 times
    assert mock_client.get.call_count == 10

    # Verify acquire_tokens was called the correct number of times for each endpoint
    assert len(users_acquire_calls) == 5
    assert len(posts_acquire_calls) == 5

    # Verify the rate limits are correctly set
    assert users_limiter.rate == 2.0
    assert posts_limiter.rate == 5.0


@pytest.mark.asyncio
async def test_adaptive_rate_limiter_with_api_client():
    """Test integration of AdaptiveRateLimiter with AsyncAPIClient."""
    # Arrange
    adaptive_limiter = AdaptiveRateLimiter(
        initial_rate=10.0, min_rate=1.0, safety_factor=0.8
    )

    # Mock API client to avoid actual HTTP requests
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value={"data": "response"})

    # Mock response headers with rate limit information
    headers = {
        "X-RateLimit-Limit": "100",
        "X-RateLimit-Remaining": "20",
        "X-RateLimit-Reset": "60",  # 60 seconds until reset
    }

    # Act
    # Update rate limits based on headers
    adaptive_limiter.update_from_headers(headers)

    # Verify the rate was adjusted
    # 20 remaining / 60 seconds = 0.33 per second
    # With safety factor 0.8: 0.33 * 0.8 = 0.264
    # But min_rate is 1.0, so should be 1.0
    assert adaptive_limiter.rate == 1.0

    # Mock the acquire method to verify it's called correctly
    original_acquire = adaptive_limiter.acquire
    acquire_calls = []

    async def mock_acquire(tokens=1.0):
        acquire_calls.append(tokens)
        return await original_acquire(tokens)

    adaptive_limiter.acquire = mock_acquire

    # Make 5 requests with the adjusted rate limit
    results = []
    for i in range(5):
        result = await adaptive_limiter.execute(mock_client.get, f"/endpoint/{i}")
        results.append(result)

    # Assert
    assert len(results) == 5

    # Verify the API client was called 5 times
    assert mock_client.get.call_count == 5

    # Verify acquire_tokens was called 5 times with the default token amount
    assert len(acquire_calls) == 5
    assert all(tokens == 1.0 for tokens in acquire_calls)


@pytest.mark.asyncio
async def test_rate_limited_executor_with_endpoint_rate_limiting():
    """Test RateLimitedExecutor with endpoint-specific rate limiting."""
    # Arrange
    executor = RateLimitedExecutor(
        endpoint_rate_limiting=True, default_rate=10.0, max_concurrency=5
    )

    # Update rate limits for specific endpoints
    await executor.update_rate_limit("api/v1/users", rate=2.0)
    await executor.update_rate_limit("api/v1/posts", rate=5.0)

    # Mock function to execute
    mock_func = AsyncMock(return_value="result")

    # Get the endpoint-specific limiters
    users_limiter = executor.limiter.get_limiter("api/v1/users")
    posts_limiter = executor.limiter.get_limiter("api/v1/posts")

    # Verify the rate limits are correctly set
    assert users_limiter.rate == 2.0
    assert posts_limiter.rate == 5.0

    # Act
    # Make 5 requests to the users endpoint (rate limit: 2 per second)
    users_results = []
    for i in range(5):
        result = await executor.execute(mock_func, i, endpoint="api/v1/users")
        users_results.append(result)

    # Make 5 requests to the posts endpoint (rate limit: 5 per second)
    posts_results = []
    for i in range(5):
        result = await executor.execute(mock_func, i, endpoint="api/v1/posts")
        posts_results.append(result)

    # Assert
    assert len(users_results) == 5
    assert len(posts_results) == 5

    # Verify the function was called 10 times
    assert mock_func.call_count == 10

    # Clean up
    await executor.shutdown()


@pytest.mark.asyncio
async def test_rate_limited_executor_with_adaptive_rate_limiting():
    """Test RateLimitedExecutor with adaptive rate limiting."""
    # Arrange
    executor = RateLimitedExecutor(
        adaptive_rate_limiting=True, rate=10.0, min_rate=1.0, safety_factor=0.8
    )

    # Mock function to execute
    mock_func = AsyncMock(return_value="result")

    # Mock response headers with rate limit information
    headers = {
        "X-RateLimit-Limit": "100",
        "X-RateLimit-Remaining": "20",
        "X-RateLimit-Reset": "60",  # 60 seconds until reset
    }

    # Act
    # Make a request with response headers to update rate limits
    await executor.execute(mock_func, 0, response_headers=headers)

    # Verify the rate was adjusted (through the adaptive limiter)
    assert isinstance(executor.limiter, AdaptiveRateLimiter)
    assert executor.limiter.rate == 1.0  # Min rate enforced

    # Clean up
    await executor.shutdown()


@pytest.mark.asyncio
async def test_token_bucket_custom_tokens():
    """Test that the token bucket respects custom token costs."""
    # Arrange
    with patch("time.monotonic") as mock_time:
        # Set up mock time to advance by 0.1 seconds on each call
        # We need many more values because the event loop also calls time.monotonic()
        mock_time.side_effect = [i * 0.1 for i in range(100)]

        rate_limiter = TokenBucketRateLimiter(rate=10.0, period=1.0)

        # Mock function to execute
        mock_func = AsyncMock(return_value="result")

        # Mock the acquire method to verify it's called correctly
        original_acquire = rate_limiter.acquire
        acquire_calls = []

        async def mock_acquire(tokens=1.0):
            acquire_calls.append(tokens)
            return await original_acquire(tokens)

        rate_limiter.acquire = mock_acquire

        # Act
        # Execute with different token costs
        result1 = await rate_limiter.execute(mock_func, "arg1", tokens=1.0)
        result2 = await rate_limiter.execute(mock_func, "arg2", tokens=2.5)
        result3 = await rate_limiter.execute(mock_func, "arg3", tokens=3.0)

        # Assert
        assert result1 == result2 == result3 == "result"
        assert mock_func.call_count == 3

        # Verify acquire_tokens was called with the correct token amounts
        assert len(acquire_calls) == 3
        assert acquire_calls[0] == 1.0
        assert acquire_calls[1] == 2.5
        assert acquire_calls[2] == 3.0
