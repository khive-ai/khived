# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the BoundedQueue and WorkQueue classes.

This module tests the bounded async queue implementation with backpressure
for API requests, including initialization, operations, lifecycle management,
worker management, and integration with the executor framework.
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from khive.clients.errors import QueueStateError
from khive.clients.queue import BoundedQueue, QueueConfig, QueueStatus, WorkQueue


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    return Mock(spec=logging.Logger)


@pytest.mark.asyncio
async def test_bounded_queue_initialization(mock_logger):
    """Test that BoundedQueue initializes with correct default values."""
    # Arrange & Act
    queue = BoundedQueue(maxsize=10, logger=mock_logger)

    # Assert
    assert queue.maxsize == 10
    assert queue.timeout == 0.1
    assert queue.status == QueueStatus.IDLE
    assert queue.size == 0
    assert queue.is_empty
    assert not queue.is_full
    assert queue.metrics["enqueued"] == 0
    assert queue.metrics["processed"] == 0
    assert queue.metrics["errors"] == 0
    assert queue.metrics["backpressure_events"] == 0


@pytest.mark.asyncio
async def test_bounded_queue_initialization_custom_values(mock_logger):
    """Test that BoundedQueue initializes with custom values."""
    # Arrange & Act
    queue = BoundedQueue(maxsize=5, timeout=0.5, logger=mock_logger)

    # Assert
    assert queue.maxsize == 5
    assert queue.timeout == 0.5


@pytest.mark.asyncio
async def test_bounded_queue_initialization_invalid_maxsize(mock_logger):
    """Test that BoundedQueue raises ValueError for invalid maxsize."""
    # Arrange & Act & Assert
    with pytest.raises(ValueError, match="Queue maxsize must be at least 1"):
        BoundedQueue(maxsize=0, logger=mock_logger)


@pytest.mark.asyncio
async def test_bounded_queue_put_get(mock_logger):
    """Test that put and get operations work correctly."""
    # Arrange
    queue = BoundedQueue(maxsize=2, logger=mock_logger)
    await queue.start()

    # Act & Assert
    # Put items
    assert await queue.put("item1")
    assert await queue.put("item2")

    # Queue should be full now
    assert queue.is_full
    assert queue.size == 2

    # Get items
    item1 = await queue.get()
    queue.task_done()
    item2 = await queue.get()
    queue.task_done()

    assert item1 == "item1"
    assert item2 == "item2"
    assert queue.is_empty

    # Confirm metrics
    assert queue.metrics["enqueued"] == 2
    assert queue.metrics["processed"] == 2
    assert queue.metrics["errors"] == 0

    # Cleanup
    await queue.stop()


@pytest.mark.asyncio
async def test_bounded_queue_backpressure(mock_logger):
    """Test that the queue applies backpressure when full."""
    # Arrange
    queue = BoundedQueue(maxsize=1, timeout=0.01, logger=mock_logger)
    await queue.start()

    # Act & Assert
    # Put first item should succeed
    assert await queue.put("item1")

    # Second item should fail (backpressure)
    assert not await queue.put("item2")

    # Metrics should show backpressure event
    assert queue.metrics["backpressure_events"] == 1

    # Cleanup
    await queue.stop()


@pytest.mark.asyncio
async def test_bounded_queue_join(mock_logger):
    """Test that join waits for all items to be processed."""
    # Arrange
    queue = BoundedQueue(maxsize=10, logger=mock_logger)
    await queue.start()

    # Put items
    await queue.put("item1")
    await queue.put("item2")

    # Process items in a separate task
    async def process_items():
        item1 = await queue.get()
        await asyncio.sleep(0.01)  # Simulate processing
        queue.task_done()

        item2 = await queue.get()
        await asyncio.sleep(0.01)  # Simulate processing
        queue.task_done()

    task = asyncio.create_task(process_items())

    # Act
    # Join should wait for all items to be processed
    await queue.join()

    # Assert
    assert queue.is_empty

    # Cleanup
    await task
    await queue.stop()


@pytest.mark.asyncio
async def test_bounded_queue_start_stop(mock_logger):
    """Test that start and stop methods change queue status correctly."""
    # Arrange
    queue = BoundedQueue(maxsize=10, logger=mock_logger)

    # Assert initial state
    assert queue.status == QueueStatus.IDLE

    # Act & Assert - Start
    await queue.start()
    assert queue.status == QueueStatus.PROCESSING

    # Act & Assert - Stop
    await queue.stop()
    assert queue.status == QueueStatus.STOPPED


@pytest.mark.asyncio
async def test_bounded_queue_operations_non_processing(mock_logger):
    """Test that operations raise errors when queue is not in PROCESSING state."""
    # Arrange
    queue = BoundedQueue(maxsize=10, logger=mock_logger)

    # Act & Assert - Operations should fail when queue is IDLE
    with pytest.raises(QueueStateError, match="Cannot put items when queue is idle"):
        await queue.put("item")

    with pytest.raises(QueueStateError, match="Cannot get items when queue is idle"):
        await queue.get()

    # Start and then stop the queue
    await queue.start()
    await queue.stop()

    # Act & Assert - Operations should fail when queue is STOPPED
    with pytest.raises(QueueStateError, match="Cannot put items when queue is stopped"):
        await queue.put("item")

    with pytest.raises(QueueStateError, match="Cannot get items when queue is stopped"):
        await queue.get()


@pytest.mark.asyncio
async def test_bounded_queue_context_manager(mock_logger):
    """Test that the queue works correctly as an async context manager."""
    # Arrange & Act
    async with BoundedQueue(maxsize=10, logger=mock_logger) as queue:
        # Assert
        assert queue.status == QueueStatus.PROCESSING

        # Use the queue
        await queue.put("item")
        item = await queue.get()
        queue.task_done()

        assert item == "item"

    # Assert - Queue should be stopped after exiting context
    assert queue.status == QueueStatus.STOPPED


@pytest.mark.asyncio
async def test_bounded_queue_start_workers(mock_logger):
    """Test that start_workers creates the specified number of workers."""
    # Arrange
    queue = BoundedQueue(maxsize=10, logger=mock_logger)
    await queue.start()

    # Define a simple worker function
    async def worker(item):
        return item

    # Act
    await queue.start_workers(worker, num_workers=3)

    # Assert
    assert queue.worker_count == 3

    # Cleanup
    await queue.stop()


@pytest.mark.asyncio
async def test_bounded_queue_workers_process_items(mock_logger):
    """Test that workers process items from the queue."""
    # Arrange
    queue = BoundedQueue(maxsize=10, logger=mock_logger)
    await queue.start()

    # Track processed items
    processed_items = []

    # Define a worker function
    async def worker(item):
        processed_items.append(item)

    # Start workers
    await queue.start_workers(worker, num_workers=2)

    # Act
    # Add items to the queue
    for i in range(5):
        await queue.put(f"item{i}")

    # Wait for all items to be processed
    await queue.join()

    # Assert
    assert len(processed_items) == 5
    assert set(processed_items) == {f"item{i}" for i in range(5)}

    # Cleanup
    await queue.stop()


@pytest.mark.asyncio
async def test_bounded_queue_worker_error_handling(mock_logger):
    """Test that workers handle errors gracefully."""
    # Arrange
    queue = BoundedQueue(maxsize=10, logger=mock_logger)
    await queue.start()

    # Define a worker function that raises an exception for certain items
    async def worker(item):
        if item == "error_item":
            raise ValueError("Test error")

    # Define an error handler
    error_items = []

    async def error_handler(error, item):
        error_items.append((error, item))

    # Start workers with error handler
    await queue.start_workers(worker, num_workers=1, error_handler=error_handler)

    # Act
    # Add items to the queue, including one that will cause an error
    await queue.put("item1")
    await queue.put("error_item")
    await queue.put("item2")

    # Wait for all items to be processed
    await queue.join()

    # Assert
    assert len(error_items) == 1
    error, item = error_items[0]
    assert isinstance(error, ValueError)
    assert str(error) == "Test error"
    assert item == "error_item"

    # Check metrics
    assert queue.metrics["errors"] == 1
    assert queue.metrics["processed"] == 3  # All items should be marked as processed

    # Cleanup
    await queue.stop()


@pytest.mark.asyncio
async def test_bounded_queue_stop_workers(mock_logger):
    """Test that stop_workers cancels all worker tasks."""
    # Arrange
    queue = BoundedQueue(maxsize=10, logger=mock_logger)
    await queue.start()

    # Define a simple worker function
    async def worker(item):
        return item

    # Start workers
    await queue.start_workers(worker, num_workers=3)
    assert queue.worker_count == 3

    # Act
    await queue.stop()

    # Assert
    assert queue.worker_count == 0


@pytest.mark.asyncio
async def test_bounded_queue_invalid_num_workers(mock_logger):
    """Test that start_workers raises ValueError for invalid num_workers."""
    # Arrange
    queue = BoundedQueue(maxsize=10, logger=mock_logger)
    await queue.start()

    # Define a simple worker function
    async def worker(item):
        return item

    # Act & Assert
    with pytest.raises(ValueError, match="Number of workers must be at least 1"):
        await queue.start_workers(worker, num_workers=0)

    # Cleanup
    await queue.stop()


@pytest.mark.asyncio
async def test_work_queue_initialization(mock_logger):
    """Test that WorkQueue initializes correctly."""
    # Arrange & Act
    queue = WorkQueue(maxsize=10, timeout=0.5, concurrency_limit=5, logger=mock_logger)

    # Assert
    assert queue.queue.maxsize == 10
    assert queue.queue.timeout == 0.5
    assert queue.concurrency_limit == 5


@pytest.mark.asyncio
async def test_work_queue_delegation(mock_logger):
    """Test that WorkQueue delegates operations to BoundedQueue."""
    # Arrange
    # Create a mock BoundedQueue
    mock_queue = AsyncMock()
    mock_queue.put = AsyncMock(return_value=True)
    mock_queue.get = AsyncMock(return_value="item")
    mock_queue.join = AsyncMock()
    mock_queue.start = AsyncMock()
    mock_queue.stop = AsyncMock()
    mock_queue.start_workers = AsyncMock()

    # Create a WorkQueue with the mock
    queue = WorkQueue(maxsize=10, logger=mock_logger)
    queue.queue = mock_queue

    # Act & Assert
    # Test delegation
    await queue.start()
    mock_queue.start.assert_called_once()

    await queue.put("item")
    mock_queue.put.assert_called_once_with("item")

    await queue.join()
    mock_queue.join.assert_called_once()

    await queue.stop()
    mock_queue.stop.assert_called_once()

    await queue.process(worker_func=lambda x: x, num_workers=2)
    mock_queue.start_workers.assert_called_once()


@pytest.mark.asyncio
async def test_work_queue_batch_process(mock_logger):
    """Test that batch_process handles a list of items correctly."""
    # Arrange
    queue = WorkQueue(maxsize=5, concurrency_limit=2, logger=mock_logger)

    # Track processed items
    processed_items = []

    # Define a worker function
    async def worker(item):
        await asyncio.sleep(0.01)  # Simulate processing
        processed_items.append(item)

    # Act
    # Process a batch of items
    items = [f"item{i}" for i in range(10)]
    await queue.batch_process(items, worker)

    # Assert
    assert len(processed_items) == 10
    assert set(processed_items) == set(items)


@pytest.mark.asyncio
async def test_work_queue_context_manager(mock_logger):
    """Test that WorkQueue works correctly as an async context manager."""
    # Arrange
    # Create a mock BoundedQueue
    mock_queue = AsyncMock()
    mock_queue.start = AsyncMock()
    mock_queue.stop = AsyncMock()

    # Create a WorkQueue with the mock
    queue = WorkQueue(maxsize=10, logger=mock_logger)
    queue.queue = mock_queue

    # Act
    async with queue:
        pass

    # Assert
    mock_queue.start.assert_called_once()
    mock_queue.stop.assert_called_once()


def test_queue_config_validation():
    """Test that QueueConfig validates parameters correctly."""
    # Arrange & Act & Assert
    # Valid configuration
    config = QueueConfig(
        queue_capacity=10, capacity_refresh_time=1.0, concurrency_limit=5
    )
    assert config.queue_capacity == 10
    assert config.capacity_refresh_time == 1.0
    assert config.concurrency_limit == 5

    # Invalid queue_capacity
    with pytest.raises(ValueError, match="Queue capacity must be at least 1"):
        QueueConfig(queue_capacity=0)

    # Invalid capacity_refresh_time
    with pytest.raises(ValueError, match="Capacity refresh time must be positive"):
        QueueConfig(capacity_refresh_time=0)

    # Invalid concurrency_limit
    with pytest.raises(ValueError, match="Concurrency limit must be at least 1"):
        QueueConfig(concurrency_limit=0)


@pytest.mark.asyncio
async def test_bounded_queue_worker_error_without_handler(mock_logger):
    """Test that workers handle errors gracefully without an error handler."""
    # Arrange
    queue = BoundedQueue(maxsize=10, logger=mock_logger)
    await queue.start()

    # Define a worker function that raises an exception for certain items
    async def worker(item):
        if item == "error_item":
            raise ValueError("Test error")

    # Start workers without error handler
    await queue.start_workers(worker, num_workers=1)

    # Act
    # Add items to the queue, including one that will cause an error
    await queue.put("item1")
    await queue.put("error_item")
    await queue.put("item2")

    # Wait for all items to be processed
    await queue.join()

    # Assert
    # Check metrics
    assert queue.metrics["errors"] == 1
    assert queue.metrics["processed"] == 3  # All items should be marked as processed

    # Verify logger was called with error message
    mock_logger.exception.assert_called_with("Error processing item")

    # Cleanup
    await queue.stop()


@pytest.mark.asyncio
async def test_bounded_queue_worker_error_handler_error(mock_logger):
    """Test that workers handle errors in the error handler."""
    # Arrange
    queue = BoundedQueue(maxsize=10, logger=mock_logger)
    await queue.start()

    # Define a worker function that raises an exception for certain items
    async def worker(item):
        if item == "error_item":
            raise ValueError("Test error")

    # Define an error handler that also raises an exception
    async def error_handler(error, item):
        raise RuntimeError("Error handler error")

    # Start workers with error handler
    await queue.start_workers(worker, num_workers=1, error_handler=error_handler)

    # Act
    # Add items to the queue, including one that will cause an error
    await queue.put("error_item")

    # Wait for all items to be processed
    await queue.join()

    # Assert
    # Check metrics
    assert queue.metrics["errors"] == 1
    assert queue.metrics["processed"] == 1  # All items should be marked as processed

    # Verify logger was called with error message
    mock_logger.exception.assert_called_with(
        "Error in error handler. Original error: Test error"
    )

    # Cleanup
    await queue.stop()


@pytest.mark.asyncio
async def test_work_queue_process_default_workers(mock_logger):
    """Test that process uses concurrency_limit as default num_workers."""
    # Arrange
    queue = WorkQueue(maxsize=10, concurrency_limit=3, logger=mock_logger)

    # Create a mock BoundedQueue
    mock_bounded_queue = AsyncMock()
    mock_bounded_queue.start_workers = AsyncMock()
    queue.queue = mock_bounded_queue

    # Define a simple worker function
    async def worker(item):
        return item

    # Act
    await queue.process(worker)

    # Assert
    mock_bounded_queue.start_workers.assert_called_once_with(
        worker_func=worker, num_workers=3, error_handler=None
    )


@pytest.mark.asyncio
async def test_work_queue_process_custom_workers(mock_logger):
    """Test that process uses custom num_workers when provided."""
    # Arrange
    queue = WorkQueue(maxsize=10, concurrency_limit=3, logger=mock_logger)

    # Create a mock BoundedQueue
    mock_bounded_queue = AsyncMock()
    mock_bounded_queue.start_workers = AsyncMock()
    queue.queue = mock_bounded_queue

    # Define a simple worker function
    async def worker(item):
        return item

    # Act
    await queue.process(worker, num_workers=5)

    # Assert
    mock_bounded_queue.start_workers.assert_called_once_with(
        worker_func=worker, num_workers=5, error_handler=None
    )


@pytest.mark.asyncio
async def test_work_queue_process_no_concurrency_limit(mock_logger):
    """Test that process uses 1 as default num_workers when no concurrency_limit."""
    # Arrange
    queue = WorkQueue(maxsize=10, concurrency_limit=None, logger=mock_logger)

    # Create a mock BoundedQueue
    mock_bounded_queue = AsyncMock()
    mock_bounded_queue.start_workers = AsyncMock()
    queue.queue = mock_bounded_queue

    # Define a simple worker function
    async def worker(item):
        return item

    # Act
    await queue.process(worker)

    # Assert
    mock_bounded_queue.start_workers.assert_called_once_with(
        worker_func=worker, num_workers=1, error_handler=None
    )


@pytest.mark.asyncio
async def test_bounded_queue_properties(mock_logger):
    """Test that queue properties return correct values."""
    # Arrange
    queue = BoundedQueue(maxsize=10, logger=mock_logger)
    await queue.start()

    # Act & Assert
    # Initially empty
    assert queue.size == 0
    assert queue.is_empty
    assert not queue.is_full

    # Add an item
    await queue.put("item1")
    assert queue.size == 1
    assert not queue.is_empty
    assert not queue.is_full

    # Fill the queue
    for i in range(9):
        await queue.put(f"item{i + 2}")
    assert queue.size == 10
    assert not queue.is_empty
    assert queue.is_full

    # Cleanup
    await queue.stop()


@pytest.mark.asyncio
async def test_work_queue_properties(mock_logger):
    """Test that WorkQueue properties delegate to BoundedQueue."""
    # Arrange
    # Create a mock BoundedQueue with property values
    mock_queue = MagicMock()
    mock_queue.is_full = True
    mock_queue.is_empty = False
    mock_queue.metrics = {"test": 123}
    mock_queue.size = 42

    # Create a WorkQueue with the mock
    queue = WorkQueue(maxsize=10, logger=mock_logger)
    queue.queue = mock_queue

    # Act & Assert
    assert queue.is_full is True
    assert queue.is_empty is False
    assert queue.metrics == {"test": 123}
    assert queue.size == 42
