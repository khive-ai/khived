# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Executor implementations for managing concurrent operations.

This module provides the AsyncExecutor class for managing concurrent
operations with concurrency control, and the RateLimitedExecutor class
that combines rate limiting and concurrency control.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from .rate_limiter import (
    AdaptiveRateLimiter,
    EndpointRateLimiter,
    TokenBucketRateLimiter,
)

T = TypeVar("T")
R = TypeVar("R")
logger = logging.getLogger(__name__)


class AsyncExecutor:
    """
    Manages concurrent execution of async tasks with concurrency control.

    This executor limits the number of concurrent tasks that can be
    executed at once, and provides methods for executing individual
    tasks and mapping a function over a list of items.

    Example:
        ```python
        # Create an executor with a maximum of 10 concurrent tasks
        executor = AsyncExecutor(max_concurrency=10)

        # Use with async context manager (recommended)
        async with executor as exec:
            result = await exec.execute(my_async_function, arg1, arg2, kwarg1=value1)
            results = await exec.map(my_async_function, [item1, item2, item3])
        # Resources automatically cleaned up

        # Or manually:
        executor = AsyncExecutor(max_concurrency=10)
        result = await executor.execute(my_async_function, arg1, arg2, kwarg1=value1)
        results = await executor.map(my_async_function, [item1, item2, item3])
        await executor.shutdown()
        ```
    """

    def __init__(self, max_concurrency: int | None = None):
        """
        Initialize the executor.

        Args:
            max_concurrency: Maximum number of concurrent tasks.
                If None, there is no limit on concurrency.
        """
        self.semaphore = asyncio.Semaphore(max_concurrency) if max_concurrency else None
        self._active_tasks: dict[asyncio.Task, None] = {}
        self._lock = asyncio.Lock()

        logger.debug(
            f"Initialized AsyncExecutor with max_concurrency={max_concurrency}"
        )

    async def _track_task(self, task: asyncio.Task) -> None:
        """
        Track an active task and remove it when done.

        Args:
            task: The task to track.
        """
        try:
            await task
        except asyncio.CancelledError:
            logger.debug(f"Task {task.get_name()} was cancelled")
            raise
        except Exception:
            logger.exception(f"Task {task.get_name()} failed")
            raise
        finally:
            async with self._lock:
                self._active_tasks.pop(task, None)
                logger.debug(
                    f"Task {task.get_name()} completed, "
                    f"active tasks: {len(self._active_tasks)}"
                )

    async def execute(
        self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
    ) -> T:
        """
        Execute a coroutine with concurrency control.

        Args:
            func: The coroutine function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            The result of the function execution.
        """

        async def _wrapped_execution():
            if self.semaphore:
                async with self.semaphore:
                    logger.debug(f"Executing {func.__name__} with semaphore")
                    return await func(*args, **kwargs)
            else:
                logger.debug(f"Executing {func.__name__} without concurrency limit")
                return await func(*args, **kwargs)

        task_name = f"{func.__name__}_{id(_wrapped_execution)}"
        task = asyncio.create_task(_wrapped_execution(), name=task_name)

        async with self._lock:
            self._active_tasks[task] = None
            logger.debug(
                f"Created task {task_name}, active tasks: {len(self._active_tasks)}"
            )
            # Create tracker task but don't store it in _active_tasks
            # We intentionally ignore the task reference since we don't need to track or await it
            # The task will be kept alive by the event loop until it completes
            _ = asyncio.create_task(self._track_task(task))  # noqa: RUF006

        try:
            return await task
        finally:
            # Ensure task is removed from _active_tasks even if awaiting fails
            async with self._lock:
                self._active_tasks.pop(task, None)

    async def map(self, func: Callable[[T], Awaitable[R]], items: list[T]) -> list[R]:
        """
        Apply function to each item with concurrency control.

        Args:
            func: The coroutine function to apply to each item.
            items: The list of items to process.

        Returns:
            A list of results, one for each input item.
        """
        logger.debug(f"Mapping {func.__name__} over {len(items)} items")
        tasks = [self.execute(func, item) for item in items]
        return await asyncio.gather(*tasks)

    async def shutdown(self, timeout: float | None = None) -> None:
        """
        Wait for active tasks to complete and shut down the executor.

        Args:
            timeout: Maximum time to wait for tasks to complete.
                If None, wait indefinitely.
        """
        async with self._lock:
            active_tasks = list(self._active_tasks.keys())
            logger.debug(f"Shutting down with {len(active_tasks)} active tasks")

        if active_tasks:
            if timeout is not None:
                logger.debug(f"Waiting up to {timeout}s for tasks to complete")
                done, pending = await asyncio.wait(active_tasks, timeout=timeout)

                if pending:
                    logger.warning(
                        f"Timeout reached, cancelling {len(pending)} pending tasks"
                    )
                    for task in pending:
                        task.cancel()

                    # Wait for cancelled tasks to complete
                    await asyncio.gather(*pending, return_exceptions=True)
            else:
                logger.debug("Waiting indefinitely for tasks to complete")
                await asyncio.gather(*active_tasks, return_exceptions=True)

        logger.debug("Executor shutdown complete")

    async def __aenter__(self) -> "AsyncExecutor":
        """
        Enter the async context manager.

        Returns:
            The executor instance.
        """
        logger.debug("Entering AsyncExecutor context")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the async context manager and release resources.

        Args:
            exc_type: The exception type, if an exception was raised.
            exc_val: The exception value, if an exception was raised.
            exc_tb: The exception traceback, if an exception was raised.
        """
        logger.debug("Exiting AsyncExecutor context")
        await self.shutdown()


class RateLimitedExecutor:
    """
    Executor that applies both rate limiting and concurrency control.

    This executor combines a TokenBucketRateLimiter and an AsyncExecutor
    to provide both rate limiting and concurrency control for async
    operations. It can be configured with different rate limiting strategies
    including per-endpoint rate limiting and adaptive rate limiting.

    Example:
        ```python
        # Create a rate-limited executor with 10 requests per second
        # and a maximum of 5 concurrent tasks
        executor = RateLimitedExecutor(rate=10, period=1.0, max_concurrency=5)

        # Use with async context manager (recommended)
        async with executor as exec:
            result = await exec.execute(my_async_function, arg1, arg2, kwarg1=value1)
        # Resources automatically cleaned up

        # Or manually:
        executor = RateLimitedExecutor(rate=10, period=1.0, max_concurrency=5)
        result = await executor.execute(my_async_function, arg1, arg2, kwarg1=value1)
        await executor.shutdown()

        # Create with endpoint-specific rate limiting
        executor = RateLimitedExecutor(
            endpoint_rate_limiting=True,
            default_rate=10.0,
            max_concurrency=5
        )

        # Execute with endpoint-specific rate limiting
        result = await executor.execute(
            my_async_function, arg1, kwarg1=value1,
            endpoint="api/v1/users"
        )
        ```
    """

    def __init__(
        self,
        rate: float | None = None,
        period: float = 1.0,
        max_concurrency: int | None = None,
        endpoint_rate_limiting: bool = False,
        default_rate: float = 10.0,
        adaptive_rate_limiting: bool = False,
        min_rate: float = 1.0,
        safety_factor: float = 0.9,
    ):
        """
        Initialize the rate-limited executor.

        Args:
            rate: Maximum operations per period. If None and endpoint_rate_limiting
                 is False, defaults to default_rate.
            period: Time period in seconds.
            max_concurrency: Maximum concurrent operations.
                If None, there is no limit on concurrency.
            endpoint_rate_limiting: Whether to use per-endpoint rate limiting.
            default_rate: Default rate for endpoint rate limiting.
            adaptive_rate_limiting: Whether to use adaptive rate limiting.
            min_rate: Minimum rate for adaptive rate limiting.
            safety_factor: Safety factor for adaptive rate limiting.
        """
        self.executor = AsyncExecutor(max_concurrency)
        self.endpoint_rate_limiting = endpoint_rate_limiting
        self.adaptive_rate_limiting = adaptive_rate_limiting

        # Create the appropriate rate limiter based on configuration
        if endpoint_rate_limiting:
            self.limiter = EndpointRateLimiter(
                default_rate=default_rate, default_period=period
            )
            logger.debug(
                f"Initialized RateLimitedExecutor with endpoint rate limiting, "
                f"default_rate={default_rate}, default_period={period}, "
                f"max_concurrency={max_concurrency}"
            )
        elif adaptive_rate_limiting:
            effective_rate = rate if rate is not None else default_rate
            self.limiter = AdaptiveRateLimiter(
                initial_rate=effective_rate,
                initial_period=period,
                min_rate=min_rate,
                safety_factor=safety_factor,
            )
            logger.debug(
                f"Initialized RateLimitedExecutor with adaptive rate limiting, "
                f"initial_rate={effective_rate}, period={period}, "
                f"min_rate={min_rate}, safety_factor={safety_factor}, "
                f"max_concurrency={max_concurrency}"
            )
        else:
            effective_rate = rate if rate is not None else default_rate
            self.limiter = TokenBucketRateLimiter(effective_rate, period)
            logger.debug(
                f"Initialized RateLimitedExecutor with rate={effective_rate}, "
                f"period={period}, max_concurrency={max_concurrency}"
            )

    async def execute(
        self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
    ) -> T:
        """
        Execute a coroutine with rate limiting and concurrency control.

        Args:
            func: The coroutine function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.
                endpoint: Optional endpoint identifier for endpoint rate limiting.
                tokens: Optional number of tokens to acquire (default: 1.0).

        Returns:
            The result of the function execution.
        """
        logger.debug(
            f"Executing {func.__name__} with rate limiting and concurrency control"
        )

        # Extract endpoint parameter if present (for endpoint rate limiting)
        endpoint = kwargs.pop("endpoint", None)

        # Extract response_headers parameter if present (for adaptive rate limiting)
        response_headers = kwargs.pop("response_headers", None)

        # Update adaptive rate limiter if headers are provided
        if (
            self.adaptive_rate_limiting
            and response_headers
            and isinstance(self.limiter, AdaptiveRateLimiter)
        ):
            self.limiter.update_from_headers(response_headers)

        # Execute with the appropriate rate limiter
        if (
            self.endpoint_rate_limiting
            and endpoint
            and isinstance(self.limiter, EndpointRateLimiter)
        ):
            return await self.limiter.execute(
                endpoint, self.executor.execute, func, *args, **kwargs
            )

        # Default execution path
        return await self.limiter.execute(self.executor.execute, func, *args, **kwargs)

    async def update_rate_limit(
        self,
        endpoint: str,
        rate: float | None = None,
        period: float | None = None,
        max_tokens: float | None = None,
        reset_tokens: bool = False,
    ) -> None:
        """
        Update the rate limit parameters for an endpoint.

        This method only works when endpoint_rate_limiting is enabled.

        Args:
            endpoint: API endpoint identifier.
            rate: New maximum operations per period (if None, keep current).
            period: New time period in seconds (if None, keep current).
            max_tokens: New maximum token capacity (if None, keep current).
            reset_tokens: If True, reset current tokens to max_tokens.

        Raises:
            TypeError: If endpoint_rate_limiting is not enabled.
        """
        if not self.endpoint_rate_limiting:
            raise TypeError("Endpoint rate limiting is not enabled")

        if isinstance(self.limiter, EndpointRateLimiter):
            self.limiter.update_rate_limit(
                endpoint=endpoint,
                rate=rate,
                period=period,
                max_tokens=max_tokens,
                reset_tokens=reset_tokens,
            )

    async def shutdown(self, timeout: float | None = None) -> None:
        """
        Shut down the executor.

        Args:
            timeout: Maximum time to wait for tasks to complete.
                If None, wait indefinitely.
        """
        logger.debug("Shutting down rate-limited executor")
        await self.executor.shutdown(timeout=timeout)

    async def __aenter__(self) -> "RateLimitedExecutor":
        """
        Enter the async context manager.

        Returns:
            The executor instance.
        """
        logger.debug("Entering RateLimitedExecutor context")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the async context manager and release resources.

        Args:
            exc_type: The exception type, if an exception was raised.
            exc_val: The exception value, if an exception was raised.
            exc_tb: The exception traceback, if an exception was raised.
        """
        logger.debug("Exiting RateLimitedExecutor context")
        await self.shutdown()
