import asyncio
from collections import deque
from typing import Any
from uuid import UUID

from pydapter.protocols.types import ExecutionStatus
from typing_extensions import Self

from .queue import Event, Queue, QueueConfig


class Executor:
    def __init__(
        self,
        event_type: type[Event],
        queue_config: QueueConfig | dict[str, Any],
        counter: int = None,
    ):
        self.event_type = event_type
        self.queue_config = queue_config.model_dump() if hasattr(queue_config, "model_dump") else queue_config
        self.task_queue: Queue | None = None
        self.pending: deque[Event] = deque()
        self.execution_mode: bool = False
        self.events: dict[UUID, Event] = {}
        self.async_lock: asyncio.Lock = asyncio.Lock()
        self.counter: int = counter or 0

    async def __aenter__(self) -> Self:
        """Enter async context."""
        if self.task_queue is None:
            self._create_queue()
        await self.async_lock.acquire()
        await self.task_queue.start()
        await self.execute()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context."""
        async with self.async_lock:
            await self.task_queue.join()
            await self.task_queue.stop()
        self.async_lock.release()
        self.task_queue = None

    def _create_queue(self) -> None:
        """Instantiates the processor using the stored config."""
        self.task_queue = Queue(**self.queue_config)

    async def process(self):
        tasks = set()
        prev_event: Event | None = None

        while (
            self.task_queue.available_capacity > 0 and not self.task_queue.queue.empty()
        ):
            next_event = None
            if prev_event and prev_event.execution.status == ExecutionStatus.PENDING:
                # Wait if previous event is still pending
                await asyncio.sleep(self.task_queue.capacity_refresh_time)
                next_event = prev_event
            else:
                next_event = await self.task_queue.dequeue()

            if await self.request_permission(event=next_event):
                task = asyncio.create_task(next_event.invoke())
                tasks.add(task)

            prev_event = next_event
            self.task_queue.available_capacity -= 1

        if tasks:
            await asyncio.wait(tasks)
            self.task_queue.available_capacity = self.task_queue.queue_capacity

    async def request_permission(self, event: Event) -> bool:
        """Requests permission to process an event.

        Override this method to implement custom permission logic (e.g., rate limiting).

        Args:
            event (Event): The event to check permissions for.

        Returns:
            bool: True if permission is granted, False otherwise.
        """
        return True

    async def execute(self) -> None:
        """Continuously processes events until `stop()` is called.

        Respects the capacity refresh time between processing cycles.
        """
        self.execution_mode = True
        while not self.task_queue.is_stopped():
            await self.process()
            await asyncio.sleep(self.task_queue.capacity_refresh_time)

        self.execution_mode = False

    async def forward(self) -> None:
        """Forwards all pending events from the pile to the processor.

        After all events are enqueued, it calls `processor.process()` for
        immediate handling.
        """
        while len(self.pending) > 0:
            id_ = self.pending.popleft()
            event = self.events[id_]
            await self.task_queue.enqueue(event)
            self.counter += 1

        await self.process()

    def append(self, event: Event) -> None:
        """Adds a new Event to the pile and marks it as pending.

        Args:
            event (Event): The event to add.
        """
        self.events[event.id] = event
        self.pending.append(event.id)

    def pop(self, id_: UUID) -> Event | None:
        """Removes an event from the pile.

        Args:
            id_ (UUID): The ID of the event to remove.

        Returns:
            Event | None: The removed event or None if not found.
        """
        return self.events.pop(id_, None)

    @property
    def is_all_processed(self) -> bool:
        """Checks if all events in the pile are completed.

        Returns:
            bool: True if all events are completed, False otherwise.
        """
        return self.task_queue.is_empty()
