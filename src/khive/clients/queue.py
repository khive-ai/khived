# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Bounded async queue implementation with backpressure for API requests.

This module provides the BoundedQueue and WorkQueue classes for managing
API requests with proper backpressure and worker management.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, field_validator

from khive.clients.errors import QueueStateError

T = TypeVar("T")
logger = logging.getLogger(__name__)


class QueueStatus(str, Enum):
    """Possible states of the queue."""

    IDLE = "idle"
    PROCESSING = "processing"
    STOPPING = "stopping"
    STOPPED = "stopped"


class QueueConfig(BaseModel):
    """Configuration options for work queues."""

    queue_capacity: int = 100
    capacity_refresh_time: float = 1.0
    concurrency_limit: int | None = None

    @field_validator("queue_capacity")
    def validate_queue_capacity(cls, v):
        """Validate that queue capacity is at least 1."""
        if v < 1:
            raise ValueError("Queue capacity must be at least 1")
        return v

    @field_validator("capacity_refresh_time")
    def validate_capacity_refresh_time(cls, v):
        """Validate that capacity refresh time is positive."""
        if v <= 0:
            raise ValueError("Capacity refresh time must be positive")
        return v

    @field_validator("concurrency_limit")
    def validate_concurrency_limit(cls, v):
        """Validate that concurrency limit is at least 1 if provided."""
        if v is not None and v < 1:
            raise ValueError("Concurrency limit must be at least 1")
        return v


class BoundedQueue(Generic[T]):
    """
    Bounded async queue with backpressure support.

    This implementation wraps asyncio.Queue with additional functionality
    for worker management, backpressure, and lifecycle control.

    Example:
        ```python
        # Create a bounded queue with a maximum size of 100
        queue = BoundedQueue(maxsize=100)

        # Start the queue for processing
        await queue.start()

        # Add items to the queue with backpressure
        if await queue.put(item):
            print("Item added to queue")
        else:
            print("Queue is full, backpressure applied")

        # Start worker tasks to process queue items
        await queue.start_workers(worker_func, num_workers=5)

        # Wait for all items to be processed
        await queue.join()

        # Stop the queue and all worker tasks
        await queue.stop()

        # Or use with async context manager
        async with BoundedQueue(maxsize=100) as queue:
            # Queue is automatically started
            await queue.start_workers(worker_func, num_workers=5)
            await queue.put(item)
            await queue.join()
            # Queue is automatically stopped on exit
        ```
    """

    def __init__(
        self,
        maxsize: int = 100,
        timeout: float = 0.1,
        logger: logging.Logger | None = None,
    ):
        """
        Initialize the bounded queue.

        Args:
            maxsize: Maximum queue size (must be > 0)
            timeout: Timeout for queue operations in seconds
            logger: Optional logger
        """
        if maxsize < 1:
            raise ValueError("Queue maxsize must be at least 1")

        self.maxsize = maxsize
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)
        self.queue = asyncio.Queue(maxsize=maxsize)
        self._status = QueueStatus.IDLE
        self._workers: list[asyncio.Task] = []
        self._stop_event = asyncio.Event()
        self._lock = asyncio.Lock()
        self._metrics: dict[str, int] = {
            "enqueued": 0,
            "processed": 0,
            "errors": 0,
            "backpressure_events": 0,
        }

        logger.debug(
            f"Initialized BoundedQueue with maxsize={maxsize}, timeout={timeout}"
        )

    @property
    def status(self) -> QueueStatus:
        """Get the current queue status."""
        return self._status

    @property
    def metrics(self) -> dict[str, int]:
        """Get queue metrics."""
        return self._metrics.copy()

    @property
    def size(self) -> int:
        """Get the current queue size."""
        return self.queue.qsize()

    @property
    def is_full(self) -> bool:
        """Check if the queue is full."""
        return self.queue.full()

    @property
    def is_empty(self) -> bool:
        """Check if the queue is empty."""
        return self.queue.empty()

    @property
    def worker_count(self) -> int:
        """Get the current number of active workers."""
        return len([w for w in self._workers if not w.done()])

    async def put(self, item: T, timeout: float | None = None) -> bool:
        """
        Add an item to the queue with backpressure.

        Args:
            item: The item to enqueue
            timeout: Operation timeout (overrides default)

        Returns:
            True if the item was enqueued, False if backpressure was applied

        Raises:
            QueueStateError: If the queue is not in PROCESSING state
            QueueFullError: If the queue is full and backpressure is applied
        """
        if self._status != QueueStatus.PROCESSING:
            raise QueueStateError(
                f"Cannot put items when queue is {self._status.value}",
                current_state=self._status.value,
            )

        try:
            # Use wait_for to implement backpressure with timeout
            await asyncio.wait_for(
                self.queue.put(item), timeout=timeout or self.timeout
            )
            self._metrics["enqueued"] += 1
            self.logger.debug(f"Item enqueued. Queue size: {self.size}/{self.maxsize}")
            return True
        except asyncio.TimeoutError:
            # Queue is full - apply backpressure
            self._metrics["backpressure_events"] += 1
            self.logger.warning(
                f"Backpressure applied - queue full ({self.size}/{self.maxsize})"
            )
            return False

    async def get(self) -> T:
        """
        Get an item from the queue.

        Returns:
            The next item from the queue

        Raises:
            QueueStateError: If the queue is not in PROCESSING state
            QueueEmptyError: If the queue is empty (when using get_nowait)
        """
        if self._status != QueueStatus.PROCESSING:
            raise QueueStateError(
                f"Cannot get items when queue is {self._status.value}",
                current_state=self._status.value,
            )

        return await self.queue.get()

    def task_done(self) -> None:
        """Mark a task as done."""
        self.queue.task_done()
        self._metrics["processed"] += 1

    async def join(self) -> None:
        """Wait for all queue items to be processed."""
        await self.queue.join()

    async def start(self) -> None:
        """Start the queue for processing."""
        async with self._lock:
            if self._status in (QueueStatus.PROCESSING, QueueStatus.STOPPING):
                return

            self._stop_event.clear()
            self._status = QueueStatus.PROCESSING
            self.logger.info(f"Queue started with maxsize {self.maxsize}")

    async def stop(self, timeout: float | None = None) -> None:
        """
        Stop the queue and all worker tasks.

        Args:
            timeout: Maximum time to wait for pending tasks
        """
        async with self._lock:
            if self._status == QueueStatus.STOPPED:
                return

            self._status = QueueStatus.STOPPING
            self.logger.info("Stopping queue and workers...")

            # Signal workers to stop
            self._stop_event.set()

            # Wait for workers to finish
            if self._workers:
                if timeout is not None:
                    try:
                        done, pending = await asyncio.wait(
                            self._workers, timeout=timeout
                        )
                        for task in pending:
                            task.cancel()
                    except Exception:
                        self.logger.exception("Error waiting for workers")
                else:
                    try:
                        await asyncio.gather(*self._workers, return_exceptions=True)
                    except Exception:
                        self.logger.exception("Error waiting for workers")

            # Clear worker list
            self._workers.clear()
            self._status = QueueStatus.STOPPED
            self.logger.info("Queue stopped")

    async def start_workers(
        self,
        worker_func: Callable[[T], Awaitable[Any]],
        num_workers: int,
        error_handler: Callable[[Exception, T], Awaitable[None]] | None = None,
    ) -> None:
        """
        Start worker tasks to process queue items.

        Args:
            worker_func: Async function that processes each queue item
            num_workers: Number of worker tasks to start
            error_handler: Optional async function to handle worker errors

        Raises:
            ValueError: If num_workers is less than 1
        """
        if num_workers < 1:
            raise ValueError("Number of workers must be at least 1")

        if self._status != QueueStatus.PROCESSING:
            await self.start()

        async with self._lock:
            # Stop existing workers if any
            if self._workers:
                self.logger.warning(
                    "Stopping existing workers before starting new ones"
                )
                for task in self._workers:
                    if not task.done():
                        task.cancel()
                self._workers.clear()

            # Start new workers
            for i in range(num_workers):
                task = asyncio.create_task(
                    self._worker_loop(i, worker_func, error_handler)
                )
                self._workers.append(task)

            self.logger.info(f"Started {num_workers} worker tasks")

    async def _worker_loop(
        self,
        worker_id: int,
        worker_func: Callable[[T], Awaitable[Any]],
        error_handler: Callable[[Exception, T], Awaitable[None]] | None = None,
    ) -> None:
        """
        Worker loop that processes queue items.

        Args:
            worker_id: Identifier for the worker
            worker_func: Async function that processes each queue item
            error_handler: Optional async function to handle worker errors
        """
        self.logger.debug(f"Worker {worker_id} started")

        while not self._stop_event.is_set():
            try:
                # Use wait_for with a short timeout to allow checking stop_event periodically
                try:
                    item = await asyncio.wait_for(self.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    # No items available within timeout, check stop event again
                    continue

                try:
                    # Process the item
                    await worker_func(item)
                except Exception as e:
                    self._metrics["errors"] += 1

                    if error_handler:
                        try:
                            await error_handler(e, item)
                        except Exception:
                            self.logger.exception(
                                f"Error in error handler. Original error: {e}"
                            )
                    else:
                        self.logger.exception("Error processing item")
                finally:
                    # Mark the task as done regardless of success/failure
                    self.task_done()

            except asyncio.CancelledError:
                self.logger.debug(f"Worker {worker_id} cancelled")
                break

        self.logger.debug(f"Worker {worker_id} stopped")

    async def __aenter__(self) -> "BoundedQueue[T]":
        """Enter async context."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context."""
        await self.stop()


class WorkQueue(Generic[T]):
    """
    High-level wrapper around BoundedQueue with additional functionality.

    This class provides a simplified interface for working with BoundedQueue,
    including batch processing and integration with the executor framework.

    Example:
        ```python
        # Create a work queue with a maximum size of 100 and 5 concurrent workers
        queue = WorkQueue(maxsize=100, concurrency_limit=5)

        # Use with async context manager
        async with queue:
            # Process items with a worker function
            await queue.process(worker_func, num_workers=5)

            # Add items to the queue
            await queue.put(item)

            # Wait for all items to be processed
            await queue.join()

        # Or batch process a list of items
        await queue.batch_process(items, worker_func, num_workers=5)
        ```
    """

    def __init__(
        self,
        maxsize: int = 100,
        timeout: float = 0.1,
        concurrency_limit: int | None = None,
        logger: logging.Logger | None = None,
    ):
        """
        Initialize the work queue.

        Args:
            maxsize: Maximum queue size
            timeout: Timeout for queue operations
            concurrency_limit: Maximum number of concurrent workers
            logger: Optional logger
        """
        self.queue = BoundedQueue(maxsize=maxsize, timeout=timeout, logger=logger)
        self.concurrency_limit = concurrency_limit
        self.logger = logger or logging.getLogger(__name__)
        self._executor = None  # Optional external executor

        self.logger.debug(
            f"Initialized WorkQueue with maxsize={maxsize}, "
            f"timeout={timeout}, concurrency_limit={concurrency_limit}"
        )

    async def __aenter__(self) -> "WorkQueue[T]":
        """Enter async context."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context."""
        await self.stop()

    @property
    def is_full(self) -> bool:
        """Check if the queue is full."""
        return self.queue.is_full

    @property
    def is_empty(self) -> bool:
        """Check if the queue is empty."""
        return self.queue.is_empty

    @property
    def metrics(self) -> dict[str, int]:
        """Get queue metrics."""
        return self.queue.metrics

    @property
    def size(self) -> int:
        """Get the current queue size."""
        return self.queue.size

    async def start(self) -> None:
        """Start the queue for processing."""
        await self.queue.start()

    async def stop(self, timeout: float | None = None) -> None:
        """
        Stop the queue and all worker tasks.

        Args:
            timeout: Maximum time to wait for tasks to complete
        """
        await self.queue.stop(timeout=timeout)

    async def put(self, item: T) -> bool:
        """
        Add an item to the queue.

        Args:
            item: The item to add to the queue

        Returns:
            True if the item was added, False if the queue is full
        """
        return await self.queue.put(item)

    async def process(
        self,
        worker_func: Callable[[T], Awaitable[Any]],
        num_workers: int | None = None,
        error_handler: Callable[[Exception, T], Awaitable[None]] | None = None,
    ) -> None:
        """
        Process queue items using the specified worker function.

        Args:
            worker_func: Async function that processes each queue item
            num_workers: Number of worker tasks (defaults to concurrency_limit)
            error_handler: Optional async function to handle worker errors
        """
        if num_workers is None:
            num_workers = self.concurrency_limit or 1

        await self.queue.start_workers(
            worker_func=worker_func,
            num_workers=num_workers,
            error_handler=error_handler,
        )

    async def join(self) -> None:
        """Wait for all queue items to be processed."""
        await self.queue.join()

    async def batch_process(
        self,
        items: list[T],
        worker_func: Callable[[T], Awaitable[Any]],
        num_workers: int | None = None,
        error_handler: Callable[[Exception, T], Awaitable[None]] | None = None,
    ) -> None:
        """
        Process a batch of items through the queue.

        Args:
            items: List of items to process
            worker_func: Async function that processes each queue item
            num_workers: Number of worker tasks (defaults to concurrency_limit)
            error_handler: Optional async function to handle worker errors
        """
        # Start the queue and workers
        await self.start()
        await self.process(
            worker_func=worker_func,
            num_workers=num_workers,
            error_handler=error_handler,
        )

        # Enqueue all items
        for item in items:
            # Keep trying until the item is enqueued
            while True:
                if await self.put(item):
                    break
                await asyncio.sleep(0.1)

        # Wait for all items to be processed
        await self.join()

        # Stop the queue and workers
        await self.stop()
