from __future__ import annotations

import asyncio

from pydantic import BaseModel
from pydapter.protocols.event import Event

__all__ = (
    "Queue",
    "QueueConfig",
)


class QueueConfig(BaseModel):
    queue_capacity: int
    capacity_refresh_time: float
    concurrency_limit: int | None = None


class Queue:
    """A async queue for processing events. with a capacity limit, concurrency limit and a capacity refresh time."""

    def __init__(
        self,
        queue_capacity: int,
        capacity_refresh_time: float,
        concurrency_limit: int | None = None,
    ):
        if queue_capacity < 1:
            raise ValueError("Queue capacity must be greater than 0.")
        if capacity_refresh_time <= 0:
            raise ValueError("Capacity refresh time must be larger than 0.")

        self.queue_capacity = queue_capacity
        self.capacity_refresh_time = capacity_refresh_time
        self.queue = asyncio.Queue()
        self._available_capacity = queue_capacity
        self._execution_mode = False
        self._stop_event = asyncio.Event()
        if concurrency_limit:
            self._concurrency_sem = asyncio.Semaphore(concurrency_limit)
        else:
            self._concurrency_sem = None

    @property
    def available_capacity(self) -> int:
        """int: The current capacity available for processing."""
        return self._available_capacity

    @available_capacity.setter
    def available_capacity(self, value: int) -> None:
        self._available_capacity = value

    async def enqueue(self, event: Event) -> None:
        """Adds an event to the queue asynchronously.

        Args:
            event (Event): The event to enqueue.
        """
        await self.queue.put(event)

    async def dequeue(self) -> Event:
        """Retrieves the next event from the queue.

        Returns:
            Event: The next event in the queue.
        """
        return await self.queue.get()

    async def join(self) -> None:
        """Blocks until the queue is empty and all tasks are done."""
        await self.queue.join()

    async def stop(self) -> None:
        """Signals the processor to stop processing events."""
        self._stop_event.set()

    async def start(self) -> None:
        """Clears the stop signal, allowing event processing to resume."""
        self._stop_event.clear()

    def is_stopped(self) -> bool:
        """Checks whether the processor is in a stopped state.

        Returns:
            bool: True if the processor has been signaled to stop.
        """
        return self._stop_event.is_set()

    def is_empty(self) -> bool:
        """Checks if the queue is empty.

        Returns:
            bool: True if the queue is empty, False otherwise.
        """
        return self.queue.empty()
