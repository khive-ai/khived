# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Rate limiter implementation using the token bucket algorithm.

This module provides the TokenBucketRateLimiter class, which implements
the token bucket algorithm for rate limiting API requests.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """
    Rate limiter using the token bucket algorithm.

    The token bucket algorithm allows for controlled bursts of requests
    while maintaining a long-term rate limit. Tokens are added to the
    bucket at a constant rate, and each request consumes one or more tokens.
    If the bucket is empty, requests must wait until enough tokens are
    available.

    Example:
        ```python
        # Create a rate limiter with 10 requests per second
        limiter = TokenBucketRateLimiter(rate=10, period=1.0)

        # Execute a function with rate limiting
        result = await limiter.execute(my_async_function, arg1, arg2, kwarg1=value1)
        ```
    """

    def __init__(
        self, rate: float, period: float = 1.0, max_tokens: float | None = None
    ):
        """
        Initialize the rate limiter.

        Args:
            rate: Maximum number of tokens per period.
            period: Time period in seconds.
            max_tokens: Maximum token bucket capacity (defaults to rate).
        """
        self.rate = rate
        self.period = period
        self.max_tokens = max_tokens if max_tokens is not None else rate
        self.tokens = self.max_tokens
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

        logger.debug(
            f"Initialized TokenBucketRateLimiter with rate={rate}, "
            f"period={period}, max_tokens={self.max_tokens}"
        )

    async def _refill(self) -> None:
        """
        Refill tokens based on elapsed time.

        This method calculates the number of tokens to add based on the
        time elapsed since the last refill, and adds them to the bucket
        up to the maximum capacity.
        """
        now = time.monotonic()
        elapsed = now - self.last_refill
        new_tokens = elapsed * (self.rate / self.period)

        if new_tokens > 0:
            self.tokens = min(self.tokens + new_tokens, self.max_tokens)
            self.last_refill = now
            logger.debug(
                f"Refilled {new_tokens:.2f} tokens, current tokens: {self.tokens:.2f}"
            )

    async def acquire(self, tokens: float = 1.0) -> float:
        """
        Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire.

        Returns:
            Wait time in seconds before tokens are available.
            Returns 0.0 if tokens are immediately available.
        """
        async with self._lock:
            await self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                logger.debug(f"Acquired {tokens} tokens, remaining: {self.tokens:.2f}")
                return 0.0

            # Calculate wait time until enough tokens are available
            deficit = tokens - self.tokens
            wait_time = deficit * self.period / self.rate

            logger.debug(
                f"Not enough tokens (requested: {tokens}, available: {self.tokens:.2f}), "
                f"wait time: {wait_time:.2f}s"
            )

            return wait_time

    async def execute(
        self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
    ) -> T:
        """
        Execute a coroutine with rate limiting.

        Args:
            func: Async function to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            Result from func.
        """
        wait_time = await self.acquire()

        if wait_time > 0:
            logger.debug(f"Rate limited: waiting {wait_time:.2f}s before execution")
            await asyncio.sleep(wait_time)

        logger.debug(f"Executing rate-limited function: {func.__name__}")
        return await func(*args, **kwargs)
