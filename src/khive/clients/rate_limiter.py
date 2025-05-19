# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Rate limiter implementation using the token bucket algorithm.

This module provides rate limiting classes for API requests:
- TokenBucketRateLimiter: Core implementation of the token bucket algorithm
- EndpointRateLimiter: Manages per-endpoint rate limits
- AdaptiveRateLimiter: Adjusts rate limits based on API response headers
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

        # Execute with custom token cost
        result = await limiter.execute(my_async_function, arg1, arg2, tokens=2.5)
        ```
    """

    def __init__(
        self,
        rate: float,
        period: float = 1.0,
        max_tokens: float | None = None,
        initial_tokens: float | None = None,
    ):
        """
        Initialize the rate limiter.

        Args:
            rate: Maximum number of tokens per period.
            period: Time period in seconds.
            max_tokens: Maximum token bucket capacity (defaults to rate).
            initial_tokens: Initial token count (defaults to max_tokens).
        """
        self.rate = rate
        self.period = period
        self.max_tokens = max_tokens if max_tokens is not None else rate
        self.tokens = initial_tokens if initial_tokens is not None else self.max_tokens
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

        logger.debug(
            f"Initialized TokenBucketRateLimiter with rate={rate}, "
            f"period={period}, max_tokens={self.max_tokens}, "
            f"initial_tokens={self.tokens}"
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
                f"Refilled {new_tokens:.2f} tokens, current tokens: {self.tokens:.2f}/{self.max_tokens}"
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
                logger.debug(
                    f"Acquired {tokens} tokens, remaining: {self.tokens:.2f}/{self.max_tokens}"
                )
                return 0.0

            # Calculate wait time until enough tokens are available
            deficit = tokens - self.tokens
            wait_time = deficit * self.period / self.rate

            logger.debug(
                f"Not enough tokens (requested: {tokens}, available: {self.tokens:.2f}/{self.max_tokens}), "
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
                tokens: Optional number of tokens to acquire (default: 1.0).
                        This will be removed from kwargs before calling func.

        Returns:
            Result from func.
        """
        # Extract tokens parameter if present, default to 1.0
        tokens = kwargs.pop("tokens", 1.0)

        # Acquire tokens (waiting if necessary)
        wait_time = await self.acquire(tokens)

        if wait_time > 0:
            logger.debug(f"Rate limited: waiting {wait_time:.2f}s before execution")
            await asyncio.sleep(wait_time)

        logger.debug(f"Executing rate-limited function: {func.__name__}")
        return await func(*args, **kwargs)


class EndpointRateLimiter:
    """
    Rate limiter that manages multiple endpoints with different rate limits.

    This class maintains separate rate limiters for different API endpoints,
    allowing for fine-grained control over rate limiting.

    Example:
        ```python
        # Create an endpoint rate limiter with default limits
        limiter = EndpointRateLimiter(default_rate=10.0, default_period=1.0)

        # Execute with endpoint-specific rate limiting
        result = await limiter.execute("api/v1/users", my_async_function, arg1, kwarg1=value1)

        # Update rate limits for a specific endpoint
        limiter.update_rate_limit("api/v1/users", rate=5.0, period=1.0)
        ```
    """

    def __init__(self, default_rate: float = 10.0, default_period: float = 1.0):
        """
        Initialize the endpoint rate limiter.

        Args:
            default_rate: Default rate for unknown endpoints.
            default_period: Default period for unknown endpoints.
        """
        self.default_rate = default_rate
        self.default_period = default_period
        self.limiters: dict[str, TokenBucketRateLimiter] = {}
        self._lock = asyncio.Lock()

        logger.debug(
            f"Initialized EndpointRateLimiter with default_rate={default_rate}, "
            f"default_period={default_period}"
        )

    def get_limiter(self, endpoint: str) -> TokenBucketRateLimiter:
        """
        Get or create a rate limiter for the endpoint.

        Args:
            endpoint: API endpoint identifier.

        Returns:
            The rate limiter for the specified endpoint.
        """
        if endpoint not in self.limiters:
            logger.debug(f"Creating new rate limiter for endpoint: {endpoint}")
            self.limiters[endpoint] = TokenBucketRateLimiter(
                rate=self.default_rate, period=self.default_period
            )
        return self.limiters[endpoint]

    async def execute(
        self,
        endpoint: str,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Execute a coroutine with endpoint-specific rate limiting.

        Args:
            endpoint: API endpoint identifier.
            func: Async function to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.
                tokens: Optional number of tokens to acquire (default: 1.0).

        Returns:
            Result from func.
        """
        # Get the limiter for this endpoint
        limiter = self.get_limiter(endpoint)

        # Execute the function with the endpoint-specific limiter
        return await limiter.execute(func, *args, **kwargs)

    def update_rate_limit(
        self,
        endpoint: str,
        rate: float | None = None,
        period: float | None = None,
        max_tokens: float | None = None,
        reset_tokens: bool = False,
    ) -> None:
        """
        Update the rate limit parameters for an endpoint.

        Args:
            endpoint: API endpoint identifier.
            rate: New maximum operations per period (if None, keep current).
            period: New time period in seconds (if None, keep current).
            max_tokens: New maximum token capacity (if None, keep current).
            reset_tokens: If True, reset current tokens to max_tokens.
        """
        limiter = self.get_limiter(endpoint)

        # Store original tokens value before any updates
        original_tokens = limiter.tokens

        if rate is not None:
            logger.debug(
                f"Updating rate for endpoint {endpoint}: {limiter.rate} -> {rate}"
            )
            limiter.rate = rate

        if period is not None:
            logger.debug(
                f"Updating period for endpoint {endpoint}: {limiter.period} -> {period}"
            )
            limiter.period = period

        if max_tokens is not None:
            logger.debug(
                f"Updating max_tokens for endpoint {endpoint}: {limiter.max_tokens} -> {max_tokens}"
            )
            limiter.max_tokens = max_tokens

        if reset_tokens:
            logger.debug(
                f"Resetting tokens for endpoint {endpoint}: {limiter.tokens} -> {limiter.max_tokens}"
            )
            limiter.tokens = limiter.max_tokens
        else:
            # If not resetting tokens and rate was reduced, reduce tokens proportionally
            if rate is not None and rate < limiter.rate and original_tokens > 0:
                # Reduce tokens proportionally to the rate reduction
                reduction_factor = rate / limiter.rate
                limiter.tokens = min(
                    original_tokens * reduction_factor, original_tokens
                )
                logger.debug(
                    f"Adjusted tokens for endpoint {endpoint}: {original_tokens} -> {limiter.tokens}"
                )


class AdaptiveRateLimiter(TokenBucketRateLimiter):
    """
    Rate limiter that can adapt its limits based on API response headers.

    This class extends TokenBucketRateLimiter to automatically adjust
    rate limits based on response headers from API calls. It supports
    common rate limit header patterns used by various APIs.

    Example:
        ```python
        # Create an adaptive rate limiter
        limiter = AdaptiveRateLimiter(initial_rate=10.0)

        # Execute a function with adaptive rate limiting
        result = await limiter.execute(my_async_function, arg1, kwarg1=value1)

        # Update rate limits based on response headers
        limiter.update_from_headers(response.headers)
        ```
    """

    def __init__(
        self,
        initial_rate: float,
        initial_period: float = 1.0,
        max_tokens: float | None = None,
        min_rate: float = 1.0,
        safety_factor: float = 0.9,
    ):
        """
        Initialize adaptive rate limiter.

        Args:
            initial_rate: Initial maximum operations per period.
            initial_period: Initial time period in seconds.
            max_tokens: Maximum token capacity (defaults to initial_rate).
            min_rate: Minimum rate to maintain even with strict API limits.
            safety_factor: Factor to multiply API limits by for safety margin.
        """
        super().__init__(
            rate=initial_rate, period=initial_period, max_tokens=max_tokens
        )
        self.min_rate = min_rate
        self.safety_factor = safety_factor

        logger.debug(
            f"Initialized AdaptiveRateLimiter with initial_rate={initial_rate}, "
            f"initial_period={initial_period}, min_rate={min_rate}, "
            f"safety_factor={safety_factor}"
        )

    def update_from_headers(self, headers: dict[str, str]) -> None:
        """
        Update rate limits based on API response headers.

        Supports common header patterns:
        - X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
        - X-Rate-Limit-Limit, X-Rate-Limit-Remaining, X-Rate-Limit-Reset
        - RateLimit-Limit, RateLimit-Remaining, RateLimit-Reset
        - ratelimit-limit, ratelimit-remaining, ratelimit-reset
        - X-RL-Limit, X-RL-Remaining, X-RL-Reset

        Args:
            headers: Response headers from API.
        """
        # Convert headers to lowercase for case-insensitive matching
        lower_headers = {k.lower(): v for k, v in headers.items()}

        # Look for rate limit info in headers
        limit = None
        remaining = None
        reset = None

        # Try different header patterns
        for prefix in ["x-ratelimit-", "x-rate-limit-", "ratelimit-", "x-rl-"]:
            if (
                f"{prefix}limit" in lower_headers
                and f"{prefix}remaining" in lower_headers
            ):
                try:
                    limit = int(lower_headers[f"{prefix}limit"])
                    remaining = int(lower_headers[f"{prefix}remaining"])

                    # Reset time can be in different formats
                    if f"{prefix}reset" in lower_headers:
                        reset_value = lower_headers[f"{prefix}reset"]
                        try:
                            # Try parsing as epoch timestamp
                            reset = float(reset_value)
                            # If it's a Unix timestamp (seconds since epoch), convert to relative time
                            now = time.time()
                            if reset > now:
                                reset = reset - now
                        except ValueError:
                            # If not a number, ignore
                            logger.warning(
                                f"Could not parse reset value: {reset_value}"
                            )
                            reset = 60.0  # Default to 60 seconds
                    else:
                        # Default reset time if not provided
                        reset = 60.0

                    logger.debug(
                        f"Found rate limit headers with prefix '{prefix}': "
                        f"limit={limit}, remaining={remaining}, reset={reset}"
                    )
                    break
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing rate limit headers: {e}")

        # Check for Retry-After header (simpler format used by some APIs)
        if "retry-after" in lower_headers and not (limit and remaining):
            try:
                retry_after = float(lower_headers["retry-after"])
                # Assume we're at the limit
                limit = 1
                remaining = 0
                reset = retry_after
                logger.debug(f"Found Retry-After header: {retry_after}s")
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing Retry-After header: {e}")

        if limit and remaining is not None and reset:
            # Calculate new rate based on remaining calls and reset time
            time_until_reset = max(reset, 1.0)  # At least 1 second

            # Calculate new rate based on remaining calls and reset time
            new_rate = remaining / time_until_reset

            # Apply safety factor
            adjusted_rate = new_rate * self.safety_factor

            # Apply minimum rate
            final_rate = max(adjusted_rate, self.min_rate)

            logger.info(
                f"Adjusting rate limit based on headers: {final_rate:.2f} "
                f"requests per second (was: {self.rate:.2f})"
            )

            # Update the rate
            self.rate = final_rate
