# Bounded Async Queue with Backpressure

This document explains the bounded async queue implementation in Khive, focusing
on the `BoundedQueue` and `WorkQueue` classes that provide backpressure and
worker management for API requests.

## Overview

Khive's bounded async queue system provides a robust mechanism for managing
asynchronous API requests with proper backpressure and worker management. This
is particularly important for applications that interact with rate-limited
external services, where controlling the flow of requests is essential to
prevent overwhelming these services and to ensure system stability.

The queue system is built around two main classes:

- `BoundedQueue`: Core implementation with backpressure and worker management
- `WorkQueue`: High-level wrapper with additional functionality

These components integrate with the existing executor framework to provide a
comprehensive solution for managing API requests.

## Key Features

- **Bounded Queue Size**: Limits the number of pending requests to prevent
  memory exhaustion
- **Backpressure Mechanism**: Applies backpressure when the queue is full to
  prevent overwhelming the system
- **Worker Management**: Manages worker tasks that process queue items
- **Lifecycle Control**: Provides clear lifecycle management (starting,
  processing, stopping)
- **Error Handling**: Gracefully handles errors without crashing the system
- **Metrics Tracking**: Collects metrics on queue operations for monitoring
- **Async Context Manager Support**: Implements the `AsyncResourceManager`
  protocol

## BoundedQueue Class

The `BoundedQueue` class is the core implementation of the bounded async queue
with backpressure. It wraps the standard `asyncio.Queue` with additional
functionality for worker management, backpressure, and lifecycle control.

### Queue Status States

The queue can be in one of the following states, defined by the `QueueStatus`
enum:

```python
class QueueStatus(str, Enum):
    """Possible states of the queue."""
    IDLE = "idle"         # Initial state, not processing
    PROCESSING = "processing"  # Normal operation, processing items
    STOPPING = "stopping"      # In the process of stopping
    STOPPED = "stopped"        # Fully stopped
```

### Initialization

```python
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
```

### Key Methods

#### Put Operation with Backpressure

```python
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
    """
```

The `put` method implements backpressure by using `asyncio.wait_for` with a
timeout. If the queue is full and the timeout is reached, it returns `False` to
indicate that backpressure was applied, allowing the caller to handle this
situation appropriately.

#### Worker Management

```python
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
    """
```

The `start_workers` method creates a specified number of worker tasks that
process items from the queue. Each worker runs in a loop, getting items from the
queue and processing them with the provided worker function. If an error occurs
during processing, it can be handled by an optional error handler.

#### Lifecycle Management

```python
async def start(self) -> None:
    """Start the queue for processing."""

async def stop(self, timeout: float | None = None) -> None:
    """
    Stop the queue and all worker tasks.

    Args:
        timeout: Maximum time to wait for pending tasks
    """
```

The `start` and `stop` methods manage the queue lifecycle, ensuring proper
initialization and cleanup of resources. The `stop` method gracefully shuts down
worker tasks, waiting for them to complete or cancelling them after a timeout.

#### Async Context Manager Support

```python
async def __aenter__(self) -> "BoundedQueue[T]":
    """Enter async context."""
    await self.start()
    return self

async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
    """Exit async context."""
    await self.stop()
```

The `BoundedQueue` implements the async context manager protocol, allowing it to
be used with the `async with` statement for automatic resource management.

### Metrics

The `BoundedQueue` tracks the following metrics:

- `enqueued`: Number of items successfully added to the queue
- `processed`: Number of items processed by workers
- `errors`: Number of errors encountered during processing
- `backpressure_events`: Number of times backpressure was applied

These metrics can be accessed through the `metrics` property:

```python
@property
def metrics(self) -> dict[str, int]:
    """Get queue metrics."""
    return self._metrics.copy()
```

## WorkQueue Class

The `WorkQueue` class is a high-level wrapper around `BoundedQueue` that
provides additional functionality and a simplified interface.

### Initialization

```python
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
```

### Key Methods

#### Process Method

```python
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
```

The `process` method starts worker tasks to process queue items. If
`num_workers` is not specified, it uses the `concurrency_limit` provided during
initialization.

#### Batch Processing

```python
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
```

The `batch_process` method provides a convenient way to process a list of items
through the queue. It starts the queue, processes all items, and then stops the
queue when done.

## QueueConfig Class

The `QueueConfig` class provides a standardized way to configure queue
parameters using Pydantic for validation.

```python
class QueueConfig(BaseModel):
    """Configuration options for work queues."""

    queue_capacity: int = 100
    capacity_refresh_time: float = 1.0
    concurrency_limit: int | None = None
```

The class includes validators to ensure that:

- `queue_capacity` is at least 1
- `capacity_refresh_time` is positive
- `concurrency_limit` is at least 1 if provided

## Queue-Related Exceptions

The queue implementation defines several specific exception types in
`src/khive/clients/errors.py`:

```python
class QueueError(APIClientError):
    """Base exception for all queue-related errors."""

class QueueFullError(QueueError):
    """Exception raised when a queue is full and cannot accept more items."""

class QueueEmptyError(QueueError):
    """Exception raised when trying to get an item from an empty queue."""

class QueueStateError(QueueError):
    """Exception raised when queue operations are attempted in invalid states."""
```

These exceptions provide clear error messages and include relevant context
information, such as the current queue state or size.

## Integration with Executor

The queue system integrates with the existing executor framework to provide a
comprehensive solution for managing API requests. The `AsyncExecutor` class can
be used in conjunction with the queue to control concurrency:

```python
# Example: Using WorkQueue with AsyncExecutor
async def example():
    # Create an executor with concurrency control
    executor = AsyncExecutor(max_concurrency=10)

    # Create a work queue with the same concurrency limit
    queue = WorkQueue(maxsize=100, concurrency_limit=10)

    # Define a worker function that uses the executor
    async def worker(item):
        return await executor.execute(process_item, item)

    # Use both components together
    async with executor:
        async with queue:
            await queue.process(worker)

            # Add items to the queue
            for item in items:
                await queue.put(item)

            # Wait for all items to be processed
            await queue.join()
```

## Usage Patterns

### Basic Usage with Context Manager

The recommended way to use the queue is with the async context manager pattern:

```python
async def example():
    # Using BoundedQueue with context manager
    async with BoundedQueue(maxsize=100) as queue:
        # Start workers
        await queue.start_workers(worker_func, num_workers=5)

        # Add items to the queue
        await queue.put(item)

        # Wait for all items to be processed
        await queue.join()

    # Using WorkQueue with context manager
    async with WorkQueue(maxsize=100, concurrency_limit=5) as queue:
        # Process items with a worker function
        await queue.process(worker_func)

        # Add items to the queue
        await queue.put(item)

        # Wait for all items to be processed
        await queue.join()
```

### Batch Processing

For processing a batch of items, use the `batch_process` method:

```python
async def example():
    # Create a work queue
    queue = WorkQueue(maxsize=100, concurrency_limit=5)

    # Process a batch of items
    items = [item1, item2, item3, ...]
    await queue.batch_process(items, worker_func)
```

### Handling Backpressure

When the queue is full, the `put` method applies backpressure by returning
`False`. You can handle this situation by retrying after a delay:

```python
async def example():
    # Create a queue
    queue = WorkQueue(maxsize=10)

    # Start the queue
    await queue.start()
    await queue.process(worker_func)

    # Add items with backpressure handling
    while True:
        if await queue.put(item):
            break  # Item was added successfully
        # Backpressure applied, wait and retry
        await asyncio.sleep(0.1)
```

### Error Handling

You can provide an error handler to handle exceptions that occur during
processing:

```python
async def example():
    # Define an error handler
    async def error_handler(error, item):
        logger.error(f"Error processing item {item}: {error}")
        # Optionally retry or store the item for later processing

    # Create a queue with error handling
    queue = WorkQueue(maxsize=100)

    # Start processing with error handler
    await queue.start()
    await queue.process(worker_func, error_handler=error_handler)
```

## Best Practices

1. **Use Context Managers**: Always use the async context manager pattern
   (`async with`) to ensure proper resource cleanup.

2. **Set Appropriate Queue Size**: Choose a queue size that balances memory
   usage with the need to buffer requests. Too small a queue can limit
   throughput, while too large a queue can consume excessive memory.

3. **Handle Backpressure**: Always check the return value of the `put` method
   and implement appropriate backpressure handling.

4. **Provide Error Handlers**: Use error handlers to gracefully handle
   exceptions during processing.

5. **Monitor Queue Metrics**: Track queue metrics to identify potential issues,
   such as frequent backpressure events or high error rates.

6. **Set Reasonable Timeouts**: Configure appropriate timeouts for queue
   operations to prevent indefinite blocking.

7. **Clean Up Resources**: Always call `stop()` when done with the queue to
   ensure proper resource cleanup.

8. **Use Batch Processing**: For processing a known set of items, use the
   `batch_process` method for simplified handling.

## Conclusion

The bounded async queue implementation in Khive provides a robust solution for
managing asynchronous API requests with proper backpressure and worker
management. By using the `BoundedQueue` and `WorkQueue` classes, applications
can control the flow of requests to external services, prevent overwhelming
these services, and ensure system stability even under high load.

This implementation is particularly valuable in distributed systems where API
rate limits and resource constraints are common. By properly configuring and
using the queue system, Khive applications can achieve high throughput while
maintaining reliability and preventing resource exhaustion.
