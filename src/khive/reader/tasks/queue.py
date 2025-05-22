import asyncio
from typing import Any, TypeVar, Generic

T = TypeVar("T")

class AsyncTaskQueue(Generic[T]):
    """
    An asynchronous task queue based on asyncio.Queue.
    """
    def __init__(self, maxsize: int = 0):
        """
        Initializes the task queue.

        Args:
            maxsize: The maximum number of items that can be put in the queue.
                     If maxsize is less than or equal to zero, the queue size is infinite.
        """
        self._queue: asyncio.Queue[T] = asyncio.Queue(maxsize)

    async def submit_task(self, item: T) -> None:
        """
        Submits a task (item) to the queue.

        Args:
            item: The task item to be added to the queue.
        """
        await self._queue.put(item)

    async def get_task(self) -> T:
        """
        Retrieves a task from the queue.
        This will block until a task is available.

        Returns:
            The task item retrieved from the queue.
        """
        return await self._queue.get()

    def task_done(self) -> None:
        """
        Indicates that a formerly enqueued task is complete.
        Used by queue consumers. For each get() used to fetch a task,
        a subsequent call to task_done() tells the queue that the processing
        on the task is complete.
        """
        self._queue.task_done()

    async def join(self) -> None:
        """
        Blocks until all items in the queue have been gotten and processed.
        The count of unfinished tasks goes up whenever an item is added to the
        queue. The count goes down whenever a consumer calls task_done() to
        indicate that the item was retrieved and all work on it is complete.
        When the count of unfinished tasks drops to zero, join() unblocks.
        """
        await self._queue.join()

    def qsize(self) -> int:
        """
        Returns the approximate size of the queue.
        Note, qsize() > 0 doesn’t guarantee that a subsequent get()
        will not block, nor will qsize() < maxsize guarantee that put()
        will not block.
        """
        return self._queue.qsize()

    def empty(self) -> bool:
        """
        Return True if the queue is empty, False otherwise.
        """
        return self._queue.empty()

    def full(self) -> bool:
        """
        Return True if the queue is full, False otherwise.
        """
        return self._queue.full()