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

from .rate_limiter import TokenBucketRateLimiter

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

        # Execute a function with concurrency control
        result = await executor.execute(my_async_function, arg1, arg2, kwarg1=value1)

        # Map a function over a list of items with concurrency control
        results = await executor.map(my_async_function, [item1, item2, item3])

        # Shut down the executor when done
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
        except Exception as e:
            logger.error(f"Task {task.get_name()} failed with error: {e!s}")
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
            asyncio.create_task(self._track_task(task))

        return await task

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


class RateLimitedExecutor:
    """
    Executor that applies both rate limiting and concurrency control.

    This executor combines a TokenBucketRateLimiter and an AsyncExecutor
    to provide both rate limiting and concurrency control for async
    operations.

    Example:
        ```python
        # Create a rate-limited executor with 10 requests per second
        # and a maximum of 5 concurrent tasks
        executor = RateLimitedExecutor(rate=10, period=1.0, max_concurrency=5)

        # Execute a function with rate limiting and concurrency control
        result = await executor.execute(my_async_function, arg1, arg2, kwarg1=value1)

        # Shut down the executor when done
        await executor.shutdown()
        ```
    """

    def __init__(
        self, rate: float, period: float = 1.0, max_concurrency: int | None = None
    ):
        """
        Initialize the rate-limited executor.

        Args:
            rate: Maximum operations per period.
            period: Time period in seconds.
            max_concurrency: Maximum concurrent operations.
                If None, there is no limit on concurrency.
        """
        self.limiter = TokenBucketRateLimiter(rate, period)
        self.executor = AsyncExecutor(max_concurrency)

        logger.debug(
            f"Initialized RateLimitedExecutor with rate={rate}, "
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

        Returns:
            The result of the function execution.
        """
        logger.debug(
            f"Executing {func.__name__} with rate limiting and concurrency control"
        )
        return await self.limiter.execute(self.executor.execute, func, *args, **kwargs)

    async def shutdown(self, timeout: float | None = None) -> None:
        """
        Shut down the executor.

        Args:
            timeout: Maximum time to wait for tasks to complete.
                If None, wait indefinitely.
        """
        logger.debug("Shutting down rate-limited executor")
        await self.executor.shutdown(timeout=timeout)
