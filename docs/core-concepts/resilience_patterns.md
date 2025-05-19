# Resilience Patterns

This document explains the resilience patterns implemented in Khive, focusing on
the Circuit Breaker and Retry patterns that enhance the reliability of API
operations.

## Overview

Khive's resilience patterns provide robust error handling mechanisms for
asynchronous operations, particularly when interacting with external services.
These patterns help prevent cascading failures, manage transient errors, and
ensure system stability even when external dependencies are unreliable.

The two primary resilience patterns implemented are:

1. **Circuit Breaker Pattern**: Prevents repeated calls to failing services,
   allowing them time to recover
2. **Retry Pattern**: Handles transient failures by automatically retrying
   operations with exponential backoff

These patterns can be used independently or combined for comprehensive
resilience.

## Circuit Breaker Pattern

### Purpose

The Circuit Breaker pattern prevents a system from repeatedly trying to execute
an operation that's likely to fail, allowing the failing service time to recover
and preventing cascading failures throughout the system.

### How It Works

The Circuit Breaker operates like an electrical circuit breaker, with three
states:

1. **CLOSED**: Normal operation, requests pass through
2. **OPEN**: Failing state, requests are immediately rejected
3. **HALF_OPEN**: Recovery testing state, limited requests are allowed through
   to test if the service has recovered

![Circuit Breaker State Diagram](https://miro.medium.com/max/1400/1*CjNXJ1hBpbJTD-5_Fw75cA.png)

### Implementation

Khive implements the Circuit Breaker pattern in the `CircuitBreaker` class in
`src/khive/clients/resilience.py`:

````python
class CircuitBreaker:
    """
    Circuit breaker pattern implementation for preventing calls to failing services.

    The circuit breaker pattern prevents repeated calls to a failing service,
    based on the principle of "fail fast" for better system resilience. When
    a service fails repeatedly, the circuit opens and rejects requests for a
    period of time, then transitions to a half-open state to test if the
    service has recovered.

    Example:
        ```python
        # Create a circuit breaker with a failure threshold of 5
        # and a recovery time of 30 seconds
        breaker = CircuitBreaker(failure_threshold=5, recovery_time=30.0)

        # Execute a function with circuit breaker protection
        try:
            result = await breaker.execute(my_async_function, arg1, arg2, kwarg1=value1)
        except CircuitBreakerOpenError:
            # Handle the case where the circuit is open
            with contextlib.suppress(Exception):
                # Alternative approach using contextlib.suppress
                pass
        ```
    """
````

### Key Features

- **Failure Threshold**: Configurable number of failures before opening the
  circuit
- **Recovery Time**: Configurable time period before attempting recovery
- **Half-Open State Management**: Controls the number of test requests allowed
  in half-open state
- **Excluded Exceptions**: Ability to specify exceptions that should not count
  as failures
- **Metrics Tracking**: Tracks success, failure, and rejection counts for
  monitoring
- **Decorator Support**: Easy application to any async function using the
  `@circuit_breaker()` decorator

### Usage Examples

#### Basic Usage

```python
# Create a circuit breaker
breaker = CircuitBreaker(
    failure_threshold=5,  # Open after 5 failures
    recovery_time=30.0,   # Wait 30 seconds before recovery attempt
    half_open_max_calls=1 # Allow 1 test call in half-open state
)

# Execute a function with circuit breaker protection
try:
    result = await breaker.execute(api_client.get, "/endpoint")
except CircuitBreakerOpenError:
    # Handle the case where the circuit is open
    result = get_cached_result()  # Fallback strategy
```

#### Using the Decorator

```python
from khive.clients.resilience import circuit_breaker

@circuit_breaker(failure_threshold=3, recovery_time=10.0)
async def call_external_service(service_id):
    # This function is now protected by a circuit breaker
    return await api_client.get(f"/services/{service_id}")

# Use the protected function
try:
    result = await call_external_service("service-123")
except CircuitBreakerOpenError:
    # Handle the case where the circuit is open
    result = get_cached_result()  # Fallback strategy
```

## Retry Pattern

### Purpose

The Retry pattern enables an application to handle transient failures when
connecting to a service or network resource by transparently retrying the
operation with an exponential backoff strategy.

### How It Works

When an operation fails, the retry mechanism:

1. Waits for a short delay
2. Retries the operation
3. If it fails again, increases the delay (exponential backoff)
4. Continues this process until either:
   - The operation succeeds
   - The maximum number of retries is reached
   - A non-retryable error occurs

### Implementation

Khive implements the Retry pattern in the `retry_with_backoff` function in
`src/khive/clients/resilience.py`:

```python
async def retry_with_backoff(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    retry_exceptions: tuple[type[Exception], ...] = (Exception,),
    exclude_exceptions: tuple[type[Exception], ...] = (),
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    jitter_factor: float = 0.2,
    **kwargs: Any,
) -> T:
    """
    Retry an async function with exponential backoff.

    Args:
        func: The async function to retry.
        *args: Positional arguments for the function.
        retry_exceptions: Tuple of exception types to retry.
        exclude_exceptions: Tuple of exception types to not retry.
        max_retries: Maximum number of retries.
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay between retries in seconds.
        backoff_factor: Factor to increase delay with each retry.
        jitter: Whether to add randomness to the delay.
        jitter_factor: How much randomness to add as a percentage.
        **kwargs: Keyword arguments for the function.

    Returns:
        The result of the function execution.

    Raises:
        Exception: The last exception raised by the function after all retries.
    """
```

### Key Features

- **Configurable Retry Count**: Set the maximum number of retry attempts
- **Exponential Backoff**: Delay increases exponentially with each retry
- **Maximum Delay Cap**: Prevents excessive wait times
- **Jitter Support**: Adds randomness to prevent thundering herd problems
- **Exception Filtering**: Specify which exceptions should trigger retries and
  which should not
- **Decorator Support**: Easy application to any async function using the
  `@with_retry()` decorator

### Usage Examples

#### Basic Usage

```python
# Retry a function with default settings (3 retries, 1s initial delay)
result = await retry_with_backoff(api_client.get, "/endpoint")

# Retry with custom settings
result = await retry_with_backoff(
    api_client.get,
    "/endpoint",
    retry_exceptions=(ConnectionError, TimeoutError),  # Only retry these exceptions
    exclude_exceptions=(AuthenticationError,),         # Never retry these
    max_retries=5,                                     # Try up to 5 times
    base_delay=0.5,                                    # Start with 0.5s delay
    max_delay=30.0,                                    # Never wait more than 30s
    backoff_factor=3.0                                 # Triple the delay each time
)
```

#### Using the Decorator

```python
from khive.clients.resilience import with_retry

@with_retry(
    max_retries=5,
    base_delay=0.5,
    retry_exceptions=(ConnectionError, TimeoutError)
)
async def call_external_service(service_id):
    # This function will automatically retry on ConnectionError or TimeoutError
    return await api_client.get(f"/services/{service_id}")

# Use the retry-enabled function
result = await call_external_service("service-123")
```

#### Using RetryConfig

For reusable retry configurations, use the `RetryConfig` class:

```python
from khive.clients.resilience import RetryConfig, retry_with_backoff

# Create a reusable configuration
http_retry_config = RetryConfig(
    max_retries=3,
    base_delay=0.5,
    retry_exceptions=(ConnectionError, TimeoutError, httpx.HTTPError)
)

# Use the configuration
result = await retry_with_backoff(
    api_client.get,
    "/endpoint",
    **http_retry_config.as_kwargs()
)
```

## Combining Resilience Patterns

### Integration with AsyncAPIClient

The `AsyncAPIClient` class integrates both resilience patterns:

```python
# Create a client with both circuit breaker and retry
client = AsyncAPIClient(
    base_url="https://api.example.com",
    circuit_breaker=CircuitBreaker(failure_threshold=5, recovery_time=30.0),
    retry_config=RetryConfig(max_retries=3, base_delay=1.0)
)

# Make a request with both patterns applied
try:
    result = await client.get("/endpoint")
except CircuitBreakerOpenError:
    # Handle circuit breaker open
    result = get_cached_result()
except Exception as e:
    # Handle other exceptions after retries are exhausted
    logger.error(f"Request failed after retries: {e}")
    result = get_default_result()
```

### Integration with Endpoint

The `Endpoint` class also integrates both resilience patterns:

```python
# Create an endpoint with both circuit breaker and retry
endpoint = Endpoint(
    config=endpoint_config,
    circuit_breaker=CircuitBreaker(failure_threshold=5, recovery_time=30.0),
    retry_config=RetryConfig(max_retries=3, base_delay=1.0)
)

# Make a call with both patterns applied
try:
    result = await endpoint.call(request)
except CircuitBreakerOpenError:
    # Handle circuit breaker open
    result = get_cached_result()
except Exception as e:
    # Handle other exceptions after retries are exhausted
    logger.error(f"Call failed after retries: {e}")
    result = get_default_result()
```

## Best Practices

1. **Configure Appropriately**: Set failure thresholds, retry counts, and delays
   based on the specific service characteristics

2. **Use Jitter**: Always enable jitter for retries to prevent thundering herd
   problems

3. **Set Reasonable Timeouts**: Ensure operations have appropriate timeouts to
   prevent long-running operations

4. **Implement Fallback Strategies**: Always have a fallback strategy when the
   circuit is open

5. **Monitor Circuit State**: Track and alert on circuit state changes to
   identify problematic services

6. **Exclude Non-Retryable Errors**: Configure retry mechanisms to not retry
   errors that won't be resolved by retrying (e.g., authentication errors)

7. **Combine with Caching**: Use caching as a fallback strategy when the circuit
   is open

8. **Log Retry Attempts**: Log retry attempts and circuit state changes for
   debugging

## Conclusion

The resilience patterns implemented in Khive provide robust error handling
mechanisms for asynchronous operations. By using the Circuit Breaker and Retry
patterns, applications can gracefully handle transient failures, prevent
cascading failures, and ensure system stability even when external dependencies
are unreliable.

| These patterns are particularly valuable in distributed systems where network
| calls and external service dependencies are common. By properly configuring
and | combining these patterns, Khive applications can achieve high reliability
and | fault tolerance.

## Related Documentation

- [Async Resource Management](async_resource_management.md): Documentation on
  the standardized async resource cleanup patterns implemented in Khive.
- [Bounded Async Queue with Backpressure](async_queue.md): Documentation on the
  queue-based backpressure mechanism that complements resilience patterns by
  preventing system overload.
