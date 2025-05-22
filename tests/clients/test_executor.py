# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the AsyncExecutor and RateLimitedExecutor classes.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from khive.clients.executor import AsyncExecutor, RateLimitedExecutor


@pytest.mark.asyncio
async def test_async_executor_init():
    """Test that AsyncExecutor initializes correctly."""
    # Arrange & Act
    executor = AsyncExecutor(max_concurrency=5)

    # Assert
    assert executor.semaphore is not None
    assert executor._active_tasks == {}


@pytest.mark.asyncio
async def test_async_executor_init_no_concurrency_limit():
    """Test that AsyncExecutor initializes correctly with no concurrency limit."""
    # Arrange & Act
    executor = AsyncExecutor()

    # Assert
    assert executor.semaphore is None
    assert executor._active_tasks == {}


@pytest.mark.asyncio
async def test_async_executor_execute():
    """Test that execute method works correctly."""
    # Arrange
    executor = AsyncExecutor(max_concurrency=5)
    mock_func = AsyncMock(return_value="result")

    # Act
    result = await executor.execute(mock_func, "arg1", "arg2", kwarg1="value1")

    # Assert
    mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")
    assert result == "result"
    assert len(executor._active_tasks) == 0  # Task should be removed after completion


@pytest.mark.asyncio
async def test_async_executor_execute_with_exception():
    """Test that execute method handles exceptions correctly."""
    # Arrange
    executor = AsyncExecutor(max_concurrency=5)
    mock_func = AsyncMock(side_effect=ValueError("Test error"))

    # Act & Assert
    with pytest.raises(ValueError) as excinfo:
        await executor.execute(mock_func)

    # Assert
    assert "Test error" in str(excinfo.value)
    assert len(executor._active_tasks) == 0  # Task should be removed after exception


@pytest.mark.asyncio
async def test_async_executor_map():
    """Test that map method works correctly."""
    # Arrange
    executor = AsyncExecutor(max_concurrency=5)
    mock_func = AsyncMock(side_effect=lambda x: x * 2)
    items = [1, 2, 3, 4, 5]

    # Act
    results = await executor.map(mock_func, items)

    # Assert
    assert results == [2, 4, 6, 8, 10]
    assert mock_func.call_count == 5
    assert (
        len(executor._active_tasks) == 0
    )  # All tasks should be removed after completion


@pytest.mark.asyncio
async def test_async_executor_shutdown_no_tasks():
    """Test that shutdown method works correctly with no active tasks."""
    # Arrange
    executor = AsyncExecutor(max_concurrency=5)

    # Act
    await executor.shutdown()

    # Assert
    assert len(executor._active_tasks) == 0


@pytest.mark.asyncio
async def test_async_executor_shutdown_with_tasks():
    """Test that shutdown method waits for active tasks."""
    # Arrange
    executor = AsyncExecutor(max_concurrency=5)

    # Create a task that will complete after a short delay
    async def delayed_task():
        await asyncio.sleep(0.1)
        return "result"

    # Start the task
    task = await executor.execute(delayed_task)

    # Act
    await executor.shutdown()

    # Assert
    assert task == "result"
    assert len(executor._active_tasks) == 0


@pytest.mark.asyncio
async def test_async_executor_shutdown_with_timeout():
    """Test that shutdown method cancels tasks after timeout."""
    # Arrange
    executor = AsyncExecutor(max_concurrency=5)

    # Create a mock for the _lock
    mock_lock = AsyncMock()
    mock_lock.__aenter__.return_value = None
    mock_lock.__aexit__.return_value = None
    executor._lock = mock_lock

    # Create a mock task
    mock_task = AsyncMock()

    # Set up active tasks with the mock task
    executor._active_tasks = {mock_task: None}

    # Mock asyncio.wait to return an empty set of done tasks and our mock task as pending
    mock_wait = AsyncMock(return_value=(set(), {mock_task}))

    # Mock asyncio.gather to do nothing
    mock_gather = AsyncMock()

    # Act
    with patch("asyncio.wait", mock_wait):
        with patch("asyncio.gather", mock_gather):
            await executor.shutdown(timeout=0.1)

    # Assert
    # With active tasks, asyncio.wait should be called once
    mock_wait.assert_called_once()
    # The task should be cancelled
    mock_task.cancel.assert_called_once()
    mock_task.cancel.assert_called_once()


@pytest.mark.asyncio
async def test_rate_limited_executor_init():
    """Test that RateLimitedExecutor initializes correctly."""
    # Arrange & Act
    executor = RateLimitedExecutor(rate=10, period=1.0, max_concurrency=5)

    # Assert
    assert executor.limiter is not None
    assert executor.executor is not None
    assert executor.limiter.rate == 10
    assert executor.limiter.period == 1.0
    assert executor.executor.semaphore is not None


@pytest.mark.asyncio
async def test_rate_limited_executor_execute():
    """Test that execute method works correctly."""
    # Arrange
    executor = RateLimitedExecutor(rate=10, period=1.0, max_concurrency=5)
    mock_func = AsyncMock(return_value="result")

    # Create a mock function that will actually call the function
    async def mock_execute(func, *args, **kwargs):
        return await func(*args, **kwargs)

    # Mock the limiter.execute method
    mock_limiter_execute = AsyncMock(side_effect=mock_execute)
    executor.limiter.execute = mock_limiter_execute

    # Mock the executor.execute method
    mock_executor_execute = AsyncMock(side_effect=mock_execute)
    executor.executor.execute = mock_executor_execute

    # Act
    result = await executor.execute(mock_func, "arg1", "arg2", kwarg1="value1")

    # Assert
    mock_limiter_execute.assert_called_once()
    mock_executor_execute.assert_called_once()
    mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")
    assert result == "result"


@pytest.mark.asyncio
async def test_rate_limited_executor_shutdown():
    """Test that shutdown method works correctly."""
    # Arrange
    executor = RateLimitedExecutor(rate=10, period=1.0, max_concurrency=5)

    # Mock the executor.shutdown method
    mock_executor_shutdown = AsyncMock()
    executor.executor.shutdown = mock_executor_shutdown

    # Act
    await executor.shutdown(timeout=0.1)

    # Assert
    mock_executor_shutdown.assert_called_once_with(timeout=0.1)


@pytest.mark.asyncio
async def test_rate_limited_executor_integration():
    """Integration test for RateLimitedExecutor."""
    # Arrange
    executor = RateLimitedExecutor(rate=10, period=1.0, max_concurrency=5)

    # Create a simple async function
    async def test_func(x):
        return x * 2

    # Act
    results = await asyncio.gather(*[executor.execute(test_func, i) for i in range(10)])

    # Assert
    assert results == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]

    # Clean up
    await executor.shutdown()
