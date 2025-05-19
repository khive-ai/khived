# Async Resource Management

This document explains the standardized async resource cleanup patterns
implemented in Khive, focusing on the `AsyncResourceManager` protocol and its
implementations.

## Overview

Khive's async resource management system provides a consistent pattern for
managing asynchronous resources, ensuring proper initialization and cleanup.
This is particularly important for components that interact with external
services, manage connections, or allocate resources that need to be released
when no longer needed.

The system is built around the `AsyncResourceManager` protocol, which defines a
standard interface for components that need to manage async resources with
context managers.

## AsyncResourceManager Protocol

The `AsyncResourceManager` protocol is defined in
`src/khive/clients/protocols.py` and serves as the foundation for async resource
management in Khive:

```python
class AsyncResourceManager(Protocol):
    """Protocol for components that manage async resources with context managers."""

    async def __aenter__(self) -> "AsyncResourceManager":
        """
        Enter the async context manager.

        Returns:
            The resource manager instance.
        """
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the async context manager and release resources.

        Args:
            exc_type: The exception type, if an exception was raised.
            exc_val: The exception value, if an exception was raised.
            exc_tb: The exception traceback, if an exception was raised.
        """
        ...
```

This protocol defines the standard async context manager methods that
implementing classes must provide:

- `__aenter__`: Initializes resources and returns the manager instance
- `__aexit__`: Releases resources, handling any exceptions that occurred

## Protocol Extensions

The `AsyncResourceManager` protocol is extended by other protocols to provide
more specific functionality:

### ResourceClient Protocol

The `ResourceClient` protocol extends `AsyncResourceManager` to define a
standard interface for clients that interact with external APIs:

```python
class ResourceClient(AsyncResourceManager, Protocol):
    """Protocol for resource clients that interact with external APIs."""

    async def call(self, request: Any, **kwargs) -> Any:
        """
        Make a call to the external resource.

        Args:
            request: The request to send to the external resource.
            **kwargs: Additional keyword arguments for the request.

        Returns:
            The response from the external resource.
        """
        ...

    async def close(self) -> None:
        """Close the client and release any resources."""
        ...
```

### Executor Protocol

The `Executor` protocol extends `AsyncResourceManager` to define a standard
interface for components that manage concurrent operations:

```python
class Executor(AsyncResourceManager, Protocol):
    """Protocol for executors that manage concurrent operations."""

    async def execute(
        self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
    ) -> T:
        """
        Execute a coroutine with concurrency control.

        Args:
            func: The coroutine function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            The result of the function execution.
        """
        ...

    async def shutdown(self, timeout: float | None = None) -> None:
        """
        Shut down the executor and wait for active tasks to complete.

        Args:
            timeout: Maximum time to wait for tasks to complete.
                If None, wait indefinitely.
        """
        ...
```

## Key Implementations

### Endpoint Class

The `Endpoint` class in `src/khive/connections/endpoint.py` implements the
`AsyncResourceManager` protocol to manage connections to external APIs:

```python
class Endpoint:
    # ... initialization and other methods ...

    async def __aenter__(self):
        """
        Enter the async context manager and initialize the client.

        Returns:
            The Endpoint instance with an initialized client.
        """
        self.client = self._create_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Close the client when exiting the context manager.

        This method ensures proper resource cleanup for both HTTP and SDK clients.
        It handles exceptions gracefully to ensure resources are always released.

        Args:
            exc_type: The exception type, if an exception was raised.
            exc_val: The exception value, if an exception was raised.
            exc_tb: The exception traceback, if an exception was raised.
        """
        await self._close_client()

    async def _close_client(self):
        """
        Internal method to close the client and release resources.

        This method handles different client types and ensures proper cleanup
        in all cases, including error scenarios.
        """
        if self.client is None:
            return

        try:
            if self.config.transport_type == "http":
                await self.client.close()
            elif self.config.transport_type == "sdk" and hasattr(self.client, "close"):
                # Some SDK clients might have a close method
                if asyncio.iscoroutinefunction(self.client.close):
                    await self.client.close()
                else:
                    self.client.close()
        except Exception as e:
            # Log the error but don't re-raise to ensure cleanup continues
            logger.warning(
                "Error closing client",
                extra={
                    "error": str(e),
                    "client_type": self.config.transport_type,
                    "endpoint": self.config.endpoint,
                    "provider": self.config.provider,
                },
            )
        finally:
            # Always clear the client reference
            self.client = None
```

The `Endpoint` class provides a robust implementation of the async context
manager pattern, with these key features:

1. **Client Initialization**: Creates the appropriate client type (HTTP or SDK)
   when entering the context
2. **Resource Cleanup**: Properly closes the client when exiting the context
3. **Error Handling**: Catches and logs exceptions during cleanup to ensure
   resources are always released
4. **Reference Clearing**: Sets the client reference to `None` after cleanup to
   prevent resource leaks

### AsyncExecutor Class

The `AsyncExecutor` class in `src/khive/clients/executor.py` implements the
`AsyncResourceManager` protocol to manage concurrent operations:

```python
class AsyncExecutor:
    # ... initialization and other methods ...

    async def __aenter__(self) -> "AsyncExecutor":
        """
        Enter the async context manager.

        Returns:
            The executor instance.
        """
        logger.debug("Entering AsyncExecutor context")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the async context manager and release resources.

        Args:
            exc_type: The exception type, if an exception was raised.
            exc_val: The exception value, if an exception was raised.
            exc_tb: The exception traceback, if an exception was raised.
        """
        logger.debug("Exiting AsyncExecutor context")
        await self.shutdown()

    async def shutdown(self, timeout: float | None = None) -> None:
        """
        Wait for active tasks to complete and shut down the executor.

        Args:
            timeout: Maximum time to wait for tasks to complete.
                If None, wait indefinitely.
        """
        async with self._lock:
            active_tasks = list(self._active_tasks.keys())
            logger.debug(f"Shutting down with {len(active_tasks)} active tasks")

        if active_tasks:
            if timeout is not None:
                logger.debug(f"Waiting up to {timeout}s for tasks to complete")
                done, pending = await asyncio.wait(active_tasks, timeout=timeout)

                if pending:
                    logger.warning(
                        f"Timeout reached, cancelling {len(pending)} pending tasks"
                    )
                    for task in pending:
                        task.cancel()

                    # Wait for cancelled tasks to complete
                    await asyncio.gather(*pending, return_exceptions=True)
            else:
                logger.debug("Waiting indefinitely for tasks to complete")
                await asyncio.gather(*active_tasks, return_exceptions=True)

        logger.debug("Executor shutdown complete")
```

The `AsyncExecutor` class provides a comprehensive implementation of the async
context manager pattern for task execution, with these key features:

1. **Task Tracking**: Keeps track of all active tasks
2. **Graceful Shutdown**: Waits for active tasks to complete when exiting the
   context
3. **Timeout Support**: Allows specifying a maximum wait time for tasks to
   complete
4. **Task Cancellation**: Cancels pending tasks if a timeout is reached
5. **Comprehensive Logging**: Logs all key events for debugging

### RateLimitedExecutor Class

The `RateLimitedExecutor` class in `src/khive/clients/executor.py` combines rate
limiting and concurrency control, also implementing the `AsyncResourceManager`
protocol:

```python
class RateLimitedExecutor:
    # ... initialization and other methods ...

    async def __aenter__(self) -> "RateLimitedExecutor":
        """
        Enter the async context manager.

        Returns:
            The executor instance.
        """
        logger.debug("Entering RateLimitedExecutor context")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the async context manager and release resources.

        Args:
            exc_type: The exception type, if an exception was raised.
            exc_val: The exception value, if an exception was raised.
            exc_tb: The exception traceback, if an exception was raised.
        """
        logger.debug("Exiting RateLimitedExecutor context")
        await self.shutdown()

    async def shutdown(self, timeout: float | None = None) -> None:
        """
        Shut down the executor.

        Args:
            timeout: Maximum time to wait for tasks to complete.
                If None, wait indefinitely.
        """
        logger.debug("Shutting down rate-limited executor")
        await self.executor.shutdown(timeout=timeout)
```

The `RateLimitedExecutor` delegates most of its resource management to the
underlying `AsyncExecutor`, providing a clean composition pattern.

## Usage Patterns

### Basic Usage with Context Manager

The recommended way to use async resource managers is with the async context
manager pattern:

```python
async def example():
    # Using Endpoint with context manager
    async with Endpoint(config) as endpoint:
        response = await endpoint.call(request)
        # Resources automatically cleaned up when exiting the context

    # Using AsyncExecutor with context manager
    async with AsyncExecutor(max_concurrency=10) as executor:
        result = await executor.execute(my_async_function, arg1, arg2)
        # Tasks properly shut down when exiting the context

    # Using RateLimitedExecutor with context manager
    async with RateLimitedExecutor(rate=10, period=1.0, max_concurrency=5) as executor:
        result = await executor.execute(my_async_function, arg1, arg2)
        # Rate limiting and concurrency control with proper cleanup
```

### Manual Resource Management

While the context manager pattern is recommended, you can also manage resources
manually:

```python
async def example():
    # Manual resource management for Endpoint
    endpoint = Endpoint(config)
    try:
        response = await endpoint.call(request)
    finally:
        await endpoint.aclose()

    # Manual resource management for AsyncExecutor
    executor = AsyncExecutor(max_concurrency=10)
    try:
        result = await executor.execute(my_async_function, arg1, arg2)
    finally:
        await executor.shutdown()
```

### Nested Context Managers

Async resource managers can be nested to create complex resource management
patterns:

```python
async def example():
    async with AsyncExecutor(max_concurrency=10) as executor:
        async with Endpoint(config) as endpoint:
            # Use both resources together
            result = await executor.execute(endpoint.call, request)
```

## Best Practices

1. **Always Use Context Managers**: Prefer the async context manager pattern
   (`async with`) over manual resource management to ensure proper cleanup.

2. **Handle Exceptions During Cleanup**: Catch and log exceptions during
   resource cleanup to ensure resources are always released, even in error
   scenarios.

3. **Clear References**: Set resource references to `None` after cleanup to
   prevent resource leaks.

4. **Use Timeouts**: Specify timeouts when waiting for tasks to complete to
   prevent indefinite blocking.

5. **Log Resource Lifecycle Events**: Log key events in the resource lifecycle
   (creation, initialization, cleanup) for debugging.

6. **Implement Both `__aenter__` and `__aexit__`**: Always implement both
   methods of the async context manager protocol.

7. **Delegate to Specialized Methods**: Implement specialized methods for
   resource initialization and cleanup, and call them from the context manager
   methods.

## Conclusion

The standardized async resource management system in Khive provides a consistent
pattern for managing asynchronous resources, ensuring proper initialization and
cleanup. By following the `AsyncResourceManager` protocol and its extensions,
components can ensure reliable resource management, even in complex scenarios
with multiple resources and error conditions.

This system is particularly important for components that interact with external
| services, manage connections, or allocate resources that need to be released |
when no longer needed, helping to prevent resource leaks and ensure efficient |
resource utilization.

## Related Documentation

- [Bounded Async Queue with Backpressure](async_queue.md): Documentation on the
  `BoundedQueue` and `WorkQueue` classes that implement the
  `AsyncResourceManager` protocol for queue-based resource management.
- [Resilience Patterns](resilience_patterns.md): Documentation on the Circuit
  Breaker and Retry patterns that enhance the reliability of API operations.
