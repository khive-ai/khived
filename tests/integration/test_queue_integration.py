# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for the bounded async queue with the Executor class.

This module tests the integration of the BoundedQueue and WorkQueue classes
with the Executor class, verifying that they work together correctly for
task management, backpressure, and resource cleanup.
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from khive.clients.executor import AsyncExecutor
from khive.clients.queue import QueueConfig, WorkQueue


class MockEvent:
    """Mock event for testing with Executor."""

    def __init__(self, value):
        """Initialize the mock event."""
        self.id = value
        self.value = value
        self.execution = MagicMock()
        self.execution.status = "PENDING"

    async def invoke(self):
        """Simulate event invocation."""
        await asyncio.sleep(0.01)  # Simulate processing
        self.execution.status = "COMPLETED"
        return self.value


class SlowMockEvent(MockEvent):
    """Mock event with slow processing for testing backpressure."""

    async def invoke(self):
        """Simulate slow event invocation."""
        await asyncio.sleep(0.1)  # Slow processing
        self.execution.status = "COMPLETED"
        return self.value


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    return Mock(spec=logging.Logger)


@pytest.mark.asyncio
async def test_executor_with_work_queue(mock_logger):
    """Test that Executor correctly uses WorkQueue for task management."""

    # Arrange
    # Create a custom Executor class that uses our WorkQueue
    class TestExecutor(AsyncExecutor):
        def __init__(self, event_type, queue_config):
            super().__init__(max_concurrency=queue_config.concurrency_limit)
            self.event_type = event_type
            self.queue_config = queue_config
            self.work_queue = WorkQueue(
                maxsize=queue_config.queue_capacity,
                concurrency_limit=queue_config.concurrency_limit,
                logger=mock_logger,
            )
            self.pending = []
            self.events = {}

        async def __aenter__(self):
            await self.work_queue.start()
            await self.work_queue.process(self.process_event)
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.work_queue.join()
            await self.work_queue.stop()

        async def process_event(self, event):
            await event.invoke()

        def append(self, event):
            self.events[event.id] = event
            self.pending.append(event)

        async def forward(self):
            while self.pending:
                event = self.pending.pop(0)
                # Keep trying until the event is enqueued
                while True:
                    if await self.work_queue.put(event):
                        break
                    await asyncio.sleep(0.01)

        @property
        def is_all_processed(self):
            return self.work_queue.is_empty and not self.pending

    # Create queue config and executor
    queue_config = QueueConfig(queue_capacity=5, concurrency_limit=2)
    executor = TestExecutor(event_type=MockEvent, queue_config=queue_config)

    # Act
    # Add events
    events = []
    async with executor:
        for i in range(10):
            event = MockEvent(f"value{i}")
            events.append(event)
            executor.append(event)

        # Process all events
        await executor.forward()

        # Wait for completion
        while not executor.is_all_processed:
            await asyncio.sleep(0.01)

    # Assert
    # Verify all events were processed
    for event in events:
        assert event.execution.status == "COMPLETED"


@pytest.mark.asyncio
async def test_executor_with_queue_backpressure(mock_logger):
    """Test that Executor handles queue backpressure gracefully."""

    # Arrange
    # Create a custom Executor class that uses our WorkQueue
    class TestExecutor(AsyncExecutor):
        def __init__(self, event_type, queue_config):
            super().__init__(max_concurrency=queue_config.concurrency_limit)
            self.event_type = event_type
            self.queue_config = queue_config
            self.work_queue = WorkQueue(
                maxsize=queue_config.queue_capacity,
                concurrency_limit=queue_config.concurrency_limit,
                logger=mock_logger,
            )
            self.pending = []
            self.events = {}
            self.backpressure_count = 0

        async def __aenter__(self):
            await self.work_queue.start()
            await self.work_queue.process(self.process_event)
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.work_queue.join()
            await self.work_queue.stop()

        async def process_event(self, event):
            await event.invoke()

        def append(self, event):
            self.events[event.id] = event
            self.pending.append(event)

        async def forward(self):
            while self.pending:
                event = self.pending.pop(0)
                # Keep trying until the event is enqueued
                while True:
                    if await self.work_queue.put(event):
                        break
                    self.backpressure_count += 1
                    await asyncio.sleep(0.01)

        @property
        def is_all_processed(self):
            return self.work_queue.is_empty and not self.pending

    # Create queue config with small capacity
    queue_config = QueueConfig(queue_capacity=2, concurrency_limit=1)
    executor = TestExecutor(event_type=SlowMockEvent, queue_config=queue_config)

    # Act
    # Add events
    events = []
    async with executor:
        for i in range(5):
            event = SlowMockEvent(f"value{i}")
            events.append(event)
            executor.append(event)

        # Process all events
        await executor.forward()

        # Wait for completion
        while not executor.is_all_processed:
            await asyncio.sleep(0.01)

    # Assert
    # Verify all events were processed despite backpressure
    for event in events:
        assert event.execution.status == "COMPLETED"

    # Verify backpressure was applied
    assert executor.backpressure_count > 0
    assert executor.work_queue.metrics["backpressure_events"] > 0


@pytest.mark.asyncio
async def test_executor_resource_cleanup():
    """Test that Executor properly cleans up queue resources."""

    # Arrange
    # Create a custom Executor class that uses our WorkQueue
    class TestExecutor(AsyncExecutor):
        def __init__(self, event_type, queue_config):
            super().__init__(max_concurrency=queue_config.concurrency_limit)
            self.event_type = event_type
            self.queue_config = queue_config
            self.work_queue = AsyncMock()
            self.work_queue.start = AsyncMock()
            self.work_queue.stop = AsyncMock()
            self.work_queue.join = AsyncMock()
            self.work_queue.put = AsyncMock(return_value=True)
            self.work_queue.process = AsyncMock()
            self.work_queue.is_empty = True
            self.pending = []
            self.events = {}

        async def __aenter__(self):
            await self.work_queue.start()
            await self.work_queue.process(self.process_event)
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.work_queue.join()
            await self.work_queue.stop()

        async def process_event(self, event):
            await event.invoke()

        def append(self, event):
            self.events[event.id] = event
            self.pending.append(event)

        async def forward(self):
            while self.pending:
                event = self.pending.pop(0)
                await self.work_queue.put(event)

        @property
        def is_all_processed(self):
            return self.work_queue.is_empty and not self.pending

    # Create queue config and executor
    queue_config = QueueConfig(queue_capacity=5, concurrency_limit=2)
    executor = TestExecutor(event_type=MockEvent, queue_config=queue_config)

    # Act
    # Use executor in context manager
    async with executor:
        # Simulate some work
        event = MockEvent("test")
        executor.append(event)
        await executor.forward()

    # Assert
    # Verify resource cleanup
    executor.work_queue.start.assert_called_once()
    executor.work_queue.process.assert_called_once()
    executor.work_queue.join.assert_called_once()
    executor.work_queue.stop.assert_called_once()
