# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Resilience patterns for API clients.

This module provides resilience patterns for API clients, including
the CircuitBreaker pattern and retry with exponential backoff.
"""

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any, TypeVar

from .errors import CircuitBreakerOpenError

T = TypeVar("T")
logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for preventing calls to failing services.

    The circuit breaker pattern prevents repeated calls to a failing service,
    based on the principle of "fail fast" for better system resilience. When
    a service fails repeatedly, the circuit opens and rejects requests for a
    period of time, then transitions to a half-open state to test if the
    service has recovered.

    Example:
        ```python
        # Create a circuit breaker with a failure threshold of 5
        # and a recovery time of 30 seconds
        breaker = CircuitBreaker(failure_threshold=5, recovery_time=30.0)

        # Execute a function with circuit breaker protection
        try:
            result = await breaker.execute(my_async_function, arg1, arg2, kwarg1=value1)
        except CircuitBreakerOpenError:
            # Handle the case where the circuit is open
            with contextlib.suppress(Exception):
                # Alternative approach using contextlib.suppress
                pass
        ```
    """

    def __init__(self, failure_threshold: int = 5, recovery_time: float = 30.0):
        """
        Initialize the circuit breaker.

        Args:
            failure_threshold: Number of failures before opening the circuit.
            recovery_time: Time in seconds to wait before transitioning to half-open.
        """
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = 0
        self._lock = asyncio.Lock()

        logger.debug(
            f"Initialized CircuitBreaker with failure_threshold={failure_threshold}, "
            f"recovery_time={recovery_time}"
        )

    async def execute(
        self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
    ) -> T:
        """
        Execute a coroutine with circuit breaker protection.

        Args:
            func: The coroutine function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            The result of the function execution.

        Raises:
            CircuitBreakerOpenError: If the circuit is open.
            Exception: Any exception raised by the function.
        """
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.recovery_time:
                    # Try to recover
                    logger.info(
                        f"Circuit transitioning from OPEN to HALF_OPEN after "
                        f"{self.recovery_time}s recovery time"
                    )
                    self.state = CircuitState.HALF_OPEN
                else:
                    remaining = self.recovery_time - (
                        time.time() - self.last_failure_time
                    )
                    logger.warning(
                        f"Circuit is OPEN, rejecting request. "
                        f"Try again in {remaining:.2f}s"
                    )
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker is open. Retry after {remaining:.2f} seconds",
                        retry_after=remaining,
                    )

        try:
            logger.debug(
                f"Executing {func.__name__} with circuit state: {self.state.value}"
            )
            result = await func(*args, **kwargs)

            async with self._lock:
                if self.state == CircuitState.HALF_OPEN:
                    # Success in half-open state means service recovered
                    logger.info(
                        "Circuit recovered, transitioning from HALF_OPEN to CLOSED"
                    )
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0

            return result

        except Exception:
            async with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()

                if (
                    self.failure_count >= self.failure_threshold
                    or self.state == CircuitState.HALF_OPEN
                ):
                    old_state = self.state
                    self.state = CircuitState.OPEN
                    logger.warning(
                        f"Circuit transitioning from {old_state.value} to OPEN "
                        f"after {self.failure_count} failures"
                    )

            logger.exception("Circuit breaker caught exception")
            raise


async def retry_with_backoff(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    retry_exceptions: tuple[type[Exception], ...] = (Exception,),
    exclude_exceptions: tuple[type[Exception], ...] = (),
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    **kwargs: Any,
) -> T:
    """
    Retry an async function with exponential backoff.

    Args:
        func: The async function to retry.
        *args: Positional arguments for the function.
        retry_exceptions: Tuple of exception types to retry.
        exclude_exceptions: Tuple of exception types to not retry.
        max_retries: Maximum number of retries.
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay between retries in seconds.
        backoff_factor: Factor to increase delay with each retry.
        jitter: Whether to add randomness to the delay.
        **kwargs: Keyword arguments for the function.

    Returns:
        The result of the function execution.

    Raises:
        Exception: The last exception raised by the function after all retries.
    """
    retries = 0
    delay = base_delay

    while True:
        try:
            return await func(*args, **kwargs)
        except exclude_exceptions:
            # Don't retry these exceptions
            logger.debug(f"Not retrying {func.__name__} for excluded exception type")
            raise
        except retry_exceptions as e:
            retries += 1
            if retries > max_retries:
                logger.warning(
                    f"Maximum retries ({max_retries}) reached for {func.__name__}"
                )
                raise

            # Calculate backoff with optional jitter
            if jitter:
                # This is not used for cryptographic purposes, just for jitter
                jitter_amount = random.uniform(0.8, 1.2)  # noqa: S311
                current_delay = min(delay * jitter_amount, max_delay)
            else:
                current_delay = min(delay, max_delay)

            logger.info(
                f"Retry {retries}/{max_retries} for {func.__name__} "
                f"after {current_delay:.2f}s delay. Error: {e!s}"
            )

            # Increase delay for next iteration
            delay = delay * backoff_factor

            # Wait before retrying
            await asyncio.sleep(current_delay)
