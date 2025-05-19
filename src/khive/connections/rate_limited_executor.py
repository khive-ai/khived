import asyncio
import logging
from typing import Any

from typing_extensions import Self

from khive.types.executor import Executor
from khive.types.queue import QueueConfig

from .api_call import APICalling


class RateLimitedExecutor(Executor):
    def __init__(
        self,
        queue_capacity: int = 100,
        capacity_refresh_time: float = 1.0,
        interval: float | None = None,
        limit_requests: int = None,
        limit_tokens: int = None,
        concurrency_limit: int | None = None,
        counter: int = None,
    ):
        queue_config = QueueConfig(
            queue_capacity=queue_capacity,
            capacity_refresh_time=capacity_refresh_time,
            concurrency_limit=concurrency_limit,
        )

        super().__init__(
            event_type=APICalling, queue_config=queue_config, counter=counter
        )
        self.limit_tokens = limit_tokens
        self.limit_requests = limit_requests
        self.interval = interval or self.task_queue.capacity_refresh_time
        self.available_request = self.limit_requests
        self.available_token = self.limit_tokens
        self._rate_limit_replenisher_task: asyncio.Task | None = None

    async def start_replenishing(self):
        """Start replenishing rate limit capacities at regular intervals."""
        if self.task_queue is None:
            self._create_queue()
        await self.task_queue.start()

        self._rate_limit_replenisher_task = asyncio.create_task(
            self._replenish_rate_limits()
        )

    async def _replenish_rate_limits(self):
        try:
            while not self.task_queue.is_stopped():
                await asyncio.sleep(delay=self.interval)
                async with self.async_lock:
                    if self.limit_requests is not None:
                        self.available_request = (
                            self.limit_requests - self.task_queue.queue.qsize()
                        )
                    if self.limit_tokens is not None:
                        self.available_token = self.limit_tokens

        except asyncio.CancelledError:
            logging.info("Rate limit replenisher task cancelled.")
        except Exception as e:
            logging.exception(f"Error in rate limit replenisher: {e}")

    async def __aenter__(self) -> Self:
        """Enter async context."""
        if self.task_queue is None:
            self._create_queue()
        await self.async_lock.acquire()
        await self.task_queue.start()
        await self.start_replenishing()
        await self.execute()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context."""
        if self._rate_limit_replenisher_task:
            self._rate_limit_replenisher_task.cancel()
            await self._rate_limit_replenisher_task
        async with self.async_lock:
            await self.task_queue.join()
            await self.task_queue.stop()

        self.async_lock.release()
        self.task_queue = None

    async def request_permission(self, event: APICalling) -> bool:
        async with self.async_lock:
            if self.limit_requests is None and self.limit_tokens is None:
                if self.task_queue.queue.qsize() < self.task_queue.queue_capacity:
                    return True

            if self.limit_requests is not None:
                if self.available_request > 0:
                    self.available_request -= 1
                if event.required_tokens is None:
                    return True
                else:
                    if self.limit_tokens >= event.required_tokens:
                        self.limit_tokens -= event.required_tokens
                        return True

            if self.limit_tokens is not None:
                if event.required_tokens is None:
                    return True
                if self.limit_tokens >= event.required_tokens:
                    self.limit_tokens -= event.required_tokens
                    return True

            return False

    def to_dict(self) -> dict[str, Any]:
        """Convert the RateLimitedExecutor to a dictionary."""
        return {
            "executor_type": "RateLimitedExecutor",
            "queue_capacity": self.queue_config.queue_capacity,
            "capacity_refresh_time": self.queue_config.capacity_refresh_time,
            "concurrency_limit": self.queue_config.concurrency_limit,
            "limit_requests": self.limit_requests,
            "limit_tokens": self.limit_tokens,
            "interval": self.interval,
            "counter": self.counter,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        data.pop("executor_type", None)
        return cls(**data)
