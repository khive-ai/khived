# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Protocol definitions for the API client components.

This module defines the Protocol interfaces for the AsyncResourceManager,
ResourceClient, Executor, RateLimiter, and Queue components.
"""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, TypeVar

T = TypeVar("T")
R = TypeVar("R")


class AsyncResourceManager(Protocol):
    """Protocol for components that manage async resources with context managers."""

    async def __aenter__(self) -> "AsyncResourceManager":
        """
        Enter the async context manager.

        Returns:
            The resource manager instance.
        """
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the async context manager and release resources.

        Args:
            exc_type: The exception type, if an exception was raised.
            exc_val: The exception value, if an exception was raised.
            exc_tb: The exception traceback, if an exception was raised.
        """
        ...


class ResourceClient(AsyncResourceManager, Protocol):
    """Protocol for resource clients that interact with external APIs."""

    async def call(self, request: Any, **kwargs) -> Any:
        """
        Make a call to the external resource.

        Args:
            request: The request to send to the external resource.
            **kwargs: Additional keyword arguments for the request.

        Returns:
            The response from the external resource.
        """
        ...

    async def close(self) -> None:
        """Close the client and release any resources."""
        ...

    async def __aenter__(self) -> "ResourceClient":
        """Enter the async context manager."""
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the async context manager."""
        ...


class Executor(AsyncResourceManager, Protocol):
    """Protocol for executors that manage concurrent operations."""

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
        ...

    async def shutdown(self, timeout: float | None = None) -> None:
        """
        Shut down the executor and wait for active tasks to complete.

        Args:
            timeout: Maximum time to wait for tasks to complete.
                If None, wait indefinitely.
        """
        ...


class RateLimiter(Protocol):
    """Protocol for rate limiters that control request frequency."""

    async def acquire(self, tokens: float = 1.0) -> float:
        """
        Acquire tokens from the rate limiter.

        Args:
            tokens: Number of tokens to acquire.

        Returns:
            Wait time in seconds before tokens are available.
        """
        ...

    async def execute(
        self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
    ) -> T:
        """
        Execute a coroutine with rate limiting.

        Args:
            func: The coroutine function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            The result of the function execution.
        """
        ...


class Queue(Protocol):
    """Protocol for queues that distribute work with backpressure."""

    async def put(self, item: T) -> bool:
        """
        Add an item to the queue with backpressure.

        Args:
            item: The item to add to the queue.

        Returns:
            True if the item was added, False if the queue is full.
        """
        ...

    async def get(self) -> T:
        """
        Get an item from the queue.

        Returns:
            The next item from the queue.
        """
        ...

    def task_done(self) -> None:
        """Mark a task as done."""
        ...

    async def join(self) -> None:
        """Wait for all items to be processed."""
        ...

    async def start_workers(
        self, worker_func: Callable[[T], Awaitable[Any]], num_workers: int
    ) -> None:
        """
        Start worker tasks to process queue items.

        Args:
            worker_func: Async function to process each item.
            num_workers: Number of worker tasks to start.
        """
        ...

    async def stop_workers(self, timeout: float | None = None) -> None:
        """
        Stop worker tasks.

        Args:
            timeout: Maximum time to wait for tasks to finish.
        """
        ...
