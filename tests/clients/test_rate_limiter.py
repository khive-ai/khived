# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the rate limiter components.

This module contains tests for:
- TokenBucketRateLimiter
- EndpointRateLimiter
- AdaptiveRateLimiter
"""

from unittest.mock import AsyncMock, patch

import pytest
from khive.clients.rate_limiter import (
    AdaptiveRateLimiter,
    EndpointRateLimiter,
    TokenBucketRateLimiter,
)


# TokenBucketRateLimiter Tests
@pytest.mark.asyncio
async def test_token_bucket_rate_limiter_init():
    """Test that TokenBucketRateLimiter initializes correctly."""
    # Arrange
    rate = 10
    period = 1.0
    max_tokens = 15

    # Act
    limiter = TokenBucketRateLimiter(rate=rate, period=period, max_tokens=max_tokens)

    # Assert
    assert limiter.rate == rate
    assert limiter.period == period
    assert limiter.max_tokens == max_tokens
    assert limiter.tokens == max_tokens


@pytest.mark.asyncio
async def test_token_bucket_rate_limiter_init_default_max_tokens():
    """Test that TokenBucketRateLimiter uses rate as default max_tokens."""
    # Arrange
    rate = 10
    period = 1.0

    # Act
    limiter = TokenBucketRateLimiter(rate=rate, period=period)

    # Assert
    assert limiter.max_tokens == rate
    assert limiter.tokens == rate


@pytest.mark.asyncio
async def test_token_bucket_rate_limiter_init_with_initial_tokens():
    """Test that TokenBucketRateLimiter respects initial_tokens parameter."""
    # Arrange
    rate = 10
    period = 1.0
    max_tokens = 15
    initial_tokens = 5

    # Act
    limiter = TokenBucketRateLimiter(
        rate=rate, period=period, max_tokens=max_tokens, initial_tokens=initial_tokens
    )

    # Assert
    assert limiter.rate == rate
    assert limiter.period == period
    assert limiter.max_tokens == max_tokens
    assert limiter.tokens == initial_tokens


@pytest.mark.asyncio
async def test_token_bucket_rate_limiter_refill():
    """Test that _refill method adds tokens correctly."""
    # Arrange
    rate = 10
    period = 1.0
    limiter = TokenBucketRateLimiter(rate=rate, period=period)
    limiter.tokens = 5  # Start with 5 tokens

    # Set the initial state
    limiter.last_refill = 0.0

    # Mock time.monotonic to return a specific value
    with patch("time.monotonic", return_value=0.5):
        # Act
        await limiter._refill()

        # Assert
        # After 0.5 seconds, should add 0.5 * (10/1.0) = 5 tokens
        assert limiter.tokens == 10.0


@pytest.mark.asyncio
async def test_token_bucket_rate_limiter_refill_max_tokens():
    """Test that _refill method respects max_tokens."""
    # Arrange
    rate = 10
    period = 1.0
    max_tokens = 15
    limiter = TokenBucketRateLimiter(rate=rate, period=period, max_tokens=max_tokens)
    limiter.tokens = 10  # Start with 10 tokens

    # Set the initial state
    limiter.last_refill = 0.0

    # Mock time.monotonic to return a specific value
    with patch("time.monotonic", return_value=2.0):
        # Act
        await limiter._refill()

        # Assert
        # After 2.0 seconds, should add 2.0 * (10/1.0) = 20 tokens
        # But max_tokens is 15, so should be capped at 15
        assert limiter.tokens == 15.0


@pytest.mark.asyncio
async def test_token_bucket_rate_limiter_acquire_tokens_available():
    """Test that acquire returns 0 when tokens are available."""
    # Arrange
    rate = 10
    period = 1.0
    limiter = TokenBucketRateLimiter(rate=rate, period=period)
    limiter.tokens = 5  # Start with 5 tokens

    # Mock _refill to do nothing
    with patch.object(limiter, "_refill", AsyncMock()):
        # Act
        wait_time = await limiter.acquire(tokens=3)

        # Assert
        assert wait_time == 0.0
        assert limiter.tokens == 2  # 5 - 3 = 2


@pytest.mark.asyncio
async def test_token_bucket_rate_limiter_acquire_tokens_not_available():
    """Test that acquire returns wait time when tokens are not available."""
    # Arrange
    rate = 10
    period = 1.0
    limiter = TokenBucketRateLimiter(rate=rate, period=period)
    limiter.tokens = 3  # Start with 3 tokens

    # Mock _refill to do nothing
    with patch.object(limiter, "_refill", AsyncMock()):
        # Act
        wait_time = await limiter.acquire(tokens=5)

        # Assert
        # Need 2 more tokens, at rate 10 per period 1.0
        # Wait time should be (5 - 3) * 1.0 / 10 = 0.2
        assert wait_time == 0.2
        assert limiter.tokens == 3.0  # Tokens unchanged


@pytest.mark.asyncio
async def test_token_bucket_rate_limiter_execute_no_wait():
    """Test that execute calls function immediately when tokens are available."""
    # Arrange
    rate = 10
    period = 1.0
    limiter = TokenBucketRateLimiter(rate=rate, period=period)

    # Mock acquire to return 0 (no wait)
    with patch.object(limiter, "acquire", AsyncMock(return_value=0.0)):
        # Mock the function to be executed
        mock_func = AsyncMock(return_value="result")

        # Act
        result = await limiter.execute(mock_func, "arg1", "arg2", kwarg1="value1")

        # Assert
        mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")
        assert result == "result"


@pytest.mark.asyncio
async def test_token_bucket_rate_limiter_execute_with_wait():
    """Test that execute waits before calling function when tokens are not available."""
    # Arrange
    rate = 10
    period = 1.0
    limiter = TokenBucketRateLimiter(rate=rate, period=period)

    # Mock acquire to return 0.2 (wait 0.2 seconds)
    with patch.object(limiter, "acquire", AsyncMock(return_value=0.2)):
        # Mock asyncio.sleep
        mock_sleep = AsyncMock()

        # Mock the function to be executed
        mock_func = AsyncMock(return_value="result")

        # Act
        with patch("asyncio.sleep", mock_sleep):
            result = await limiter.execute(mock_func, "arg1", "arg2", kwarg1="value1")

        # Assert
        mock_sleep.assert_called_once_with(0.2)
        mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")
        assert result == "result"


@pytest.mark.asyncio
async def test_token_bucket_rate_limiter_execute_with_custom_tokens():
    """Test that execute respects custom token cost."""
    # Arrange
    rate = 10
    period = 1.0
    limiter = TokenBucketRateLimiter(rate=rate, period=period)

    # Mock acquire to verify it's called with the right token count
    mock_acquire = AsyncMock(return_value=0.0)
    with patch.object(limiter, "acquire", mock_acquire):
        # Mock the function to be executed
        mock_func = AsyncMock(return_value="result")

        # Act
        result = await limiter.execute(mock_func, "arg1", tokens=2.5)

        # Assert
        mock_acquire.assert_called_once_with(2.5)
        mock_func.assert_called_once_with("arg1")
        assert result == "result"


@pytest.mark.asyncio
async def test_token_bucket_rate_limiter_integration():
    """Integration test for TokenBucketRateLimiter."""
    # Arrange
    rate = 10
    period = 1.0
    limiter = TokenBucketRateLimiter(rate=rate, period=period)

    # Act & Assert
    # First 10 calls should not be rate limited
    for i in range(10):
        wait_time = await limiter.acquire()
        assert wait_time == 0.0

    # 11th call should be rate limited
    wait_time = await limiter.acquire()
    assert wait_time > 0.0
    assert wait_time <= 0.1  # Should be close to 0.1 seconds


# EndpointRateLimiter Tests
@pytest.mark.asyncio
async def test_endpoint_rate_limiter_init():
    """Test that EndpointRateLimiter initializes correctly."""
    # Arrange & Act
    limiter = EndpointRateLimiter(default_rate=10.0, default_period=1.0)

    # Assert
    assert limiter.default_rate == 10.0
    assert limiter.default_period == 1.0
    assert isinstance(limiter.limiters, dict)
    assert len(limiter.limiters) == 0


@pytest.mark.asyncio
async def test_endpoint_rate_limiter_get_limiter_new_endpoint():
    """Test that get_limiter creates a new limiter for an unknown endpoint."""
    # Arrange
    limiter = EndpointRateLimiter(default_rate=10.0, default_period=1.0)
    endpoint = "api/v1/users"

    # Act
    endpoint_limiter = limiter.get_limiter(endpoint)

    # Assert
    assert isinstance(endpoint_limiter, TokenBucketRateLimiter)
    assert endpoint_limiter.rate == 10.0
    assert endpoint_limiter.period == 1.0
    assert endpoint in limiter.limiters
    assert limiter.limiters[endpoint] is endpoint_limiter


@pytest.mark.asyncio
async def test_endpoint_rate_limiter_get_limiter_existing_endpoint():
    """Test that get_limiter returns existing limiter for a known endpoint."""
    # Arrange
    limiter = EndpointRateLimiter(default_rate=10.0, default_period=1.0)
    endpoint = "api/v1/users"
    first_limiter = limiter.get_limiter(endpoint)

    # Act
    second_limiter = limiter.get_limiter(endpoint)

    # Assert
    assert second_limiter is first_limiter


@pytest.mark.asyncio
async def test_endpoint_rate_limiter_execute():
    """Test that execute uses the correct endpoint-specific rate limiter."""
    # Arrange
    limiter = EndpointRateLimiter(default_rate=10.0, default_period=1.0)
    endpoint = "api/v1/users"
    mock_func = AsyncMock(return_value="result")

    # Mock the execute method of the endpoint limiter
    endpoint_limiter = limiter.get_limiter(endpoint)
    with patch.object(endpoint_limiter, "execute", AsyncMock(return_value="result")):
        # Act
        result = await limiter.execute(endpoint, mock_func, "arg1", kwarg1="value1")

        # Assert
        assert result == "result"
        endpoint_limiter.execute.assert_called_once_with(
            mock_func, "arg1", kwarg1="value1"
        )


@pytest.mark.asyncio
async def test_endpoint_rate_limiter_update_rate_limit():
    """Test that update_rate_limit updates the parameters correctly."""
    # Arrange
    limiter = EndpointRateLimiter(default_rate=10.0, default_period=1.0)
    endpoint = "api/v1/users"
    endpoint_limiter = limiter.get_limiter(endpoint)

    # Act
    limiter.update_rate_limit(
        endpoint=endpoint, rate=5.0, period=2.0, max_tokens=15.0, reset_tokens=True
    )

    # Assert
    assert endpoint_limiter.rate == 5.0
    assert endpoint_limiter.period == 2.0
    assert endpoint_limiter.max_tokens == 15.0
    assert endpoint_limiter.tokens == 15.0


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_endpoint_rate_limiter_update_rate_limit_partial():
    """Test that update_rate_limit handles partial updates correctly."""
    # Arrange
    limiter = EndpointRateLimiter(default_rate=10.0, default_period=1.0)
    endpoint = "api/v1/users"
    endpoint_limiter = limiter.get_limiter(endpoint)
    original_period = endpoint_limiter.period
    original_max_tokens = endpoint_limiter.max_tokens

    # Manually set tokens to less than max to test that they're not reset
    endpoint_limiter.tokens = 8.0

    # Act
    limiter.update_rate_limit(endpoint=endpoint, rate=5.0, reset_tokens=False)

    # Assert
    assert endpoint_limiter.rate == 5.0
    assert endpoint_limiter.period == original_period
    assert endpoint_limiter.max_tokens == original_max_tokens
    assert endpoint_limiter.tokens < original_max_tokens  # Not reset


# AdaptiveRateLimiter Tests
@pytest.mark.asyncio
async def test_adaptive_rate_limiter_init():
    """Test that AdaptiveRateLimiter initializes correctly."""
    # Arrange & Act
    limiter = AdaptiveRateLimiter(
        initial_rate=10.0,
        initial_period=1.0,
        max_tokens=20.0,
        min_rate=2.0,
        safety_factor=0.8,
    )

    # Assert
    assert limiter.rate == 10.0
    assert limiter.period == 1.0
    assert limiter.max_tokens == 20.0
    assert limiter.min_rate == 2.0
    assert limiter.safety_factor == 0.8


@pytest.mark.asyncio
async def test_adaptive_rate_limiter_update_from_headers_x_ratelimit():
    """Test that update_from_headers handles X-RateLimit headers correctly."""
    # Arrange
    with (
        patch("time.monotonic", return_value=1000.0),
        patch("time.time", return_value=1000.0),
    ):
        limiter = AdaptiveRateLimiter(initial_rate=10.0)

        headers = {
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Remaining": "80",
            "X-RateLimit-Reset": "1030",  # 30 seconds from now
        }

        # Act
        limiter.update_from_headers(headers)

        # Assert
        # 80 remaining / 30 seconds = 2.67 per second
        # With safety factor 0.9: 2.67 * 0.9 = 2.4
        assert limiter.rate == pytest.approx(2.4, 0.1)


@pytest.mark.asyncio
async def test_adaptive_rate_limiter_update_from_headers_ratelimit():
    """Test that update_from_headers handles RateLimit headers correctly."""
    # Arrange
    with (
        patch("time.monotonic", return_value=1000.0),
        patch("time.time", return_value=1000.0),
    ):
        limiter = AdaptiveRateLimiter(initial_rate=10.0)

        headers = {
            "RateLimit-Limit": "100",
            "RateLimit-Remaining": "80",
            "RateLimit-Reset": "1030",  # 30 seconds from now
        }

        # Act
        limiter.update_from_headers(headers)

        # Assert
        # 80 remaining / 30 seconds = 2.67 per second
        # With safety factor 0.9: 2.67 * 0.9 = 2.4
        assert limiter.rate == pytest.approx(2.4, 0.1)


@pytest.mark.asyncio
async def test_adaptive_rate_limiter_update_from_headers_no_relevant_headers():
    """Test that update_from_headers does nothing when no relevant headers are present."""
    # Arrange
    limiter = AdaptiveRateLimiter(initial_rate=10.0)
    original_rate = limiter.rate

    headers = {"Content-Type": "application/json", "Server": "nginx"}

    # Act
    limiter.update_from_headers(headers)

    # Assert
    assert limiter.rate == original_rate


@pytest.mark.asyncio
async def test_adaptive_rate_limiter_minimum_rate_enforcement():
    """Test that min_rate is enforced when headers would result in a lower rate."""
    # Arrange
    with (
        patch("time.monotonic", return_value=1000.0),
        patch("time.time", return_value=1000.0),
    ):
        limiter = AdaptiveRateLimiter(initial_rate=10.0, min_rate=3.0)

        headers = {
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Remaining": "10",
            "X-RateLimit-Reset": "1030",  # 30 seconds from now
        }

        # Act
        limiter.update_from_headers(headers)

        # Assert
        # 10 remaining / 30 seconds = 0.33 per second
        # With safety factor 0.9: 0.33 * 0.9 = 0.3
        # But min_rate is 3.0, so should be 3.0
        assert limiter.rate == 3.0


@pytest.mark.asyncio
async def test_adaptive_rate_limiter_retry_after_header():
    """Test that update_from_headers handles Retry-After header correctly."""
    # Arrange
    with (
        patch("time.monotonic", return_value=1000.0),
        patch("time.time", return_value=1000.0),
    ):
        limiter = AdaptiveRateLimiter(initial_rate=10.0, min_rate=0.1)

        headers = {"Retry-After": "30"}  # Wait 30 seconds

        # Act
        limiter.update_from_headers(headers)

        # Assert
        # With Retry-After: 30, we should set rate to 0 remaining / 30 seconds
        # But min_rate is 0.1, so should be 0.1
        assert limiter.rate == 0.1
