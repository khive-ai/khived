import asyncio
import pytest
import pytest_asyncio
from khive.reader.tasks.queue import AsyncTaskQueue

@pytest_asyncio.fixture
async def task_queue() -> AsyncTaskQueue[str]:
    """Provides an instance of AsyncTaskQueue for testing."""
    return AsyncTaskQueue[str]()

@pytest.mark.asyncio
async def test_submit_and_get_task(task_queue: AsyncTaskQueue[str]):
    """Test submitting a single task and retrieving it."""
    test_item = "document_id_123"
    assert task_queue.empty()
    assert task_queue.qsize() == 0

    await task_queue.submit_task(test_item)
    assert not task_queue.empty()
    assert task_queue.qsize() == 1

    retrieved_item = await task_queue.get_task()
    assert retrieved_item == test_item
    # qsize decreases after get() if task_done() is not immediately called,
    # but the item is considered "gotten".
    # For asyncio.Queue, qsize reflects items not yet gotten.
    # After get(), the item is no longer in the queue from qsize perspective.
    assert task_queue.qsize() == 0
    # We still need to call task_done for join() to work correctly
    task_queue.task_done()


@pytest.mark.asyncio
async def test_get_task_from_empty_queue_blocks_and_retrieves(task_queue: AsyncTaskQueue[str]):
    """Test that get_task blocks until an item is available and then retrieves it."""
    test_item = "document_id_456"

    async def producer():
        await asyncio.sleep(0.01) # Ensure consumer starts waiting
        await task_queue.submit_task(test_item)

    async def consumer():
        return await task_queue.get_task()

    # Run producer and consumer concurrently
    producer_task = asyncio.create_task(producer())
    consumer_task = asyncio.create_task(consumer())

    retrieved_item = await consumer_task
    await producer_task # Ensure producer completes

    assert retrieved_item == test_item
    task_queue.task_done()

@pytest.mark.asyncio
async def test_multiple_tasks_retrieved_in_order(task_queue: AsyncTaskQueue[str]):
    """Test submitting multiple tasks and retrieving them in FIFO order."""
    items = ["task1", "task2", "task3"]
    for item in items:
        await task_queue.submit_task(item)

    retrieved_items = []
    for _ in items:
        retrieved_items.append(await task_queue.get_task())
        task_queue.task_done() # Mark each task as done

    assert retrieved_items == items
    assert task_queue.empty()

@pytest.mark.asyncio
async def test_task_done_functionality(task_queue: AsyncTaskQueue[str]):
    """Test the task_done method and its effect on join()."""
    test_item = "document_id_789"
    await task_queue.submit_task(test_item)

    retrieved_item = await task_queue.get_task()
    assert retrieved_item == test_item

    # join() should block if task_done() hasn't been called
    join_task_before_done = asyncio.create_task(task_queue.join())
    await asyncio.sleep(0.01) # Give join_task a chance to run and block
    assert not join_task_before_done.done()

    task_queue.task_done()

    # join() should now unblock
    await asyncio.wait_for(join_task_before_done, timeout=0.1)
    assert join_task_before_done.done()

@pytest.mark.asyncio
async def test_join_empty_queue(task_queue: AsyncTaskQueue[str]):
    """Test that join() on an empty queue returns immediately."""
    await asyncio.wait_for(task_queue.join(), timeout=0.01) # Should not block

@pytest.mark.asyncio
async def test_qsize_empty_full_methods(task_queue: AsyncTaskQueue[str]):
    """Test qsize, empty, and full methods."""
    assert task_queue.qsize() == 0
    assert task_queue.empty()
    assert not task_queue.full() # Infinite size queue is never full

    await task_queue.submit_task("task1")
    assert task_queue.qsize() == 1
    assert not task_queue.empty()
    assert not task_queue.full()

    await task_queue.get_task()
    task_queue.task_done()
    assert task_queue.qsize() == 0
    assert task_queue.empty()

@pytest.mark.asyncio
async def test_queue_with_maxsize(mocker):
    """Test queue behavior with a maxsize."""
    queue_max_size = AsyncTaskQueue[int](maxsize=1)
    assert not queue_max_size.full()
    await queue_max_size.submit_task(1)
    assert queue_max_size.full()

    # Test that submitting to a full queue blocks (or would raise if not awaited carefully)
    submit_block_task = asyncio.create_task(queue_max_size.submit_task(2))
    await asyncio.sleep(0.01) # Give it a chance to block
    assert not submit_block_task.done() # It should be blocked

    item = await queue_max_size.get_task()
    assert item == 1
    queue_max_size.task_done()

    await asyncio.wait_for(submit_block_task, timeout=0.1) # Now it should complete
    assert submit_block_task.done()
    assert not queue_max_size.empty()
    assert queue_max_size.full() # Item 2 is now in

    item2 = await queue_max_size.get_task()
    assert item2 == 2
    queue_max_size.task_done()
    assert queue_max_size.empty()