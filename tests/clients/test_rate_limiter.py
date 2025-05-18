# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the TokenBucketRateLimiter class.
"""

from unittest.mock import AsyncMock, patch

import pytest
from khive.clients.rate_limiter import TokenBucketRateLimiter


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
